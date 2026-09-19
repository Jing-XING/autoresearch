"""Replay the first rejected call batch per episode without repairing arguments.

This CPU diagnostic does not continue the model or rescore its original run.
"""
import argparse
import asyncio
from collections import Counter
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autolab.native_tool_agent import parse_calls
from autolab.vakra_mcp_audit import decode_result


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def decoded_or_error(result):
    try:return {'value': decode_result(result), 'execution_error': False}
    except ValueError as exc:return {'error': str(exc), 'execution_error': True}


async def run(a):
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
    selected=[]
    for p in sorted(a.root.glob('*/*/*/shard-0/case-*.json')):
        raw=json.loads(p.read_bytes())
        for event in raw.get('trace',[]):
            if event.get('protocol_error')=='At most one tool call per iteration is allowed':
                selected.append((p,raw,event));break
    assert selected, 'No rejected batches found'
    rows=[];provenance={}
    with a.output.with_suffix('.stderr.log').open('x',encoding='utf-8') as log:
        for domain in sorted({p.relative_to(a.root).parts[0] for p,_,_ in selected}):
            prep=ROOT/f'results/vakra-{domain}-replication-v1'
            manifest=json.loads((prep/'preparation_manifest.json').read_bytes())
            db=prep/f'{domain}.sqlite';before=sha(db)
            assert before==manifest['database_sha256']
            for rel,digest in manifest['runtime_files'].items():assert sha(prep/'runtime'/rel)==digest
            provenance[domain]={'preparation_sha256':sha(prep/'preparation_manifest.json'),'database_sha256':before}
            queries=json.loads((prep/'queries.json').read_bytes())
            params=StdioServerParameters(command=sys.executable,args=['-X','utf8','-m','autolab.vakra_stdio',
                '--runtime',str(prep/'runtime'),'--database',str(db),'--domain',domain],cwd=str(ROOT),
                env={'PYTHON_DOTENV_DISABLED':'1','PYTHONUTF8':'1','PYTHONPATH':str(ROOT)})
            async with stdio_client(params,errlog=log) as (read,write):
                async with ClientSession(read,write,read_timeout_seconds=timedelta(seconds=60)) as session:
                    await session.initialize()
                    for path,raw,event in selected:
                        if path.relative_to(a.root).parts[0]!=domain:continue
                        warm=next(q['uuid'] for q in queries if q['uuid']!=raw['uuid'])
                        decode_result(await session.call_tool('get_data',{'tool_universe_id':warm}))
                        initial=decode_result(await session.call_tool('get_data',{'tool_universe_id':raw['uuid']}))
                        assert initial==raw['initial_peek'], (path,'initial mismatch')
                        prefix=[]
                        for previous in raw['trace'][:event['step']]:
                            if 'tool_call' not in previous:continue
                            call=previous['tool_call']
                            result=await session.call_tool(call['name'],call['arguments'])
                            original=previous['tool_result']
                            assert result.model_dump(mode='json')['content']==original['content'], (path,'prefix content mismatch')
                            assert result.isError==original['isError']
                            prefix.append(call)
                        tested=[]
                        for call in parse_calls(event['reply']['text']):
                            result=await session.call_tool(call['name'],call['arguments'])
                            tested.append({'call':call,**decoded_or_error(result),
                                           'mcp_result':result.model_dump(mode='json')})
                        rows.append({'source':path.relative_to(a.root).as_posix(),'source_sha256':sha(path),
                                     'uuid':raw['uuid'],'rejected_step':event['step'],'prefix_calls_replayed':prefix,
                                     'all_batch_calls_executable':all(not t['execution_error'] for t in tested),
                                     'calls':tested})
            assert sha(db)==before
    report={'purpose':'post-outcome adapter diagnostic; not model continuation, semantic validation or rescore',
            'selection':'first multiple-call rejection in every episode containing one; no repairs or retries',
            'mode':'execute the fixed batch sequentially, retain each response including errors',
            'source_sha256':sha(Path(__file__)),'provenance':provenance,'episodes':len(rows),
            'all_batch_calls_executable':sum(r['all_batch_calls_executable'] for r in rows),
            'calls':sum(len(r['calls']) for r in rows),
            'execution_errors':sum(t['execution_error'] for r in rows for t in r['calls']),
            'rows':rows}
    with a.output.open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
    print(json.dumps({k:report[k] for k in ('episodes','all_batch_calls_executable','calls','execution_errors')}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();assert not a.output.exists()
    asyncio.run(run(a))


if __name__=='__main__':main()
