"""Compare fixed inputs and stable generation prefixes across executor policies."""
import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def inputs(messages):
    result = copy.deepcopy(messages)
    for m in result:
        if m['role'] == 'tool':
            m.pop('tool_call_id', None)
    return result


def stable(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--strict-root', type=Path, required=True)
    p.add_argument('--permissive-root', type=Path, required=True)
    p.add_argument('--strict-summary', type=Path, required=True)
    p.add_argument('--permissive-summary', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    strict, permissive = [json.loads(p.read_bytes()) for p in (a.strict_summary, a.permissive_summary)]
    assert strict['complete'] and permissive['complete']
    assert strict['registration_sha256'] == permissive['registration_sha256']
    assert set(strict['input_sha256']) == set(permissive['input_sha256'])
    records = []
    for row in permissive['rows']:
        rel = row['source']
        sp, pp = a.strict_root / rel, a.permissive_root / rel
        assert sha(sp) == strict['input_sha256'][rel]
        assert sha(pp) == permissive['input_sha256'][rel]
        x, y = json.loads(sp.read_bytes()), json.loads(pp.read_bytes())
        for key in ('uuid', 'query', 'initial_peek', 'tools', 'instruction_condition'):
            assert stable(x[key]) == stable(y[key]), (rel, key)
        sm, pm = [json.loads(p.with_name('manifest.json').read_bytes()) for p in (sp, pp)]
        for key in ('model_files_sha256', 'packages', 'agent_prompt_source_sha256', 'preparation_sha256',
                    'queries_sha256', 'selected_task_ids', 'seed', 'decoder', 'supplied_prefix',
                    'instruction_suffix', 'max_steps', 'max_new_tokens', 'max_input_tokens'):
            assert sm[key] == pm[key], (rel, key)
        for key in sm['source_sha256']:
            if key != 'vakra_native.py':
                assert sm['source_sha256'][key] == pm['source_sha256'][key], (rel, key)
        assert stable(x['trace'][0]['input']) == stable(y['trace'][0]['input'])
        same_prefix = 0
        first_difference = None
        for old, new in zip(x['trace'], y['trace']):
            if stable(inputs(old['input'])) != stable(inputs(new['input'])):
                first_difference = {'step': old['step'], 'type': 'model_input_changed'}
                break
            if old.get('reply', {}).get('text') != new.get('reply', {}).get('text'):
                first_difference = {'step': old['step'], 'type': 'reply_changed_with_same_logical_input'}
                break
            if 'reply' in old:
                assert old['reply']['input_tokens'] == new['reply']['input_tokens'], rel
                same_prefix += 1
        records.append({'source': rel, 'strict_sha256': sha(sp), 'permissive_sha256': sha(pp),
            'same_first_reply': x['trace'][0].get('reply', {}).get('text') == y['trace'][0].get('reply', {}).get('text'),
            'identical_generation_prefix_length': same_prefix, 'first_difference': first_difference,
            'final_text_equal': x.get('final_answer') == y.get('final_answer'),
            'strict_termination': x['termination'], 'permissive_termination': y['termination']})
    assert len(records) == 240
    report = {'purpose': __doc__, 'strict_summary_sha256': sha(a.strict_summary),
        'permissive_summary_sha256': sha(a.permissive_summary), 'source_sha256': sha(Path(__file__)),
        'episodes': len(records), 'same_first_reply': sum(r['same_first_reply'] for r in records),
        'same_final_text': sum(r['final_text_equal'] for r in records),
        'first_difference_types': dict(Counter((r['first_difference'] or {}).get('type', 'none') for r in records)),
        'rows': records,
        'limits': 'Tool-call IDs alone are omitted from logical-input comparison, following the actual tokenizer preflight. This is not a semantic answer score. First-input/source checks do not rule out numerical nondeterminism.'}
    with a.output.open('x', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: report[k] for k in ('episodes', 'same_first_reply', 'same_final_text', 'first_difference_types')}))


if __name__ == '__main__':
    main()
