"""Audit a complete registered capacity/expansion grid before answer review.

The immutable deployment archive supplies selection, source and preparation
hashes. An execution summary is not an answer score or an official benchmark
result. Missing, failed and extra runs cause rejection, never silent filtering.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import zipfile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=True)


def audit(root, archive, kind):
    expected_archives = {
        'capacity': {'9d4bfabd959a02a0c72aca3fc054d7f028aa34403bcbbef391ecd147080b9d1f'},
        'expansion': {
            'f76dae6430ca433afad53b39b1c54e67d777802d2f95dbcb1c81c674180fbc61',
            # Registered infrastructure restart: only placement-log serialization
            # and separately recorded supervisor paths changed, no task outputs.
            'b254562e1969a6bff4299bee152777dc86d29f2489a93455956ef97766ef0961',
        },
    }[kind]
    expected_archive = sha(archive)
    assert expected_archive in expected_archives, 'Deployment archive changed'
    with zipfile.ZipFile(archive) as z:
        selection = json.loads(z.read('protocol/selection.json'))
        source_hashes = {Path(n).name: hashlib.sha256(z.read(n)).hexdigest()
                         for n in z.namelist() if n.startswith('autolab/')}
        prompt_hash = hashlib.sha256(z.read('upstream/agent_interface.py')).hexdigest()
        preparations = {}
        for d in selection['domains']:
            prefix = 'prepared/' + d['domain'] + '/'
            blob = z.read(prefix + 'preparation_manifest.json')
            assert hashlib.sha256(blob).hexdigest() == d['preparation_sha256']
            preparations[d['domain']] = json.loads(blob)
    gp = root / 'grid_manifest.json'
    grid = json.loads(gp.read_bytes())
    expected_n = 120 if kind == 'capacity' else 420
    assert grid['status'] == 'complete' and grid['registered_episodes'] == expected_n
    assert grid['selection'] == selection
    domains = {d['domain']: d for d in selection['domains']}
    models = ['qwen30b'] if kind == 'capacity' else ['qwen3', 'qwen25', 'qwen30b']
    arms = {(d, c, m) for d in domains for c in ('original', 'coverage_check') for m in models}
    worker_arms = {(w['domain'], w['condition'], w.get('model', 'qwen30b')) for w in grid['workers']}
    assert len(grid['workers']) == len(arms) and worker_arms == arms
    assert all(w['exit_code'] == 0 for w in grid['workers']), 'Failed worker'
    pinned = json.loads(Path('research/evidence/qwen30b_download_manifest.json').read_bytes())
    reference = {}
    if kind == 'expansion':
        prior = Path('results/remote/vakra-permissive-v1/runs/vakra-permissive-v1')
        for model in ('qwen3', 'qwen25'):
            p = prior / 'cars/original' / model / 'shard-0/manifest.json'
            reference[model] = {'manifest_sha256': sha(p), 'manifest': json.loads(p.read_bytes())}
    rows, manifests, episodes, hashes, observed_cases = [], {}, {}, {}, set()
    for domain, condition, model in sorted(arms):
        directory = (root / domain / 'sequential' / condition / 'shard-0' if kind == 'capacity'
                     else root / domain / condition / model / 'shard-0')
        mp = directory / 'manifest.json'
        m = json.loads(mp.read_bytes())
        manifests[(domain, condition, model)] = m
        assert (m['domain'], m['instruction_condition'], m['call_policy']) == (domain, condition, 'sequential')
        assert tuple(m[k] for k in ('max_steps', 'max_tool_calls', 'max_new_tokens', 'max_input_tokens')) == (20, 20, 512, 32768)
        assert (m['seed'], m['decoder'], m['supplied_prefix'], m['template_profile']) == (20260919, 'greedy_native_template', '', 'standard')
        assert m['agent_prompt_source_sha256'] == prompt_hash
        assert m['preparation_sha256'] == domains[domain]['preparation_sha256']
        assert m['queries_sha256'] == preparations[domain]['prepared_queries_sha256']
        assert m['all_task_ids'] == m['selected_task_ids'] == domains[domain]['selected_task_ids']
        assert len(m['source_sha256']) == 5
        for name, digest in m['source_sha256'].items():
            assert source_hashes[name] == digest, name
        if model == 'qwen30b':
            for entry in pinned['files']:
                assert m['model_files_sha256'][entry['name']] == entry['sha256'], entry['name']
        else:
            assert m['model_files_sha256'] == reference[model]['manifest']['model_files_sha256']
        pp = directory / 'model_placement.json'
        placement = json.loads(pp.read_bytes())
        profile = 'two_gpu_balanced' if model == 'qwen30b' else 'single_gpu'
        assert m['device_profile'] == placement['profile'] == profile
        devices = {str(v).removeprefix('cuda:') for v in placement['hf_device_map'].values()}
        assert devices == ({'0', '1'} if model == 'qwen30b' else {'0'})
        for p in (mp, pp, directory / 'startup.json'):
            hashes[p.relative_to(root).as_posix()] = sha(p)
        cases = sorted(directory.glob('case-*.json'))
        ids = domains[domain]['selected_task_ids']
        assert [p.name for p in cases] == [f'case-{i:03d}.json' for i in range(len(ids))]
        for index, path in enumerate(cases):
            observed_cases.add(path)
            e = json.loads(path.read_bytes())
            assert e['uuid'] == ids[index]
            episodes[(domain, condition, model, e['uuid'])] = e
            trace, usage = e.get('trace', []), e.get('usage', {})
            calls = [c for t in trace for c in t.get('calls', [t]) if 'tool_call' in c]
            if trace:
                assert e['call_policy'] == 'sequential'
                assert e['instruction_condition'] == condition
                assert len(trace) == usage['model_calls'] <= 20
                assert len(calls) == usage['tool_calls'] <= 20
                assert sum('protocol_error' in t for t in trace) == usage['protocol_errors']
                for key in ('input_tokens', 'output_tokens'):
                    assert sum(t['reply'][key] for t in trace if 'reply' in t) == usage[key]
                assert all(t['reply']['output_tokens'] <= 512 for t in trace if 'reply' in t)
                assert [x['role'] for x in trace[0]['input']] == ['system', 'user']
            rel = path.relative_to(root).as_posix()
            hashes[rel] = sha(path)
            rows.append({'domain': domain, 'condition': condition, 'model': model,
                         'call_policy': 'sequential', 'task_index': index, 'uuid': e['uuid'],
                         'source': rel, 'termination': e['termination'], 'final_answer': e.get('final_answer'),
                         'usage': usage, 'elapsed_seconds': e.get('elapsed_seconds'),
                         'protocol_error_messages': dict(Counter(t['protocol_error'] for t in trace if 'protocol_error' in t)),
                         'mcp_flagged_errors': sum(bool(c.get('tool_result', {}).get('isError')) for c in calls),
                         'validation_error_payloads': sum(any(b.get('text', '').startswith('Input validation error:') for b in c.get('tool_result', {}).get('content', [])) for c in calls),
                         'tool_budget_rejections': sum('tool_budget_rejection' in t for t in trace),
                         'final_at_generation_token_ceiling': bool(e.get('final_answer') is not None and trace and trace[-1].get('reply', {}).get('output_tokens') == 512)})
    assert set(root.rglob('case-*.json')) == observed_cases and len(rows) == expected_n
    first = next(iter(manifests.values()))
    for m in manifests.values():
        assert m['source_sha256'] == first['source_sha256'] and m['packages'] == first['packages']
    pairs = []
    for model in models:
        pool = [m for (d, c, mdl), m in manifests.items() if mdl == model]
        assert all(m['model_files_sha256'] == pool[0]['model_files_sha256'] for m in pool)
        for domain in domains:
            orig, rem = [manifests[(domain, c, model)] for c in ('original', 'coverage_check')]
            assert orig['instruction_suffix'] == '' and rem['instruction_suffix']
            for uid in domains[domain]['selected_task_ids']:
                x, y = [episodes[(domain, c, model, uid)] for c in ('original', 'coverage_check')]
                available = bool(x.get('trace') and y.get('trace'))
                if available:
                    a, b = x['trace'][0]['input'], y['trace'][0]['input']
                    assert b[0]['content'] == a[0]['content'] + rem['instruction_suffix'] and b[1:] == a[1:]
                    assert stable(x['tools']) == stable(y['tools'])
                    assert stable(x['initial_peek']) == stable(y['initial_peek'])
                pairs.append({'domain': domain, 'model': model, 'uuid': uid,
                              'initial_pairing_verified': available})
    groups = []
    for domain, condition, model in sorted(arms):
        pool = [r for r in rows if (r['domain'], r['condition'], r['model']) == (domain, condition, model)]
        groups.append({'domain': domain, 'condition': condition, 'model': model, 'n': len(pool),
                       'terminations': dict(Counter(r['termination'] for r in pool)),
                       'final_answers': sum(r['final_answer'] is not None for r in pool),
                       'usage': {k: sum(r['usage'].get(k, 0) for r in pool) for k in ('model_calls', 'tool_calls', 'input_tokens', 'output_tokens', 'generation_seconds', 'protocol_errors')}})
    return {'purpose': __doc__, 'complete': True, 'kind': kind, 'registered_episodes': expected_n,
            'distinct_tasks': sum(len(d['selected_task_ids']) for d in domains.values()),
            'domains': list(domains), 'models': models, 'deployment_archive_sha256': expected_archive,
            'grid_manifest_sha256': sha(gp), 'input_sha256': hashes, 'rows': rows, 'groups': groups,
            'prompt_pairs': pairs, 'batch_wall_seconds': grid['finished'] - grid['started'],
            'model_reference_manifests': {k: v['manifest_sha256'] for k, v in reference.items()}}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--kind', choices=('capacity', 'expansion'), required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    report = audit(a.root, a.archive, a.kind)
    with a.output.open('x', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({'episodes': len(report['rows']), 'groups': report['groups'],
                      'initial_pairs_verified': sum(x['initial_pairing_verified'] for x in report['prompt_pairs'])}))


if __name__ == '__main__':
    main()
