# Cyclic Freight Service Design with Cross-Dock Handling
# Complete runnable Python + gurobipy model

import gurobipy as gp
from gurobipy import GRB

# -----------------------------
# Data
# -----------------------------
slots = [0, 1, 2, 3]
locs = ["O", "H", "D"]

# Periodic tractor network nodes: (location, slot)
nodes = [(loc, t) for loc in locs for t in slots]

def n(loc, t):
    return (loc, t)

# Service legs
# tail -> head in the periodic weekly network
legs = {
    "F1": {"tail": n("O", 0), "head": n("H", 1), "cost": 2.0,  "ship_ok": True},
    "R1": {"tail": n("H", 1), "head": n("O", 0), "cost": 2.0,  "ship_ok": False},  # next week
    "F2": {"tail": n("H", 1), "head": n("D", 2), "cost": 2.0,  "ship_ok": True},
    "R2": {"tail": n("D", 2), "head": n("H", 1), "cost": 2.0,  "ship_ok": False},  # next week
    "F3": {"tail": n("H", 2), "head": n("D", 3), "cost": 10.0, "ship_ok": True},
    "R3": {"tail": n("D", 3), "head": n("H", 2), "cost": 10.0, "ship_ok": False},  # next week
    "F4": {"tail": n("O", 0), "head": n("D", 3), "cost": 7.5,  "ship_ok": True},
    "R4": {"tail": n("D", 3), "head": n("O", 0), "cost": 7.5,  "ship_ok": False},  # next week
}

# Zero-cost waiting arcs for tractors
# Wait one slot at same terminal; slot 3 -> slot 0 is next week
wait_arcs = {}
for loc in locs:
    for t in slots:
        t2 = (t + 1) % 4
        name = f"W_{loc}{t}_{loc}{t2}"
        wait_arcs[name] = {"tail": n(loc, t), "head": n(loc, t2), "cost": 0.0}

all_arcs = {}
all_arcs.update(legs)
all_arcs.update(wait_arcs)

# Arcs that cross the weekly cut (from this week to next week)
# A tractor circulation crosses this cut exactly once per cycle.
def crosses_weekly_cut(arc):
    tail_t = arc["tail"][1]
    head_t = arc["head"][1]
    return head_t <= tail_t

cut_arcs = [a for a, dat in all_arcs.items() if crosses_weekly_cut(dat)]

# -----------------------------
# Shipment path network
# -----------------------------
# To enforce H handling taking one full slot:
# - Freight arriving on F1 reaches H-arrival at slot 1.
# - It must traverse processing arc P_H1_H2 to become eligible at H slot 2.
# - Therefore it cannot use F2 after F1.
#
# Separate shipment-specific nodes:
ship_nodes = ["O0", "H1_DEP", "H1_ARR", "H2_READY", "D2", "D3"]

ship_arcs = {
    "F1":      {"tail": "O0",      "head": "H1_ARR"},
    "P_H1_H2": {"tail": "H1_ARR",  "head": "H2_READY"},
    "F2":      {"tail": "H1_DEP",  "head": "D2"},
    "F3":      {"tail": "H2_READY","head": "D3"},
    "F4":      {"tail": "O0",      "head": "D3"},
}

# Flow balance for one indivisible load
ship_balance = {v: 0 for v in ship_nodes}
ship_balance["O0"] = 1
ship_balance["D2"] = -1
ship_balance["D3"] = -1
# Since only one unit ships, exactly one destination node will absorb it.

# -----------------------------
# Model
# -----------------------------
m = gp.Model("cyclic_freight_service_design")

# Leg opening decisions
y = m.addVars(legs.keys(), vtype=GRB.BINARY, name="open")

# Tractor circulation arc flows (integer, up to 2 because at most 2 tractors exist)
f = m.addVars(all_arcs.keys(), vtype=GRB.INTEGER, lb=0, ub=2, name="tractor")

# Shipment path binary arc usage
x = m.addVars(ship_arcs.keys(), vtype=GRB.BINARY, name="ship")

# Objective: minimize weekly operating cost of opened service legs
m.setObjective(gp.quicksum(legs[a]["cost"] * y[a] for a in legs), GRB.MINIMIZE)

# -----------------------------
# Constraints
# -----------------------------

# Each opened service leg uses exactly one tractor on that service arc
for a in legs:
    m.addConstr(f[a] == y[a], name=f"service_tractor_link_{a}")

# Tractor flow conservation at every periodic node
for v in nodes:
    inflow = gp.quicksum(f[a] for a, dat in all_arcs.items() if dat["head"] == v)
    outflow = gp.quicksum(f[a] for a, dat in all_arcs.items() if dat["tail"] == v)
    m.addConstr(inflow == outflow, name=f"tractor_balance_{v[0]}_{v[1]}")

# At most two tractors in the weekly cyclic plan
m.addConstr(gp.quicksum(f[a] for a in cut_arcs) <= 2, name="fleet_limit")

# Shipment flow conservation
for v in ship_nodes:
    inflow = gp.quicksum(x[a] for a, dat in ship_arcs.items() if dat["head"] == v)
    outflow = gp.quicksum(x[a] for a, dat in ship_arcs.items() if dat["tail"] == v)
    rhs = ship_balance[v]
    m.addConstr(outflow - inflow == rhs, name=f"ship_balance_{v}")

# Shipment can only use opened service legs
for a in ["F1", "F2", "F3", "F4"]:
    m.addConstr(x[a] <= y[a], name=f"ship_leg_open_{a}")

# Process arc only if freight actually arrived at H in slot 1
m.addConstr(x["P_H1_H2"] == x["F1"], name="process_if_arrive_H1")

# Because destination is "no later than end of slot 3", both D2 and D3 are acceptable sinks.
# The node balances above already enforce exactly one unit gets absorbed at either D2 or D3.

# Optional: tighten integrality logic
# If no shipment arrives to H1_ARR, no processing; already enforced.
# F2 is available only from H1_DEP, and no supply reaches H1_DEP in this instance, so model will set x[F2]=0.

m.optimize()

# -----------------------------
# Reporting helpers
# -----------------------------
def node_str(v):
    return f"{v[0]}@{v[1]}"

def arc_desc(name, dat):
    tail = node_str(dat["tail"])
    head = node_str(dat["head"])
    nxt = " (next week arrival)" if crosses_weekly_cut(dat) else ""
    return f"{name}: {tail} -> {head}{nxt}"

def chosen_outgoing(remaining, current_node):
    for a, cnt in remaining.items():
        if cnt > 0 and all_arcs[a]["tail"] == current_node:
            return a
    return None

def decompose_rotations(flow_solution):
    """
    Decompose integer tractor circulation into closed weekly rotations.
    We start one rotation per unit of flow on the weekly cut arcs.
    """
    remaining = {a: int(round(flow_solution[a])) for a in all_arcs}
    rotations = []

    # Build a list of cut-crossing arc units; each tractor cycle crosses cut exactly once
    cut_units = []
    for a in cut_arcs:
        cut_units.extend([a] * remaining[a])

    used_as_starter = {i: False for i in range(len(cut_units))}

    for idx, start_arc in enumerate(cut_units):
        if used_as_starter[idx]:
            continue
        if remaining[start_arc] <= 0:
            used_as_starter[idx] = True
            continue

        used_as_starter[idx] = True
        remaining[start_arc] -= 1

        dat0 = all_arcs[start_arc]
        start_tail = dat0["tail"]
        current = dat0["head"]

        cycle = [start_arc]

        # Follow arcs until we return to the tail of the starting cut-crossing arc
        safety = 0
        while current != start_tail:
            a = chosen_outgoing(remaining, current)
            if a is None:
                raise RuntimeError(f"Could not complete tractor rotation from node {current}")
            cycle.append(a)
            remaining[a] -= 1
            current = all_arcs[a]["head"]
            safety += 1
            if safety > 100:
                raise RuntimeError("Rotation decomposition exceeded safety limit.")

        rotations.append(cycle)

    # Check no used arcs remain
    leftovers = [a for a, cnt in remaining.items() if cnt > 0]
    if leftovers:
        raise RuntimeError(f"Unused positive-flow arcs left after decomposition: {leftovers}")

    return rotations

def shipment_path_string(xsol):
    used = [a for a in ship_arcs if xsol[a] > 0.5]
    if not used:
        return "No shipment path selected."

    # Trace from O0
    outgoing = {}
    for a in used:
        outgoing.setdefault(ship_arcs[a]["tail"], []).append(a)

    path = []
    cur = "O0"
    visited = 0
    while cur in outgoing and outgoing[cur]:
        a = outgoing[cur][0]
        path.append(a)
        cur = ship_arcs[a]["head"]
        visited += 1
        if visited > 20:
            break

    # Friendly display
    parts = []
    cur = "O0"
    parts.append(cur)
    for a in path:
        cur = ship_arcs[a]["head"]
        if a == "P_H1_H2":
            parts.append("[cross-dock process 1 slot]")
        else:
            parts.append(a)
        parts.append(cur)
    return " -> ".join(parts)

# -----------------------------
# Print results
# -----------------------------
print("\n================ SOLVER RESULT ================")
print(f"Status code: {m.Status}")
print(f"Status text: {m.Status if m.Status != GRB.OPTIMAL else 'OPTIMAL'}")

if m.SolCount > 0:
    print(f"Proven objective: {m.ObjVal}")
    print(f"Best bound: {m.ObjBound}")
    gap = abs(m.ObjVal - m.ObjBound) / max(1e-10, abs(m.ObjVal))
    print(f"Relative gap: {gap:.6f}")
else:
    print("No feasible solution found.")
    raise SystemExit(0)

# Opened legs
open_legs = [a for a in legs if y[a].X > 0.5]
print("\nOpened weekly service legs:")
for a in open_legs:
    print(f"  {arc_desc(a, legs[a])}, cost = {legs[a]['cost']}")

# Shipment path
xsol = {a: x[a].X for a in ship_arcs}
print("\nShipment path:")
print(f"  {shipment_path_string(xsol)}")

# Tractor rotations
fsol = {a: f[a].X for a in all_arcs}
rotations = decompose_rotations(fsol)

print("\nClosed weekly tractor rotation(s):")
for i, cyc in enumerate(rotations, 1):
    print(f"  Rotation {i}:")
    for a in cyc:
        dat = all_arcs[a]
        kind = "WAIT" if a in wait_arcs else "LEG "
        print(f"    {kind}  {arc_desc(a, dat)}")

# Also print all used tractor arcs, including waits
used_arcs = [a for a in all_arcs if f[a].X > 0.5]
print("\nAll tractor arcs used in the cyclic plan:")
for a in used_arcs:
    dat = all_arcs[a]
    val = int(round(f[a].X))
    print(f"  flow {val}: {arc_desc(a, dat)}")
