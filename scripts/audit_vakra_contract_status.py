"""Development audit of a named binary-contract perturbation class in publishing."""
import asyncio
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autolab.relational_mutations import answer, apply
from audit_vakra_mutation_search import main as replay_main, sha


def prepare():
    prepared = ROOT / 'results/vakra-book_publishing_company-replication-v1'
    database = prepared / 'book_publishing_company.sqlite'
    cards_path = ROOT / 'research/evidence/vakra_crossdomain_sql_cards_v1.json'
    cards = json.loads(cards_path.read_bytes())['cards']
    rows = []
    with sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True) as original:
        assert not original.execute("SELECT name FROM sqlite_master WHERE type='trigger'").fetchall()
        for card in cards:
            if card['domain'] != 'book_publishing_company' or card['task_index'] not in (7, 8):
                continue
            sql = card['sql'].replace('SELECT DISTINCT t.title_id,t.title,t.ytd_sales', 'SELECT DISTINCT t.title,t.ytd_sales')
            with sqlite3.connect(':memory:') as memory:
                original.backup(memory)
                memory.execute('PRAGMA foreign_keys=ON')
                flags = memory.execute('SELECT au_id,contract FROM authors ORDER BY au_id').fetchall()
                assert len(flags) == 23 and all(value == '0' for _, value in flags)
                baseline = answer(memory, sql)
                candidates = []
                for index, (key, value) in enumerate(flags):
                    mutation = {'table': 'authors', 'column': 'contract', 'keys': ['au_id'],
                                'operator': 'single_contract_flag_flip',
                                'changes': [{'key': [key], 'before': value, 'after': '1'}]}
                    memory.execute('SAVEPOINT candidate')
                    try:
                        apply(memory, mutation)
                        assert not memory.execute('PRAGMA foreign_key_check').fetchall()
                        changed = answer(memory, sql)
                        if changed != baseline:
                            candidates.append({'draw': index, 'mutation': mutation, 'answer': changed})
                    finally:
                        memory.execute('ROLLBACK TO candidate'); memory.execute('RELEASE candidate')
                rows.append({'task_index': card['task_index'], 'uuid': card['uuid'], 'query': card['query'],
                             'target_sql': sql, 'search': {'original_answer': baseline, 'draws': len(flags), 'candidates': candidates}})
    report = {'purpose': __doc__, 'database_sha256': sha(database), 'cards_sha256': sha(cards_path),
              'source_sha256': sha(Path(__file__)), 'mutation_source_sha256': sha(ROOT / 'autolab/relational_mutations.py'),
              'rows': rows,
              'scope': 'Post-outcome development on two known publishing tasks. A declared synthetic-world contract allows one authors.contract status to change from string 0 to string 1, with all other cells unchanged. Every observed original flag is 0; value 1 is an explicit counterfactual-domain assumption, not sampled observed support. Enumerate all 23 single-author flips per task, retain every answer-changing flip and replay all four existing sequential-executor model/prompt arms. Stop after the first target-observation-preserving witness. No claim about real historical contract changes, multi-cell sufficiency or general prevalence.'}
    output = ROOT / 'research/evidence/vakra_publishing_contract_candidates_v1.json'
    with output.open('x', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(json.dumps([{'task': r['task_index'], 'flips': r['search']['draws'], 'answer_changing': len(r['search']['candidates'])} for r in rows]), flush=True)
    return output, prepared


if __name__ == '__main__':
    candidate, prepared = prepare()
    asyncio.run(replay_main(candidate, ROOT / 'results/vakra-publishing-contract-v1',
                           ROOT / 'research/evidence/vakra_publishing_contract_audit_v1.json', prepared,
                           ROOT / 'results/remote/vakra-permissive-v1/runs/vakra-permissive-v1/book_publishing_company'))
