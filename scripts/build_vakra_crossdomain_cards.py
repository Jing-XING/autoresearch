"""Offline, assistant-authored SQL interpretations, frozen before reading model answers.

These are inspectable audit candidates, not benchmark corrections or an official
judge. Several questions have alternate interpretations recorded explicitly.
"""
import hashlib
import json
from pathlib import Path
import sqlite3

BASE=Path('results/third_party/vakra-data')
SQL={
'computer_student':[
"SELECT COUNT(DISTINCT p_id) FROM taughtBy WHERE course_id=18",
"SELECT course_id FROM course WHERE courseLevel='Level_500' ORDER BY course_id",
"SELECT COUNT(*) FROM course WHERE courseLevel='Level_300'",
"SELECT DISTINCT t.p_id FROM taughtBy t JOIN course c USING(course_id) JOIN person p ON p.p_id=t.p_id WHERE c.courseLevel='Level_400' AND p.professor=1 ORDER BY t.p_id",
"SELECT DISTINCT t.course_id FROM advisedBy a JOIN taughtBy t ON a.p_id_dummy=t.p_id WHERE a.p_id=376 ORDER BY t.course_id",
"SELECT DISTINCT a.p_id_dummy FROM advisedBy a JOIN person p ON a.p_id=p.p_id WHERE p.yearsInProgram='Year_3' ORDER BY a.p_id_dummy",
"SELECT DISTINCT c.courseLevel FROM course c JOIN taughtBy t USING(course_id) WHERE t.p_id=297",
"SELECT DISTINCT a.p_id_dummy FROM advisedBy a JOIN person p ON a.p_id=p.p_id WHERE p.yearsInProgram='Year_12' ORDER BY a.p_id_dummy",
"SELECT COUNT(*) FROM course WHERE courseLevel='Level_300'",
"SELECT COUNT(DISTINCT p_id) FROM taughtBy WHERE course_id=11",
"SELECT COUNT(*) FROM person WHERE hasPosition='Faculty_eme'",
"SELECT COUNT(DISTINCT c.course_id) FROM course c JOIN taughtBy t USING(course_id) JOIN person p ON p.p_id=t.p_id WHERE c.courseLevel='Level_300' AND p.professor=1",
"SELECT DISTINCT p.p_id FROM course c JOIN taughtBy t USING(course_id) JOIN person p ON p.p_id=t.p_id WHERE c.courseLevel='Level_300' AND p.hasPosition='Faculty_eme'",
"SELECT p.p_id,p.hasPosition FROM taughtBy t JOIN person p USING(p_id) WHERE t.course_id=9",
"SELECT COUNT(DISTINCT c.course_id) FROM course c JOIN taughtBy t USING(course_id) JOIN person p ON p.p_id=t.p_id WHERE c.courseLevel='Level_300' AND p.hasPosition!='0'",
"SELECT DISTINCT t.course_id FROM advisedBy a JOIN taughtBy t ON a.p_id_dummy=t.p_id WHERE a.p_id=6 ORDER BY t.course_id",
"SELECT COUNT(DISTINCT a.p_id_dummy) FROM advisedBy a JOIN person p ON a.p_id=p.p_id WHERE p.yearsInProgram='Year_3'",
"SELECT p_id FROM taughtBy WHERE course_id=18 ORDER BY p_id",
"SELECT c.courseLevel,t.p_id FROM course c JOIN taughtBy t USING(course_id) WHERE c.course_id=147 ORDER BY t.p_id",
"SELECT DISTINCT p.p_id,p.hasPosition FROM person p JOIN taughtBy t USING(p_id) JOIN course c USING(course_id) WHERE c.courseLevel='Level_400' AND c.course_id<10 AND p.professor=1 ORDER BY p.p_id"],
'cars':[
"SELECT d.car_name FROM data d JOIN price p USING(ID) WHERE d.cylinders=8 AND p.price=(SELECT MAX(p2.price) FROM data d2 JOIN price p2 USING(ID) WHERE d2.cylinders=8)",
"SELECT COUNT(*) FROM data d JOIN price p USING(ID) WHERE d.weight>3000 AND p.price<30000",
"SELECT d.acceleration FROM data d JOIN price p USING(ID) WHERE p.price=(SELECT MAX(price) FROM price)",
"SELECT p.price FROM data d JOIN price p USING(ID) WHERE lower(d.car_name)='ford torino'",
"SELECT DISTINCT c.country FROM data d JOIN production pr USING(ID) JOIN country c ON c.origin=pr.country WHERE lower(d.car_name)='ford torino' AND pr.model_year=1970",
"SELECT COUNT(DISTINCT pr.ID) FROM production pr JOIN country c ON c.origin=pr.country WHERE pr.model_year=1970 AND c.country='USA'",
"SELECT DISTINCT d.car_name FROM data d JOIN production pr USING(ID) JOIN country c ON c.origin=pr.country WHERE c.country='USA' ORDER BY d.car_name",
"SELECT d.car_name,p.price FROM data d JOIN price p USING(ID) ORDER BY p.price DESC,d.ID LIMIT 3",
"SELECT DISTINCT pr.model_year FROM data d JOIN production pr USING(ID) WHERE lower(d.car_name)='chevrolet impala' ORDER BY pr.model_year",
"SELECT d.weight FROM data d JOIN price p USING(ID) WHERE p.price>40000 ORDER BY d.ID",
"SELECT MAX(d.acceleration) FROM data d JOIN price p USING(ID) WHERE p.price>40000",
"SELECT AVG(p.price) FROM data d JOIN price p USING(ID) WHERE d.cylinders=8",
"SELECT COUNT(DISTINCT pr.ID) FROM production pr JOIN country c ON c.origin=pr.country WHERE c.country='Europe'",
"SELECT DISTINCT c.country FROM data d JOIN production pr USING(ID) JOIN country c ON c.origin=pr.country WHERE lower(d.car_name)='chevrolet malibu'",
"SELECT d.mpg FROM data d JOIN price p USING(ID) WHERE p.price=(SELECT MAX(price) FROM price)",
"SELECT DISTINCT c.country FROM price p JOIN production pr USING(ID) JOIN country c ON c.origin=pr.country WHERE ROUND(p.price,5)=44274.40748",
"SELECT p.price FROM data d JOIN price p USING(ID) WHERE lower(d.car_name)='volkswagen dasher' AND d.acceleration=14.1",
"SELECT d.displacement FROM data d JOIN price p USING(ID) WHERE ROUND(p.price,5)=37443.85589",
"SELECT d.model,pr.model_year FROM data d JOIN price p USING(ID) JOIN production pr USING(ID) WHERE ROUND(p.price,5)=32650.65157",
"SELECT DISTINCT c.country FROM data d JOIN production pr USING(ID) JOIN country c ON c.origin=pr.country WHERE d.horsepower=(SELECT MAX(horsepower) FROM data)"],
'book_publishing_company':[
"SELECT t.title,SUM(s.qty) AS total_qty FROM titles t JOIN sales s USING(title_id) WHERE strftime('%Y',s.ord_date)='1992' GROUP BY t.title_id,t.title ORDER BY total_qty DESC,t.title_id",
"SELECT t.title,r.lorange,r.royalty FROM titles t JOIN roysched r USING(title_id) WHERE r.royalty=(SELECT MAX(royalty) FROM roysched) ORDER BY t.title_id,r.lorange",
"SELECT fname,lname FROM employee WHERE hire_date<'1990-01-01' ORDER BY fname,lname",
"SELECT fname,lname,hire_date FROM employee WHERE job_lvl=(SELECT MIN(job_lvl) FROM employee)",
"SELECT e.fname,e.lname,e.hire_date FROM employee e JOIN jobs j USING(job_id) WHERE j.job_desc='Chief Executive Officer'",
"SELECT t.title,t.price FROM titles t JOIN publishers p USING(pub_id) WHERE p.pub_name='Binnet & Hardley' ORDER BY t.price DESC,t.title_id",
"SELECT e.fname,e.lname,j.job_desc FROM employee e JOIN jobs j USING(job_id) WHERE e.job_lvl>200 ORDER BY e.fname,e.lname",
"SELECT DISTINCT t.title_id,t.title,t.ytd_sales FROM titles t JOIN titleauthor ta USING(title_id) JOIN authors a USING(au_id) WHERE a.contract='0' ORDER BY t.title_id",
"SELECT DISTINCT t.title,t.ytd_sales FROM titles t JOIN titleauthor ta USING(title_id) JOIN authors a USING(au_id) WHERE a.contract='0' AND a.state='CA' ORDER BY t.ytd_sales DESC,t.title",
"SELECT COUNT(*) FROM publishers WHERE country='USA'",
"SELECT e.fname FROM employee e JOIN jobs j USING(job_id) WHERE j.job_desc='Managing Editor' ORDER BY e.fname",
"SELECT e.fname,e.lname,j.max_lvl FROM employee e JOIN jobs j USING(job_id) WHERE e.hire_date=(SELECT MIN(hire_date) FROM employee)",
"SELECT t.title,t.price,SUM(s.qty) AS total_qty FROM titles t JOIN sales s USING(title_id) GROUP BY t.title_id,t.title,t.price ORDER BY total_qty DESC,t.title_id",
"SELECT DISTINCT p.country FROM titles t JOIN publishers p USING(pub_id) WHERE t.title='Life Without Fear'",
"SELECT p.pub_name,t.title,t.price FROM titles t JOIN publishers p USING(pub_id) WHERE t.price=(SELECT MAX(price) FROM titles)",
"SELECT COUNT(DISTINCT p.pub_id) FROM publishers p JOIN titles t USING(pub_id) WHERE p.country='USA' AND t.price>15",
"SELECT type,advance FROM titles WHERE advance=(SELECT MAX(advance) FROM titles)",
"SELECT title,royalty,ytd_sales FROM titles WHERE ytd_sales=(SELECT MAX(ytd_sales) FROM titles)",
"SELECT fname,lname,job_lvl FROM employee WHERE lname='O''Rourke'",
"SELECT emp_id,job_lvl FROM employee WHERE (minit IS NULL OR minit='') ORDER BY job_lvl DESC,emp_id"]}

ALTERNATIVES={
('computer_student',3):"SELECT DISTINCT t.p_id FROM taughtBy t JOIN course c USING(course_id) WHERE c.courseLevel='Level_400' ORDER BY t.p_id",
('computer_student',11):"SELECT COUNT(*) FROM course c JOIN taughtBy t USING(course_id) JOIN person p ON p.p_id=t.p_id WHERE c.courseLevel='Level_300' AND p.professor=1",
('computer_student',14):"SELECT COUNT(*) FROM course c JOIN taughtBy t USING(course_id) JOIN person p ON p.p_id=t.p_id WHERE c.courseLevel='Level_300' AND p.professor=1",
('cars',5):"SELECT COUNT(*) FROM production pr JOIN country c ON c.origin=pr.country WHERE pr.model_year=1970 AND c.country='USA'",
('cars',12):"SELECT COUNT(*) FROM production pr JOIN country c ON c.origin=pr.country WHERE c.country='Europe'",
('cars',13):"SELECT DISTINCT c.country FROM data d JOIN production pr USING(ID) JOIN country c ON c.origin=pr.country WHERE lower(d.car_name) LIKE '%chevrolet malibu%'",
('cars',19):"SELECT DISTINCT c.country FROM data d JOIN production pr USING(ID) JOIN country c ON c.origin=pr.country WHERE d.acceleration=(SELECT MIN(acceleration) FROM data)",
('book_publishing_company',0):"SELECT t.title,s.qty FROM titles t JOIN sales s USING(title_id) WHERE strftime('%Y',s.ord_date)='1992' ORDER BY s.qty DESC,t.title_id",
('book_publishing_company',12):"SELECT t.title,t.price,s.qty FROM titles t JOIN sales s USING(title_id) ORDER BY s.qty DESC,t.title_id"}

NOTES={
('computer_student',3):'Professor flag 1 follows empirical binary indicator usage; released person.csv value_description conflicts with that usage. Alternative includes all teaching persons, as reference does. Duplicate IDs need not be repeated for an entity list.',
('computer_student',4):'advisedBy.p_id_dummy is the advisor per official schema description. Reference instead filters student ID 141 despite query 376 and joins teaching to the student side.',
('computer_student',5):'Question asks advisors; reference retrieves advisedBy.p_id (student side), not documented p_id_dummy (advisor). Names are unavailable, so IDs are the representable answer.',
('computer_student',10):'Faculty employee maps to Faculty_eme only via the released glossary; ordinary faculty-member interpretation would differ.',
('computer_student',11):'Distinct courses versus professor-course assignment rows. Reference counts rows (27); preserve both interpretations.',
('computer_student',12):'Faculty employee maps to Faculty_eme via released glossary.',
('computer_student',14):'Distinct courses taught by faculty versus reference professor-course assignment count; predicates also differ.',
('computer_student',15):'Student 6 has multiple advisors in the database; question singular is misleading. Reference filters teaching-person ID 9 instead of the advisors of 6.',
('computer_student',19):'High-level undergraduate is Level_400 per released glossary. Professor flag caveat as in task 3.',
('cars',5):'Count distinct car records versus production records; alternative preserves reference row count.',
('cars',6):'Exhaustive names; reference is long. Report output-token ceiling as a separate limitation, do not silently score a prefix as complete.',
('cars',12):'Count distinct car records versus production records; the country table uses Europe as a category.',
('cars',13):'Exact Chevrolet Malibu name versus substring family; retain both if they differ.',
('cars',18):'Reference returns two-digit data.model, query asks introduced year; retain production.model_year to diagnose any mismatch.',
('cars',19):'Fastest is not directly measured. Reference uses maximum horsepower; minimum acceleration time is a different plausible proxy. No unique semantic gold is asserted.',
('book_publishing_company',0):'Most ordered quantity may mean total orders per title or largest single order. Both interpretations are returned; first row(s) determine extremum.',
('book_publishing_company',1):'Report all tied maximum-royalty schedules and their lower range; reference chooses one row.',
('book_publishing_company',4):'Query asks CEO; released reference explicitly filters CFO. SQL uses CEO.',
('book_publishing_company',5):'Full ordered rows retained for tie inspection; target is greatest price.',
('book_publishing_company',7):'Question requests titles; reference emits title IDs with duplicates from authorship join. Card includes ID/name/sales and deduplicates repeated title observations.',
('book_publishing_company',8):'Full ordered candidates retained for tie inspection; target is greatest YTD sales.',
('book_publishing_company',11):'Highest achievable job level is jobs.max_lvl, not employee.job_lvl.',
('book_publishing_company',12):'Bestselling may mean total sold per title or largest single order; reference uses latter. Both returned.',
('book_publishing_company',17):'Uses maximum ytd_sales, as reference; royalty is percentage in stored data.',
('book_publishing_company',19):'Highest is interpreted as job_lvl. Missing middle initial includes NULL and empty string; all sorted rows retained to expose ties.'}


def main():
    cards=[];hashes={}
    for domain,queries in SQL.items():
        db=BASE/f'databases/{domain}/{domain}.sqlite'
        ip=BASE/f'train/capability_1_bi_apis/input/{domain}.json'
        rp=BASE/f'train/capability_1_bi_apis/output/{domain}.json'
        inputs=json.loads(ip.read_bytes())[:20]
        refs={r['uuid']:r for r in json.loads(rp.read_bytes())}
        assert len(inputs)==len(queries)==20
        for path in (db,ip,rp):hashes[path.relative_to(BASE).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
        with sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True) as con:
            for i,(q,sql) in enumerate(zip(inputs,queries)):
                cur=con.execute(sql)
                card={'domain':domain,'task_index':i,'uuid':q['uuid'],'query':q['dialogue']['turns'][0]['query'],
                      'reference_answer':refs[q['uuid']]['output'][0]['answer'],
                      'sql':sql,'columns':[x[0] for x in cur.description],'rows':cur.fetchall(),
                      'interpretation_note':NOTES.get((domain,i),'Direct SQL interpretation; values refer to this fixed database, not current real-world facts.'),
                      'annotation_status':'candidate interpretation; review before assigning model answer labels'}
                if (domain,i) in ALTERNATIVES:
                    alt=ALTERNATIVES[(domain,i)];cur=con.execute(alt)
                    card['alternative']={'sql':alt,'columns':[x[0] for x in cur.description],'rows':cur.fetchall()}
                cards.append(card)
        assert hashlib.sha256(db.read_bytes()).hexdigest()==hashes[db.relative_to(BASE).as_posix()]
    out={'purpose':'offline SQL audit candidates, not official scoring or corrected benchmark',
         'model_answers_inspected':False,'model_outcome_labels_used':False,
         'input_sha256':hashes,'cards':cards,
         'global_notes':['Level_300/400/500 follow released course glossary.','Faculty_eme is called faculty employee by the released glossary.','The professor column glossary conflicts with observed binary indicator usage; related cards explicitly disclose this.','All 60 selected questions remain in execution counts. Ambiguity and reference disagreements cannot be silently dropped.']}
    path=Path('research/evidence/vakra_crossdomain_sql_cards_v1.json')
    with path.open('x',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,indent=2)
    for c in cards:
        print(c['domain'],c['task_index'],'rows',len(c['rows']),'first',str(c['rows'][:3])[:230])


if __name__=='__main__':main()
