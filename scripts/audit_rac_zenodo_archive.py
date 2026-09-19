"""Inventory the fixed RAC Zenodo release without executing author code.

Status fields are reported as recorded. Missing status is never inferred from
token usage; repeated snapshots are never treated as independent trials.
"""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import zipfile


ROOT = 'Kavirubc-react-agent-compensation-12e6678/'
ZIP_SHA256 = '6faee4dedc04c242922d3b4fcf4bed5521e3b824d42ee1ad88c48be538d7cad4'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def stable(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def main():
    path = Path('results/third_party/rac/zenodo-19753969.zip')
    raw = path.read_bytes()
    assert digest(raw) == ZIP_SHA256 and len(raw) == 13843052
    assert hashlib.md5(raw).hexdigest() == '437c54898f402da1c6b30445b26ef273'
    tau, realm, aggregate, members, mismatches = [], [], [], [], []
    exact_records = defaultdict(list)
    realm_groups = defaultdict(list)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        names = z.namelist()
        assert len(names) == len(set(names))
        for info in z.infolist():
            assert info.filename.startswith(ROOT) and '..' not in Path(info.filename).parts
            if not info.filename.endswith('.json'):
                continue
            data = z.read(info.filename)
            name = info.filename[len(ROOT):]
            obj = json.loads(data)
            members.append(dict(path=name, bytes=len(data), sha256=digest(data), keys=sorted(obj)))
            if '/all_tasks/' in name:
                records = obj['results']
                frameworks = Counter(r['framework'] for r in records)
                for index, record in enumerate(records):
                    exact_records[digest(stable(record))].append(dict(file=name, index=index,
                        framework=record['framework'], task_id=record['task_id']))
                aggregate.append(dict(path=name, rows=len(records), frameworks=dict(frameworks),
                    explicit_success_counts=dict(Counter(str(r.get('success')) for r in records)),
                    goal_satisfaction_values=dict(Counter(str(r.get('goal_satisfaction_rate')) for r in records)),
                    nonempty_compensation_actions=sum(bool(r.get('compensation_actions')) for r in records),
                    rollback_success_true=sum(r.get('rollback_success') is True for r in records),
                    metadata=obj['metadata']))
            elif '/Tau^2 Bench/' in name:
                steps = obj['steps']
                token_obj = obj.get('total_tokens')
                if isinstance(token_obj, dict):
                    tokens = token_obj.get('total', 0)
                else:
                    tokens = sum(s.get('tokens', {}).get('total', 0) for s in steps if isinstance(s, dict))
                tau.append(dict(path=name, framework_recorded=obj.get('framework'),
                    task_id_recorded=obj.get('task_id'), status_recorded=obj.get('status'),
                    steps=len(steps), token_total_recorded_or_summed=tokens,
                    missing_status_with_positive_tokens=obj.get('status') is None and tokens > 0))
            elif '/REALMBench/' in name:
                events = obj['events']
                row = dict(path=name, framework=obj['framework'], task_id=obj['task_id'],
                    start_time=obj['start_time'], end_time=obj['end_time'], success_recorded=obj['success'],
                    events=len(events), event_types=dict(Counter(e['event_type'] for e in events)),
                    compensation_events=len(obj['compensation_events']),
                    compensation_success_values=dict(Counter(str(e.get('success')) for e in obj['compensation_events'])),
                    final_state_sha256=digest(stable(obj['final_state'])), summary=obj['summary'])
                realm.append(row)
                if obj['start_time'] is not None:
                    key = (obj['framework'], obj['task_id'], str(obj['start_time']))
                    realm_groups[key].append((name, events))
                for i, event in enumerate(events):
                    result = event.get('result')
                    if isinstance(result, str):
                        try:
                            result = json.loads(result)
                        except (ValueError, TypeError):
                            pass
                    explicit_error = isinstance(result, dict) and (
                        result.get('success') is False or result.get('isError') is True or
                        str(result.get('status', '')).lower() in ('error', 'failed', 'failure'))
                    if explicit_error and event.get('success') is True:
                        mismatches.append(dict(path=name, event_index=i, event_type=event['event_type'],
                            result_sha256=digest(stable(result))))
            else:
                raise ValueError('Unexpected JSON source: ' + name)
    snapshots = []
    for key, items in realm_groups.items():
        if len(items) < 2:
            continue
        items = sorted(items, key=lambda x: (len(x[1]), x[0]))
        pair_checks = []
        for (left_name, left), (right_name, right) in zip(items, items[1:]):
            pair_checks.append(dict(left=left_name, right=right_name, left_events=len(left),
                right_events=len(right), exact_event_prefix=left == right[:len(left)]))
        snapshots.append(dict(framework=key[0], task_id=key[1], start_time=key[2],
            files=len(items), all_events_form_prefix_chain=all(r['exact_event_prefix'] for r in pair_checks),
            checks=pair_checks))
    result = dict(purpose=__doc__, source_url='https://doi.org/10.5281/zenodo.19753969',
        archive_sha256=ZIP_SHA256, archive_members=len(names),
        script_sha256=digest(Path(__file__).read_bytes()), json_members=members,
        tau_trace_files=tau, realm_files=realm, aggregate_files=aggregate,
        aggregate_record_occurrences=sum(r['rows'] for r in aggregate),
        aggregate_exact_distinct_records=len(exact_records),
        aggregate_exact_duplicates=[dict(record_sha256=h, occurrences=v)
            for h, v in exact_records.items() if len(v) > 1],
        realm_shared_start_time_groups=snapshots, realm_structured_status_mismatches=mismatches,
        limitations=[
            'Recorded success fields are not independently verified environment outcomes',
            'No status inferred from nonzero tokens; no goal failure inferred from zero default fields',
            'No mixing of progress snapshots, selected reference files, or unequal framework collections into a performance rate',
            'Zero explicit structured mismatches does not exclude silent, textual, nested, missing-state or unexercised failures',
            'Original RAC code and its experiment-generating model were not executed by this archive audit',
        ])
    target = Path('research/evidence/rac_zenodo_archive_audit_v1.json')
    with target.open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps(dict(json_files=len(members), tau_traces=len(tau), realm_files=len(realm),
        aggregate_files=len(aggregate), aggregate_occurrences=result['aggregate_record_occurrences'],
        exact_distinct_aggregate_records=len(exact_records),
        tau_missing_status=sum(r['status_recorded'] is None for r in tau),
        tau_missing_status_positive_tokens=sum(r['missing_status_with_positive_tokens'] for r in tau),
        shared_start_time_groups=[{k:v for k,v in r.items() if k != 'checks'} for r in snapshots],
        structured_mismatches=len(mismatches)), ensure_ascii=False))


if __name__ == '__main__':
    main()
