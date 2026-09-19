"""Offline query/reference audit. Never ship these answer cards to an agent."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3


CARDS = [
    ("486ea46224d1-2b5bb9f47372", "SELECT c.Name FROM Country c JOIN CountryLanguage l ON c.Code=l.CountryCode WHERE l.Language='English' AND l.IsOfficial='T' ORDER BY c.Code",
     "Any five distinct eligible countries satisfy the query; matching the reference's exact first five is unnecessary."),
    ("486ea46224d1-674a4702614a", "SELECT COUNT(*) FROM City WHERE District='England'",
     "Count only England records, not all City rows."),
    ("486ea46224d1-74c57403a8e6", "SELECT Language FROM CountryLanguage WHERE CountryCode='TKM' ORDER BY Language",
     "Complete language set required, including Uzbek. Official language alone is insufficient."),
    ("486ea46224d1-9bae74dab965", "SELECT c.Name,c.Capital,city.Name,l.Language FROM Country c JOIN City city ON c.Capital=city.ID JOIN CountryLanguage l ON c.Code=l.CountryCode WHERE c.LifeExpectancy=(SELECT MAX(LifeExpectancy) FROM Country) AND l.IsOfficial='T'",
     "Reference uses numeric capital ID; the query asks for the capital city. Resolve the foreign key for semantic audit. Include only official languages."),
    ("486ea46224d1-27cb99545c51", "SELECT DISTINCT l.Language FROM Country c JOIN CountryLanguage l ON c.Code=l.CountryCode WHERE c.Region='Baltic Countries' AND l.Percentage>80 ORDER BY l.Language",
     "Percentage is strictly greater than 80; exact language set."),
    ("486ea46224d1-aff4c9603f4d", "SELECT city.Name,c.Code,c.Name,c.LifeExpectancy FROM City city JOIN Country c ON c.Code=city.CountryCode WHERE city.Population=(SELECT MAX(Population) FROM City)",
     "Reference country is a code. Its corresponding country name is semantically equivalent."),
    ("486ea46224d1-7d79ad7c0e0e", "SELECT c.Name,c.Population,c.Capital,city.Name,l.Language FROM Country c JOIN City city ON c.Capital=city.ID JOIN CountryLanguage l ON c.Code=l.CountryCode WHERE c.SurfaceArea=(SELECT MIN(SurfaceArea) FROM Country) AND l.IsOfficial='T'",
     "Reference uses numeric capital ID. Distinguish country population from city population and official from merely spoken languages."),
    ("486ea46224d1-65e39fac89be", "SELECT Name,Population,District FROM City WHERE Population=(SELECT MIN(Population) FROM City)",
     "The stored district is an en dash. Explicitly reporting that the district is unspecified is semantically different from claiming tool failure."),
    ("486ea46224d1-cd809c9ef7fa", "SELECT Name,Continent FROM Country WHERE SurfaceArea=(SELECT MIN(SurfaceArea) FROM Country)",
     "Return continent of the minimum-surface-area country."),
    ("486ea46224d1-cd446461ab5d", "SELECT city.Name,c.Name,c.HeadOfState FROM City city JOIN Country c ON c.Code=city.CountryCode WHERE city.Population=(SELECT MAX(Population) FROM City)",
     "Reference interprets most crowded as largest population, not density. Answer is relative to this historical database, not current head of state."),
    ("486ea46224d1-5df43dad6593", "SELECT c.Code,c.Name,c.Capital FROM Country c JOIN CountryLanguage l ON c.Code=l.CountryCode WHERE l.Language='English' AND l.IsOfficial='T' ORDER BY c.Capital DESC LIMIT 1",
     "Ambiguous natural-language query: reference maximizes capital-city identifier, not altitude, population or financial capital. Report reference compatibility separately; do not call this unambiguous semantic correctness."),
    ("486ea46224d1-c859d649b4b5", "SELECT city.Name FROM City city JOIN Country c ON c.Code=city.CountryCode WHERE c.LifeExpectancy=66.4 ORDER BY city.ID",
     "Complete city set; do not stop at a preview unless its coverage is complete."),
]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    database = args.dataset / "databases/world/world.sqlite"
    inputs = args.dataset / "train/capability_1_bi_apis/input/world.json"
    reference = args.dataset / "train/capability_1_bi_apis/output/world.json"
    queries = json.loads(inputs.read_bytes())
    gold = {x["uuid"]:x for x in json.loads(reference.read_bytes())}
    if [q["uuid"] for q in queries[:12]] != [c[0] for c in CARDS]:
        raise ValueError("Frozen task order changed")
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    cards = []
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as db:
        for query, (uuid, sql, note) in zip(queries, CARDS):
            ref = gold[uuid]["output"][0]
            text = query["dialogue"]["turns"][0]["query"]
            if ref["query"] != text:
                raise ValueError("Reference/input query mismatch")
            result = db.execute(sql)
            cards.append({"uuid": uuid, "query": text, "reference_answer": ref["answer"],
                          "audit_sql": sql, "columns": [c[0] for c in result.description],
                          "rows": result.fetchall(), "interpretation": note})
    if hashlib.sha256(database.read_bytes()).hexdigest() != before:
        raise ValueError("Database mutated")
    report = {"purpose": "offline assistant-authored semantic audit cards, not an official evaluator or human annotation",
              "model_outputs_inspected": "first4-v1 only; coverage12 outcomes not used to define these cards",
              "input_sha256": {str(x.relative_to(args.dataset)): hashlib.sha256(x.read_bytes()).hexdigest()
                               for x in (database, inputs, reference)}, "cards": cards}
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({"cards": len(cards), "database_unchanged": True}))


if __name__ == "__main__":
    main()
