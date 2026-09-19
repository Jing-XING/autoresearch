"""Test a post-hoc observation-preserving database mutation on one full trace.

No model is rerun; both databases are replayed through the unchanged MCP tools.
"""
import asyncio
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from autolab.vakra_mcp_audit import decode_result


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stable(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,allow_nan=True).encode()


async def replay(prep,database,episode,prior,log):
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters,stdio_client
    qs=json.loads((prep/'queries.json').read_bytes())
    warm=next(q['uuid'] for q in qs if q['uuid']!=prior[0]['uuid'])
    params=StdioServerParameters(command=sys.executable,args=['-X','utf8','-m','autolab.vakra_stdio',
        '--runtime',str(prep/'runtime'),'--database',str(database),'--domain','world'],cwd=str(ROOT),
        env={'PYTHON_DOTENV_DISABLED':'1','PYTHONUTF8':'1','PYTHONPATH':str(ROOT)})
    async with stdio_client(params,errlog=log) as (read,write):
        async with ClientSession(read,write,read_timeout_seconds=timedelta(seconds=60)) as session:
            await session.initialize()
            decode_result(await session.call_tool('get_data',{'tool_universe_id':warm}))
            prefix_differences=[]
            # Dynamic schema ordering depends on previous universe registration.
            # Reproduce the actual worker prefix instead of normalizing schemas.
            for previous_episode in prior:
                prefix_peek=decode_result(await session.call_tool('get_data',{'tool_universe_id':previous_episode['uuid']}))
                assert prefix_peek==previous_episode['initial_peek']
                for event in previous_episode['trace']:
                    if 'tool_call' not in event:continue
                    call=event['tool_call'];result=await session.call_tool(call['name'],call['arguments'])
                    if result.model_dump(mode='json')['content']!=event['tool_result']['content']:
                        prefix_differences.append({'uuid':previous_episode['uuid'],'call':call})
                    assert result.isError==event['tool_result']['isError']
            peek=decode_result(await session.call_tool('get_data',{'tool_universe_id':episode['uuid']}))
            tools=[{'type':'function','function':{'name':t.name,'description':t.description or '',
                      'parameters':t.inputSchema}} for t in (await session.list_tools()).tools]
            assert peek==episode['initial_peek']
            if tools!=episode['tools']:
                raise ValueError(json.dumps({'database':database.name,'actual_tools':tools,'expected_tools':episode['tools']},ensure_ascii=False)[:6000])
            events=[]
            for event in episode['trace']:
                if 'tool_call' not in event:continue
                call=event['tool_call'];result=await session.call_tool(call['name'],call['arguments'])
                observed=result.model_dump(mode='json')
                assert observed['content']==event['tool_result']['content']
                assert observed['isError']==event['tool_result']['isError']
                events.append({'call':call,'content':observed['content'],'isError':observed['isError']})
    return {'initial_peek':peek,'tools':tools,'events':events},prefix_differences


async def main():
    source=ROOT/'results/remote/vakra-coverage12-v1/runs/vakra-coverage12-v1/coverage_check/qwen3/shard-0/case-003.json'
    episode=json.loads(source.read_bytes())
    assert len(episode['trace'][0]['input'])==2
    assert [m['role'] for m in episode['trace'][0]['input']]==['system','user']
    prior_paths=[source.with_name(f'case-{i:03d}.json') for i in range(3)]
    prior=[json.loads(p.read_bytes()) for p in prior_paths]
    prep=ROOT/'results/vakra-world-runtime-v3'
    manifest=json.loads((prep/'preparation_manifest.json').read_bytes())
    db=prep/'world.sqlite'
    assert sha(db)==manifest['database_sha256']
    for name,digest in manifest['runtime_files'].items():assert sha(prep/'runtime'/name)==digest
    before_sha=sha(db)
    output=ROOT/'results/vakra-full-history-witness-v5';output.mkdir(exist_ok=False)
    changed=output/'world-spanish-official.sqlite';shutil.copy2(db,changed)
    mutation="UPDATE CountryLanguage SET IsOfficial='T' WHERE CountryCode='AND' AND Language='Spanish' AND IsOfficial='F'"
    with sqlite3.connect(changed) as con:
        con.execute('PRAGMA foreign_keys=ON');assert con.execute(mutation).rowcount==1
        assert con.execute('PRAGMA foreign_key_check').fetchall()==[]
    target="SELECT c.Name, city.Name, l.Language FROM Country c JOIN City city ON city.ID=c.Capital JOIN CountryLanguage l ON l.CountryCode=c.Code WHERE c.LifeExpectancy=(SELECT MAX(LifeExpectancy) FROM Country) AND l.IsOfficial='T' ORDER BY c.Code,l.Language"
    answers=[]
    for path in (db,changed):
        with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as con:answers.append(con.execute(target).fetchall())
    assert answers[0]!=answers[1]
    with (output/'mcp.stderr.log').open('x',encoding='utf-8') as log:
        replays=[await replay(prep,path,episode,prior,log) for path in (db,changed)]
    observations=[r[0] for r in replays]
    assert not replays[0][1], 'Original worker prefix mismatch'
    assert stable(observations[0])==stable(observations[1])
    assert sha(db)==before_sha
    report={'purpose':'post-hoc full-recorded-history indistinguishability witness, not a new model experiment or prevalence estimate',
            'source':str(source.relative_to(ROOT)),'source_sha256':sha(source),'uuid':episode['uuid'],
            'worker_prefix_files_sha256':{p.name:sha(p) for p in prior_paths},
            'setup_note':'First attempt used a different warmup and failed exact schema-order comparison. Subsequent attempts showed that the mutation changes a previous independent episode. The final check reproduces worker registration history but compares the target episode only; its model starts with a fresh two-message input. No schema or target-observation normalization is applied.',
            'previous_independent_episode_differences':replays[1][1],
            'original_final_answer':episode['final_answer'],'database_sha256':before_sha,
            'counterfactual_database_sha256':sha(changed),'mutation_sql':mutation,'target_sql':target,
            'original_answer':answers[0],'counterfactual_answer':answers[1],
            'initial_peek_equal':True,'tool_schemas_equal':True,'all_recorded_tool_responses_equal':True,
            'tool_calls_replayed_per_database':len(observations[0]['events']),
            'observable_history_sha256':hashlib.sha256(stable(observations[0])).hexdigest(),
            'serialization':'Python JSON with literal NaN preserved as in the source artifacts; sorted object keys for digest, no value normalization.',
            'observation':observations[0],
            'scope':'Same target-episode query, schemas, initial preview and every tool-result content; deterministic relational tools and fixed recorded actions. Earlier independent episodes are not part of this model input. No claim about cross-episode memory, external or prior knowledge.',
            'interpretation':'The actual answer is correct in the original database, but these tool observations alone cannot establish that Catalan is the only official language. This does not prove all incomplete previews are insufficient.',
            'script_sha256':sha(Path(__file__))}
    target_path=ROOT/'research/evidence/vakra_full_history_witness.json'
    with target_path.open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
    print(json.dumps({k:report[k] for k in ('tool_calls_replayed_per_database','original_answer','counterfactual_answer','all_recorded_tool_responses_equal')}))


if __name__=='__main__':asyncio.run(main())
