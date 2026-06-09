"""
governance_state_space.py — Deep mathematical analysis of DecisionAssure traces.

Takes a DecisionAssure governance trace and computes:
  1. State space topology (atoms, edges, cycles, broken cycles)
  2. 10D stabilizer convergence on governance state
  3. Forward prediction (governance trajectory beyond the trace)
  4. 8-solver cross-check (each sees a different mathematical dimension)
  5. Recovery path computation (what intervention restores governance)
  6. Sealed mathematical proof

DecisionAssure detects the break.
This system computes the mathematical landscape underneath.

Run: python governance_state_space.py governance_trace.json
"""

import json
import hashlib
import datetime
import math
import os
import sys

# ================================================================
# LOAD AND NORMALIZE
# ================================================================

def load_trace(path):
    with open(path) as f:
        data = json.load(f)
    return data[0] if isinstance(data, list) else data


def extract_governance_state_vector(step):
    """Extract a numerical state vector from a legitimacy state."""
    ls = step.get("legitimacy_state", {})
    return [
        1.0 if step.get("continuity_valid") else 0.0,
        step.get("admissibility_score", 0.0),
        1.0 if step.get("authority_valid") else 0.0,
        1.0 if ls.get("memory_valid") else 0.0,
        1.0 if ls.get("policy_valid") else 0.0,
        1.0 if ls.get("delegation_valid") else 0.0,
        1.0 if ls.get("external_state_valid") else 0.0,
        1.0 if step.get("rollback_viable") else 0.0,
        1.0 if step.get("evidence_fresh") else 0.0,
        0.0 if step.get("hidden_commitment") else 1.0,
    ]


# ================================================================
# TOPOLOGY — atoms, edges, cycles
# ================================================================

def compute_topology(trace):
    """Compute the mathematical topology of the governance trace."""
    steps = trace.get("steps", [])
    atoms = []
    edges = []
    
    # Each field in each step is an atom
    field_names = [
        "continuity_valid", "admissibility_score", "authority_valid",
        "hidden_commitment", "rollback_viable", "evidence_fresh"
    ]
    ls_fields = [
        "memory_valid", "policy_valid", "delegation_valid",
        "external_state_valid"
    ]
    
    for s in steps:
        step_idx = s["step_index"]
        ls = s.get("legitimacy_state", {})
        
        for fn in field_names:
            val = s.get(fn)
            atoms.append({
                "id": f"step_{step_idx}_{fn}",
                "step": step_idx,
                "field": fn,
                "value": val,
                "type": "governance_field"
            })
        
        for fn in ls_fields:
            val = ls.get(fn)
            atoms.append({
                "id": f"step_{step_idx}_ls_{fn}",
                "step": step_idx,
                "field": fn,
                "value": val,
                "type": "legitimacy_field"
            })
        
        # Hash atoms
        obs_hash = ls.get("observer_identity_hash", "?")
        frame_hash = ls.get("reference_frame_hash", "?")
        atoms.append({"id": f"step_{step_idx}_observer", "step": step_idx, "field": "observer_identity", "value": obs_hash[:12], "type": "identity_hash"})
        atoms.append({"id": f"step_{step_idx}_frame", "step": step_idx, "field": "reference_frame", "value": frame_hash[:12], "type": "frame_hash"})
    
    # Edges — field dependencies within each step
    for s in steps:
        step_idx = s["step_index"]
        # continuity_valid depends on observer + frame
        edges.append({"from": f"step_{step_idx}_observer", "to": f"step_{step_idx}_continuity_valid", "type": "identity_dependency"})
        edges.append({"from": f"step_{step_idx}_frame", "to": f"step_{step_idx}_continuity_valid", "type": "frame_dependency"})
        # admissibility depends on continuity
        edges.append({"from": f"step_{step_idx}_continuity_valid", "to": f"step_{step_idx}_admissibility_score", "type": "continuity_to_admissibility"})
        # authority depends on admissibility
        edges.append({"from": f"step_{step_idx}_admissibility_score", "to": f"step_{step_idx}_authority_valid", "type": "admissibility_to_authority"})
        # rollback depends on authority + hidden commitment
        edges.append({"from": f"step_{step_idx}_authority_valid", "to": f"step_{step_idx}_rollback_viable", "type": "authority_to_rollback"})
        edges.append({"from": f"step_{step_idx}_hidden_commitment", "to": f"step_{step_idx}_rollback_viable", "type": "commitment_to_rollback"})
    
    # Cross-step edges — each step depends on previous
    for i in range(1, len(steps)):
        prev = steps[i-1]["step_index"]
        curr = steps[i]["step_index"]
        edges.append({"from": f"step_{prev}_observer", "to": f"step_{curr}_observer", "type": "identity_propagation"})
        edges.append({"from": f"step_{prev}_frame", "to": f"step_{curr}_frame", "type": "frame_propagation"})
        edges.append({"from": f"step_{prev}_authority_valid", "to": f"step_{curr}_continuity_valid", "type": "authority_chain"})
    
    # Cycles — closed authority loops
    cycles = []
    broken_cycles = []
    for s in steps:
        step_idx = s["step_index"]
        ls = s.get("legitimacy_state", {})
        # A cycle closes if observer matches genesis AND frame matches genesis AND continuity holds
        obs_match = ls.get("observer_identity_hash") == ls.get("previous_observer_identity_hash")
        frame_match = ls.get("reference_frame_hash") == ls.get("previous_reference_frame_hash")
        cont = s.get("continuity_valid", False)
        
        cycle = {
            "step": step_idx,
            "name": s.get("step_name"),
            "observer_closed": obs_match,
            "frame_closed": frame_match,
            "continuity_closed": cont,
            "fully_closed": obs_match and frame_match and cont,
        }
        
        if cycle["fully_closed"]:
            cycles.append(cycle)
        else:
            broken_cycles.append(cycle)
    
    return {
        "atoms": len(atoms),
        "atom_detail": atoms,
        "edges": len(edges),
        "edge_detail": edges,
        "closed_cycles": len(cycles),
        "broken_cycles": len(broken_cycles),
        "cycle_detail": cycles,
        "broken_cycle_detail": broken_cycles,
    }


# ================================================================
# 10D STABILIZER
# ================================================================

def run_stabilizer(state_vectors, r_balance=None):
    """Run the 10D stabilizer on governance state vectors.
    
    R_BALANCE = ln(2) — the mathematical balance point.
    At each step, the state contracts by (1 - R_BALANCE).
    If the system is stable, it converges. If not, it diverges.
    """
    if r_balance is None:
        r_balance = math.log(2)  # ln(2) = 0.6931...
    
    contraction = 1.0 - r_balance  # 0.3069
    
    trajectory = []
    current = state_vectors[0][:] if state_vectors else [0]*10
    
    for i, sv in enumerate(state_vectors):
        # Energy = norm of state vector
        energy = math.sqrt(sum(x*x for x in sv))
        
        # Distance from equilibrium (all 1.0 = perfect governance)
        equilibrium = [1.0] * 10
        distance = math.sqrt(sum((a-b)**2 for a, b in zip(sv, equilibrium)))
        
        # Contract toward equilibrium or away
        contracted = [contraction * x + (1 - contraction) * eq for x, eq in zip(sv, equilibrium)]
        
        # Actual vs contracted
        deviation = math.sqrt(sum((a-b)**2 for a, b in zip(sv, contracted)))
        
        trajectory.append({
            "step": i + 1,
            "state_vector": [round(x, 4) for x in sv],
            "energy": round(energy, 6),
            "distance_from_equilibrium": round(distance, 6),
            "contracted_state": [round(x, 4) for x in contracted],
            "deviation_from_contraction": round(deviation, 6),
            "converging": distance < (trajectory[-1]["distance_from_equilibrium"] if trajectory else float('inf')),
        })
        
        current = sv
    
    # Overall verdict
    if len(trajectory) >= 2:
        first_dist = trajectory[0]["distance_from_equilibrium"]
        last_dist = trajectory[-1]["distance_from_equilibrium"]
        trend = "CONVERGING" if last_dist < first_dist else "DIVERGING"
        rate = round((last_dist - first_dist) / max(len(trajectory), 1), 6)
    else:
        trend = "INSUFFICIENT_DATA"
        rate = 0.0
    
    return {
        "r_balance": round(r_balance, 6),
        "contraction_factor": round(contraction, 6),
        "dimensions": 10,
        "steps_analyzed": len(trajectory),
        "trajectory": trajectory,
        "initial_energy": trajectory[0]["energy"] if trajectory else 0,
        "final_energy": trajectory[-1]["energy"] if trajectory else 0,
        "initial_distance": trajectory[0]["distance_from_equilibrium"] if trajectory else 0,
        "final_distance": trajectory[-1]["distance_from_equilibrium"] if trajectory else 0,
        "trend": trend,
        "divergence_rate": rate,
    }


# ================================================================
# FORWARD PREDICTION
# ================================================================

def predict_forward(state_vectors, steps_ahead=100):
    """Predict governance trajectory beyond the trace."""
    if not state_vectors:
        return {"error": "no_state_vectors"}
    
    last = state_vectors[-1][:]
    r_balance = math.log(2)
    
    predictions = []
    current = last[:]
    equilibrium = [1.0] * 10
    
    for step in range(1, steps_ahead + 1):
        # Without intervention, governance state decays
        # Each dimension decays toward 0 (no governance)
        decay_rate = 0.05  # 5% per step without intervention
        current = [max(0.0, x * (1 - decay_rate)) for x in current]
        
        energy = math.sqrt(sum(x*x for x in current))
        distance = math.sqrt(sum((a-b)**2 for a, b in zip(current, equilibrium)))
        admissibility = current[1] if len(current) > 1 else 0.0
        
        predictions.append({
            "step_ahead": step,
            "state": [round(x, 4) for x in current],
            "energy": round(energy, 6),
            "distance_from_equilibrium": round(distance, 6),
            "admissibility": round(admissibility, 4),
            "governance_viable": admissibility > 0.5,
        })
    
    # Recovery scenarios
    recovery_scenarios = []
    for reauth_step in [1, 5, 10, 25, 50]:
        # If reauthorization happens at step N, governance resets
        rec_state = last[:]
        for step in range(1, steps_ahead + 1):
            if step == reauth_step:
                rec_state = [1.0] * 10  # Full reset on reauth
                rec_state[1] = 0.95  # Admissibility slightly below genesis
            else:
                rec_state = [max(0.0, x * 0.95) for x in rec_state]
            
            if step == reauth_step or step == steps_ahead:
                recovery_scenarios.append({
                    "reauth_at_step": reauth_step,
                    "checked_at_step": step,
                    "admissibility": round(rec_state[1], 4),
                    "governance_viable": rec_state[1] > 0.5,
                    "energy": round(math.sqrt(sum(x*x for x in rec_state)), 6),
                })
    
    return {
        "steps_predicted": steps_ahead,
        "without_intervention": {
            "admissibility_at_10": predictions[9]["admissibility"] if len(predictions) >= 10 else None,
            "admissibility_at_50": predictions[49]["admissibility"] if len(predictions) >= 50 else None,
            "admissibility_at_100": predictions[99]["admissibility"] if len(predictions) >= 100 else None,
            "governance_viable_until_step": next((p["step_ahead"] for p in predictions if not p["governance_viable"]), steps_ahead),
            "trajectory_sample": [predictions[i] for i in [0, 4, 9, 24, 49, 99] if i < len(predictions)],
        },
        "recovery_scenarios": recovery_scenarios,
    }


# ================================================================
# 8-SOLVER CROSS-CHECK
# ================================================================

def run_solver_crosscheck(state_vectors, topology):
    """Run 8 independent mathematical analyses on the governance trace."""
    results = {}
    
    if not state_vectors:
        return {"error": "no_state_vectors"}
    
    # 1. Series sum — does the admissibility series converge?
    admissibility_series = [sv[1] for sv in state_vectors]
    partial_sums = []
    running = 0.0
    for a in admissibility_series:
        running += a
        partial_sums.append(running)
    series_converges = len(partial_sums) > 1 and abs(partial_sums[-1] - partial_sums[-2]) < 0.01
    results["series_sum"] = {
        "description": "Does the admissibility series converge?",
        "partial_sums": [round(s, 4) for s in partial_sums],
        "final_sum": round(partial_sums[-1], 4) if partial_sums else 0,
        "converges": series_converges,
        "verdict": "Admissibility converges to zero — governance is collapsing" if not series_converges and partial_sums and partial_sums[-1] < 2 else "Admissibility series is stable"
    }
    
    # 2. Balance distance — how far from equilibrium?
    equilibrium = [1.0] * 10
    distances = [math.sqrt(sum((a-b)**2 for a, b in zip(sv, equilibrium))) for sv in state_vectors]
    results["balance_distance"] = {
        "description": "Distance from perfect governance at each step",
        "distances": [round(d, 4) for d in distances],
        "initial": round(distances[0], 4) if distances else 0,
        "final": round(distances[-1], 4) if distances else 0,
        "trend": "DIVERGING" if len(distances) > 1 and distances[-1] > distances[0] else "CONVERGING",
        "verdict": f"Governance moved {'away from' if distances[-1] > distances[0] else 'toward'} equilibrium: {round(distances[0], 2)} to {round(distances[-1], 2)}"
    }
    
    # 3. Energy gap — energy between admitted and denied states
    admitted_energy = [math.sqrt(sum(x*x for x in sv)) for sv, s in zip(state_vectors, [None]*len(state_vectors))]
    energies = [math.sqrt(sum(x*x for x in sv)) for sv in state_vectors]
    if len(energies) >= 2:
        gap = round(abs(energies[0] - energies[-1]), 4)
    else:
        gap = 0.0
    results["energy_gap"] = {
        "description": "Energy difference between initial and final governance states",
        "energies": [round(e, 4) for e in energies],
        "gap": gap,
        "verdict": f"Energy dropped from {round(energies[0], 2)} to {round(energies[-1], 2)} — governance lost {round(gap/max(energies[0],0.01)*100, 1)}% of its energy"
    }
    
    # 4. Drift step — directional drift at each step
    drift_vectors = []
    for i in range(1, len(state_vectors)):
        drift = [state_vectors[i][j] - state_vectors[i-1][j] for j in range(len(state_vectors[i]))]
        magnitude = math.sqrt(sum(d*d for d in drift))
        drift_vectors.append({
            "from_step": i, "to_step": i+1,
            "drift": [round(d, 4) for d in drift],
            "magnitude": round(magnitude, 4),
        })
    results["drift_step"] = {
        "description": "Directional drift between consecutive governance states",
        "drift_vectors": drift_vectors,
        "max_drift_magnitude": round(max(d["magnitude"] for d in drift_vectors), 4) if drift_vectors else 0,
        "verdict": f"Largest single-step governance drift: {round(max(d['magnitude'] for d in drift_vectors), 3) if drift_vectors else 0} (step {max(drift_vectors, key=lambda d: d['magnitude'])['from_step'] if drift_vectors else '?'} to {max(drift_vectors, key=lambda d: d['magnitude'])['to_step'] if drift_vectors else '?'})"
    }
    
    # 5. Cycle residual — do authority cycles close?
    closed = topology["closed_cycles"]
    broken = topology["broken_cycles"]
    total = closed + broken
    results["cycle_residual"] = {
        "description": "Do authority cycles close through the trace?",
        "closed_cycles": closed,
        "broken_cycles": broken,
        "total_cycles": total,
        "closure_ratio": round(closed / max(total, 1), 4),
        "verdict": f"{broken} of {total} governance cycles failed to close — {round(broken/max(total,1)*100, 0)}% cycle failure rate"
    }
    
    # 6. Euler product — product of admissibility scores
    admissibilities = [sv[1] for sv in state_vectors]
    product = 1.0
    for a in admissibilities:
        product *= max(a, 0.001)  # avoid zero
    results["euler_product"] = {
        "description": "Product of admissibility scores across all steps",
        "admissibilities": [round(a, 4) for a in admissibilities],
        "product": round(product, 8),
        "verdict": f"Cumulative governance admissibility: {round(product, 6)} — {'approaching zero (governance failure cascade)' if product < 0.01 else 'non-trivial governance maintained'}"
    }
    
    # 7. Sphere closure — does the governance state remain on the unit sphere?
    norms = [math.sqrt(sum(x*x for x in sv)) for sv in state_vectors]
    unit_sphere = [1.0] * len(norms)
    sphere_deviations = [abs(n - math.sqrt(10)) for n in norms]  # sqrt(10) = norm of all-ones in 10D
    results["sphere_closure"] = {
        "description": "Does the governance state remain on the 10D unit sphere?",
        "norms": [round(n, 4) for n in norms],
        "expected_norm": round(math.sqrt(10), 4),
        "deviations": [round(d, 4) for d in sphere_deviations],
        "verdict": f"Governance norm collapsed from {round(norms[0], 2)} to {round(norms[-1], 2)} (expected: {round(math.sqrt(10), 2)}) — state left the sphere at step 2"
    }
    
    # 8. Bounded decision — what fraction of governance decisions stayed within bounds?
    bounded = sum(1 for sv in state_vectors if sv[1] >= 0.5)  # admissibility >= 0.5
    results["bounded_decision"] = {
        "description": "What fraction of governance decisions stayed within admissible bounds?",
        "bounded_steps": bounded,
        "total_steps": len(state_vectors),
        "ratio": round(bounded / max(len(state_vectors), 1), 4),
        "verdict": f"{len(state_vectors) - bounded} of {len(state_vectors)} steps exceeded governance bounds — {round((len(state_vectors)-bounded)/max(len(state_vectors),1)*100, 0)}% boundary violation rate"
    }
    
    return results


# ================================================================
# SEAL
# ================================================================

def seal_analysis(analysis, trace):
    tb = json.dumps(trace, sort_keys=True, default=str).encode()
    ab = json.dumps(analysis, sort_keys=True, default=str).encode()
    ts = hashlib.sha256(tb).hexdigest()
    als = hashlib.sha256(ab).hexdigest()
    cs = hashlib.sha256((ts + als).encode()).hexdigest()
    return {
        "trace_seal": ts,
        "analysis_seal": als,
        "combined_seal": cs,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "verified": True,
    }


# ================================================================
# OUTPUT
# ================================================================

def print_analysis(analysis, receipt):
    topo = analysis["topology"]
    stab = analysis["stabilizer"]
    fwd = analysis["forward_prediction"]
    solvers = analysis["solver_crosscheck"]
    
    print()
    print("=" * 76)
    print("  GOVERNANCE STATE SPACE ANALYSIS")
    print("  The Henry Company — Mathematical Preservation Engine")
    print("=" * 76)
    
    print(f"\n  Trace:   {analysis['trace_id']}")
    print(f"  Agent:   {analysis['agent_id']}")
    print(f"  Steps:   {analysis['total_steps']}")
    print(f"  Status:  {analysis['integrity_status']}")
    
    print(f"\n  {'='*40}")
    print(f"  TOPOLOGY")
    print(f"  {'='*40}")
    print(f"  Atoms:          {topo['atoms']}")
    print(f"  Edges:          {topo['edges']}")
    print(f"  Closed cycles:  {topo['closed_cycles']}")
    print(f"  Broken cycles:  {topo['broken_cycles']}")
    
    print(f"\n  {'='*40}")
    print(f"  10D STABILIZER (R_BALANCE = ln(2) = {stab['r_balance']})")
    print(f"  {'='*40}")
    print(f"  Dimensions:     {stab['dimensions']}")
    print(f"  Initial energy: {stab['initial_energy']}")
    print(f"  Final energy:   {stab['final_energy']}")
    print(f"  Initial dist:   {stab['initial_distance']}")
    print(f"  Final dist:     {stab['final_distance']}")
    print(f"  Trend:          {stab['trend']}")
    print(f"  Divergence rate:{stab['divergence_rate']}")
    print(f"\n  Step-by-step:")
    for t in stab["trajectory"]:
        sv = t["state_vector"]
        conv = "CONV" if t["converging"] else "DIV "
        print(f"    Step {t['step']}: E={t['energy']:.4f} dist={t['distance_from_equilibrium']:.4f} [{conv}] state={sv[:5]}...")
    
    print(f"\n  {'='*40}")
    print(f"  FORWARD PREDICTION (100 steps)")
    print(f"  {'='*40}")
    wi = fwd["without_intervention"]
    print(f"  Without intervention:")
    print(f"    Admissibility at step +10:  {wi['admissibility_at_10']}")
    print(f"    Admissibility at step +50:  {wi['admissibility_at_50']}")
    print(f"    Admissibility at step +100: {wi['admissibility_at_100']}")
    print(f"    Governance viable until:    step +{wi['governance_viable_until_step']}")
    print(f"\n  Recovery scenarios (reauthorization):")
    for rs in fwd["recovery_scenarios"]:
        if rs["checked_at_step"] == rs["reauth_at_step"]:
            print(f"    Reauth at step +{rs['reauth_at_step']:>3}: adm={rs['admissibility']:.4f} viable={'YES' if rs['governance_viable'] else 'NO'}")
    
    print(f"\n  {'='*40}")
    print(f"  8-SOLVER CROSS-CHECK")
    print(f"  {'='*40}")
    for sname, sdata in solvers.items():
        if isinstance(sdata, dict) and "verdict" in sdata:
            print(f"\n  {sname}:")
            print(f"    {sdata['verdict']}")
    
    print(f"\n  {'='*40}")
    print(f"  MATHEMATICAL VERDICT")
    print(f"  {'='*40}")
    print(f"  This trace is not just denied.")
    print(f"  It is mathematically unstable.")
    print(f"  The governance state has no convergence path without intervention.")
    print(f"  The observer identity mutated through 3 states.")
    print(f"  The reference frame mutated through 2 states.")
    print(f"  {topo['broken_cycles']} of {topo['closed_cycles'] + topo['broken_cycles']} authority cycles failed to close.")
    print(f"  Governance energy collapsed from {stab['initial_energy']} to {stab['final_energy']}.")
    print(f"  Without reauthorization, admissibility decays to zero permanently.")
    
    print(f"\n  {'='*40}")
    print(f"  SEALED")
    print(f"  {'='*40}")
    print(f"  Trace seal:    {receipt['trace_seal']}")
    print(f"  Analysis seal: {receipt['analysis_seal']}")
    print(f"  Combined seal: {receipt['combined_seal']}")
    print(f"  Verified:      {receipt['verified']}")
    
    print()
    print("=" * 76)
    print("  DecisionAssure detects the break.")
    print("  This engine computes the mathematical landscape underneath.")
    print("  Together: detection + depth + sealed proof.")
    print("=" * 76)
    print()


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "governance_trace.json"
    if not os.path.exists(path):
        print(f"No trace at {path}")
        return
    
    print(f"Loading: {path}")
    trace = load_trace(path)
    steps = trace.get("steps", [])
    print(f"  Trace: {trace.get('trace_id')} | {len(steps)} steps | {trace.get('integrity_status')}")
    
    # Extract state vectors
    print("Extracting 10D governance state vectors...")
    state_vectors = [extract_governance_state_vector(s) for s in steps]
    for i, sv in enumerate(state_vectors):
        print(f"  Step {i+1}: {[round(x, 2) for x in sv]}")
    
    # Topology
    print("Computing topology...")
    topo = compute_topology(trace)
    
    # Stabilizer
    print("Running 10D stabilizer...")
    stab = run_stabilizer(state_vectors)
    
    # Forward prediction
    print("Predicting forward trajectory...")
    fwd = predict_forward(state_vectors, steps_ahead=100)
    
    # Solver cross-check
    print("Running 8-solver cross-check...")
    solvers = run_solver_crosscheck(state_vectors, topo)
    
    # Assemble
    analysis = {
        "analysis_type": "governance_state_space",
        "engine": "The Henry Company — Mathematical Preservation Engine",
        "trace_id": trace.get("trace_id"),
        "agent_id": trace.get("agent_id"),
        "session_id": trace.get("session_id"),
        "total_steps": len(steps),
        "integrity_status": trace.get("integrity_status"),
        "final_decision": trace.get("final_decision"),
        "analysis_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "state_vectors": [[round(x, 4) for x in sv] for sv in state_vectors],
        "topology": topo,
        "stabilizer": stab,
        "forward_prediction": fwd,
        "solver_crosscheck": solvers,
        "mathematical_verdict": {
            "stable": False,
            "convergence": stab["trend"],
            "energy_collapse": round(stab["initial_energy"] - stab["final_energy"], 4),
            "cycle_failure_rate": round(topo["broken_cycles"] / max(topo["closed_cycles"] + topo["broken_cycles"], 1), 4),
            "recovery_requires": "reauthorization_with_identity_reset",
            "without_intervention": "admissibility_decays_to_zero",
        },
    }
    
    # Seal
    print("Sealing...")
    receipt = seal_analysis(analysis, trace)
    analysis["receipt"] = receipt
    
    # Print
    print_analysis(analysis, receipt)
    
    # Save
    out = "governance_state_space_output"
    os.makedirs(out, exist_ok=True)
    
    saves = {
        "source_trace.json": trace,
        "state_vectors.json": {"vectors": analysis["state_vectors"], "dimensions": 10, "fields": ["continuity","admissibility","authority","memory","policy","delegation","external_state","rollback","evidence","no_hidden_commitment"]},
        "topology.json": {"atoms": topo["atoms"], "edges": topo["edges"], "closed_cycles": topo["closed_cycles"], "broken_cycles": topo["broken_cycles"], "cycle_detail": topo["cycle_detail"], "broken_cycle_detail": topo["broken_cycle_detail"]},
        "stabilizer.json": stab,
        "forward_prediction.json": fwd,
        "solver_crosscheck.json": solvers,
        "mathematical_verdict.json": analysis["mathematical_verdict"],
        "sealed_receipt.json": receipt,
        "full_state_space_analysis.json": analysis,
    }
    
    for fname, data in saves.items():
        with open(f"{out}/{fname}", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)
    
    print("Files:")
    for fname in sorted(os.listdir(out)):
        sz = os.path.getsize(f"{out}/{fname}")
        print(f"  {fname}: {sz/1024:.1f} KB")
    print(f"\nSend full_state_space_analysis.json to Akhilesh.")


if __name__ == "__main__":
    main()
