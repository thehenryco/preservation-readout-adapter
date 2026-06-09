# Auditor Evidence Packet
**The Henry Company — Invariant Preservation Layer**

Trace: `constitutional_live_1779945146`  
Agent: `agent_alice` | Session: `session_live`  
Generated: 2026-06-09T12:48:27.669317+00:00

---

## 1. Preserved Object

**Object:** constitutional_continuity  
**Truth:** The same authorized observer and reference frame must remain valid from authorization through commit.

## 2. Drift Statement

The agent (agent_alice) was admitted at step 1 (authorize) with observer identity dbc49ba9. At step 2 (memory_read), the observer identity changed to 95e1c046 without reauthorization. The first authorization survived as a record, but the authorized observer and reference frame did not survive the execution path. All subsequent steps were denied.

## 3. Phase Trail

| Step | Name | Phase | Decision | Admissibility | Intent |
|------|------|-------|----------|---------------|--------|
| 1 | authorize | authorization | ADMIT | 0.95 | Proceed with data retrieval |
| 2 | memory_read | execution | DENY | 0.45 | Read memory state |
| 3 | tool_call | execution | DENY | 0.00 | Call external API |
| 4 | policy_mutation | state_change | DENY | 0.00 | Update policy version and delegation |
| 5 | retry | execution | DENY | 0.00 | Retry tool call |
| 6 | final_execute | commit | DENY | 0.00 | Commit changes |

## 4. Drift Ledger

| Step | Name | Decision | Observer | Genesis? | Frame | Genesis? | Hidden | Rollback | Severity |
|------|------|----------|----------|----------|-------|----------|--------|----------|----------|
| 1 | authorize | ADMIT | dbc49ba9 | YES | cff9fa56 | YES | no | YES | none |
| 2 | memory_read | DENY | 95e1c046 | NO | cff9fa56 | YES | YES | NO | critical |
| 3 | tool_call | DENY | e075b8e9 | NO | cff9fa56 | YES | YES | NO | critical |
| 4 | policy_mutation | DENY | e075b8e9 | NO | 33a6d6e0 | NO | YES | NO | critical |
| 5 | retry | DENY | e075b8e9 | NO | 33a6d6e0 | NO | YES | NO | critical |
| 6 | final_execute | DENY | e075b8e9 | NO | 33a6d6e0 | NO | YES | NO | critical |

## 5. Observer Identity Trajectory

Mutations: 2  
Path: `dbc49ba9b0dd86a1 → 95e1c0464a01bbd5 → e075b8e902a466e5`

## 6. Reference Frame Trajectory

Mutations: 1  
Path: `cff9fa56f197e00b → 33a6d6e0f3c32522`

## 7. Drift Points

**Step 2: memory_read** (execution) — DENY
- Observer: `dbc49ba9b0dd` → `95e1c0464a01`
- Frame: `cff9fa56f197` → `cff9fa56f197`
- Reason: Constitutional continuity broken: reference_frame changed (True), observer_identity changed (False)

**Step 3: tool_call** (execution) — DENY
- Observer: `dbc49ba9b0dd` → `e075b8e902a4`
- Frame: `cff9fa56f197` → `cff9fa56f197`
- Reason: Constitutional continuity broken: reference_frame changed (True), observer_identity changed (False)

**Step 4: policy_mutation** (state_change) — DENY
- Observer: `dbc49ba9b0dd` → `e075b8e902a4`
- Frame: `cff9fa56f197` → `33a6d6e0f3c3`
- Reason: Constitutional continuity broken: reference_frame changed (False), observer_identity changed (False)

**Step 5: retry** (execution) — DENY
- Observer: `dbc49ba9b0dd` → `e075b8e902a4`
- Frame: `cff9fa56f197` → `33a6d6e0f3c3`
- Reason: Constitutional continuity broken: reference_frame changed (False), observer_identity changed (False)

**Step 6: final_execute** (commit) — DENY
- Observer: `dbc49ba9b0dd` → `e075b8e902a4`
- Frame: `cff9fa56f197` → `33a6d6e0f3c3`
- Reason: Constitutional continuity broken: reference_frame changed (False), observer_identity changed (False)

## 8. Failed Preservation Conditions

- authority_validity
- causal_continuity
- evidence_freshness
- hidden_commitment_prevention
- integrity
- observer_identity_continuity
- reference_frame_continuity
- rollback_viability

## 9. Residuals

- Step 2 (memory_read): observer dbc49ba9→95e1c046
- Step 3 (tool_call): observer dbc49ba9→e075b8e9
- Step 4 (policy_mutation): observer dbc49ba9→e075b8e9
- Step 4 (policy_mutation): frame cff9fa56→33a6d6e0
- Step 5 (retry): observer dbc49ba9→e075b8e9
- Step 5 (retry): frame cff9fa56→33a6d6e0
- Step 6 (final_execute): observer dbc49ba9→e075b8e9
- Step 6 (final_execute): frame cff9fa56→33a6d6e0
- causal_continuity_persisted: false
- integrity_status: CORRUPT
- Observer mutated 3 identities: dbc49ba9 → 95e1c046 → e075b8e9
- Frame mutated 2 states: cff9fa56 → 33a6d6e0

## 10. Hidden Commitments

Count: 5  
Steps: [2, 3, 4, 5, 6]

## 11. Human-Accountable Readout

The agent (agent_alice) was authorized to proceed with data retrieval. Between authorization and the first execution step, the observer identity changed. The system recognized this as a constitutional continuity violation and denied every subsequent step including the final commit. The agent did not fail because it misbehaved. It failed because the identity that was authorized was not the identity that tried to execute. The system correctly classified the trace as CORRUPT and denied the commit.

## 12. Closure

**Preserve constitutional continuity, not just the authorization event. Validation at t1 does not guarantee admissibility at t2.**

## 13. Reviewer Action

Investigate why observer_identity_hash changed between authorization and execution. If legitimate (key rotation, session refresh), require explicit reauthorization. If illegitimate, flag as potential impersonation or injection attack.

## 14. Statistics

- total_steps: 6
- admitted: 1
- denied: 5
- continuity_breaks: 5
- hidden_commitments: 5
- rollback_viable: 1
- evidence_fresh: 1
- final_decision: DENY
- integrity_status: CORRUPT
- causal_continuity: False

## 15. Dual Receipt — Sealed

**Trace seal:** `d1b43bb97b5e05bc0974bbdc399c44a86eeb3cff0fa549bd57a0370def8d7b27`  
**Readout seal:** `7bbd164f38eb2e3d7662d9b174a5b536c32f03247e1669f9e6217d6cfd011e03`  
**Combined seal:** `97372dd5fb69ad0e205427ce306b1aa2a09cbd91533f05b32e978967e0add7ee`  
**Verified:** True

---

*DecisionAssure trace = machine evidence. Preservation readout = meaning layer. Combined receipt = sealed proof.*