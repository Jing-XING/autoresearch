# Evidence ledger for the incomplete recovery-interface manuscript

This is a working paper, not a completed submission or a new-method claim.

| Observation | Executed evidence | Boundaries |
|---|---|---|
| Core rollback ignores a normally returned error result. | `../evidence/rac_compensation_status_probe_v2.json` | Twelve constructed controls; not model-task outcomes. |
| Retry/alternative and actual LangChain message paths show related status discrepancies. | `../evidence/rac_interceptor_recovery_probe_v1.json`; `../evidence/rac_real_langchain_tools_probe_v1.json` | Same implementation; counts are path coverage, not independent defects. |
| Invocation format changes availability of a typed status. | `../evidence/langchain_error_envelope_probe_v1.json` | Eight controls; documented library behavior, not itself a LangChain bug. |
| Published source retains the ignored-result mechanism. | `../evidence/rac_archived_rollback_probe_v1.json` | Fourteen rollback cases under current dependencies, not original-environment reproduction. |
| Automatic native MCP pair discovery fails for the declared fixture schema. | `../evidence/rac_mcp_discovery_probe_v1.json` | One actual unmodified-factory workflow; no manual registration. |
| Native MCP error messages can be inconsistent with internal COMPLETED/COMPENSATED records. | `../evidence/rac_real_mcp_probe_v1.json`; `../evidence/rac_mcp_probe_validation_v1.json` | Twelve real protocol executions with explicit diagnostic registration; local constructed tools. |
| Changing the adapter version changes four explicit-error paths. | `../evidence/rac_mcp_adapter_version_probe_v1.json` | Six matched defaults, 0.2.2 vs 0.3.2; all other dependencies current. |
| Released records are not all independent trials; conservative screen finds zero status mismatches. | `../evidence/rac_zenodo_archive_audit_v1.json`; `../evidence/rac_zenodo_archive_findings.md` | All 280 JSON inspected; no general natural-language or post-state correctness proof. |

No claims of a new compensation algorithm, superiority over competitors,
production prevalence, reconstructed paper scores or independent human
adjudication are established. Do not aggregate the probe counts into a
benchmark sample size. Instructions and scope are detailed in
`../evidence/rac_native_mcp_findings.md`.
