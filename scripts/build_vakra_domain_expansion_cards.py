"""Freeze inspectable SQL interpretations before new-domain model inference.

These are evaluator-authored interpretations, not official benchmark labels.
Ambiguities are retained explicitly and never resolved using model outcomes.
"""
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
SQL = {
'cookbook': [
"SELECT DISTINCT i.name FROM Recipe r JOIN Quantity q USING(recipe_id) JOIN Ingredient i USING(ingredient_id) WHERE r.title='Warm Chinese Chicken Salad' AND q.optional='TRUE' ORDER BY i.name",
"SELECT r.title FROM Recipe r JOIN Nutrition n USING(recipe_id) WHERE n.alcohol=0 ORDER BY r.recipe_id",
"SELECT r.title FROM Recipe r JOIN Nutrition n USING(recipe_id) WHERE r.source='National Potato Board' AND n.calories=(SELECT MAX(n2.calories) FROM Recipe r2 JOIN Nutrition n2 USING(recipe_id) WHERE r2.source='National Potato Board')",
"SELECT COUNT(DISTINCT q.ingredient_id) FROM Recipe r JOIN Quantity q USING(recipe_id) JOIN Ingredient i USING(ingredient_id) WHERE r.title='No-Bake Chocolate Cheesecake' AND i.category='baking products'",
"SELECT n.total_fat FROM Recipe r JOIN Nutrition n USING(recipe_id) WHERE r.title='Raspberry Chiffon Pie'",
"SELECT DISTINCT r.title,i.name FROM Recipe r JOIN Nutrition n USING(recipe_id) JOIN Quantity q USING(recipe_id) JOIN Ingredient i USING(ingredient_id) WHERE n.vitamin_a=(SELECT MAX(vitamin_a) FROM Nutrition) ORDER BY r.title,i.name",
"SELECT DISTINCT i.name FROM Ingredient i JOIN Quantity q USING(ingredient_id) WHERE q.unit='slice(s)' ORDER BY i.name",
"SELECT r.title FROM Recipe r JOIN Nutrition n USING(recipe_id) WHERE n.calories=(SELECT MAX(calories) FROM Nutrition)",
"SELECT n.calories FROM Recipe r JOIN Nutrition n USING(recipe_id) WHERE r.title='Raspberry Chiffon Pie'",
"SELECT COUNT(DISTINCT q.ingredient_id) FROM Recipe r JOIN Quantity q USING(recipe_id) WHERE r.title='Raspberry Chiffon Pie'",
"SELECT i.name,q.min_qty,q.max_qty,q.unit FROM Recipe r JOIN Quantity q USING(recipe_id) JOIN Ingredient i USING(ingredient_id) WHERE r.title='Chicken Pocket Sandwich' AND lower(i.name) LIKE '%almond%' AND q.unit='cup(s)'",
"SELECT AVG(n.calories) FROM Recipe r JOIN Nutrition n USING(recipe_id) WHERE r.source='Produce for Better Health Foundation and 5 a Day'",
"SELECT DISTINCT i.name FROM Quantity q JOIN Ingredient i USING(ingredient_id) WHERE q.recipe_id=1397 AND q.optional='TRUE' ORDER BY i.name",
"SELECT r.title FROM Recipe r JOIN Nutrition n USING(recipe_id) WHERE n.calories=(SELECT MAX(calories) FROM Nutrition)",
"SELECT r.title FROM Recipe r JOIN Nutrition n USING(recipe_id) WHERE n.vitamin_c=(SELECT MAX(vitamin_c) FROM Nutrition)",
"SELECT DISTINCT r.title,i.name FROM Recipe r JOIN Quantity q USING(recipe_id) JOIN Ingredient i USING(ingredient_id) WHERE r.cook_min=(SELECT MAX(cook_min) FROM Recipe) ORDER BY r.title,i.name",
"SELECT COUNT(DISTINCT r.recipe_id) FROM Recipe r JOIN Quantity q USING(recipe_id) JOIN Ingredient i USING(ingredient_id) WHERE r.servings>10 AND i.category='dairy'",
"SELECT COUNT(DISTINCT q.ingredient_id) FROM Recipe r JOIN Quantity q USING(recipe_id) WHERE r.title='Apricot Yogurt Parfaits'",
"SELECT r.title FROM Recipe r JOIN Nutrition n USING(recipe_id) WHERE n.alcohol>10 AND r.prep_min=(SELECT MAX(r2.prep_min) FROM Recipe r2 JOIN Nutrition n2 USING(recipe_id) WHERE n2.alcohol>10)",
"SELECT n.calories*n.pcnt_cal_fat/100.0 FROM Recipe r JOIN Nutrition n USING(recipe_id) WHERE r.title='Raspberry Chiffon Pie'"
],
'disney': [
"SELECT COUNT(*) FROM director WHERE director='Wolfgang Reitherman'",
"SELECT m.movie_title FROM movies_total_gross m JOIN director d ON d.name=m.movie_title WHERE d.director='Wolfgang Reitherman' AND CAST(REPLACE(REPLACE(m.total_gross,'$',''),',','') AS REAL)=(SELECT MAX(CAST(REPLACE(REPLACE(m2.total_gross,'$',''),',','') AS REAL)) FROM movies_total_gross m2 JOIN director d2 ON d2.name=m2.movie_title WHERE d2.director='Wolfgang Reitherman')",
"SELECT COUNT(*) FROM movies_total_gross WHERE genre='Horror'",
"SELECT DISTINCT m.MPAA_rating FROM characters c JOIN movies_total_gross m USING(movie_title) WHERE c.villian='Turbo'",
"SELECT c.hero FROM characters c JOIN director d ON c.movie_title=d.name WHERE d.director='Will Finn'",
"SELECT director FROM director WHERE name='Pinocchio'",
"SELECT m.total_gross FROM characters c JOIN movies_total_gross m USING(movie_title) WHERE c.song='Little Wonders'",
"SELECT DISTINCT m.movie_title FROM director d JOIN movies_total_gross m ON m.movie_title=d.name WHERE d.director='Wolfgang Reitherman' AND m.MPAA_rating='G' ORDER BY m.movie_title",
"SELECT c.hero FROM characters c JOIN movies_total_gross m USING(movie_title) WHERE m.total_gross='$222,527,828'",
"SELECT c.song FROM characters c JOIN director d ON c.movie_title=d.name WHERE d.director='Ben Sharpsteen'",
"SELECT DISTINCT m.genre FROM characters c JOIN movies_total_gross m USING(movie_title) WHERE c.villian='Commander Rourke'",
"SELECT c.hero,d.director,c.release_date FROM characters c JOIN director d ON c.movie_title=d.name WHERE c.movie_title='Mulan'",
"SELECT COUNT(DISTINCT m.movie_title) FROM director d JOIN movies_total_gross m ON m.movie_title=d.name WHERE d.director='Ron Clements' AND m.genre='Adventure' AND m.MPAA_rating='PG'",
"SELECT d.director FROM director d JOIN movies_total_gross m ON m.movie_title=d.name WHERE m.genre='Adventure' AND m.release_date='Mar 30, 2007'",
"SELECT c.villian FROM characters c JOIN movies_total_gross m USING(movie_title) WHERE CAST(REPLACE(REPLACE(m.total_gross,'$',''),',','') AS REAL)=(SELECT MAX(CAST(REPLACE(REPLACE(total_gross,'$',''),',','') AS REAL)) FROM movies_total_gross)",
"SELECT c.release_date FROM characters c JOIN director d ON c.movie_title=d.name WHERE c.movie_title='The Lion King' AND d.director='Roger Allers'",
"SELECT c.movie_title FROM characters c JOIN director d ON c.movie_title=d.name WHERE d.director='Wolfgang Reitherman' AND c.villian IS NULL ORDER BY c.movie_title",
"SELECT DISTINCT m.genre FROM characters c JOIN movies_total_gross m USING(movie_title) WHERE c.hero='Taran'",
"SELECT DISTINCT c.villian FROM characters c JOIN director d ON c.movie_title=d.name WHERE d.director='Wolfgang Reitherman' AND c.villian IS NOT NULL ORDER BY c.villian",
"SELECT movie_title FROM characters WHERE song='I Thought I Lost You'"
],
'genes': [
"SELECT DISTINCT Chromosome FROM Genes WHERE Localization='plasma membrane' ORDER BY Chromosome",
"SELECT DISTINCT i.Type FROM Interactions i WHERE EXISTS(SELECT 1 FROM Genes g WHERE (g.GeneID=i.GeneID1 OR g.GeneID=i.GeneID2) AND g.Essential='Non-Essential' AND g.Function='CELLULAR TRANSPORT AND TRANSPORTMECHANISMS') ORDER BY i.Type",
"SELECT DISTINCT Localization FROM Genes WHERE Chromosome=(SELECT MAX(Chromosome) FROM Genes) ORDER BY Localization",
"SELECT DISTINCT GeneID FROM Genes WHERE Localization='cytoplasm' AND Function='METABOLISM' ORDER BY GeneID",
"SELECT COUNT(DISTINCT GeneID) FROM Genes WHERE Localization='nucleus' AND Essential='Non-Essential'",
"SELECT AVG(i.Expression_Corr) FROM Interactions i WHERE EXISTS(SELECT 1 FROM Genes g WHERE g.GeneID=i.GeneID1 AND g.Class='ATPases') AND EXISTS(SELECT 1 FROM Genes g WHERE g.GeneID=i.GeneID2 AND g.Class='ATPases')",
"SELECT DISTINCT Motif FROM Genes WHERE Localization='cytoplasm' AND Chromosome=7 ORDER BY Motif",
"SELECT DISTINCT g.GeneID,g.Function FROM Genes g JOIN Interactions i ON g.GeneID=i.GeneID1 OR g.GeneID=i.GeneID2 WHERE i.Expression_Corr=(SELECT MIN(Expression_Corr) FROM Interactions) ORDER BY g.GeneID,g.Function",
"SELECT COUNT(*) FROM Interactions i WHERE i.Expression_Corr>0 AND EXISTS(SELECT 1 FROM Genes g WHERE g.GeneID=i.GeneID1 AND g.Essential='Non-Essential') AND EXISTS(SELECT 1 FROM Genes g WHERE g.GeneID=i.GeneID2 AND g.Essential='Non-Essential')",
"SELECT COUNT(*) FROM Interactions i WHERE i.Expression_Corr<0 AND NOT EXISTS(SELECT 1 FROM Genes g WHERE g.GeneID=i.GeneID1 AND g.Class='Motorproteins') AND NOT EXISTS(SELECT 1 FROM Genes g WHERE g.GeneID=i.GeneID2 AND g.Class='Motorproteins')"
],
'ice_hockey_draft': [
"SELECT p.PlayerName FROM PlayerInfo p JOIN weight_info w ON w.weight_id=p.weight WHERE w.weight_in_lbs=190 ORDER BY p.ELITEID",
"SELECT p.PlayerName FROM PlayerInfo p JOIN height_info h ON h.height_id=p.height WHERE h.height_in_cm=(SELECT MAX(h2.height_in_cm) FROM PlayerInfo p2 JOIN height_info h2 ON h2.height_id=p2.height)",
"SELECT DISTINCT p.PlayerName,w.weight_in_kg FROM PlayerInfo p JOIN weight_info w ON w.weight_id=p.weight JOIN SeasonStatus s USING(ELITEID) WHERE s.PLUSMINUS=(SELECT MAX(PLUSMINUS) FROM SeasonStatus)",
"SELECT DISTINCT p.PlayerName,h.height_in_inch FROM PlayerInfo p JOIN height_info h ON h.height_id=p.height JOIN SeasonStatus s USING(ELITEID) WHERE s.TEAM='Oshawa Generals' ORDER BY p.PlayerName",
"SELECT p.PlayerName FROM PlayerInfo p JOIN height_info h ON h.height_id=p.height WHERE p.nation='Italy' AND h.height_in_cm=(SELECT MIN(h2.height_in_cm) FROM PlayerInfo p2 JOIN height_info h2 ON h2.height_id=p2.height WHERE p2.nation='Italy')",
"SELECT birthplace FROM PlayerInfo WHERE PlayerName='Aaron Gagnon'",
"SELECT COUNT(*) FROM PlayerInfo p JOIN weight_info w ON w.weight_id=p.weight WHERE w.weight_in_kg>90",
"SELECT DISTINCT s.SEASON FROM PlayerInfo p JOIN SeasonStatus s USING(ELITEID) WHERE p.PlayerName='Niklas Eckerblom' ORDER BY s.SEASON",
"SELECT DISTINCT p.PlayerName FROM PlayerInfo p JOIN SeasonStatus s USING(ELITEID) WHERE p.overallby='Arizona Coyotes' AND p.draftyear=2000 AND s.PIM=(SELECT MAX(s2.PIM) FROM PlayerInfo p2 JOIN SeasonStatus s2 USING(ELITEID) WHERE p2.overallby='Arizona Coyotes' AND p2.draftyear=2000)",
"SELECT COUNT(*) FROM PlayerInfo p JOIN height_info h ON h.height_id=p.height WHERE p.shoots='R' AND h.height_id=67",
"SELECT DISTINCT p.PlayerName FROM PlayerInfo p JOIN SeasonStatus s USING(ELITEID) WHERE s.TEAM='Avangard Omsk' AND s.SEASON='2000-2001' AND s.LEAGUE='International' AND s.G=0 ORDER BY p.PlayerName",
"SELECT MAX(h.height_in_cm) FROM PlayerInfo p JOIN height_info h ON h.height_id=p.height WHERE p.birthplace='Edmonton, AB, CAN'",
"SELECT DISTINCT p.PlayerName FROM PlayerInfo p JOIN SeasonStatus s USING(ELITEID) WHERE s.TEAM='Avangard Omsk' AND s.SEASON='2000-2001' AND s.GAMETYPE='Regular Season' AND p.birthdate=(SELECT MIN(p2.birthdate) FROM PlayerInfo p2 JOIN SeasonStatus s2 USING(ELITEID) WHERE s2.TEAM='Avangard Omsk' AND s2.SEASON='2000-2001' AND s2.GAMETYPE='Regular Season')",
"SELECT PlayerName FROM PlayerInfo WHERE overallby='Toronto Maple Leafs' AND draftyear=2008 AND CSS_rank=(SELECT MIN(CSS_rank) FROM PlayerInfo WHERE overallby='Toronto Maple Leafs' AND draftyear=2008)",
"SELECT COUNT(*) FROM PlayerInfo p JOIN height_info h ON h.height_id=p.height WHERE p.birthyear=1982 AND h.height_in_cm>182",
"SELECT DISTINCT s.TEAM FROM PlayerInfo p JOIN SeasonStatus s USING(ELITEID) WHERE p.PlayerName='Andreas Jamtin' ORDER BY s.TEAM",
"SELECT h.height_in_inch FROM PlayerInfo p JOIN height_info h ON h.height_id=p.height WHERE p.PlayerName='David Bornhammar'",
"SELECT DISTINCT p.PlayerName FROM PlayerInfo p JOIN SeasonStatus s USING(ELITEID) WHERE p.sum_7yr_GP>=500 AND s.PIM=(SELECT MAX(s2.PIM) FROM PlayerInfo p2 JOIN SeasonStatus s2 USING(ELITEID) WHERE p2.sum_7yr_GP>=500)",
"SELECT COUNT(DISTINCT p.ELITEID) FROM PlayerInfo p JOIN SeasonStatus s USING(ELITEID) WHERE s.GP=72 AND p.shoots='L'",
"SELECT DISTINCT p.PlayerName FROM PlayerInfo p JOIN SeasonStatus s USING(ELITEID) WHERE trim(s.TEAM)='Chilliwack Chiefs' AND s.LEAGUE='NHL' AND s.P>=100 ORDER BY p.PlayerName"
]}

AMBIGUITIES = {
('cookbook', 7): 'Most likely to gain weight does not uniquely define maximum calories or a dietary outcome; fixed SQL uses maximum reported calories.',
('cookbook', 9): 'Required ingredients may exclude optional rows, or count all listed ingredients; fixed SQL counts distinct listed ingredient IDs.',
('cookbook', 16): 'Dairy recipe is not a stored recipe category; fixed SQL means at least one ingredient explicitly categorized dairy, not cheese/canned/frozen dairy.',
('cookbook', 19): 'Calories from fat is an energy amount, while pcnt_cal_fat is a percentage. Fixed SQL computes calories times percent / 100; grams of total fat times 9 gives a rounded alternative.',
('disney', 1): 'Most popular has no unique metric; fixed SQL uses numeric nominal total gross rather than inflation-adjusted gross.',
('disney', 14): 'Most popular has no unique metric; fixed SQL uses global numeric nominal total gross and then joins the character table, without restricting the maximum to joinable movies.',
('genes', 0): 'Question says number of chromosomes while Chromosome plausibly denotes an index; fixed SQL returns stored chromosome values.',
('genes', 1): 'Transport medicine has no exact database category, and endpoints satisfying the gene restriction are underspecified. Fixed SQL interprets transport mechanisms and at least one qualifying endpoint.',
('genes', 2): 'Most chromosomes confuses chromosome count with the stored Chromosome field; fixed SQL uses maximum stored value.',
('genes', 5): 'Interactions contains reciprocal endpoint rows. Fixed SQL averages recorded ordered interactions once each; unordered-pair averaging may differ.',
('genes', 6): 'Seven chromosomes versus chromosome 7 is underspecified; fixed SQL uses Chromosome=7.',
('genes', 8): 'Pair counting could mean ordered interaction records or distinct unordered pairs; fixed SQL counts records and avoids Genes annotation join multiplicity.',
('genes', 9): 'Pair counting orientation and both-endpoint restriction are not explicit. Fixed SQL counts records with neither endpoint annotated Motorproteins.',
('ice_hockey_draft', 2): 'All-time goal differential may mean cumulative career value; fixed SQL uses maximum recorded season PLUSMINUS and preserves ties.',
('ice_hockey_draft', 8): 'Rule violations could mean count or penalty minutes and single-season versus cumulative. Fixed SQL uses maximum recorded season PIM in the stated player pool.',
('ice_hockey_draft', 10): 'International league and draft-year qualifiers conflict with available team-season rows. Fixed SQL applies the literal International league and season with G=0, without inventing a draft-year conversion.',
('ice_hockey_draft', 13): 'Highest prospects is not an explicit numeric metric. Fixed SQL interprets lower CSS_rank as better; it does not take the largest rank number.',
('ice_hockey_draft', 15): 'Belong to has no season/current-team qualifier. Fixed SQL lists every distinct recorded historical team.',
('ice_hockey_draft', 17): 'Most rule violations may mean career sum rather than maximum recorded season PIM; fixed SQL uses the latter within the stated first-seven-year GP pool.',
('ice_hockey_draft', 18): 'Played 72 games may refer to a season or career total. Fixed SQL uses a recorded SeasonStatus.GP=72 and counts distinct players.',
('ice_hockey_draft', 19): 'Question requests NHL points for Chilliwack Chiefs, but the database has no NHL league rows. Literal fixed SQL yields empty; removing NHL or treating points as career totals changes the question.',
}

NOTES = {
('cookbook', 5): 'Interpret vision-in-dim-light vitamin as vitamin A. Return all ingredients of every tied highest-vitamin-A recipe; recipe title is auxiliary context.',
('cookbook', 10): 'Require matching almonds, cups and quantity; equal minimum/maximum can be reported as one number.',
('cookbook', 15): 'Cooking time means cook_min, not prep_min+stnd_min+cook_min. Preserve every tied recipe and all ingredient names.',
('cookbook', 18): 'Preparation time means prep_min in this specified interpretation; alcohol threshold is applied before maximum.',
('disney', 11): 'Normalize textual date format only; hero, director and date must all match.',
('disney', 15): 'Normalize textual date format only, including the two-digit historical year.',
('disney', 18): 'List actual non-null villain names; a note that other movies have no villain is allowed.',
('genes', 3): 'Distinct GeneID, not duplicate annotation rows.',
('genes', 4): 'Count distinct genes, not duplicate function/class annotation rows.',
('genes', 7): 'Functions for both endpoints of every minimum-correlation interaction; grouping by GeneID or an unambiguous complete union accepted.',
('ice_hockey_draft', 3): 'All distinct matching players and corresponding heights; no duplicate season rows. Numeric inch conversion equivalent to stored feet/inch string accepted.',
('ice_hockey_draft', 9): 'height_id 67 is the stored 5-foot-7 height key, verified against height_info before freezing.',
('ice_hockey_draft', 12): 'Oldest means minimum full ISO birthdate in the specified team-season-gametype pool, including ties.',
('ice_hockey_draft', 16): 'Numeric inches or equivalent feet/inch string accepted.',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    setup_path = ROOT / 'research/evidence/vakra_domain_expansion_setup_v1.json'
    setup = json.loads(setup_path.read_bytes())
    cards = []
    for domain in setup['domains']:
        name = domain['domain']
        base = ROOT / 'results/vakra-domain-expansion-v1' / name
        queries = json.loads((base / 'queries.json').read_bytes())[:20]
        assert len(SQL[name]) == len(queries)
        db = base / (name + '.sqlite')
        assert sha(db) == domain['database_sha256']
        with sqlite3.connect(db.resolve().as_uri() + '?mode=ro', uri=True) as con:
            if name == 'ice_hockey_draft':
                assert con.execute('SELECT height_in_inch FROM height_info WHERE height_id=67').fetchone()[0] == '5\'7"'
            for index, (q, sql) in enumerate(zip(queries, SQL[name])):
                assert q['uuid'] == domain['selected_task_ids'][index]
                result = con.execute(sql)
                values = result.fetchall()
                cards.append({'domain': name, 'task_index': index, 'uuid': q['uuid'],
                              'query': q['dialogue']['turns'][0]['query'], 'sql': sql,
                              'columns': [c[0] for c in result.description], 'answer_rows': values,
                              'database_sha256': sha(db),
                              'interpretation_stratum': 'ambiguous' if (name,index) in AMBIGUITIES else 'specified_sql_interpretation',
                              'ambiguity': AMBIGUITIES.get((name,index)),
                              'acceptance_note': NOTES.get((name,index), 'Require all requested values. Ignore row order where no ordering is requested; preserve ties and entity identity. Do not accept a procedure without an answer.')})
    assert len(cards) == 70
    report = {'purpose': __doc__, 'setup_sha256': sha(setup_path), 'script_sha256': sha(Path(__file__)),
              'model_answers_seen': False, 'cards': cards,
              'numeric_tolerance': 'Accept faithful rounding within half of the last reported decimal place; do not conflate percentages with amounts. Counts are exact.',
              'score_policy': 'Primary SQL-interpretation subtotal excludes only the ambiguity keys already listed here, retaining all seventy tasks in execution accounting. Report ambiguous outcomes separately. Absent final answers count incorrect. Correctness does not imply trace grounding. Later ambiguities are disclosed without retrospective denominator changes.',
              'limitations': 'Assistant-authored interpretations, not independent human consensus, official VAKRA score or biomedical/historical factual claims. Public training-split tasks newly held out from this development process.'}
    path = ROOT / 'research/evidence/vakra_domain_expansion_sql_cards_v1.json'
    with path.open('x', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({'cards':len(cards), 'ambiguous':sum(r['interpretation_stratum']=='ambiguous' for r in cards),
                      'by_domain':{d:{'n':sum(r['domain']==d for r in cards),
                                     'ambiguous':sum(r['domain']==d and r['interpretation_stratum']=='ambiguous' for r in cards)} for d in SQL}}, indent=2))


if __name__ == '__main__':
    main()
