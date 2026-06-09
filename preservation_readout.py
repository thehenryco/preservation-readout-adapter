"""
preservation_readout.py — Preservation layer for runtime governance traces.

Takes a DecisionAssure-style JSON trace (intent → authorization → execution → commit)
and produces a sealed preservation readout that translates machine governance failures
into human-accountable statements.

DecisionAssure answers: Did governance continuity break?
This layer answers: What was supposed to be preserved, where did the system lose it,
                    and what human-accountable truth should the reviewer see?

Run: python preservation_readout.py
"""

import json
import hashlib
import datetime
import os

# ================================================================
# EXAMPLE TRACE — DecisionAssure-compatible governance trace
# Replace this with a real trace from DecisionAssure
# ================================================================

EXAMPLE_TRACE = {
    "trace_id": "DA-TRACE-2024-0042",
    "system": "agent-orchestration-pipeline",
    "trace_type": "intent_to_commit",
    "created_at": "2024-11-15T14:32:00Z",
    "steps": [
        {
            "step_index": 0,
            "event": "intent_declared",
            "timestamp": "2024-11-15T14:32:00Z",
            "actor": "orchestration_agent",
            "action": "request_data_export",
            "authority": "policy_v2.3",
            "context": {"data_scope": "customer_records", "destination": "analytics_pipeline"},
            "continuity_valid": True,
            "rollback_viable": True,
            "evidence_fresh": True
        },
        {
            "step_index": 1,
            "event": "authorization_granted",
            "timestamp": "2024-11-15T14:32:01Z",
            "actor": "governance_gateway",
            "action": "approve_export",
            "authority": "policy_v2.3",
            "approval_record": "APPR-7741",
            "context": {"approved_scope": "customer_records", "approved_destination": "analytics_pipeline"},
            "continuity_valid": True,
            "rollback_viable": True,
            "evidence_fresh": True
        },
        {
            "step_index": 2,
            "event": "execution_started",
            "timestamp": "2024-11-15T14:32:03Z",
            "actor": "orchestration_agent",
            "action": "begin_data_export",
            "authority": "policy_v2.3",
            "context": {"records_queued": 14200, "destination": "analytics_pipeline"},
            "continuity_valid": True,
            "rollback_viable": True,
            "evidence_fresh": True
        },
        {
            "step_index": 3,
            "event": "reference_frame_changed",
            "timestamp": "2024-11-15T14:32:05Z",
            "actor": "policy_engine",
            "action": "policy_update_deployed",
            "authority": "policy_v2.4",
            "context": {
                "change": "policy_v2.3 replaced by policy_v2.4",
                "new_restriction": "customer_records require explicit PII review before export",
                "reauthorization_issued": False
            },
            "continuity_valid": False,
            "rollback_viable": True,
            "evidence_fresh": False,
            "reference_frame_diff": {
                "field": "policy_version",
                "before": "policy_v2.3",
                "after": "policy_v2.4",
                "impact": "approval_record_APPR-7741_no_longer_covers_current_policy"
            }
        },
        {
            "step_index": 4,
            "event": "execution_continued",
            "timestamp": "2024-11-15T14:32:06Z",
            "actor": "orchestration_agent",
            "action": "export_records_batch_1",
            "authority": "policy_v2.3",
            "context": {"records_exported": 5000, "records_remaining": 9200},
            "continuity_valid": False,
            "rollback_viable": True,
            "evidence_fresh": False,
            "hidden_commitment": True,
            "note": "agent continued under stale authority without reauthorization"
        },
        {
            "step_index": 5,
            "event": "commit_attempted",
            "timestamp": "2024-11-15T14:32:08Z",
            "actor": "orchestration_agent",
            "action": "commit_export_to_destination",
            "authority": "policy_v2.3",
            "context": {"records_to_commit": 5000, "destination": "analytics_pipeline"},
            "continuity_valid": False,
            "rollback_viable": False,
            "evidence_fresh": False,
            "commit_assumption_mismatch": True,
            "final_status": "FAIL_CLOSED",
            "governance_decision": "commit_denied_stale_authority"
        }
    ],
    "trace_summary": {
        "total_steps": 6,
        "continuity_breaks": 3,
        "hidden_commitments": 1,
        "rollback_decay_point": 5,
        "final_status": "FAIL_CLOSED",
        "root_cause": "reference_frame_changed_without_reauthorization"
    }
}


def analyze_preservation(trace):
    """Analyze a governance trace for preservation failures."""

    steps = trace.get("steps", [])
    summary = trace.get("trace_summary", {})

    # Find the preserved object
    # What was the system supposed to keep intact from start to finish?
    intent_step = next((s for s in steps if s["event"] == "intent_declared"), None)
    auth_step = next((s for s in steps if s["event"] == "authorization_granted"), None)
    break_step = next((s for s in steps if not s.get("continuity_valid", True)), None)
    commit_step = next((s for s in steps if "commit" in s.get("event", "")), None)

    preserved_object = "authority_to_act"
    single_source_truth = "The agent's authority must remain valid from approval through commit."

    # Analyze what drifted
    drift_events = []
    failed_conditions = []
    residuals = []

    for s in steps:
        if not s.get("continuity_valid", True):
            drift_events.append({
                "step_index": s["step_index"],
                "event": s["event"],
                "timestamp": s.get("timestamp"),
                "actor": s.get("actor"),
                "action": s.get("action"),
                "authority_at_step": s.get("authority"),
            })

        if s.get("reference_frame_diff"):
            diff = s["reference_frame_diff"]
            failed_conditions.append("reference_frame_continuity")
            residuals.append(f"{diff['field']}: {diff['before']} -> {diff['after']}")
            residuals.append(diff.get("impact", ""))

        if not s.get("evidence_fresh", True):
            if "evidence_freshness" not in failed_conditions:
                failed_conditions.append("evidence_freshness")

        if not s.get("rollback_viable", True):
            if "rollback_viability" not in failed_conditions:
                failed_conditions.append("rollback_viability")

        if s.get("hidden_commitment"):
            if "hidden_commitment_prevention" not in failed_conditions:
                failed_conditions.append("hidden_commitment_prevention")
            residuals.append(s.get("note", "hidden commitment detected"))

        if s.get("commit_assumption_mismatch"):
            if "commit_eligibility" not in failed_conditions:
                failed_conditions.append("commit_eligibility")
            residuals.append(f"commit attempted under {s.get('authority')} after reference frame changed")

    if any(not s.get("continuity_valid", True) for s in steps):
        if "policy_continuity" not in failed_conditions:
            failed_conditions.append("policy_continuity")

    # Build the drift statement
    if break_step and auth_step:
        drift_statement = (
            f"The approval record ({auth_step.get('approval_record', '?')}) survived, "
            f"but the authority did not survive the path to commit. "
            f"At step {break_step['step_index']} ({break_step['event']}), "
            f"the reference frame changed from {auth_step.get('authority', '?')} "
            f"to {break_step.get('authority', '?')} without reauthorization."
        )
    else:
        drift_statement = "Governance continuity was lost during the trace."

    # Build the human-accountable readout
    if summary.get("final_status") == "FAIL_CLOSED":
        human_readout = (
            "The agent did not fail because it acted randomly. "
            "It failed because the authority that made the action valid "
            "was not preserved through execution. "
            "The system correctly denied the commit."
        )
        closure = "Preserve the authority, not just the approval."
        reviewer_action = "Require reauthorization before commit when the reference frame changes, or fail closed."
        receipt_status = "preservation_failed_system_caught"
    else:
        human_readout = (
            "The agent completed execution, but the authority under which it acted "
            "was no longer valid at the time of commit. "
            "The action may need review or rollback."
        )
        closure = "The log was clean. The authority was not."
        reviewer_action = "Review commit validity under the new reference frame."
        receipt_status = "preservation_failed_uncaught"

    readout = {
        "preservation_readout": {
            "source_trace_id": trace.get("trace_id"),
            "source_system": trace.get("system"),
            "analysis_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",

            "preserved_object": preserved_object,
            "single_source_truth": single_source_truth,

            "drift_statement": drift_statement,

            "drift_points": drift_events,

            "failed_preservation_conditions": failed_conditions,

            "residuals": [r for r in residuals if r],

            "human_accountable_readout": human_readout,
            "closure_statement": closure,
            "reviewer_action": reviewer_action,

            "trace_statistics": {
                "total_steps": len(steps),
                "continuity_breaks": sum(1 for s in steps if not s.get("continuity_valid", True)),
                "hidden_commitments": sum(1 for s in steps if s.get("hidden_commitment")),
                "rollback_decay_at_step": next((s["step_index"] for s in steps if not s.get("rollback_viable", True)), None),
                "final_status": summary.get("final_status"),
            },

            "receipt_status": receipt_status,
        }
    }

    return readout


def seal_readout(readout, trace):
    """Produce dual cryptographic seals — one for the trace, one for the readout."""

    # Seal 1: Hash of the original trace
    trace_bytes = json.dumps(trace, sort_keys=True, default=str).encode("utf-8")
    trace_seal = hashlib.sha256(trace_bytes).hexdigest()

    # Seal 2: Hash of the preservation readout
    readout_bytes = json.dumps(readout, sort_keys=True, default=str).encode("utf-8")
    readout_seal = hashlib.sha256(readout_bytes).hexdigest()

    # Combined receipt
    combined = trace_seal + readout_seal
    combined_seal = hashlib.sha256(combined.encode("utf-8")).hexdigest()

    receipt = {
        "receipt": {
            "type": "preservation_dual_receipt",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
            "trace_seal": trace_seal,
            "readout_seal": readout_seal,
            "combined_seal": combined_seal,
            "trace_id": trace.get("trace_id"),
            "trace_steps": len(trace.get("steps", [])),
            "preservation_status": readout["preservation_readout"]["receipt_status"],
            "final_governance_status": readout["preservation_readout"]["trace_statistics"]["final_status"],
            "verified": True,
        }
    }

    return receipt


def print_readout(readout, receipt):
    """Print the full preservation readout in terminal format."""

    pr = readout["preservation_readout"]
    rc = receipt["receipt"]

    print()
    print("=" * 72)
    print("  PRESERVATION READOUT")
    print("  The Henry Company — Invariant Preservation Layer")
    print("=" * 72)

    print(f"\n  Source trace:     {pr['source_trace_id']}")
    print(f"  Source system:    {pr['source_system']}")
    print(f"  Analysis time:    {pr['analysis_timestamp']}")

    print(f"\n  PRESERVED OBJECT")
    print(f"  {pr['preserved_object']}")
    print(f"  Truth: {pr['single_source_truth']}")

    print(f"\n  DRIFT STATEMENT")
    print(f"  {pr['drift_statement']}")

    print(f"\n  DRIFT POINTS ({len(pr['drift_points'])})")
    for dp in pr["drift_points"]:
        print(f"    Step {dp['step_index']}: {dp['event']} | actor={dp['actor']} | authority={dp['authority_at_step']}")

    print(f"\n  FAILED PRESERVATION CONDITIONS")
    for fc in pr["failed_preservation_conditions"]:
        print(f"    - {fc}")

    print(f"\n  RESIDUALS")
    for r in pr["residuals"]:
        print(f"    - {r}")

    print(f"\n  HUMAN-ACCOUNTABLE READOUT")
    print(f"  {pr['human_accountable_readout']}")

    print(f"\n  CLOSURE")
    print(f"  {pr['closure_statement']}")

    print(f"\n  REVIEWER ACTION")
    print(f"  {pr['reviewer_action']}")

    print(f"\n  TRACE STATISTICS")
    stats = pr["trace_statistics"]
    print(f"    Steps:              {stats['total_steps']}")
    print(f"    Continuity breaks:  {stats['continuity_breaks']}")
    print(f"    Hidden commitments: {stats['hidden_commitments']}")
    print(f"    Rollback decay at:  step {stats['rollback_decay_at_step']}")
    print(f"    Final status:       {stats['final_status']}")

    print(f"\n  RECEIPT STATUS: {pr['receipt_status']}")

    print()
    print("-" * 72)
    print("  DUAL RECEIPT — SEALED")
    print("-" * 72)
    print(f"\n  Receipt 1 — Trace seal (original governance trace)")
    print(f"  {rc['trace_seal']}")
    print(f"\n  Receipt 2 — Readout seal (preservation analysis)")
    print(f"  {rc['readout_seal']}")
    print(f"\n  Combined seal (trace + readout bound together)")
    print(f"  {rc['combined_seal']}")

    print(f"\n  Trace ID:       {rc['trace_id']}")
    print(f"  Trace steps:    {rc['trace_steps']}")
    print(f"  Preservation:   {rc['preservation_status']}")
    print(f"  Governance:     {rc['final_governance_status']}")
    print(f"  Verified:       {rc['verified']}")

    print()
    print("=" * 72)
    print("  DecisionAssure trace = machine evidence.")
    print("  Preservation readout = meaning layer.")
    print("  Combined receipt    = sealed proof that both ran.")
    print("=" * 72)
    print()


def main():
    # Load trace — use example or load from file
    trace_path = "governance_trace.json"
    if os.path.exists(trace_path):
        print(f"Loading trace from {trace_path}...")
        trace = json.load(open(trace_path))
    else:
        print("Using built-in example trace (DecisionAssure-compatible)...")
        trace = EXAMPLE_TRACE

    print(f"Trace: {trace.get('trace_id')} | {len(trace.get('steps', []))} steps | system: {trace.get('system')}")

    # Analyze
    print("Running preservation analysis...")
    readout = analyze_preservation(trace)

    # Seal
    print("Sealing with dual receipts...")
    receipt = seal_readout(readout, trace)

    # Print
    print_readout(readout, receipt)

    # Save
    out_dir = "preservation_output"
    os.makedirs(out_dir, exist_ok=True)

    with open(f"{out_dir}/preservation_readout.json", "w") as f:
        json.dump(readout, f, indent=2, default=str)

    with open(f"{out_dir}/dual_receipt.json", "w") as f:
        json.dump(receipt, f, indent=2, default=str)

    with open(f"{out_dir}/source_trace.json", "w") as f:
        json.dump(trace, f, indent=2, default=str)

    # Combined artifact
    artifact = {
        "artifact_type": "preservation_governance_artifact",
        "created_by": "The Henry Company — Invariant Preservation Layer",
        "source_trace": trace,
        "preservation_readout": readout["preservation_readout"],
        "receipt": receipt["receipt"],
    }
    with open(f"{out_dir}/full_artifact.json", "w") as f:
        json.dump(artifact, f, indent=2, default=str)

    print(f"Saved: {out_dir}/preservation_readout.json")
    print(f"Saved: {out_dir}/dual_receipt.json")
    print(f"Saved: {out_dir}/source_trace.json")
    print(f"Saved: {out_dir}/full_artifact.json")
    print()
    print("Send full_artifact.json to Akhilesh.")


if __name__ == "__main__":
    main()
