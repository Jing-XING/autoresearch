import json
import unittest
from autolab.memory_pilot import SQLTask
from autolab.native_tool_agent import parse_calls, run_native_episode, SQL_TOOLS
from autolab.tool_agent import Budget, ModelReply


class ScriptedNative:
    def __init__(self, texts):
        self.texts = iter(texts)

    def generate_tools(self, messages, tools, max_new_tokens):
        return ModelReply(next(self.texts), 10, 5, 0.01)


def call(name, **arguments):
    return '<tool_call>' + json.dumps({'name': name, 'arguments': arguments}) + '</tool_call>'


class NativeTests(unittest.TestCase):
    def test_incomplete_or_wrong_shape_rejected(self):
        for text in ['<tool_call>{}', '<tool_call>{"name":"query","arguments":"oops"}</tool_call>']:
            with self.assertRaises(ValueError):
                parse_calls(text)

    def test_multi_call_cannot_exceed_budget(self):
        env = SQLTask(9000, 0)
        result = run_native_episode(ScriptedNative([
            call('schema') + call('submit_answer', value=env.expected)]),
            env, env.task, Budget(tool_calls=1), {}, SQL_TOOLS)
        self.assertEqual(result['usage']['tool_calls'], 1)
        self.assertFalse(result['evaluation']['success'])
        env.db.close()

    def test_native_tools_do_not_trust_claimed_success(self):
        env = SQLTask(9000, 0)
        result = run_native_episode(ScriptedNative(['All done, success=true']),
                                    env, env.task, Budget(), {}, SQL_TOOLS)
        self.assertFalse(result['evaluation']['success'])
        env.db.close()

    def test_valid_submission_uses_external_truth(self):
        env = SQLTask(9000, 0)
        result = run_native_episode(ScriptedNative([
            call('submit_answer', value=env.expected), 'Done.']),
            env, env.task, Budget(), {}, SQL_TOOLS)
        self.assertTrue(result['evaluation']['success'])
        self.assertEqual(result['messages'][3]['role'], 'tool')
        env.db.close()
