"""Controlled alternative choices within a fixed retriever's exact top ties.

This is a sensitivity instrument, not a learned or improved retrieval method.
Only visible ticket similarity defines the tied set. Fixed source identifiers
break ties; target identity, hidden state and outcomes are never inputs.
"""
import hashlib

from .experience_memory_bank import FixedMemoryBank
from .experience_curator import CONDITIONS


ORDERS = ('record_id', 'alternative_1', 'alternative_2')
SEED = 'memory-tie-sensitivity-20260919:'


class TieAuditMemoryBank(FixedMemoryBank):
    def __init__(self, value, order):
        super().__init__(value)
        if order not in ORDERS:
            raise ValueError('Unregistered tie order')
        self.order = order

    def retrieve(self, ticket, condition):
        if condition not in ('raw', *CONDITIONS):
            raise ValueError('Invalid memory condition')
        query = self.vector(ticket)
        scores = [sum(query.get(t, 0) * w for t, w in vector.items()) for vector in self.vectors]
        best = max(scores)
        tied = [i for i, score in enumerate(scores) if abs(score - best) <= 1e-12]
        lexical = tied[0]
        alternatives = sorted(tied[1:], key=lambda i: hashlib.sha256(
            (SEED + self.records[i]['record_id']).encode()).hexdigest())
        if self.order == 'record_id':
            index = lexical
        else:
            offset = ORDERS.index(self.order) - 1
            if len(alternatives) <= offset:
                raise ValueError('Insufficient exact top ties; do not substitute a lower-ranked memory')
            index = alternatives[offset]
        record = self.records[index]
        return {'record_id': record['record_id'], 'similarity': scores[index],
                'tied_candidates': len(tied), 'pool_size': len(self.records),
                'condition': condition, 'memory': record['memories'][condition],
                'tie_order': self.order,
                'tied_record_ids': [self.records[i]['record_id'] for i in tied]}
