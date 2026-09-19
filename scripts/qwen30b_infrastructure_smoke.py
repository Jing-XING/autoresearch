"""Unrelated two-turn generation test for registered two-GPU model placement."""
from dataclasses import asdict
import json
from pathlib import Path
import sys
from autolab.native_tool_agent import NativeTransformersModel, parse_calls


def main():
    root = Path('/xingjing/autoresearch-agent-papers')
    output = Path(sys.argv[1])
    assert not output.exists()
    model = NativeTransformersModel(root / 'models/Qwen3-30B-A3B-Instruct-2507',
                                   max_input_tokens=2048, device_profile='two_gpu_balanced')
    tools = [{'type': 'function', 'function': {'name': 'read_value',
        'description': 'Read the integer in this toy environment.',
        'parameters': {'type': 'object', 'properties': {}, 'additionalProperties': False}}}]
    messages = [{'role': 'system', 'content': 'Use the provided tool to answer the user.'},
                {'role': 'user', 'content': 'Read the stored integer and report it.'}]
    trace = []
    for step in range(2):
        reply = model.generate_tools(messages, tools, 128)
        event = {'step': step, 'input': list(messages), 'reply': asdict(reply)}
        trace.append(event)
        messages.append({'role': 'assistant', 'content': reply.text})
        try:
            calls = parse_calls(reply.text)
        except (ValueError, TypeError) as exc:
            event['protocol_error'] = str(exc)
            break
        if not calls:
            break
        for i, call in enumerate(calls):
            value = '37' if call == {'name': 'read_value', 'arguments': {}} else '{"error":"invalid toy call"}'
            messages.append({'role': 'tool', 'name': call['name'],
                             'tool_call_id': f'toy-{step}-{i}', 'content': value})
    with output.open('x', encoding='utf-8') as f:
        json.dump({'purpose': __doc__, 'generation_infrastructure_passed': True,
                   'placement': model.runtime_placement, 'trace': trace, 'messages': messages,
                   'answer_quality_used_to_select_grid': False}, f, indent=2)
    print(json.dumps({'generation_infrastructure_passed': True, 'calls': len(trace)}), flush=True)


if __name__ == '__main__':
    main()
