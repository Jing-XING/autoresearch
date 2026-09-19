"""Structural accounting of declared experiment identities, not significance."""
import hashlib
import json
import math

VIEWS = ('small_paired', 'repeated_paired', 'larger_paired', 'disjoint', 'partial')
FIELDS = ('unique_a', 'unique_b', 'matched_pairs', 'redundant_reports', 'design')
SYSTEM = (
    'Audit experiment records. A and B are two estimators. Within this example, '
    'one resample_id denotes one sampled label set. An evaluation_id identifies '
    'one estimator evaluated on one resample. Different arms on the same resample '
    'are valid matched evaluations, not duplicates. Multiple reports with the '
    'same evaluation_id are repeated displays of that evaluation, not new trials. '
    'Distinct resample IDs mean distinct RNG invocations, not distinct datasets. '
    'Return one JSON object, without a code fence, containing exactly unique_a '
    '(number of distinct A evaluations), unique_b, matched_pairs (resamples '
    'having both A and B), redundant_reports (display rows beyond unique '
    'evaluations), and design. Design is paired when both arms have exactly the '
    'same nonempty resample set, disjoint when their sets do not intersect, or '
    'partial otherwise. Do not assess which estimator is better.'
)


def opaque(value):
    return hashlib.sha256(value.encode()).hexdigest()[:20]


def build_example(pool, components, view):
    """components is a list of saved [e0,d] values for one fixed pool/budget."""
    if view not in VIEWS or len(components) < 24:
        raise ValueError('Unknown view or insufficient saved components')
    if any(len(r) != 2 or not all(math.isfinite(x) for x in r) for r in components):
        raise ValueError('Invalid component array')
    a = list(range(4 if view in VIEWS[:2] else 12))
    b = list(range(12,24)) if view == 'disjoint' else list(range(8,20)) if view == 'partial' else a
    copies = 3 if view == 'repeated_paired' else 1
    example_id = opaque(f'unit-pilot-v1/{pool}/{view}')
    rows, origins = [], {}
    for arm, indices in [('A',a), ('B',b)]:
        for j in indices:
            sample = opaque(f'unit-pilot-v1/{pool}/100/{202609200000+j}')
            evaluation = opaque(sample+'/'+arm)
            error = components[j][0] + (components[j][1] if arm == 'B' else 0)
            origins[evaluation] = {'pool': pool, 'block': 0, 'budget_index': 1,
                                  'seed_index': j, 'arm': arm, 'components': list(components[j])}
            for k in range(copies):
                report = opaque(example_id+'/'+evaluation+'/'+str(k))
                rows.append({'report_id':report,'evaluation_id':evaluation,
                             'resample_id':sample,'arm':arm,'squared_error':error**2})
    rows.sort(key=lambda x:opaque(example_id+'/'+x['report_id']))
    return {'id':example_id,'reports':rows}, origins


def account(item):
    evaluations, reports, samples = {}, set(), {'A':set(), 'B':set()}
    for row in item['reports']:
        if set(row) != {'report_id','evaluation_id','resample_id','arm','squared_error'}:
            raise ValueError('Unexpected record schema')
        if row['report_id'] in reports:
            raise ValueError('Duplicate display identifier')
        reports.add(row['report_id'])
        arm = row['arm']
        if arm not in samples or not math.isfinite(row['squared_error']) or row['squared_error'] < 0:
            raise ValueError('Invalid arm or value')
        identity = (arm, row['resample_id'], row['squared_error'])
        key = row['evaluation_id']
        if key in evaluations and evaluations[key] != identity:
            raise ValueError('Conflicting evaluation identity')
        evaluations[key] = identity
    # One deterministic estimator evaluation per arm/resample in this protocol.
    # Do not silently treat a second evaluation ID for it as a new replicate.
    if len({x[:2] for x in evaluations.values()}) != len(evaluations):
        raise ValueError('Two evaluation IDs alias the same arm/resample')
    for arm, sample, value in evaluations.values():
        samples[arm].add(sample)
    if not samples['A'] or not samples['B']:
        raise ValueError('Both arms must be observed')
    common = samples['A'] & samples['B']
    return dict(unique_a=len(samples['A']), unique_b=len(samples['B']),
                matched_pairs=len(common), redundant_reports=len(reports)-len(evaluations),
                design='paired' if samples['A']==samples['B'] else 'partial' if common else 'disjoint')


def score(text, expected):
    """Strict field scoring; malformed and extra-field responses stay incorrect."""
    def pairs(items):
        d={}
        for k,v in items:
            if k in d:raise ValueError('Duplicate JSON key')
            d[k]=v
        return d
    try:
        result=json.loads(text,object_pairs_hook=pairs)
        if not isinstance(result,dict) or set(result)!=set(FIELDS):raise ValueError('Schema')
        for name in FIELDS[:-1]:
            if type(result[name]) is not int or result[name]<0:raise ValueError('Count type')
        if result['design'] not in ('paired','disjoint','partial'):raise ValueError('Design')
    except (TypeError, ValueError):
        return {'valid':False,'correct':False,'fields':{k:False for k in FIELDS}}
    fields={k:result[k]==expected[k] for k in FIELDS}
    return {'valid':True,'correct':all(fields.values()),'fields':fields}
