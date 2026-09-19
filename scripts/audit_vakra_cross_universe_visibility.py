"""Check the scope limitation of existing witnesses without editing any database."""
import copy
import hashlib
import json
from pathlib import Path

from audit_vakra_initial_scope_counterfactuals import ROOT, initialize_active_data, serial, sha


def main():
    source = ROOT / 'research/evidence/vakra_initial_scope_counterfactuals.json'
    witnesses = json.loads(source.read_bytes())
    data = ROOT / 'results/third_party/vakra-data'
    db = data / 'databases/computer_student/computer_student.sqlite'
    rp = data / 'train/capability_1_bi_apis/output/computer_student.json'
    ip = data / 'train/capability_1_bi_apis/input/computer_student.json'
    refs = {r['uuid']: r for r in json.loads(rp.read_bytes())}
    queries = json.loads(ip.read_bytes())
    assert sha(db) == witnesses['database_sha256']
    assert sha(rp) == witnesses['references_sha256']
    rows = []
    for index, witness in zip((4, 15), witnesses['rows']):
        changed = ROOT / f'results/vakra-initial-scope-counterfactual-v1/task-{index:03d}.sqlite'
        assert sha(changed) == witness['counterfactual_database_sha256']
        observations = []
        for query in queries:
            args = copy.deepcopy(refs[query['uuid']]['output'][0]['sequence']['tool_call'][0]['arguments'])
            values = []
            for path in (db, changed):
                args['database_path'] = str(path.resolve())
                value = initialize_active_data(**args)
                values.append({'sha256': hashlib.sha256(serial(value)).hexdigest(),
                               'rows': len(next(v for k, v in value.items() if k != '_dtypes'))})
            observations.append({'universe': query['uuid'], 'initial_relations_equal': values[0] == values[1],
                                 'original': values[0], 'counterfactual': values[1]})
        own = next(r for r in observations if r['universe'] == witness['uuid'])
        assert own['initial_relations_equal']
        rows.append({'witness_uuid': witness['uuid'], 'universes_checked': len(observations),
                     'different_relation_universes': sum(not r['initial_relations_equal'] for r in observations),
                     'observations': observations})
        assert sha(changed) == witness['counterfactual_database_sha256']
    assert sha(db) == witnesses['database_sha256']
    result = {'purpose': 'check cross-universe scope of existing counterfactual witnesses',
              'witnesses_sha256': sha(source), 'queries_sha256': sha(ip),
              'limit': 'A changed full initial relation does not imply its three-row preview differs or that a model can identify the useful universe; this is not a live-agent result.',
              'rows': rows}
    output = ROOT / 'research/evidence/vakra_cross_universe_visibility.json'
    with output.open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps([{k: v for k, v in row.items() if k != 'observations'} for row in rows]))


if __name__ == '__main__':
    main()
