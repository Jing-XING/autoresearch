"""Local stdio MCP fixture; only modifies its explicitly named probe-state file."""
import asyncio
import json
from pathlib import Path
import sys


def deny_network(event, args):
    if event == 'socket.connect':
        raise PermissionError('MCP fixture allows stdio only')


from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, TextContent, Tool

state_path = Path(sys.argv[1]).resolve()
assert state_path.is_relative_to(Path('results/probes/rac-mcp').resolve())
mode, affected_tool = sys.argv[2:4]
assert mode in ('success', 'explicit_error', 'server_exception', 'silent_noop')
assert affected_tool in ('book', 'cancel')
server = Server('local-compensation-fixture')


@server.list_tools()
async def list_tools():
    schema = dict(type='object', properties={'booking_id':{'type':'string'}}, required=['booking_id'])
    return [Tool(name='book', description='Activate a local fixture booking.',
                 inputSchema=dict(schema, **{'x-compensation-pair':'cancel'})),
            Tool(name='cancel', description='Deactivate a local fixture booking.', inputSchema=schema)]


@server.call_tool()
async def call_tool(name, arguments):
    assert arguments['booking_id'] == 'fixture-1'
    assert name in ('book', 'cancel')
    state = json.loads(state_path.read_bytes())
    fail = name == affected_tool and mode in ('explicit_error', 'server_exception')
    if not fail and not (name == affected_tool and mode == 'silent_noop'):
        state['active'] = name == 'book'
    state['calls'].append(dict(name=name, arguments=arguments, mode=mode if name == affected_tool else 'success',
                              is_error=fail, active_after=state['active']))
    state_path.write_text(json.dumps(state), encoding='utf-8')
    if name == affected_tool and mode == 'server_exception':
        raise RuntimeError('Fixture operation unavailable')
    return CallToolResult(isError=fail, content=[TextContent(type='text', text=json.dumps(
        {'error':'Fixture operation unavailable'} if fail else {'booking_id':'fixture-1', 'status':'success'}))])


async def main():
    # Windows creates a loopback socket pair when constructing its event loop.
    # Install the external-connection guard after that stdlib initialization.
    sys.addaudithook(deny_network)
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == '__main__':
    asyncio.run(main())
