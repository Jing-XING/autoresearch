"""Print an untruncated, task-local deduplicated answer-review slice."""
import json
from pathlib import Path
import sys

domain, start, stop = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
entries = json.loads((Path('results/vakra-smollm3-review-v1') / (domain + '.json')).read_bytes())
for entry in entries[start:stop]:
    card, policy = entry['card'], entry['policy']
    print(json.dumps({'task': card['task_index'], 'query': card['query'], 'gold': card['rows'],
                      'reference': card['reference_answer'], 'policy': policy}, ensure_ascii=False))
    groups = {}
    for answer in entry['answers']:
        key = answer['final_answer']
        groups.setdefault(key, []).append(answer['call_policy'] + '/' + answer['condition'] + '/' + answer['termination'])
    for answer, arms in groups.items():
        print(json.dumps({'arms': arms, 'full_answer': answer}, ensure_ascii=False))
