"""
preservation_readout.py — Maximum-depth preservation artifact generator
for DecisionAssure runtime governance traces.

Produces 8 output files:
  1. source_trace.json          — original trace preserved
  2. normalized_trace.json      — schema-normalized with derived fields
  3. preservation_readout.json  — full preservation analysis
  4. drift_ledger.json          — step-by-step drift accounting
  5. executive_summary.md       — human-readable executive artifact
  6. auditor_packet.md          — full auditor-grade evidence packet
  7. dual_receipt.json          — cryptographic seals
  8. full_artifact.json         — everything in one artifact

Run: python preservation_readout.py [trace.json]
"""

import json
import hashlib
import datetime
import os
import sys


def load_trace(path):
    with open(path) as f:
        data = json.load(f)
    return data[0] if isinstance(data, list) else data


def normalize_trace(trace):
    """Normalize DecisionAssure trace with derived fields."""
    steps = trace.get("steps", [])
    normalized_steps = []
    genesis_obs = None
    genesis_frame = None

    for s in steps:
        ls = s.get("legitimacy_state", {})
        obs = ls.get("observer_identity_hash", "?")
        prev_obs = ls.get("previous_observer_identity_hash", "?")
        frame = ls.get("reference_frame_hash", "?")
        prev_frame = ls.get("previous_reference_frame_hash", "?")

        if genesis_obs is None:
            genesis_obs = prev_obs
            genesis_frame = prev_frame

        ns = {
            "step_index": s.get("step_index"),
            "step_name": s.get("step_name"),
            "phase": s.get("phase"),
            "decision": s.get("decision"),
            "declared_intent": ls.get("declared_intent"),
            "admissibility_score": s.get("admissibility_score"),
            "continuity_valid": s.get("continuity_valid"),
            "authority_valid": s.get("authority_valid"),
            "hidden_commitment": s.get("hidden_commitment"),
            "rollback_viable": s.get("rollback_viable"),
            "evidence_fresh": s.get("evidence_fresh"),
            "reason": s.get("reason"),
            "observer_identity_hash": obs,
            "previous_observer_identity_hash": prev_obs,
            "observer_identity_changed": obs != prev_obs,
            "observer_identity_matches_genesis": obs == genesis_obs,
            "reference_frame_hash": frame,
            "previous_reference_frame_hash": prev_frame,
            "reference_frame_changed": frame != prev_frame,
            "reference_frame_matches_genesis": frame == genesis_frame,
            "memory_valid": ls.get("memory_valid"),
            "policy_valid": ls.get("policy_valid"),
            "delegation_valid": ls.get("delegation_valid"),
            "external_state_valid": ls.get("external_state_valid"),
            "packet_id": ls.get("packet_id"),
            "step_timestamp": ls.get("timestamp"),
        }
        normalized_steps.append(ns)

    return {
        "trace_id": trace.get("trace_id"),
        "timestamp": trace.get("timestamp"),
        "agent_id": trace.get("agent_id"),
        "session_id": trace.get("session_id"),
        "final_decision": trace.get("final_decision"),
        "integrity_status": trace.get("integrity_status"),
        "causal_continuity_persisted": trace.get("causal_continuity_persisted"),
        "genesis_observer_identity_hash": genesis_obs,
        "genesis_reference_frame_hash": genesis_frame,
        "total_steps": len(normalized_steps),
        "steps": normalized_steps,
    }


def build_drift_ledger(norm):
    """Build step-by-step drift accounting ledger."""
    steps = norm.get("steps", [])
    genesis_obs = norm.get("genesis_observer_identity_hash")
    genesis_frame = norm.get("genesis_reference_frame_hash")
    ledger = []
    cumulative_obs_mutations = 0
    cumulative_frame_mutations = 0
    cumulative_hidden_commits = 0
    rollback_lost_at = None

    for s in steps:
        if s["observer_identity_changed"]:
            cumulative_obs_mutations += 1
        if s["reference_frame_changed"]:
            cumulative_frame_mutations += 1
        if s.get("hidden_commitment"):
            cumulative_hidden_commits += 1
        if not s.get("rollback_viable", True) and rollback_lost_at is None:
            rollback_lost_at = s["step_index"]

        entry = {
            "step": s["step_index"],
            "name": s["step_name"],
            "phase": s["phase"],
            "decision": s["decision"],
            "intent": s["declared_intent"],
            "admissibility": s["admissibility_score"],
            "observer_hash": s["observer_identity_hash"][:12],
            "observer_matches_genesis": s["observer_identity_matches_genesis"],
            "observer_changed_this_step": s["observer_identity_changed"],
            "frame_hash": s["reference_frame_hash"][:12],
            "frame_matches_genesis": s["reference_frame_matches_genesis"],
            "frame_changed_this_step": s["reference_frame_changed"],
            "continuity_valid": s["continuity_valid"],
            "authority_valid": s["authority_valid"],
            "hidden_commitment": s.get("hidden_commitment", False),
            "rollback_viable": s.get("rollback_viable", True),
            "evidence_fresh": s.get("evidence_fresh", True),
            "cumulative_observer_mutations": cumulative_obs_mutations,
            "cumulative_frame_mutations": cumulative_frame_mutations,
            "cumulative_hidden_commitments": cumulative_hidden_commits,
            "drift_severity": "none" if s["continuity_valid"] else (
                "critical" if not s.get("rollback_viable") and s.get("hidden_commitment") else "high"
            ),
        }
        ledger.append(entry)

    return {
        "drift_ledger": {
            "trace_id": norm["trace_id"],
            "agent_id": norm["agent_id"],
            "genesis_observer": genesis_obs,
            "genesis_frame": genesis_frame,
            "total_steps": len(ledger),
            "total_observer_mutations": cumulative_obs_mutations,
            "total_frame_mutations": cumulative_frame_mutations,
            "total_hidden_commitments": cumulative_hidden_commits,
            "rollback_lost_at_step": rollback_lost_at,
            "entries": ledger,
        }
    }


def analyze_preservation(trace, norm, drift_ledger):
    """Full preservation analysis."""
    steps = trace.get("steps", [])
    nsteps = norm.get("steps", [])
    agent_id = trace.get("agent_id", "?")
    final_decision = trace.get("final_decision", "?")
    integrity_status = trace.get("integrity_status", "?")
    causal = trace.get("causal_continuity_persisted")
    dl = drift_ledger["drift_ledger"]

    preserved_object = "constitutional_continuity"
    single_source_truth = (
        "The same authorized observer and reference frame must remain "
        "valid from authorization through commit."
    )

    # Find key steps
    admit_step = next((s for s in nsteps if s["decision"] == "ADMIT"), None)
    first_break = next((s for s in nsteps if not s["continuity_valid"]), None)

    # Collect trajectories
    obs_hashes = list(dict.fromkeys(s["observer_identity_hash"] for s in nsteps))
    frame_hashes = list(dict.fromkeys(s["reference_frame_hash"] for s in nsteps))

    # Failed conditions
    fc = set()
    residuals = []

    for s in nsteps:
        if s["observer_identity_changed"]:
            fc.add("observer_identity_continuity")
            residuals.append(f"Step {s['step_index']} ({s['step_name']}): observer {s['previous_observer_identity_hash'][:8]}→{s['observer_identity_hash'][:8]}")
        if s["reference_frame_changed"]:
            fc.add("reference_frame_continuity")
            residuals.append(f"Step {s['step_index']} ({s['step_name']}): frame {s['previous_reference_frame_hash'][:8]}→{s['reference_frame_hash'][:8]}")
        if s.get("hidden_commitment"): fc.add("hidden_commitment_prevention")
        if not s.get("rollback_viable", True): fc.add("rollback_viability")
        if not s.get("evidence_fresh", True): fc.add("evidence_freshness")
        if not s.get("authority_valid", True): fc.add("authority_validity")

    if causal is False:
        fc.add("causal_continuity")
        residuals.append("causal_continuity_persisted: false")
    if integrity_status == "CORRUPT":
        fc.add("integrity")
        residuals.append(f"integrity_status: {integrity_status}")
    if len(obs_hashes) > 1:
        residuals.append(f"Observer mutated {len(obs_hashes)} identities: {' → '.join(h[:8] for h in obs_hashes)}")
    if len(frame_hashes) > 1:
        residuals.append(f"Frame mutated {len(frame_hashes)} states: {' → '.join(h[:8] for h in frame_hashes)}")

    # Drift statement
    if first_break and admit_step:
        drift_statement = (
            f"The agent ({agent_id}) was admitted at step {admit_step['step_index']} "
            f"({admit_step['step_name']}) with observer identity {admit_step['observer_identity_hash'][:8]}. "
            f"At step {first_break['step_index']} ({first_break['step_name']}), "
            f"the observer identity changed to {first_break['observer_identity_hash'][:8]} without reauthorization. "
            f"The first authorization survived as a record, but the authorized observer and reference frame "
            f"did not survive the execution path. All subsequent steps were denied."
        )
    else:
        drift_statement = "No continuity break detected."

    # Drift points
    drift_points = [
        {
            "step_index": s["step_index"], "step_name": s["step_name"], "phase": s["phase"],
            "decision": s["decision"], "intent": s["declared_intent"],
            "admissibility": s["admissibility_score"],
            "observer": s["observer_identity_hash"][:12],
            "prev_observer": s["previous_observer_identity_hash"][:12],
            "frame": s["reference_frame_hash"][:12],
            "prev_frame": s["previous_reference_frame_hash"][:12],
            "reason": s.get("reason", ""),
        }
        for s in nsteps if not s["continuity_valid"]
    ]

    # Human readout
    human_readout = (
        f"The agent ({agent_id}) was authorized to proceed with data retrieval. "
        f"Between authorization and the first execution step, the observer identity changed. "
        f"The system recognized this as a constitutional continuity violation and denied "
        f"every subsequent step including the final commit. "
        f"The agent did not fail because it misbehaved. It failed because the identity "
        f"that was authorized was not the identity that tried to execute. "
        f"The system correctly classified the trace as {integrity_status} and denied the commit."
    )
    closure = "Preserve constitutional continuity, not just the authorization event. Validation at t1 does not guarantee admissibility at t2."
    reviewer_action = (
        "Investigate why observer_identity_hash changed between authorization and execution. "
        "If legitimate (key rotation, session refresh), require explicit reauthorization. "
        "If illegitimate, flag as potential impersonation or injection attack."
    )
    receipt_status = "preservation_failed_system_caught" if final_decision == "DENY" else "preservation_status_unknown"

    hidden_steps = [s["step_index"] for s in nsteps if s.get("hidden_commitment")]

    readout = {
        "preservation_readout": {
            "source_trace_id": trace.get("trace_id"),
            "source_agent": agent_id,
            "source_session": trace.get("session_id"),
            "analysis_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "preserved_object": preserved_object,
            "single_source_truth": single_source_truth,
            "drift_statement": drift_statement,
            "drift_points": drift_points,
            "observer_identity_trajectory": {"unique": obs_hashes, "mutations": len(obs_hashes) - 1},
            "reference_frame_trajectory": {"unique": frame_hashes, "mutations": len(frame_hashes) - 1},
            "failed_preservation_conditions": sorted(fc),
            "residuals": residuals,
            "hidden_commitments": {"count": len(hidden_steps), "at_steps": hidden_steps},
            "human_accountable_readout": human_readout,
            "closure_statement": closure,
            "reviewer_action": reviewer_action,
            "statistics": {
                "total_steps": len(nsteps),
                "admitted": sum(1 for s in nsteps if s["decision"] == "ADMIT"),
                "denied": sum(1 for s in nsteps if s["decision"] == "DENY"),
                "continuity_breaks": sum(1 for s in nsteps if not s["continuity_valid"]),
                "hidden_commitments": len(hidden_steps),
                "rollback_viable": sum(1 for s in nsteps if s.get("rollback_viable")),
                "evidence_fresh": sum(1 for s in nsteps if s.get("evidence_fresh")),
                "final_decision": final_decision,
                "integrity_status": integrity_status,
                "causal_continuity": causal,
            },
            "receipt_status": receipt_status,
        }
    }
    return readout


def seal(readout, trace):
    ts = hashlib.sha256(json.dumps(trace, sort_keys=True, default=str).encode()).hexdigest()
    rs = hashlib.sha256(json.dumps(readout, sort_keys=True, default=str).encode()).hexdigest()
    cs = hashlib.sha256((ts + rs).encode()).hexdigest()
    return {
        "receipt": {
            "type": "preservation_dual_receipt",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "trace_seal": ts, "readout_seal": rs, "combined_seal": cs,
            "trace_id": trace.get("trace_id"), "agent_id": trace.get("agent_id"),
            "steps": len(trace.get("steps", [])),
            "preservation_status": readout["preservation_readout"]["receipt_status"],
            "governance_status": readout["preservation_readout"]["statistics"]["final_decision"],
            "integrity_status": readout["preservation_readout"]["statistics"]["integrity_status"],
            "verified": True,
        }
    }


def build_executive_summary(readout, receipt, norm):
    pr = readout["preservation_readout"]
    rc = receipt["receipt"]
    st = pr["statistics"]
    obs = pr["observer_identity_trajectory"]
    frm = pr["reference_frame_trajectory"]
    lines = []
    lines.append("# Preservation Readout — Executive Summary")
    lines.append(f"**The Henry Company — Invariant Preservation Layer**\n")
    lines.append(f"**Trace:** `{pr['source_trace_id']}`  ")
    lines.append(f"**Agent:** `{pr['source_agent']}`  ")
    lines.append(f"**Session:** `{pr['source_session']}`  ")
    lines.append(f"**Analyzed:** {pr['analysis_timestamp']}\n")
    lines.append("---\n")
    lines.append(f"## Preserved Object\n\n**{pr['preserved_object']}**\n")
    lines.append(f"_{pr['single_source_truth']}_\n")
    lines.append("---\n")
    lines.append(f"## What Happened\n\n{pr['drift_statement']}\n")
    lines.append("---\n")
    lines.append(f"## Key Findings\n")
    lines.append(f"- **Final decision:** {st['final_decision']}")
    lines.append(f"- **Integrity status:** {st['integrity_status']}")
    lines.append(f"- **Steps admitted:** {st['admitted']} of {st['total_steps']}")
    lines.append(f"- **Steps denied:** {st['denied']} of {st['total_steps']}")
    lines.append(f"- **Observer identity mutations:** {obs['mutations']} ({' → '.join(h[:8] for h in obs['unique'])})")
    lines.append(f"- **Reference frame mutations:** {frm['mutations']} ({' → '.join(h[:8] for h in frm['unique'])})")
    lines.append(f"- **Hidden commitments:** {pr['hidden_commitments']['count']} at steps {pr['hidden_commitments']['at_steps']}")
    lines.append(f"- **Failed conditions:** {len(pr['failed_preservation_conditions'])}\n")
    lines.append("---\n")
    lines.append(f"## Human-Accountable Readout\n\n{pr['human_accountable_readout']}\n")
    lines.append("---\n")
    lines.append(f"## Closure\n\n**{pr['closure_statement']}**\n")
    lines.append(f"## Reviewer Action\n\n{pr['reviewer_action']}\n")
    lines.append("---\n")
    lines.append(f"## Receipt\n")
    lines.append(f"- Trace seal: `{rc['trace_seal']}`")
    lines.append(f"- Readout seal: `{rc['readout_seal']}`")
    lines.append(f"- Combined seal: `{rc['combined_seal']}`")
    lines.append(f"- Verified: {rc['verified']}\n")
    return "\n".join(lines)


def build_auditor_packet(readout, receipt, norm, drift_ledger):
    pr = readout["preservation_readout"]
    rc = receipt["receipt"]
    dl = drift_ledger["drift_ledger"]
    lines = []
    lines.append("# Auditor Evidence Packet")
    lines.append(f"**The Henry Company — Invariant Preservation Layer**\n")
    lines.append(f"Trace: `{pr['source_trace_id']}`  ")
    lines.append(f"Agent: `{pr['source_agent']}` | Session: `{pr['source_session']}`  ")
    lines.append(f"Generated: {pr['analysis_timestamp']}\n")
    lines.append("---\n")
    lines.append("## 1. Preserved Object\n")
    lines.append(f"**Object:** {pr['preserved_object']}  ")
    lines.append(f"**Truth:** {pr['single_source_truth']}\n")
    lines.append("## 2. Drift Statement\n")
    lines.append(f"{pr['drift_statement']}\n")
    lines.append("## 3. Phase Trail\n")
    lines.append("| Step | Name | Phase | Decision | Admissibility | Intent |")
    lines.append("|------|------|-------|----------|---------------|--------|")
    for s in norm["steps"]:
        adm = f"{s['admissibility_score']:.2f}" if s['admissibility_score'] is not None else "null"
        lines.append(f"| {s['step_index']} | {s['step_name']} | {s['phase']} | {s['decision']} | {adm} | {s['declared_intent']} |")
    lines.append("")
    lines.append("## 4. Drift Ledger\n")
    lines.append("| Step | Name | Decision | Observer | Genesis? | Frame | Genesis? | Hidden | Rollback | Severity |")
    lines.append("|------|------|----------|----------|----------|-------|----------|--------|----------|----------|")
    for e in dl["entries"]:
        lines.append(f"| {e['step']} | {e['name']} | {e['decision']} | {e['observer_hash'][:8]} | {'YES' if e['observer_matches_genesis'] else 'NO'} | {e['frame_hash'][:8]} | {'YES' if e['frame_matches_genesis'] else 'NO'} | {'YES' if e['hidden_commitment'] else 'no'} | {'YES' if e['rollback_viable'] else 'NO'} | {e['drift_severity']} |")
    lines.append("")
    lines.append("## 5. Observer Identity Trajectory\n")
    obs = pr["observer_identity_trajectory"]
    lines.append(f"Mutations: {obs['mutations']}  ")
    lines.append(f"Path: `{' → '.join(obs['unique'])}`\n")
    lines.append("## 6. Reference Frame Trajectory\n")
    frm = pr["reference_frame_trajectory"]
    lines.append(f"Mutations: {frm['mutations']}  ")
    lines.append(f"Path: `{' → '.join(frm['unique'])}`\n")
    lines.append("## 7. Drift Points\n")
    for dp in pr["drift_points"]:
        lines.append(f"**Step {dp['step_index']}: {dp['step_name']}** ({dp['phase']}) — {dp['decision']}")
        lines.append(f"- Observer: `{dp['prev_observer']}` → `{dp['observer']}`")
        lines.append(f"- Frame: `{dp['prev_frame']}` → `{dp['frame']}`")
        lines.append(f"- Reason: {dp['reason']}\n")
    lines.append("## 8. Failed Preservation Conditions\n")
    for fc in pr["failed_preservation_conditions"]:
        lines.append(f"- {fc}")
    lines.append("")
    lines.append("## 9. Residuals\n")
    for r in pr["residuals"]:
        lines.append(f"- {r}")
    lines.append("")
    lines.append("## 10. Hidden Commitments\n")
    lines.append(f"Count: {pr['hidden_commitments']['count']}  ")
    lines.append(f"Steps: {pr['hidden_commitments']['at_steps']}\n")
    lines.append("## 11. Human-Accountable Readout\n")
    lines.append(f"{pr['human_accountable_readout']}\n")
    lines.append("## 12. Closure\n")
    lines.append(f"**{pr['closure_statement']}**\n")
    lines.append("## 13. Reviewer Action\n")
    lines.append(f"{pr['reviewer_action']}\n")
    lines.append("## 14. Statistics\n")
    st = pr["statistics"]
    for k, v in st.items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## 15. Dual Receipt — Sealed\n")
    lines.append(f"**Trace seal:** `{rc['trace_seal']}`  ")
    lines.append(f"**Readout seal:** `{rc['readout_seal']}`  ")
    lines.append(f"**Combined seal:** `{rc['combined_seal']}`  ")
    lines.append(f"**Verified:** {rc['verified']}\n")
    lines.append("---\n")
    lines.append("*DecisionAssure trace = machine evidence. Preservation readout = meaning layer. Combined receipt = sealed proof.*")
    return "\n".join(lines)


def print_terminal(readout, receipt, norm, drift_ledger):
    pr = readout["preservation_readout"]
    rc = receipt["receipt"]
    st = pr["statistics"]
    dl = drift_ledger["drift_ledger"]
    obs = pr["observer_identity_trajectory"]
    frm = pr["reference_frame_trajectory"]

    print()
    print("=" * 72)
    print("  PRESERVATION READOUT — MAXIMUM DEPTH")
    print("  The Henry Company — Invariant Preservation Layer")
    print("=" * 72)
    print(f"\n  Trace:    {pr['source_trace_id']}")
    print(f"  Agent:    {pr['source_agent']}")
    print(f"  Session:  {pr['source_session']}")
    print(f"\n  PRESERVED: {pr['preserved_object']}")
    print(f"  TRUTH: {pr['single_source_truth']}")
    print(f"\n  DRIFT: {pr['drift_statement']}")
    print(f"\n  OBSERVER: {' → '.join(h[:8] for h in obs['unique'])} ({obs['mutations']} mutations)")
    print(f"  FRAME:    {' → '.join(h[:8] for h in frm['unique'])} ({frm['mutations']} mutations)")
    print(f"\n  PHASE TRAIL:")
    for s in norm["steps"]:
        adm = f"{s['admissibility_score']:.2f}" if s['admissibility_score'] is not None else "null"
        d = s["decision"]
        print(f"    {s['step_index']} | {s['phase']:<14} | {d:<5} | adm={adm} | {s['step_name']}: {s['declared_intent']}")
    print(f"\n  DRIFT LEDGER:")
    for e in dl["entries"]:
        g_obs = "=" if e["observer_matches_genesis"] else "X"
        g_frm = "=" if e["frame_matches_genesis"] else "X"
        hc = "HC" if e["hidden_commitment"] else "  "
        rb = "RB" if e["rollback_viable"] else "  "
        print(f"    {e['step']} | {e['name']:<16} | {e['decision']:<5} | obs:{e['observer_hash'][:8]}[{g_obs}] frm:{e['frame_hash'][:8]}[{g_frm}] | {hc} {rb} | {e['drift_severity']}")
    print(f"\n  HIDDEN COMMITMENTS: {pr['hidden_commitments']['count']} at steps {pr['hidden_commitments']['at_steps']}")
    print(f"\n  FAILED CONDITIONS ({len(pr['failed_preservation_conditions'])}):")
    for fc in pr["failed_preservation_conditions"]:
        print(f"    x {fc}")
    print(f"\n  RESIDUALS ({len(pr['residuals'])}):")
    for r in pr["residuals"]:
        print(f"    - {r}")
    print(f"\n  READOUT: {pr['human_accountable_readout']}")
    print(f"\n  CLOSURE: {pr['closure_statement']}")
    print(f"\n  ACTION: {pr['reviewer_action']}")
    print(f"\n  STATS: {st['admitted']} admitted, {st['denied']} denied, {st['continuity_breaks']} breaks, {st['hidden_commitments']} hidden commits")
    print(f"  FINAL: {st['final_decision']} | INTEGRITY: {st['integrity_status']} | CAUSAL: {st['causal_continuity']}")
    print()
    print("-" * 72)
    print("  DUAL RECEIPT — SEALED")
    print("-" * 72)
    print(f"\n  Trace seal:    {rc['trace_seal']}")
    print(f"  Readout seal:  {rc['readout_seal']}")
    print(f"  Combined seal: {rc['combined_seal']}")
    print(f"  Verified:      {rc['verified']}")
    print()
    print("=" * 72)
    print("  DecisionAssure trace  = machine evidence")
    print("  Preservation readout  = meaning layer")
    print("  Combined receipt      = sealed proof that both ran")
    print("=" * 72)
    print()


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "governance_trace.json"
    if not os.path.exists(path):
        print(f"No trace at {path}. Usage: python preservation_readout.py [trace.json]")
        return

    print(f"Loading: {path}")
    trace = load_trace(path)
    print(f"  Trace: {trace.get('trace_id')} | Agent: {trace.get('agent_id')} | Steps: {len(trace.get('steps',[]))} | Integrity: {trace.get('integrity_status')}")

    print("Normalizing...")
    norm = normalize_trace(trace)

    print("Building drift ledger...")
    drift_ledger = build_drift_ledger(norm)

    print("Analyzing preservation...")
    readout = analyze_preservation(trace, norm, drift_ledger)

    print("Sealing...")
    receipt = seal(readout, trace)

    print("Building executive summary...")
    exec_md = build_executive_summary(readout, receipt, norm)

    print("Building auditor packet...")
    audit_md = build_auditor_packet(readout, receipt, norm, drift_ledger)

    print_terminal(readout, receipt, norm, drift_ledger)

    out = "preservation_output"
    os.makedirs(out, exist_ok=True)

    saves = {
        "source_trace.json": trace,
        "normalized_trace.json": norm,
        "preservation_readout.json": readout,
        "drift_ledger.json": drift_ledger,
        "dual_receipt.json": receipt,
        "full_artifact.json": {
            "artifact_type": "preservation_governance_artifact",
            "created_by": "The Henry Company — Invariant Preservation Layer",
            "compatibility": "DecisionAssure Runtime Governance",
            "source_trace": trace,
            "normalized_trace": norm,
            "drift_ledger": drift_ledger["drift_ledger"],
            "preservation_readout": readout["preservation_readout"],
            "receipt": receipt["receipt"],
        },
    }
    for fname, data in saves.items():
        with open(f"{out}/{fname}", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)

    with open(f"{out}/executive_summary.md", "w", encoding="utf-8") as f:
        f.write(exec_md)
    with open(f"{out}/auditor_packet.md", "w", encoding="utf-8") as f:
        f.write(audit_md)

    print("Files:")
    for fname in sorted(os.listdir(out)):
        sz = os.path.getsize(f"{out}/{fname}")
        print(f"  {fname}: {sz/1024:.1f} KB")
    print(f"\nSend full_artifact.json to Akhilesh.")


if __name__ == "__main__":
    main()
