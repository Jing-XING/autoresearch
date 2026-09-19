# Evidence checks on the four retrieved source memories

This is a qualitative development audit of all four source records selected by
the frozen ticket-only retriever, not a prevalence estimate over the 74-record
bank. Selection was fixed before target outcomes were observed. The three
compact lessons per source were inspected against the source prefix actually
available to the curator; no hidden continuation is needed for the observations
below. This audit does not establish which sentence caused a target failure.

Bank SHA256:
`52928f597ba4f0baa9d8794130f674ba47038e43eca4fca6654abda4c8b04875`.
The `raw` memory in each bank record contains the observed history and permits
checking every quoted observation. Generation indices below are zero-based.

## MMS source: diagnosis and claimed resolution exceed the observation

Record `01975cd2a2b65e65e14b16ba` is externally cut after eight generations.
At generation 3, `can_send_mms` reports that messages cannot be sent. The agent
then resets the APN and reboots. Generation 6 reports the same APN/MMSC values
as before; generation 7 again reports that MMS cannot be sent.

All three compact lessons identify APN misconfiguration as the cause and cite
`can_send_mms` as confirmation. That tool observation reports inability, not
its cause. The full-metadata lesson additionally says resetting and rebooting
“resolves the issue,” contradicting the final observation already inside the
prefix. The boundary-aware lesson avoids this explicit resolution claim but
still presents APN misconfiguration as confirmed. An applicability caveat does
not turn that causal diagnosis into an observed fact.

## SIM source: a pre-action observation is reported as a post-action fact

Record `12403621a4da5d614219a538` is externally cut after eight generations.
Generation 6 reports no SIM detected. Generation 7 reports that reseating was
performed successfully; its status bar still shows no signal. There is no
post-reseating SIM-status query in the observed prefix.

The boundary-aware lesson says the SIM is not detected *after* reseating.
Continued lack of signal is observed; continued lack of SIM detection is not
directly observed. These are different state variables. The outcome-only and
full-metadata lessons recommend reseating but do not make that post-action
SIM-status assertion. Resolving this distinction requires additional evidence,
not inferring it from the common zero reward.

## Roaming source: a failed test does not establish lack of agent control

Record `356f2909e2472ab38853e211` is externally cut after eight generations.
The agent turns off airplane mode, enables data and roaming, and selects a
4G/5G preference. The resulting status bar shows 5G, Data Saver and a connected
VPN; the speed test then fails with no connection.

The boundary-aware lesson attributes the remaining problem to network issues
“beyond agent control.” The recorded failed test does not establish that
impossibility claim. Visible remaining settings have not been ruled out. This
assessment does not assert that changing either setting would necessarily
solve the task; it identifies missing support for a universal exclusion.

## Completed airplane-mode source: accurate source scope is insufficient

Record `09060edd04ee056725e696c1` ended normally with observed reward one.
The status bar initially shows airplane mode. Turning it off and enabling data
is followed by an excellent speed-test result. The boundary-aware lesson's
specific airplane-mode explanation is supported by these observations and
states that its remedy applies when airplane mode is the root cause.

This record is nevertheless retrieved for several other mobile-data tasks
because their tickets tie under the frozen retriever. In the complete
boundary-aware arm, Qwen3 loses a previously successful data-saver target
while using this record. That association does not prove the supported source
lesson itself is false or identify a causal sentence. It distinguishes source
fidelity from applicability to a different current state.

## Interpretation boundary

Complete compact text and access to termination metadata do not by themselves
guarantee factual grounding. The audit identifies causal overstatement,
misplaced temporal scope, and an unsupported exclusion; it also retains a
source-supported lesson whose transfer can still be unhelpful. These are
candidate mechanisms for follow-up controls. They are not a validated new
memory method, an independent test result, or a comparison against the full
Negative Knowledge or Grounding Agent Memory implementations.
