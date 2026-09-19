"""Validate the complete registered third-model grid before answer annotation."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def stable(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    a = parser.parse_args()
    ev = Path('research/evidence')
    registration = ev / 'vakra_crossdomain_setup_audit.json'
    model_manifest = ev / 'smollm3_download_manifest.json'
    selection = json.loads(registration.read_bytes())
    pinned = json.loads(model_manifest.read_bytes())
    grid_path = a.root / 'grid_manifest.json'
    grid = json.loads(grid_path.read_bytes())
    assert grid['status'] == 'complete' and grid['registered_episodes'] == 240
    assert grid['selection']['domains'] == selection['domains']
    assert grid['selection']['template_profile'] == 'smollm3_no_think'
    assert grid['selection']['model_revision'] == pinned['revision']
    domains = [r['domain'] for r in selection['domains']]
    arms = {(d, p, c) for d in domains for p in ('single', 'sequential')
            for c in ('original', 'coverage_check')}
    assert len(grid['workers']) == len(arms) == 12
    assert {(w['domain'], w['call_policy'], w['condition']) for w in grid['workers']} == arms
    assert all(w['exit_code'] == 0 for w in grid['workers'])
    rows, manifests, episodes, hashes = [], {}, {}, {}
    for domain, policy, condition in sorted(arms):
        directory = a.root / domain / policy / condition / 'shard-0'
        mp = directory / 'manifest.json'
        manifest = json.loads(mp.read_bytes())
        manifests[(domain, policy, condition)] = manifest
        hashes[mp.relative_to(a.root).as_posix()] = sha(mp)
        assert (manifest['domain'], manifest['call_policy'], manifest['instruction_condition']) == (domain, policy, condition)
        assert (manifest['max_steps'], manifest['max_tool_calls'], manifest['max_new_tokens'], manifest['max_input_tokens']) == (20, 20, 512, 32768)
        assert manifest['template_profile'] == 'smollm3_no_think' and manifest['template_date'] == '2026-09-19'
        registered = next(r for r in selection['domains'] if r['domain'] == domain)
        assert manifest['preparation_sha256'] == registered['preparation_sha256']
        assert manifest['selected_task_ids'] == registered['selected_task_ids']
        for f in pinned['files']:
            assert manifest['model_files_sha256'][f['name']] == f['sha256']
        cases = sorted(directory.glob('case-*.json'))
        assert len(cases) == 20
        for index, path in enumerate(cases):
            e = json.loads(path.read_bytes())
            assert e['uuid'] == registered['selected_task_ids'][index]
            episodes[(domain, policy, condition, e['uuid'])] = e
            trace, usage = e.get('trace', []), e.get('usage', {})
            calls = [x for t in trace for x in t.get('calls', [t]) if 'tool_call' in x]
            if trace:
                assert e['call_policy'] == policy
                assert len(trace) == usage['model_calls'] <= 20
                assert len(calls) == usage['tool_calls'] <= 20
                assert sum('protocol_error' in t for t in trace) == usage['protocol_errors']
                for k in ('input_tokens', 'output_tokens'):
                    assert sum(t['reply'][k] for t in trace if 'reply' in t) == usage[k]
            rel = path.relative_to(a.root).as_posix()
            hashes[rel] = sha(path)
            rows.append({'domain': domain, 'call_policy': policy, 'condition': condition, 'model': 'smollm3',
                         'task_index': index, 'uuid': e['uuid'], 'source': rel, 'termination': e['termination'],
                         'final_answer': e.get('final_answer'), 'usage': usage,
                         'protocol_error_messages': dict(Counter(t['protocol_error'] for t in trace if 'protocol_error' in t)),
                         'mcp_flagged_errors': sum(bool(c.get('tool_result', {}).get('isError')) for c in calls),
                         'validation_error_payloads': sum(any(b.get('text', '').startswith('Input validation error:') for b in c.get('tool_result', {}).get('content', [])) for c in calls),
                         'tool_budget_rejections': sum('tool_budget_rejection' in t for t in trace),
                         'final_at_generation_token_ceiling': bool(e.get('final_answer') is not None and trace and trace[-1].get('reply', {}).get('output_tokens') == 512)})
    first = next(iter(manifests.values()))
    for m in manifests.values():
        for key in ('model_files_sha256', 'source_sha256', 'packages', 'agent_prompt_source_sha256', 'seed', 'decoder', 'supplied_prefix'):
            assert m[key] == first[key], key
    pairs = []
    for domain in domains:
        ids = manifests[(domain, 'single', 'original')]['selected_task_ids']
        for policy in ('single', 'sequential'):
            orig, rem = (manifests[(domain, policy, c)] for c in ('original', 'coverage_check'))
            assert orig['instruction_suffix'] == '' and rem['instruction_suffix']
            for uid in ids:
                x, y = (episodes[(domain, policy, c, uid)] for c in ('original', 'coverage_check'))
                if x.get('trace') and y.get('trace'):
                    a0, b0 = x['trace'][0]['input'], y['trace'][0]['input']
                    assert b0[0]['content'] == a0[0]['content'] + rem['instruction_suffix'] and b0[1:] == a0[1:]
                    assert stable(x['tools']) == stable(y['tools']) and stable(x['initial_peek']) == stable(y['initial_peek'])
        for condition in ('original', 'coverage_check'):
            for uid in ids:
                x, y = (episodes[(domain, p, condition, uid)] for p in ('single', 'sequential'))
                available = bool(x.get('trace') and y.get('trace'))
                if available:
                    assert stable(x['trace'][0]['input']) == stable(y['trace'][0]['input'])
                    assert stable(x['tools']) == stable(y['tools']) and stable(x['initial_peek']) == stable(y['initial_peek'])
                pairs.append({'domain': domain, 'condition': condition, 'uuid': uid,
                              'initial_pairing_available': available,
                              'same_first_reply': available and x['trace'][0].get('reply', {}).get('text') == y['trace'][0].get('reply', {}).get('text'),
                              'same_final_text': x.get('final_answer') == y.get('final_answer')})
    groups = []
    for d, p, c in sorted(arms):
        pool = [r for r in rows if (r['domain'], r['call_policy'], r['condition']) == (d, p, c)]
        groups.append({'domain': d, 'call_policy': p, 'condition': c, 'n': len(pool),
                       'terminations': dict(Counter(r['termination'] for r in pool)),
                       'usage': {k: sum(r['usage'].get(k, 0) for r in pool) for k in ('model_calls', 'tool_calls', 'input_tokens', 'output_tokens', 'generation_seconds', 'protocol_errors')}})
    assert len(rows) == 240 and len(pairs) == 120
    report = {'purpose': __doc__, 'complete': True, 'registered_episodes': 240, 'distinct_tasks': 60,
              'registration_sha256': sha(registration), 'model_manifest_sha256': sha(model_manifest),
              'grid_manifest_sha256': sha(grid_path), 'input_sha256': hashes, 'domains': domains,
              'groups': groups, 'rows': rows, 'executor_pairs': pairs}
    with a.output.open('x', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(json.dumps({'groups': groups, 'same_first_reply': sum(r['same_first_reply'] for r in pairs),
                      'same_final_text': sum(r['same_final_text'] for r in pairs)}))


if __name__ == '__main__':
    main()
