"""Audit every pinned paired trace; do not infer benchmark causality from overlap."""
import ast
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re


ROOT = Path('results/third_party/speculative-action')
MANIFEST = Path('research/evidence/speculative_action_trajectory_manifest_v1.json')


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def main():
    manifest = json.loads(MANIFEST.read_bytes())
    groups = defaultdict(dict)
    for rel, record in manifest['files'].items():
        raw = (ROOT/'archive'/rel).read_bytes()
        assert len(raw) == record['bytes']
        assert hashlib.sha256(raw).hexdigest() == record['sha256']
        assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() == record['git_blob']
        groups[str(Path(rel).parent).replace('\\', '/')][Path(rel).name] = json.loads(raw)
    assert len(groups) == 94 and all(set(g) == {'normalobs.json', 'simobs.json'} for g in groups.values())
    counts = Counter()
    folder_questions = defaultdict(set)
    all_questions = set()
    rows, lookups = [], []
    for path, pair in sorted(groups.items()):
        normal, sim = pair['normalobs.json'], pair['simobs.json']
        assert 'Question:' in normal['prompt'] and 'Question:' in sim['prompt']
        question = normal['prompt'].rsplit('Question:', 1)[1].strip()
        sim_question = sim['prompt'].rsplit('Question:', 1)[1].strip()
        assert question and question == sim_question
        question_sha = digest(question)
        folder = path.rsplit('/', 1)[1]
        folder_questions[folder].add(question_sha)
        all_questions.add(question_sha)
        count = len(normal['actions'])
        for trace in (normal, sim):
            assert all(len(trace[k]) == count for k in ['observations', 'thoughts', 'actions', 'time_taken'])
            assert all(isinstance(x, (int, float)) and math.isfinite(x) and x >= 0 for x in trace['time_taken'])
        local = Counter()
        for i, action in enumerate(normal['actions']):
            assert isinstance(action, str)
            match = re.fullmatch(r'(Search|Lookup|Finish)\[(.*)\]', action, flags=re.S|re.I)
            assert match, (path, i, action)
            kind = match.group(1).lower()
            counts[kind] += 1
            if isinstance(sim['actions'][i], str):
                counts['simulated_action_string_steps'] += 1
            else:
                assert isinstance(sim['actions'][i], list) and all(isinstance(a, str) for a in sim['actions'][i])
                counts['simulated_action_list_steps'] += 1
            if i and kind != 'search':
                local['eligible_nonsearch_steps'] += 1
                local['sim_obs_exact_repeat_previous'] += sim['observations'][i] == sim['observations'][i-1]
            if kind == 'lookup':
                observation = normal['observations'][i]
                result = re.fullmatch(r'\(Result (\d+) / (\d+)\) (.*)', observation, flags=re.S)
                record = {'path': path, 'step_zero_based': i, 'action_sha256': digest(action),
                          'normal_observation_sha256': digest(observation),
                          'has_result': result is not None,
                          'explicit_no_more_results': observation == 'No more results.\n'}
                assert record['has_result'] or record['explicit_no_more_results']
                if result:
                    body = result.group(3)
                    assert body and i > 0
                    record.update({'result_body_sha256': digest(body),
                                   'body_exact_substring_previous_simulated_observation': body in sim['observations'][i-1],
                                   'body_exact_substring_any_earlier_logged_normal_search_observation': any(
                                       body in normal['observations'][j] for j in range(i)
                                       if normal['actions'][j].lower().startswith('search['))})
                lookups.append(record)
        rows.append({'path': path, 'folder_id': folder, 'question_sha256': question_sha,
                     'steps': count, **local})
        counts.update(local)
        counts['trajectory_pairs'] += 1
        counts['steps'] += count

    # Execute the exact upstream forwarding method with a recording adapter.
    # This is not a Gym reset, dataset sample, or full runner execution.
    rel = 'hotpotqa/src/wrappers.py'
    source = (ROOT/'source'/rel).read_bytes()
    source_manifest = json.loads(Path('research/evidence/speculative_action_source_manifest_v1.json').read_bytes())
    assert hashlib.sha256(source).hexdigest() == source_manifest['files'][rel]['sha256']
    cls = next(n for n in ast.parse(source).body if isinstance(n, ast.ClassDef) and n.name == 'HistoryWrapper')
    reset = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'reset')
    namespace = {}
    exec(compile(ast.Module(body=[reset], type_ignores=[]), rel, 'exec'), namespace)
    forwarded = []
    class RecordingEnvironment:
        def reset(self, **kwargs):
            forwarded.append(kwargs)
            return 'fixture-reset-result'
    class Wrapper:
        env = RecordingEnvironment()
        def get_empty_traj_dict(self):
            return {}
    output = namespace['reset'](Wrapper(), seed=17, return_info=True, options={'fixture': True}, idx=42)
    assert output == 'fixture-reset-result'
    assert forwarded == [{'seed': None, 'return_info': False, 'options': None, 'idx': None}]

    result = {'scope': 'complete paired normalobs/simobs slice under hotpotqa/run_metrics, not all repository artifacts or full benchmark',
              'repository': manifest['repository'], 'commit': manifest['commit'],
              'manifest_sha256': hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'counts': dict(counts), 'unique_question_text_hashes': len(all_questions),
              'unique_folder_ids': len(folder_questions),
              'folder_ids_with_multiple_question_hashes': sum(len(q) > 1 for q in folder_questions.values()),
              'folder_question_hashes': {k: sorted(v) for k, v in sorted(folder_questions.items())},
              'lookup_result_count': sum(r['has_result'] for r in lookups),
              'lookup_result_previous_sim_substring_count': sum(r.get('body_exact_substring_previous_simulated_observation', False) for r in lookups),
              'lookup_result_any_logged_normal_search_substring_count': sum(r.get('body_exact_substring_any_earlier_logged_normal_search_observation', False) for r in lookups),
              'wrapper_reset_control': {'source': rel, 'source_sha256': hashlib.sha256(source).hexdigest(),
                  'method': 'HistoryWrapper.reset', 'line': reset.lineno, 'end_line': reset.end_lineno,
                  'ast_sha256': digest(ast.dump(reset, include_attributes=False)),
                  'requested_idx': 42, 'forwarded_calls': forwarded,
                  'scope': 'exact extracted forwarding method with recording environment, no Gym/data or RNG execution'},
              'trajectories': rows, 'lookup_records': lookups,
              'limitations': ['Archive README identifies illustrative samples; selection and generating source revision are not established.',
                              'Logged normal search observations are truncated summaries, not full page states.',
                              'Text overlap alone does not establish provenance or the counterfactual answer/reward.',
                              'No action accuracy, latency or success contrast is claimed from unmatched question sets.']}
    destination = Path('research/evidence/speculative_action_trajectory_audit_v1.json')
    with destination.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k: result[k] for k in ['counts', 'unique_question_text_hashes', 'unique_folder_ids',
          'folder_ids_with_multiple_question_hashes', 'lookup_result_count',
          'lookup_result_previous_sim_substring_count', 'lookup_result_any_logged_normal_search_substring_count']}))


if __name__ == '__main__':
    main()
