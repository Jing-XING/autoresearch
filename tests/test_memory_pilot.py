import unittest
from autolab.memory_pilot import SQLTask


class SQLTaskTests(unittest.TestCase):
    def test_oracle_independent_of_model_and_database_read_only(self):
        env = SQLTask(7000, 0)
        before = env.execute("query", {"sql": "SELECT COUNT(*) FROM orders"})
        self.assertIn("error", env.execute("query", {"sql": "DELETE FROM orders"}))
        self.assertIn("error", env.execute("query", {"sql": "ATTACH DATABASE '/tmp/test.db' AS other"}))
        self.assertEqual(before, env.execute("query", {"sql": "SELECT COUNT(*) FROM orders"}))
        self.assertFalse(env.evaluate()["success"])
        env.execute("submit_answer", {"value": env.expected})
        self.assertTrue(env.evaluate()["success"])
        env.db.close()

    def test_query_has_instruction_budget(self):
        env = SQLTask(7000, 1)
        response = env.execute("query", {"sql": "WITH RECURSIVE t(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM t) SELECT sum(x) FROM t"})
        self.assertEqual(response.get("error"), "interrupted")
        env.db.close()


if __name__ == "__main__":
    unittest.main()
