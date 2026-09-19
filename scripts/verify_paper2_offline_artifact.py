"""Verify a packaged P2 record and recompute its main empirical analyses.

Standard library only. Uses saved assistant labels; does not independently
adjudicate answers, run a neural model, or reexecute native MCP mutations.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def relative(name):
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name or not p.parts:
        raise ValueError('Unsafe artifact member')
    return Path(*p.parts)


def extract(archive):
    dest = archive.with_suffix('')
    with ZipFile(archive) as z:
        names = z.namelist()
        assert len(names) == len(set(names)) and z.testzip() is None
        for info in z.infolist():
            path = dest / relative(info.filename)
            assert path.resolve().is_relative_to(dest.resolve())
            assert ((info.external_attr >> 16) & 0o170000) != 0o120000
            if info.is_dir():
                path.mkdir(parents=True, exist_ok=True)
                continue
            value = z.read(info)
            if path.exists():
                assert path.read_bytes() == value, 'Existing extraction differs'
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open('xb') as stream:
                    stream.write(value)
    return dest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True, help='New directory for derived reports')
    args = parser.parse_args()
    os.chdir(ROOT)
    manifest = load(ROOT / 'paper2-artifact-manifest.json')
    assert manifest['format'] == 'paper2-offline-v1'
    members = manifest['files']
    assert len(members) == len({r['path'] for r in members})
    for row in members:
        path = ROOT / relative(row['path'])
        assert path.resolve().is_relative_to(ROOT)
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], row['path']
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    roots, inventory = {}, []
    for component in manifest['model_archives']:
        archive = ROOT / relative(component['path'])
        dest = extract(archive)
        root = dest / 'runs' / component['batch']
        cases = sorted(p for p in root.rglob('case-*.json') if re.fullmatch(r'case-\d{3}\.json', p.name))
        assert len(cases) == component['episodes']
        grid = load(root / 'grid_manifest.json')
        assert grid['status'] == 'complete' and all(w['exit_code'] == 0 for w in grid['workers'])
        roots[component['key']] = root
        inventory.append({'batch': component['batch'], 'episodes': len(cases),
                          'zero_exit_workers': len(grid['workers']),
                          'terminations': dict(Counter(load(p)['termination'] for p in cases))})
    assert sum(r['episodes'] for r in inventory) == 1328
    ev = ROOT / 'research/evidence'
    checks = []

    def run(label, script, arguments, expected=None, fields=None, ignore=()):
        output = out / (label+'.json')
        command = [sys.executable, '-I', str(ROOT/'scripts'/script), *map(str, arguments)]
        if expected:
            command += ['--output', str(output)]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=180)
        (out/(label+'.stdout')).write_bytes(result.stdout)
        (out/(label+'.stderr')).write_bytes(result.stderr)
        assert result.returncode == 0, f'{label} failed; inspect its stderr'
        if expected:
            a, b = load(output), load(ev/expected)
            if label == 'strict':
                # The original strict report predates sequential-executor
                # fields. Require their exact neutral values before adapting
                # that documented schema, without dropping any old field.
                assert 'call_policy' not in b and a['call_policy'] == 'single'
                b['call_policy'] = 'single'
                for field in ('rows', 'groups'):
                    assert len(a[field]) == len(b[field])
                    for new, old in zip(a[field], b[field]):
                        assert 'tool_budget_rejections' not in old
                        assert new['tool_budget_rejections'] == 0
                        old['tool_budget_rejections'] = 0
            if label == 'capacity':
                grid = load(roots['capacity']/'grid_manifest.json')
                added = dict(closed_domain=None, closed_domain_complete=False,
                             audited_episodes=120,
                             scope_wall_seconds=max(w['finished'] for w in grid['workers']) -
                                                min(w['started'] for w in grid['workers']))
                for key, value in added.items():
                    assert key not in b and a[key] == value
                b.update(added)
            if label == 'capacity_answers':
                for key, value in {'review_scope': 'full_registered_grid', 'complete_batch': True}.items():
                    assert key not in b and a[key] == value
                    b[key] = value
            if fields:
                a, b = ({k: v[k] for k in fields} for v in (a, b))
            else:
                for k in ignore:
                    a.pop(k, None); b.pop(k, None)
            assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True), f'{label} differs'
        checks.append({'check': label, 'exit_code': 0, 'matches_retained_report': bool(expected),
                       'compared_fields': fields or 'all except named provenance fields',
                       'excluded_provenance_fields': list(ignore)})

    run('initial', 'summarize_vakra_native.py', ['--root', roots['initial']],
        'vakra_native_first4_v1_summary.json', ['groups', 'rows', 'input_sha256'])
    run('development', 'analyze_vakra_coverage_control.py', ['--root', roots['development']],
        'vakra_coverage12_v1_summary.json', ['groups', 'rows', 'input_sha256'])
    run('development_answers', 'summarize_vakra_semantic_audit.py', ['--root', roots['development']],
        'vakra_coverage12_v1_answer_audit_summary.json')
    for key, prefix, policy in [('strict', 'vakra_crossdomain_v1', 'single'),
                                ('sequential', 'vakra_permissive_v1', 'sequential')]:
        run(key, 'analyze_vakra_crossdomain.py', ['--root', roots[key], '--call-policy', policy],
            prefix+'_execution_summary.json')
        run(key+'_answers', 'summarize_vakra_crossdomain_answers.py',
            ['--root', roots[key], '--summary', ev/(prefix+'_execution_summary.json'),
             '--annotations', ev/(prefix+'_answer_annotations.json')], prefix+'_answer_summary.json')
    run('executor_pairing', 'compare_vakra_executors.py',
        ['--strict-root', roots['strict'], '--permissive-root', roots['sequential'],
         '--strict-summary', ev/'vakra_crossdomain_v1_execution_summary.json',
         '--permissive-summary', ev/'vakra_permissive_v1_execution_summary.json'],
        'vakra_executor_pairing_v1.json')
    run('smollm3', 'analyze_vakra_smollm3.py', ['--root', roots['smollm3']],
        'vakra_smollm3_v1_execution_summary.json')
    run('smollm3_answers', 'summarize_vakra_smollm3.py', [], 'vakra_smollm3_v1_answer_summary.json')
    for key, archive, prefix, annotations in [
        ('capacity', 'vakra-qwen30b-v1.zip', 'vakra_qwen30b_complete_grid_v1', 'vakra_qwen30b_answer_annotations_v1'),
        ('expansion', 'vakra-expansion-v2.zip', 'vakra_expansion_complete_grid_v1', 'vakra_expansion_complete_annotations_v1')]:
        run(key, 'analyze_vakra_registered_grid.py',
            ['--root', roots[key], '--archive', ROOT/'results/deploy'/archive, '--kind', key], prefix+'.json',
            ignore=('analysis_source_sha256',))
        expected = 'vakra_qwen30b_answer_summary_v1.json' if key == 'capacity' else 'vakra_expansion_complete_answer_summary_v1.json'
        run(key+'_answers', 'summarize_vakra_registered_answers.py',
            ['--root', roots[key], '--summary', ev/(prefix+'.json'), '--annotations', ev/(annotations+'.json')],
            expected, ignore=('analysis_source_sha256',))
    run('output_budget', 'analyze_vakra_output_budget_complete_v1.py', [],
        'vakra_output_budget_complete_analysis_v1.json', ignore=('script_sha256',))
    run('expansion_uncertainty', 'analyze_expansion_complete_sensitivity_v1.py', [],
        'vakra_expansion_complete_sensitivity_v1.json', ignore=('script_sha256',))
    run('manuscript_tables', 'check_paper2_manuscript_tables.py', [])
    report = {'format': manifest['format'], 'verified_payload_files': len(members),
              'manifest_sha256': sha(ROOT/'paper2-artifact-manifest.json'),
              'model_execution_records': 1328, 'inventory': inventory, 'checks': checks,
              'limits': ['Saved assistant annotations are reused, not independently adjudicated.',
                         'No neural inference or native MCP mutation replay is performed by this verifier.',
                         'Native replay records, scripts and prepared databases are included for inspection.',
                         'Only named machine-local source-path and analysis-script fingerprints are excluded from report equality.',
                         'Hash agreement establishes provenance, not semantic truth or paper readiness.']}
    report['legacy_schema_adaptations'] = [{
        'report': 'vakra_crossdomain_v1_execution_summary.json',
        'added_neutral_fields': {'call_policy': 'single', 'rows_and_groups.tool_budget_rejections': 0},
        'guard': 'New values must match these constants; every retained old field is compared.'}, {
        'report': 'vakra_qwen30b_complete_grid_v1.json',
        'added_fields': {'closed_domain': None, 'closed_domain_complete': False, 'audited_episodes': 120,
                         'scope_wall_seconds': 'max worker finish minus min worker start from raw grid'},
        'guard': 'New values must match the fixed full-grid scope and raw worker timestamps.'}]
    report['legacy_schema_adaptations'].append({
        'report': 'vakra_qwen30b_answer_summary_v1.json',
        'added_fields': {'review_scope': 'full_registered_grid', 'complete_batch': True},
        'guard': 'New scope markers must match the verified complete 120-record batch.'})
    with (out/'report.json').open('x', encoding='utf-8') as f:
        json.dump(report, f, indent=2); f.write('\n')
    print(json.dumps({'verified_payload_files': len(members), 'model_execution_records': 1328,
                      'completed_checks': len(checks), 'report': str(out/'report.json')}))


if __name__ == '__main__':
    main()
