import sqlite3
import unittest

from autolab.relational_mutations import answer, apply, candidate_columns, search


class MutationTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.addCleanup(self.db.close)
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
            CREATE TABLE items(id INTEGER PRIMARY KEY, label TEXT UNIQUE, score INTEGER CHECK(score>=0));
            INSERT INTO items VALUES(1,'a',1),(2,'b',2),(3,'c',3);
            CREATE TABLE child(id INTEGER PRIMARY KEY, item_id INTEGER REFERENCES items(id), value INTEGER);
            INSERT INTO child VALUES(1,1,4),(2,2,5);
        ''')

    def test_only_relevant_nonkey_columns_are_mutable(self):
        columns = candidate_columns(self.db, 'SELECT i.id,i.label,i.score,c.item_id,c.value FROM items i JOIN child c ON c.item_id=i.id')
        self.assertEqual({(c['table'], c['column']) for c in columns}, {('items', 'score'), ('child', 'value')})

    def test_search_is_reproducible_and_does_not_change_source(self):
        sql = 'SELECT score FROM items WHERE id=1'
        before = answer(self.db, 'SELECT * FROM items')
        x = search(self.db, sql, 'fixture', proposals=100, retained=3)
        self.assertEqual(x, search(self.db, sql, 'fixture', proposals=100, retained=3))
        self.assertEqual(len(x['candidates']), 3)
        self.assertEqual(answer(self.db, 'SELECT * FROM items'), before)
        for candidate in x['candidates']:
            self.assertNotEqual(candidate['answer'], x['original_answer'])

    def test_count_can_change_with_replacement_and_duplicate_rows_remain(self):
        x = search(self.db, 'SELECT COUNT(*) FROM items WHERE score=1', 'count', proposals=100)
        self.assertTrue(x['candidates'])
        self.assertTrue(all(c['mutation']['operator'] == 'replace_observed_value' for c in x['candidates']))
        self.assertEqual(answer(self.db, 'SELECT 1 FROM items'), [[1], [1], [1]])

    def test_preconditions_prevent_wrong_row_mutation(self):
        mutation = {'table': 'items', 'column': 'score', 'keys': ['id'],
                    'changes': [{'key': [1], 'before': 99, 'after': 2}]}
        with self.assertRaises(ValueError):
            apply(self.db, mutation)
        self.assertEqual(answer(self.db, 'SELECT score FROM items WHERE id=1'), [[1]])


if __name__ == '__main__':
    unittest.main()
