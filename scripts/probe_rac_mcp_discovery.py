"""Check automatic discovery without manually registering a compensation pair."""
import asyncio
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import tempfile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def main():
    os.environ['LANGCHAIN_TRACING_V2'] = 'false'
    os.environ['LANGSMITH_TRACING'] = 'false'
    attempts = []
    def deny_network(event, args):
        if event == 'socket.connect':
            attempts.append(event)
            raise PermissionError('Discovery fixture permits stdio only')
    sys.addaudithook(deny_network)
    prior_path = Path('research/evidence/rac_real_mcp_probe_v1.json')
    prior = json.loads(prior_path.read_bytes())
    source = Path('results/third_party/rac/source')
    for name, digest in prior['source_sha256'].items():
        assert sha(source/name) == digest
    assert all(importlib.metadata.version(k) == v for k,v in prior['packages'].items())
    sys.path.insert(0, str((source/'src').resolve()))
    from react_agent_compensation.core.mcp.client import MCPCompensationClient
    from react_agent_compensation.core.mcp.parser import parse_mcp_schema
    root = Path('results/probes/rac-mcp')
    run = Path(tempfile.mkdtemp(prefix='discovery-', dir=root))
    state_path = (run/'state.json').resolve()
    state_path.write_text(json.dumps(dict(active=False,calls=[])),encoding='utf-8')
    server = Path('scripts/rac_mcp_fixture_server.py').resolve()
    assert sha(server) == prior['scripts_sha256'][str(server)]
    config = {'fixture':dict(transport='stdio',command=sys.executable,
              args=['-X','utf8',str(server),str(state_path),'success','cancel'])}
    client = MCPCompensationClient(config)
    await client.connect()
    discovered = await client.get_compensation_pairs()
    raw = next(t for t in client._raw_tools if t.name == 'book')
    input_schema = raw.get_input_schema()
    schema = dict(name=raw.name,inputSchema=raw.args_schema)
    declared_pair = parse_mcp_schema(schema)
    book = next(t for t in await client.get_tools() if t.name == 'book')
    tracking = book.should_track
    await book.ainvoke({'booking_id':'fixture-1'})
    log_size = len(client.recovery_manager.log)
    rollback = client.recovery_manager.rollback()
    state = json.loads(state_path.read_bytes())
    await client.close()
    assert not attempts
    assert declared_pair == ('book','cancel') and discovered == {}
    assert not tracking and log_size == 0 and rollback.success
    assert state['active'] and [r['name'] for r in state['calls']] == ['book']
    result = dict(purpose=__doc__, prior_probe_sha256=sha(prior_path),
        rac_revision=prior['rac_revision'], packages=prior['packages'],
        script_sha256=sha(Path(__file__)), server_sha256=sha(server),
        declared_tool_schema=schema, direct_parser_result=declared_pair,
        get_input_schema_is_dict=isinstance(input_schema,dict),
        get_input_schema_type=str(type(input_schema)), automatic_discovered_pairs=discovered,
        wrapper_should_track=tracking, recorded_actions=log_size,
        rollback_report=rollback.model_dump(mode='json'), fixture_state=state,
        state_sha256=sha(state_path), network_attempts=len(attempts), model_calls=0,
        controls_passed=True,
        limits=['One local schema-declared pair with current dependencies, not all MCP metadata forms.',
                'No compensation mapping manually added; successful no-op rollback means an empty recorded plan, not verified absence of effects.',
                'Constructed tool workflow, not an original paper task or failure-prevalence estimate.'])
    output = Path('research/evidence/rac_mcp_discovery_probe_v1.json')
    with output.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({k:result[k] for k in ('automatic_discovered_pairs','wrapper_should_track','recorded_actions','rollback_report','fixture_state','controls_passed')}))


if __name__ == '__main__':
    asyncio.run(main())
