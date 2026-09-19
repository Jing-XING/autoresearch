"""Audit known car episodes under an explicit marginal-preserving price contract.

This post-outcome development audit never treats bounded search as a certificate.
Candidates depend on database and frozen SQL only, never on a model's trace.
"""
import asyncio
import hashlib
import json
from pathlib import Path
import random
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autolab.relational_mutations import answer, apply
from audit_vakra_mutation_search import main as replay_main, sha


def prepare():
    prepared = ROOT / 'results/vakra-cars-replication-v1'
    database = prepared / 'cars.sqlite'
    cards_path = ROOT / 'research/evidence/vakra_crossdomain_sql_cards_v1.json'
    cards = [c for c in json.loads(cards_path.read_bytes())['cards'] if c['domain'] == 'cars']
    assert len(cards) == 20
    rows = []
    with sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True) as original:
        assert not original.execute("SELECT name FROM sqlite_master WHERE type='trigger'").fetchall()
        with sqlite3.connect(':memory:') as con:
            original.backup(con)
            con.execute('PRAGMA foreign_keys=ON')
            assert not con.execute('PRAGMA foreign_key_check').fetchall()
            prices = con.execute('SELECT ID,price FROM price ORDER BY ID').fetchall()
            assert len({r[0] for r in prices}) == len(prices)
            assert all(isinstance(v, (float, int)) and v > 0 for _, v in prices)
            distribution = sorted(v for _, v in prices)
            for card in cards:
                baseline = answer(con, card['sql'])
                seed = hashlib.sha256(('price-swap-20260919:' + card['uuid']).encode()).hexdigest()
                rng = random.Random(seed)
                search = {'seed': seed, 'proposal_limit': 2048, 'retained_limit': 8,
                          'draws': 0, 'unchanged_answers': 0, 'duplicate_proposals': 0,
                          'original_answer': baseline, 'candidates': []}
                seen = set()
                for draw in range(2048):
                    search['draws'] += 1
                    left, right = rng.sample(prices, 2)
                    pair = tuple(sorted((left[0], right[0])))
                    if pair in seen:
                        search['duplicate_proposals'] += 1
                        continue
                    seen.add(pair)
                    mutation = {'table': 'price', 'column': 'price', 'keys': ['ID'],
                                'operator': 'swap_existing_positive_prices',
                                'changes': [{'key': [left[0]], 'before': left[1], 'after': right[1]},
                                            {'key': [right[0]], 'before': right[1], 'after': left[1]}]}
                    con.execute('SAVEPOINT candidate')
                    try:
                        apply(con, mutation)
                        assert not con.execute('PRAGMA foreign_key_check').fetchall()
                        assert sorted(r[0] for r in con.execute('SELECT price FROM price')) == distribution
                        changed = answer(con, card['sql'])
                        if changed == baseline:
                            search['unchanged_answers'] += 1
                        else:
                            search['candidates'].append({'draw': draw, 'mutation': mutation, 'answer': changed})
                    finally:
                        con.execute('ROLLBACK TO candidate'); con.execute('RELEASE candidate')
                    if len(search['candidates']) == 8:
                        break
                rows.append({'task_index': card['task_index'], 'uuid': card['uuid'], 'query': card['query'],
                             'target_sql': card['sql'], 'search': search})
    report = {'purpose': __doc__, 'database_sha256': sha(database), 'cards_sha256': sha(cards_path),
              'source_sha256': sha(Path(__file__)), 'mutation_source_sha256': sha(ROOT / 'autolab/relational_mutations.py'),
              'rows': rows,
              'scope': 'Post-outcome development on all twenty known car tasks, retaining all four Qwen sequential-executor model/prompt arms regardless of answer correctness. Admissible synthetic worlds exchange prices of two existing car IDs and fix every other cell. Positive price values and their full multiset, all declared keys/foreign keys, and row counts are preserved. Price-car associations may change by explicit assumption; this is not a claim about historical markets. Per task, propose up to 2048 seeded distinct-or-duplicate pairs and retain the first eight SQL-answer-changing candidates. Model traces and answers are not used to generate candidates. Stop replay at first full target-observation-preserving witness. No witness means unknown. Existing SQL interpretation ambiguities remain; no general natural-language failure prevalence or model rerun.'}
    output = ROOT / 'research/evidence/vakra_cars_price_swap_candidates_v1.json'
    with output.open('x', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(json.dumps([{'task': r['task_index'], 'draws': r['search']['draws'],
                       'retained': len(r['search']['candidates'])} for r in rows]), flush=True)
    return output, prepared


if __name__ == '__main__':
    candidates, prepared = prepare()
    asyncio.run(replay_main(candidates, ROOT / 'results/vakra-cars-price-swaps-v1',
                           ROOT / 'research/evidence/vakra_cars_price_swap_audit_v1.json', prepared,
                           ROOT / 'results/remote/vakra-permissive-v1/runs/vakra-permissive-v1/cars'))
