import unittest

from autolab.preview_cursor import enumerate_strings


def peek(values, n=None, handle="h"):
    return {"handle": handle, "num_records": len(values) if n is None else n,
            "key_details": [{"name": "name", "first_3_values": values[:3]}]}


class CursorTest(unittest.IsolatedAsyncioTestCase):
    async def test_duplicate_rows_do_not_drop_distinct_values(self):
        # A page boundary inside a repeated value must skip only duplicates.
        remaining = ["a", "a", "a", "a", "b", "c", "d"]

        async def call(name, arguments):
            nonlocal remaining
            if name == "filter_data":
                remaining = [x for x in remaining if x > arguments["value"]]
            return peek(remaining)

        result = await enumerate_strings(call, "h", "name", 20)
        self.assertTrue(result["complete"])
        self.assertEqual(result["values"], ["a", "b", "c", "d"])

    async def test_budget_exhaustion_is_explicitly_incomplete(self):
        async def call(name, arguments):
            return peek(["a", "b", "c"], 10)

        result = await enumerate_strings(call, "h", "name", 1)
        self.assertFalse(result["complete"])
        self.assertEqual(result["values"], ["a", "b", "c"])

    async def test_empty_relation_and_zero_budget_are_distinct(self):
        async def call(name, arguments):
            return peek([])

        self.assertTrue((await enumerate_strings(call, "h", "name", 1))["complete"])
        self.assertFalse((await enumerate_strings(call, "h", "name", 0))["complete"])

    async def test_invalid_observations_cannot_certify_completion(self):
        for invalid in (peek([None]), peek(["b", "a"]), peek(["a"], 4)):
            async def call(name, arguments):
                return invalid
            with self.assertRaises(ValueError):
                await enumerate_strings(call, "h", "name", 20)
        responses = iter([peek(["a", "b", "c"], 4), peek(["c"], 1)])

        async def nonprogress(name, arguments):
            return next(responses)

        with self.assertRaisesRegex(ValueError, "Cursor did not advance"):
            await enumerate_strings(nonprogress, "h", "name", 20)


if __name__ == "__main__":
    unittest.main()
