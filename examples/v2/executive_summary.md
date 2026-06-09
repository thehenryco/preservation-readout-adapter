# Preservation Readout — Executive Summary
**The Henry Company — Invariant Preservation Layer**

**Trace:** `constitutional_live_1779945146`  
**Agent:** `agent_alice`  
**Session:** `session_live`  
**Analyzed:** 2026-06-09T12:48:27.669317+00:00

---

## Preserved Object

**constitutional_continuity**

_The same authorized observer and reference frame must remain valid from authorization through commit._

---

## What Happened

The agent (agent_alice) was admitted at step 1 (authorize) with observer identity dbc49ba9. At step 2 (memory_read), the observer identity changed to 95e1c046 without reauthorization. The first authorization survived as a record, but the authorized observer and reference frame did not survive the execution path. All subsequent steps were denied.

---

## Key Findings

- **Final decision:** DENY
- **Integrity status:** CORRUPT
- **Steps admitted:** 1 of 6
- **Steps denied:** 5 of 6
- **Observer identity mutations:** 2 (dbc49ba9 → 95e1c046 → e075b8e9)
- **Reference frame mutations:** 1 (cff9fa56 → 33a6d6e0)
- **Hidden commitments:** 5 at steps [2, 3, 4, 5, 6]
- **Failed conditions:** 8

---

## Human-Accountable Readout

The agent (agent_alice) was authorized to proceed with data retrieval. Between authorization and the first execution step, the observer identity changed. The system recognized this as a constitutional continuity violation and denied every subsequent step including the final commit. The agent did not fail because it misbehaved. It failed because the identity that was authorized was not the identity that tried to execute. The system correctly classified the trace as CORRUPT and denied the commit.

---

## Closure

**Preserve constitutional continuity, not just the authorization event. Validation at t1 does not guarantee admissibility at t2.**

## Reviewer Action

Investigate why observer_identity_hash changed between authorization and execution. If legitimate (key rotation, session refresh), require explicit reauthorization. If illegitimate, flag as potential impersonation or injection attack.

---

## Receipt

- Trace seal: `d1b43bb97b5e05bc0974bbdc399c44a86eeb3cff0fa549bd57a0370def8d7b27`
- Readout seal: `7bbd164f38eb2e3d7662d9b174a5b536c32f03247e1669f9e6217d6cfd011e03`
- Combined seal: `97372dd5fb69ad0e205427ce306b1aa2a09cbd91533f05b32e978967e0add7ee`
- Verified: True
