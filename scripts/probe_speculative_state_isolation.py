"""Offline method-level probe of pinned Speculative Actions HotPotQA code.

Execute exact AST function bodies, not upstream imports or provider clients.
Constructors, wrappers, network search and model outputs are fixture adapters.
This diagnoses state flow; it is not a benchmark or paper reproduction.
"""
import ast
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import time


ROOT = Path('results/third_party/speculative-action/source')
MANIFEST = Path('research/evidence/speculative_action_source_manifest_v1.json')
LOADED = []


def methods(path, class_name, names, namespace):
    raw = (ROOT/path).read_bytes()
    manifest = json.loads(MANIFEST.read_bytes())
    assert hashlib.sha256(raw).hexdigest() == manifest['files'][path]['sha256']
    parsed = ast.parse(raw.decode('utf-8'))
    cls = next(n for n in parsed.body if isinstance(n, ast.ClassDef) and n.name == class_name)
    selected = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert {n.name for n in selected} == set(names)
    for node in selected:
        LOADED.append({'path': path, 'class': class_name, 'method': node.name,
                       'line': node.lineno, 'end_line': node.end_lineno,
                       'ast_sha256': hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()})
    # Unmodified bodies and decorators; only remove the need to import SDKs.
    executable = ast.Module(body=selected, type_ignores=[])
    exec(compile(executable, str(ROOT/path), 'exec'), namespace)
    return type(class_name+'MethodProbe', (), {n.name: namespace[n.name] for n in selected})


def main():
    Wiki = methods('hotpotqa/src/environment.py', 'WikiEnv',
                   ['_get_obs', '_get_info', 'reset', 'construct_lookup_list',
                    'get_page_obs', 'guess_step', 'step'],
                   {'PromptTemplates': SimpleNamespace(GUESS_STEP_PROMPT='Predict {}')})
    Runner = methods('hotpotqa/src/runner.py', 'HotPotQARun',
                     ['step', 'webthink', 'action_lowercase'],
                     {'time': time, 'requests': SimpleNamespace(exceptions=SimpleNamespace(Timeout=TimeoutError)),
                      'constants': SimpleNamespace(max_agent_retries=1, max_guess_retries=1, guess_num_actions=3),
                      'PromptTemplates': SimpleNamespace(NEXT_STEP_PROMPT='Thought {i}: {thought}\nAction {i}: {action}\nObservation {i}: {obs}\n')})

    def environment(prediction):
        env = Wiki()
        env.guess_llm = SimpleNamespace(call=lambda prompt: prediction)
        env.sim_obs = None
        env.reset()
        def search(entity):
            assert entity == 'fixture'
            env.page = 'needle authoritative first. needle authoritative second.'
            env.obs = env.get_page_obs(env.page)
            env.lookup_keyword = env.lookup_list = env.lookup_cnt = None
        env.search_step = search
        return env

    def state(env):
        return {key: copy.deepcopy(getattr(env, key)) for key in
                ['page', 'obs', 'lookup_keyword', 'lookup_list', 'lookup_cnt', 'steps', 'answer']}

    direct = []
    for kind in ['none', 'search', 'lookup', 'finish']:
        env = environment('needle predicted first. needle predicted second.')
        env.step('search[fixture]')
        before = state(env)
        if kind != 'none':
            env.step({'search': 'search[fixture]', 'lookup': 'lookup[needle]', 'finish': 'finish[predicted]'}[kind], step_type='simulate')
        after = state(env)
        observation = env.step('lookup[needle]')[0]
        direct.append({'simulation': kind, 'before': before, 'after': after,
                       'next_authoritative_lookup': observation, 'final': state(env)})
    assert 'authoritative first' in direct[0]['next_authoritative_lookup']
    assert 'predicted first' in direct[1]['next_authoritative_lookup']
    assert 'authoritative second' in direct[2]['next_authoritative_lookup']
    assert direct[3]['final']['answer'] == 'predicted'

    class Wrapper:
        """Declared minimal wrapper; upstream Gym/data/history wrappers are not run."""
        def __init__(self, env):
            self.env = env
        @property
        def sim_obs(self):
            return self.env.sim_obs
        def reset(self, idx):
            assert idx == 0
            self.env.reset()
            self.normal_trajectory_dict = {'observations': [], 'actions': []}
            self.sim_trajectory_dict = {'observations': [], 'actions': []}
            return 'Find needle in fixture.'
        def step(self, action, step_type='wiki'):
            return self.env.step(action, step_type)
        def update_traj_dict_records(self, thought, action, observation, elapsed, sim):
            target = self.sim_trajectory_dict if sim else self.normal_trajectory_dict
            target['observations'].append(observation)
            target['actions'].append(action)

    runs = []
    for mode in ['baseline', 'shared_upstream_flow', 'snapshot_restore_control']:
        raw_env = environment('needle predicted first. needle predicted second.')
        wrapped = Wrapper(raw_env)
        runner = Runner()
        runner.env = wrapped
        runner.log = lambda *args, **kwargs: None
        actions = ['Search[fixture]', 'Lookup[needle]', 'Finish[done]']
        calls = []
        def generate(i, prompt, counts, num_actions=1, max_retries=1):
            calls.append({'step': i, 'candidates_requested': num_actions})
            return 'Scripted fixed action', [actions[i-1]]
        runner.generate_thought_actions = generate
        if mode == 'snapshot_restore_control':
            original_step = runner.step
            def isolated_step(env, action, simulate=False):
                before = state(env.env)
                result = original_step(env, action, simulate)
                if simulate:
                    # Preserve the explicit speculative output slot, but restore
                    # every authoritative field tracked by the fixture.
                    for key, value in before.items():
                        setattr(env.env, key, value)
                return result
            runner.step = isolated_step
        runner.webthink(idx=0, prompt='Fixture\n', to_print=False, n=4, simulate=mode != 'baseline')
        runs.append({'mode': mode, 'normal': wrapped.normal_trajectory_dict,
                     'simulated': wrapped.sim_trajectory_dict, 'state': state(raw_env),
                     'scripted_generation_calls': calls})
    assert 'authoritative first' in runs[0]['normal']['observations'][1]
    assert 'predicted first' in runs[1]['normal']['observations'][1]
    assert runs[0]['normal'] == runs[2]['normal']
    assert runs[0]['state'] == runs[2]['state']
    output = {'scope': 'AST-extracted unmodified methods with explicitly substituted I/O and wrappers',
              'benchmark_reproduction': False, 'llm_calls': 0, 'network_calls': 0,
              'source_manifest_sha256': hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
              'probe_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'executed_methods': LOADED, 'direct_controls': direct, 'runner_controls': runs,
              'finding': 'Shared simulated search changes the page read by the next authoritative lookup; snapshot/restore of authoritative state restores the fixed baseline in this fixture.'}
    destination = Path('research/evidence/speculative_state_isolation_probe_v1.json')
    with destination.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(output, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'direct_controls': len(direct), 'runner_controls': len(runs),
                      'state_interference_observed': True, 'full_benchmark_run': False}))


if __name__ == '__main__':
    main()
