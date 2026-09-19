"""Construct two database witnesses with equal task-local initial observations.

Only new local copies are edited. This proves insufficiency of the prescribed
initial relation, not impossibility under unrestricted cross-universe get_data.
"""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'results/third_party/vakra'))
from environment.m3.python_tools.tools.sql_tools import initialize_active_data


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def serial(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False,default=str).encode()


def main():
    data=ROOT/'results/third_party/vakra-data'
    db=data/'databases/computer_student/computer_student.sqlite'
    ip=data/'train/capability_1_bi_apis/input/computer_student.json'
    rp=data/'train/capability_1_bi_apis/output/computer_student.json'
    qs=json.loads(ip.read_bytes());refs={r['uuid']:r for r in json.loads(rp.read_bytes())}
    output=ROOT/'results/vakra-initial-scope-counterfactual-v1'
    output.mkdir(exist_ok=False)
    original_sha=sha(db);rows=[]
    for index,student,teacher,old_course in [(4,376,107,4),(15,6,165,27)]:
        q=qs[index];ref=refs[q['uuid']]
        changed=output/f'task-{index:03d}.sqlite'
        shutil.copy2(db,changed)
        mutation='UPDATE taughtBy SET course_id=0 WHERE p_id=? AND course_id=?'
        with sqlite3.connect(changed) as con:
            con.execute('PRAGMA foreign_keys=ON')
            assert con.execute('SELECT COUNT(*) FROM course WHERE course_id=0').fetchone()[0]==1
            assert con.execute('SELECT COUNT(*) FROM taughtBy WHERE p_id=? AND course_id=0',(teacher,)).fetchone()[0]==0
            assert con.execute(mutation,(teacher,old_course)).rowcount==1
        args=copy.deepcopy(ref['output'][0]['sequence']['tool_call'][0]['arguments'])
        args['database_path']=str(db.resolve());before=initialize_active_data(**args)
        args['database_path']=str(changed.resolve());after=initialize_active_data(**args)
        before_bytes,after_bytes=serial(before),serial(after)
        assert before_bytes==after_bytes,'Counterfactual changed visible initial relation'
        target_sql='SELECT DISTINCT t.course_id FROM advisedBy a JOIN taughtBy t ON a.p_id_dummy=t.p_id WHERE a.p_id=? ORDER BY t.course_id'
        answers=[]
        for path in (db,changed):
            with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as con:
                answers.append(con.execute(target_sql,(student,)).fetchall())
        assert answers[0]!=answers[1]
        rows.append({'uuid':q['uuid'],'query':q['dialogue']['turns'][0]['query'],
                     'mutation_sql':mutation,'mutation_parameters':[teacher,old_course],
                     'counterfactual_database_sha256':sha(changed),
                     'initial_relation_equal':True,'initial_relation_sha256':hashlib.sha256(before_bytes).hexdigest(),
                     'initial_relation_rows':len(next(v for k,v in before.items() if k!='_dtypes')),
                     'target_sql':target_sql,'target_parameters':[student],
                     'original_answer':answers[0],'counterfactual_answer':answers[1]})
    assert sha(db)==original_sha
    report={'purpose':'task-local observation insufficiency witnesses, not model results',
            'scope_condition':'Tools operate on the prescribed initial relation or its descendants; no cross-task universe switch, external database access or prior database knowledge.',
            'important_limit':'The actual MCP get_data accepts other universe IDs. Therefore this is NOT a proof that the unrestricted live API makes these tasks impossible.',
            'database_sha256':original_sha,'references_sha256':sha(rp),
            'upstream_initializer_sha256':sha(ROOT/'results/third_party/vakra/environment/m3/python_tools/tools/sql_tools.py'),
            'rows':rows}
    p=ROOT/'research/evidence/vakra_initial_scope_counterfactuals.json'
    with p.open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
    print(json.dumps({'witnesses':len(rows),'unchanged_original_database':True,'rows':rows}))


if __name__=='__main__':main()
