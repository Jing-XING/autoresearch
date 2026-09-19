"""Local stdio bridge for native benchmark airline tools and declared faults."""
import asyncio
import copy
import json
from pathlib import Path
import socket
import sys


def deny_network(event, args):
    if event == 'socket.connect':
        caller = sys._getframe(1)
        if (caller.f_code.co_name == '_fallback_socketpair'
                and Path(caller.f_code.co_filename).resolve() == Path(socket.__file__).resolve()
                and args[1][0] in ('127.0.0.1', '::1')):
            return
        raise PermissionError('Native airline fixture permits stdio only')


sys.addaudithook(deny_network)
from tau_airline_compensation_fixture import load
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, TextContent, Tool

state_path = Path(sys.argv[1]).resolve()
assert state_path.is_relative_to(Path('results/probes/tau-airline-mcp').resolve())
profile, mode = sys.argv[2:4]
assert mode in ('normal', 'native_error_before_effect', 'shadow_only', 'error_after_effect')
tools, booking, metadata = load(profile)
server = Server('native-tau-airline-recovery-control')
if not state_path.exists():
    initial = tools.db.model_dump(mode='json')
    with state_path.open('x', encoding='utf-8') as stream:
        json.dump({'before': initial, 'current': initial, 'booking': booking,
                   'metadata': metadata, 'mode': mode, 'calls': []}, stream)


@server.list_tools()
async def list_tools():
    result = []
    for name, tool in tools.get_tools(include=['book_reservation', 'cancel_reservation']).items():
        definition = tool.openai_schema['function']
        schema = copy.deepcopy(definition['parameters'])
        if name == 'book_reservation':
            schema['x-compensation-pair'] = 'cancel_reservation'
        result.append(Tool(name=name, description=definition.get('description', ''), inputSchema=schema))
    return result


@server.call_tool()
async def call_tool(name, arguments):
    assert name in ('book_reservation', 'cancel_reservation')
    state = json.loads(state_path.read_bytes())
    assert state['metadata'] == metadata and state['mode'] == mode
    tools.db = type(tools.db).model_validate(state['current'])
    event = {'name': name, 'arguments': arguments, 'fault': mode if name == 'cancel_reservation' else None}
    result, error = None, None
    try:
        if name == 'book_reservation':
            assert arguments == booking
            result = tools.book_reservation(**arguments)
        elif mode == 'native_error_before_effect':
            result = tools.cancel_reservation('EXPERIMENTALLY_MISSING_ID')
        elif mode == 'shadow_only':
            shadow = type(tools)(tools.db.model_copy(deep=True))
            result = shadow.cancel_reservation(**arguments)
            event['native_cancel_on_disposable_copy'] = True
        else:
            result = tools.cancel_reservation(**arguments)
            if mode == 'error_after_effect':
                raise RuntimeError('Constructed acknowledgement error after native cancellation committed')
    except Exception as exc:
        error = exc
        event['exception'] = {'type': type(exc).__name__, 'message': str(exc)}
    state['current'] = tools.db.model_dump(mode='json')
    if result is not None:
        event['native_result'] = result.model_dump(mode='json')
    state['calls'].append(event)
    state_path.write_text(json.dumps(state), encoding='utf-8')
    if error is not None:
        raise error  # SDK emits the actual MCP tool-level error response.
    payload = result.model_dump(mode='json')
    return CallToolResult(isError=False, content=[TextContent(type='text', text=json.dumps(payload))],
                          structuredContent=payload)


async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == '__main__':
    asyncio.run(main())
