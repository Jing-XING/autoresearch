"""Passive VAKRA observation lineage; no database, answer key or model access.

This is an analysis instrument, not a natural-language correctness verifier.
Only documented selection/sort/getter semantics receive lineage claims.
Unknown operations lose certified lineage instead of inheriting a convenient
earlier filter. It is not yet connected to model prompts or a policy.
"""
from copy import deepcopy
import json


CONDITIONS = {'equal_to', 'not_equal_to', 'greater_than', 'less_than',
              'greater_than_equal_to', 'less_than_equal_to', 'contains', 'like'}


def decode_observation(result):
    texts = [x.get('text', '') for x in result.get('content', []) if x.get('type') == 'text']
    text = '\n'.join(texts)
    try:
        value = json.loads(text)
    except (ValueError, TypeError):
        value = text
    error = bool(result.get('isError')) or text.startswith('Input validation error:')
    error = error or (isinstance(value, dict) and 'error' in value)
    return value, error


class EvidenceLedger:
    def __init__(self, initial_peek, universe_id, tool_names):
        self.universe_id = universe_id
        self.tool_names = set(tool_names)
        self.handles = {}
        self.events = []
        self._register(initial_peek, [], [], 'initial_relation')

    def _register(self, peek, predicates, order, lineage_status):
        count = peek.get('num_records')
        if type(count) is not int or count < 0 or not isinstance(peek.get('handle'), str):
            raise ValueError('Invalid observed handle/cardinality')
        columns = {}
        for column in peek.get('key_details', []):
            values = column.get('first_3_values')
            if not isinstance(values, list) or len(values) > min(3, count):
                raise ValueError('Invalid preview cardinality')
            columns[column['name']] = {'preview_values': len(values),
                                       'complete_column_observed': len(values) == count,
                                       'full_getter_observed': False}
        state = {'handle': peek['handle'], 'num_records': count, 'columns': columns,
                 'predicates': deepcopy(predicates), 'order': deepcopy(order),
                 'lineage_status': lineage_status}
        self.handles[peek['handle']] = state
        return state

    @staticmethod
    def _scope(state):
        if state is None:
            return {'lineage_status': 'unknown_source'}
        return {k: deepcopy(state[k]) for k in ('handle', 'num_records', 'predicates', 'order', 'lineage_status')}

    def observe(self, call, result):
        name, args = call['name'], call.get('arguments', {})
        value, error = decode_observation(result)
        source = self.handles.get(args.get('data_label'))
        event = {'tool': name, 'source_scope': self._scope(source),
                 'status': 'error' if error else 'observed',
                 'query_semantics_verified': False}
        if error:
            self.events.append(event)
            return deepcopy(event)

        if isinstance(value, dict) and 'handle' in value and 'num_records' in value:
            predicates, order, status = [], [], 'unknown_operation'
            if name == 'get_data':
                universe = args.get('tool_universe_id')
                if universe is not None and universe != self.universe_id:
                    self.handles.clear()
                    self.universe_id = universe
                status = 'initial_relation'
            elif source is not None and source['lineage_status'] != 'unknown_operation':
                condition = name.removeprefix('select_data_')
                if condition in CONDITIONS and name.startswith('select_data_'):
                    # Reject conflicting explicitly supplied bound parameters.
                    if args.get('condition', condition) == condition and args.get('key_name') in source['columns']:
                        predicates = source['predicates'] + [{
                            'column': args['key_name'], 'operator': condition, 'value': deepcopy(args.get('value'))}]
                        order, status = source['order'], 'known_operations'
                elif name in ('sort_data_ascending', 'sort_data_descending'):
                    ascending = name == 'sort_data_ascending'
                    if args.get('ascending', ascending) == ascending and args.get('key_name') in source['columns']:
                        predicates = source['predicates']
                        order = [{'column': args['key_name'], 'ascending': ascending}]
                        status = 'known_operations'
            state = self._register(value, predicates, order, status)
            event['result_scope'] = self._scope(state)
            event['preview_complete_columns'] = [k for k,v in state['columns'].items() if v['complete_column_observed']]
            event['preview_partial_columns'] = [k for k,v in state['columns'].items() if not v['complete_column_observed']]
        elif isinstance(value, list) and source is not None and name in self.tool_names:
            matches = [k for k in source['columns'] if name == f'get_{k}s']
            if len(matches) == 1:
                column = matches[0]
                complete = len(value) == source['num_records']
                if complete:
                    source['columns'][column]['complete_column_observed'] = True
                    source['columns'][column]['full_getter_observed'] = True
                event['column_observation'] = {'column': column, 'values_returned': len(value),
                                               'matches_handle_cardinality': complete}
        elif name.startswith('compute_data_') and source is not None:
            # Describe the actual call's source, never infer the user's scope.
            event['aggregate_observation'] = {'operation': name.removeprefix('compute_data_'),
                'column': args.get('key_name'), 'value': value,
                'distinct': args.get('distinct', False)}
        self.events.append(event)
        return deepcopy(event)

    def snapshot(self):
        return {'universe_id': self.universe_id,
                'limitation': 'Observed lineage/cardinality only; user-query interpretation and answer truth are not certified.',
                'handles': deepcopy(self.handles), 'events': deepcopy(self.events)}
