"""Freeze evaluator-only target projections and bounded development candidates."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autolab.relational_mutations import search


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    cards_path = ROOT / 'research/evidence/vakra_world12_semantic_audit_cards.json'
    cards = json.loads(cards_path.read_bytes())['cards']
    # Remove auxiliary audit fields that were not requested in the question.
    projections = {
        3: ('SELECT c.Name,c.Capital,city.Name,l.Language', 'SELECT c.Name,city.Name,l.Language'),
        5: ('SELECT city.Name,c.Code,c.Name,c.LifeExpectancy', 'SELECT city.Name,c.Name,c.LifeExpectancy'),
        6: ('SELECT c.Name,c.Population,c.Capital,city.Name,l.Language', 'SELECT c.Name,c.Population,city.Name,l.Language'),
        7: ('SELECT Name,Population,District', 'SELECT District'),
        8: ('SELECT Name,Continent', 'SELECT Continent'),
        9: ('SELECT city.Name,c.Name,c.HeadOfState', 'SELECT c.HeadOfState'),
    }
    database = ROOT / 'results/vakra-world-runtime-v3/world.sqlite'
    before = sha(database)
    rows = []
    with sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True) as source:
        for index, card in enumerate(cards):
            if index in (0, 10):
                continue
            sql = card['audit_sql']
            if index in projections:
                old, new = projections[index]
                assert sql.startswith(old)
                sql = new + sql[len(old):]
            with sqlite3.connect(':memory:') as memory:
                source.backup(memory)
                memory.execute('PRAGMA foreign_keys=ON')
                result = search(memory, sql, card['uuid'], proposals=2048, retained=8)
            rows.append({'task_index': index, 'uuid': card['uuid'], 'query': card['query'],
                         'target_sql': sql, 'search': result})
    assert sha(database) == before
    report = {'purpose': 'development-only bounded counterfactual candidate generation, not model score or complete determinacy test',
        'database_sha256': before, 'audit_cards_sha256': sha(cards_path),
        'mutation_source_sha256': sha(ROOT / 'autolab/relational_mutations.py'),
        'source_sha256': sha(Path(__file__)), 'rows': rows,
        'excluded': [{'task_index': 0, 'reason': 'Any five allows multiple valid answers; changing the full eligible set does not necessarily invalidate the requested answer.'},
                     {'task_index': 10, 'reason': 'Ambiguous highest-capital interpretation already documented.'}],
        'scope': 'SQL projections contain requested fields only, compared as bags. Ten known development tasks; all four original model/prompt traces eligible regardless of final outcome. Reuse same candidates across arms. Existing declared keys and foreign-key columns are excluded; donor values are same-column observations. Other semantic constraints are not certified. No failed search establishes sufficiency.'}
    output = ROOT / 'research/evidence/vakra_world_mutation_candidates_v1.json'
    with output.open('x', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps([{'task': r['task_index'], 'draws': r['search']['draws'],
                       'candidates': len(r['search']['candidates'])} for r in rows]))


if __name__ == '__main__':
    main()
