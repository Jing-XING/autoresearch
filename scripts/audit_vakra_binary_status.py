"""Development refinement: vary only one official-language flag at a time.

Designed after both a known manual witness and the schema-only search results.
This is a positive-control/constraint-sensitivity audit, not independent data.
"""
import asyncio
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autolab.relational_mutations import answer, apply, candidate_columns
from audit_vakra_mutation_search import main as replay_main, sha


def prepare():
    source = ROOT / 'research/evidence/vakra_world_mutation_candidates_v1.json'
    old = json.loads(source.read_bytes())
    database = ROOT / 'results/vakra-world-runtime-v3/world.sqlite'
    rows, eligibility = [], []
    with sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True) as original:
        assert not original.execute("SELECT name FROM sqlite_master WHERE type='trigger'").fetchall()
        for card in old['rows']:
            with sqlite3.connect(':memory:') as memory:
                original.backup(memory)
                memory.execute('PRAGMA foreign_keys=ON')
                pools = candidate_columns(memory, card['target_sql'])
                pools = [p for p in pools if (p['table'], p['column']) == ('CountryLanguage', 'IsOfficial')]
                eligibility.append({'task_index': card['task_index'], 'eligible': bool(pools)})
                if not pools:
                    continue
                baseline = answer(memory, card['target_sql'])
                candidates, checked = [], 0
                for pool in pools:
                    values = {r[-1] for r in pool['rows']}
                    assert values == {'T', 'F'}
                    for row in pool['rows']:
                        mutation = {k: pool[k] for k in ('table', 'column', 'keys')}
                        mutation.update(operator='single_official_flag_flip', changes=[
                            {'key': list(row[:-1]), 'before': row[-1], 'after': 'F' if row[-1] == 'T' else 'T'}])
                        memory.execute('SAVEPOINT candidate')
                        try:
                            apply(memory, mutation)
                            assert not memory.execute('PRAGMA foreign_key_check').fetchall()
                            changed = answer(memory, card['target_sql'])
                            if changed != baseline:
                                candidates.append({'draw': checked, 'mutation': mutation, 'answer': changed})
                        finally:
                            memory.execute('ROLLBACK TO candidate')
                            memory.execute('RELEASE candidate')
                        checked += 1
                rows.append({k: card[k] for k in ('task_index', 'uuid', 'query', 'target_sql')} | {
                    'search': {'original_answer': baseline, 'draws': checked, 'candidates': candidates}})
    report = {'purpose': __doc__, 'database_sha256': sha(database), 'preceding_candidate_file_sha256': sha(source),
        'mutation_source_sha256': sha(ROOT / 'autolab/relational_mutations.py'),
        'source_sha256': sha(Path(__file__)), 'eligibility': eligibility, 'rows': rows,
        'scope': 'Post-outcome development refinement. Only one CountryLanguage.IsOfficial flag may change, T/F; every other database cell stays fixed. This preserves geography/identities but does not certify all domain semantics. Exhaustively enumerate this single-cell class over existing rows; retain every SQL-answer-changing flip. All four model/prompt arms on eligible tasks are checked. Stop replay after the first witness; a negative does not prove sufficiency under multiple changes or other allowed data variations.'}
    output = ROOT / 'research/evidence/vakra_world_binary_status_candidates_v1.json'
    with output.open('x', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps([{'task': r['task_index'], 'flips': r['search']['draws'],
                       'answer_changing': len(r['search']['candidates'])} for r in rows]), flush=True)
    return output


if __name__ == '__main__':
    candidate_path = prepare()
    asyncio.run(replay_main(candidate_path, ROOT / 'results/vakra-world-binary-status-v1',
                           ROOT / 'research/evidence/vakra_world_binary_status_audit_v1.json'))
