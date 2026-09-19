"""Check observed native-MCP mechanisms and preserve dependency-file identities."""
import base64
import hashlib
import importlib.metadata
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    evidence = Path('research/evidence')
    p = evidence/'rac_real_mcp_probe_v1.json'
    d = json.loads(p.read_bytes())
    rows = d['cases']
    assert len(rows) == 12 and d['parent_network_connection_attempts'] == 0
    assert d['allowed_stdlib_loopback_socketpairs'] == 8
    for i,r in enumerate(rows):
        state_path = Path(d['raw_fixture_directory'])/f'case-{i:02d}.json'
        assert sha(state_path) == r['state_sha256']
        assert json.loads(state_path.read_bytes()) == r['fixture_state']
        assert r['discovered_pairs'] == {} and r['adapter_schema_compensation'] == 'cancel'
        assert r['explicitly_added_pair']
        if r['route'] == 'rollback':
            calls = r['fixture_state']['calls']
            assert [c['name'] for c in calls] == ['book','cancel']
            assert calls[0]['active_after']
            assert r['fixture_state']['active'] == (r['behavior'] != 'success')
            rejected = r['legacy_raise_control'] and r['behavior'] in ('explicit_error','server_exception')
            assert r['marked_compensated'] == (not rejected)
            assert r['rollback_reported_success'] == (None if rejected else True)
            if rejected:
                assert r['exception']['type'] == 'CriticalFailure'
        else:
            assert not r['fixture_state']['active']
            assert len(r['fixture_state']['calls']) == 1 and r['fixture_state']['calls'][0]['is_error']
            assert r['record_status'] == ('FAILED' if r['legacy_raise_control'] else 'COMPLETED')
            if not r['legacy_raise_control'] and r['route'] == 'forward_tool_call':
                assert r['forward_result_type'] == 'ToolMessage' and r['forward_result_status'] == 'error'
    dp = evidence/'rac_mcp_discovery_probe_v1.json'
    discovery = json.loads(dp.read_bytes())
    assert discovery['prior_probe_sha256'] == sha(p)
    assert discovery['controls_passed'] and discovery['recorded_actions'] == 0
    assert discovery['rollback_report']['message'] == 'No actions to rollback'
    files = {}
    selected = {'langchain-mcp-adapters':['langchain_mcp_adapters/tools.py','langchain_mcp_adapters/client.py','langchain_mcp_adapters/sessions.py'],
                'langchain-core':['langchain_core/tools/base.py'],
                'mcp':['mcp/server/lowlevel/server.py']}
    for name, names in selected.items():
        dist = importlib.metadata.distribution(name)
        paths = {str(f):f for f in dist.files}
        for n in names:
            entry = paths[n]
            path = Path(dist.locate_file(entry))
            assert entry.hash.mode == 'sha256'
            assert base64.urlsafe_b64encode(hashlib.sha256(path.read_bytes()).digest()).decode().rstrip('=') == entry.hash.value
            files[n] = sha(path)
    report = json.loads(Path('results/third_party/rac/mcp_install_report.json').read_bytes())
    package = next(r for r in report['install'] if r['metadata']['name'] == 'langchain-mcp-adapters')
    assert package['download_info']['archive_info']['hashes']['sha256'] == '094e6b3096dbcc408417d5722f6915f164772e50c502ae3d8989405bf12c3c84'
    result = dict(controls_passed=True, native_mcp_cases=12, additional_automatic_discovery_case=1,
        source_probes_sha256={str(x):sha(x) for x in (p,dp)},
        dependency_files_sha256=files, installed_record_hashes_verified=True,
        official_adapter_wheel_sha256=package['download_info']['archive_info']['hashes']['sha256'],
        script_sha256=sha(Path(__file__)),
        limits='Thirteen constructed executions, not thirteen independent defects or tasks. No original-paper model result replicated.')
    with (evidence/'rac_mcp_probe_validation_v1.json').open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps(dict(controls_passed=True,native_cases=12,automatic_discovery_cases=1,dependency_files=len(files))))


if __name__ == '__main__':
    main()
