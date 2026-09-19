"""Bounded, offline database mutations; never a completeness certificate.

Candidates reuse values from the same column and leave declared keys alone.
The target SQL is an evaluator-side interpretation, never agent input.
"""
import hashlib
import json
import random
import sqlite3


def quoted(name):
    return '"' + name.replace('"', '""') + '"'


def answer(connection, sql):
    # Bag equality ignores only row order, preserving duplicate multiplicities.
    return sorted([list(row) for row in connection.execute(sql)],
                  key=lambda row: json.dumps(row, ensure_ascii=False, sort_keys=True))


def candidate_columns(connection, sql):
    reads = set()

    def record(action, table, column, *unused):
        if action == sqlite3.SQLITE_READ and column:
            reads.add((table, column))
        return sqlite3.SQLITE_OK

    connection.set_authorizer(record)
    try:
        answer(connection, sql)
    finally:
        connection.set_authorizer(None)
    pools = []
    for table, column in sorted(reads):
        info = connection.execute(f'PRAGMA table_info({quoted(table)})').fetchall()
        keys = [r[1] for r in sorted(info, key=lambda r: r[5]) if r[5]]
        protected = set(keys)
        protected.update(r[3] for r in connection.execute(f'PRAGMA foreign_key_list({quoted(table)})'))
        for index in connection.execute(f'PRAGMA index_list({quoted(table)})'):
            if index[2]:
                protected.update(r[2] for r in connection.execute(f'PRAGMA index_info({quoted(index[1])})'))
        if column in protected:
            continue
        if not keys:
            # Avoid ambiguous aliases if a schema shadows SQLite's rowid names.
            names = {r[1].lower() for r in info}
            keys = [next((x for x in ('rowid', '_rowid_', 'oid') if x not in names), '')]
            if not keys[0]:
                continue
        projection = ','.join(quoted(k) for k in [*keys, column])
        try:
            rows = connection.execute(f'SELECT {projection} FROM {quoted(table)} ORDER BY '
                                      + ','.join(quoted(k) for k in keys)).fetchall()
        except sqlite3.OperationalError:
            continue
        rows = [r for r in rows if r[-1] is not None and not isinstance(r[-1], bytes)]
        if len({(type(r[-1]).__name__, r[-1]) for r in rows}) > 1:
            pools.append({'table': table, 'column': column, 'keys': keys, 'rows': rows})
    return pools


def apply(connection, mutation):
    table, column, keys = (mutation[k] for k in ('table', 'column', 'keys'))
    where = ' AND '.join(f'{quoted(k)} IS ?' for k in keys)
    for change in mutation['changes']:
        actual = connection.execute(f'SELECT {quoted(column)} FROM {quoted(table)} WHERE {where}',
                                    change['key']).fetchall()
        if actual != [(change['before'],)]:
            raise ValueError('Mutation precondition does not identify one unchanged row')
    for change in mutation['changes']:
        cursor = connection.execute(f'UPDATE {quoted(table)} SET {quoted(column)}=? WHERE {where}',
                                    [change['after'], *change['key']])
        if cursor.rowcount != 1:
            raise ValueError('Mutation changed an unexpected number of rows')


def search(connection, sql, task_id, proposals=2048, retained=8):
    original = answer(connection, sql)
    foreign_errors = connection.execute('PRAGMA foreign_key_check').fetchall()
    pools = candidate_columns(connection, sql)
    seed = hashlib.sha256(('20260919:' + task_id).encode()).hexdigest()
    rng = random.Random(seed)
    result = {'seed': seed, 'proposal_limit': proposals, 'retained_limit': retained,
              'eligible_columns': [{k: p[k] for k in ('table', 'column', 'keys')} for p in pools],
              'original_answer': original, 'draws': 0, 'unchanged_answers': 0,
              'constraint_rejections': 0, 'candidates': []}
    seen = set()
    if not pools:
        return result
    for draw in range(proposals):
        result['draws'] += 1
        pool = pools[draw % len(pools)]
        left, right = rng.sample(pool['rows'], 2)
        if type(left[-1]) != type(right[-1]) or left[-1] == right[-1]:
            continue
        mutation = {k: pool[k] for k in ('table', 'column', 'keys')}
        mutation['operator'] = 'replace_observed_value' if rng.randrange(2) else 'swap_values'
        mutation['changes'] = [{'key': list(left[:-1]), 'before': left[-1], 'after': right[-1]}]
        if mutation['operator'] == 'swap_values':
            mutation['changes'].append({'key': list(right[:-1]), 'before': right[-1], 'after': left[-1]})
        identity = json.dumps(mutation, sort_keys=True, ensure_ascii=False)
        if identity in seen:
            continue
        seen.add(identity)
        connection.execute('SAVEPOINT candidate')
        try:
            apply(connection, mutation)
            if connection.execute('PRAGMA foreign_key_check').fetchall() != foreign_errors:
                result['constraint_rejections'] += 1
                continue
            changed = answer(connection, sql)
            if changed == original:
                result['unchanged_answers'] += 1
            else:
                result['candidates'].append({'draw': draw, 'mutation': mutation, 'answer': changed})
        except sqlite3.IntegrityError:
            result['constraint_rejections'] += 1
        finally:
            connection.execute('ROLLBACK TO candidate')
            connection.execute('RELEASE candidate')
        if len(result['candidates']) >= retained:
            break
    assert answer(connection, sql) == original
    return result
