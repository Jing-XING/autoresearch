import unittest
from types import SimpleNamespace
from autolab.vakra_budget_replay import InitialInputGuard, InitialPeekGuard


class RecordingModel:
    def __init__(self):
        self.calls = []

    def generate_tools(self, messages, tools, max_new_tokens):
        self.calls.append((messages, tools, max_new_tokens))
        return 'delegated'


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.model = RecordingModel()
        self.messages = [{'role':'system','content':'rules'}, {'role':'user','content':'task'}]
        self.tools = [{'name':'first'}, {'name':'second'}]

    def test_mismatch_prevents_any_inference(self):
        guard = InitialInputGuard(self.model, self.messages, self.tools)
        with self.assertRaises(ValueError):
            guard.generate_tools(self.messages, list(reversed(self.tools)), 8192)
        self.assertEqual(self.model.calls, [])
        self.assertFalse(guard.checked)
        self.assertIsNotNone(guard.failure)

    def test_exact_input_allows_new_budget_then_continuation(self):
        guard = InitialInputGuard(self.model, self.messages, self.tools)
        self.assertEqual(guard.generate_tools(self.messages, self.tools, 8192), 'delegated')
        guard.generate_tools(self.messages + [{'role':'assistant','content':'next'}], self.tools, 8192)
        self.assertTrue(guard.checked)
        self.assertEqual([c[2] for c in self.model.calls], [8192,8192])

    def test_prior_answers_cannot_be_initial_messages(self):
        with self.assertRaises(ValueError):
            InitialInputGuard(self.model, self.messages + [{'role':'assistant','content':'answer'}], self.tools)


class PeekTests(unittest.IsolatedAsyncioTestCase):
    async def test_complete_peek_compared_before_model_execution(self):
        class Session:
            async def call_tool(self, name, arguments):
                return SimpleNamespace(isError=False, content=[SimpleNamespace(type='text', text='{"handle":"h0","count":4}')])
        guard = InitialPeekGuard(Session(), 'task', {'handle':'h0','count':3})
        with self.assertRaisesRegex(ValueError, 'preview differs'):
            await guard.call_tool('get_data', {'tool_universe_id':'task'})
        self.assertFalse(guard.checked)

    async def test_matching_peek_allows_followup_tools(self):
        class Session:
            async def call_tool(self, name, arguments):
                return SimpleNamespace(isError=False, content=[SimpleNamespace(type='text', text='{"handle":"h0","count":4}')])
        guard = InitialPeekGuard(Session(), 'task', {'handle':'h0','count':4})
        await guard.call_tool('get_data', {'tool_universe_id':'task'})
        self.assertTrue(guard.checked)
        await guard.call_tool('later', {})


if __name__ == '__main__':
    unittest.main()
