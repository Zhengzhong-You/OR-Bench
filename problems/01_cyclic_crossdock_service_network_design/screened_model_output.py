# cyclic_freight_gurobi.py
# Requires gurobipy (Gurobi Python API).
# Models tractor rotations (up to 2 distinct tractors) on a weekly periodic time-space network,
# enforces listed legs can be opened at most once per week, enforces each opened leg must be
# traversed by exactly one tractor, allows waiting at terminals, and selects a shipment path.
#
# Prints:
# - solver status
# - proven objective, bound and gap
# - chosen shipment path
# - every opened leg
# - closed weekly tractor rotation(s)

from gurobipy import Model, GRB, quicksum

def build_and_solve():
    # Locations and slots (periodic: 4 slots 0..3)
    locs = ['O', 'H', 'D']
    slots = [0, 1, 2, 3]

    # Helper to make node label
    def node_label(node):
        loc, slot = node
        return f"{loc}@{slot}"

    # Build nodes: (loc, slot)
    nodes = [(loc, s) for loc in locs for s in slots]

    # Define listed legs (name, origin node, dest node, cost, forward_eligible_for_shipment)
    # 'dest' times that are earlier than origin are treated modulo the weekly period (wrap to next week)
    listed_legs = [
        ("F1", ("O", 0), ("H", 1), 2.0, True),
        ("R1", ("H", 1), ("O", 0), 2.0, False),
        ("F2", ("H", 1), ("D", 2), 2.0, True),   # forward but cannot be used in feasible path due to reload rule
        ("R2", ("D", 2), ("H", 1), 2.0, False),
        ("F3", ("H", 2), ("D", 3), 10.0, True),
        ("R3", ("D", 3), ("H", 2), 10.0, False),
        ("F4", ("O", 0), ("D", 3), 7.5, True),
        ("R4", ("D", 3), ("O", 0), 7.5, False),
    ]

    # Build full arc list: waiting arcs + listed legs
    arcs = []
    # waiting arcs (stay at terminal from slot t to t+1 mod 4)
    for loc in locs:
        for t in slots:
            origin = (loc, t)
            dest = (loc, (t + 1) % 4)
            arcs.append({
                "name": f"wait_{loc}_{t}_to_{loc}_{(t+1)%4}",
                "origin": origin,
                "dest": dest,
                "cost": 0.0,
                "leg": None,        # not a listed leg
                "listed": False,
                "forward_eligible": False
            })

    # Add the listed legs as arcs
    for (lname, orig, dest, cost, forward_ok) in listed_legs:
        arcs.append({
            "name": lname,
            "origin": orig,
            "dest": dest,
            "cost": cost,
            "leg": lname,
            "listed": True,
            "forward_eligible": forward_ok
        })

    # Index arcs for convenience
    arc_count = len(arcs)
    arc_index = list(range(arc_count))

    # Precompute incoming/outgoing arc indices per node
    incoming = {node: [] for node in nodes}
    outgoing = {node: [] for node in nodes}
    for aidx, a in enumerate(arcs):
        outgoing[a["origin"]].append(aidx)
        incoming[a["dest"]].append(aidx)

    # Map leg name to its arc index (for listed legs)
    leg_to_arc = {a["leg"]: idx for idx, a in enumerate(arcs) if a["leg"] is not None}

    # Candidate shipment paths (enumerated from business logic, respecting reload rule)
    # The freight is at O@0 and must arrive at D by end of slot 3.
    # Because freight arriving at H in slot 1 cannot board a departure in slot 1,
    # path using F2 (H@1 -> D@2) is infeasible for this specific freight.
    # Feasible paths for the freight starting O@0 by slot3 are:
    # - Direct F4 (O@0 -> D@3)
    # - F1 then F3 (O@0 -> H@1 ; wait/unload -> H@2 -> D@3)
    path_defs = {
        "P_F4": ["F4"],
        "P_F1_F3": ["F1", "F3"]
    }

    # Build optimization model
    m = Model("Cyclic_Freight_Service_Design")
    m.setParam('OutputFlag', 1)  # 1 to get Gurobi output; set to 0 to be quiet

    tractors = [1, 2]  # up to 2 owned tractors

    # Decision variables:
    # x_leg[l] = 1 if listed leg l is operated this week
    x_leg = {}
    for (lname, _, _, _, _) in listed_legs:
        x_leg[lname] = m.addVar(vtype=GRB.BINARY, name=f"x_{lname}")

    # f[a,k] = 1 if tractor k traverses arc a (arcs include waiting arcs and listed legs)
    f = {}
    for aidx in arc_index:
        for k in tractors:
            f[(aidx, k)] = m.addVar(vtype=GRB.BINARY, name=f"f_a{aidx}_t{k}")

    # Path selection variables (choose exactly one shipment path)
    p = {}
    for pname in path_defs:
        p[pname] = m.addVar(vtype=GRB.BINARY, name=f"p_{pname}")

    m.update()

    # Constraints:

    # 1) If a listed leg is operated, exactly one tractor must traverse it; if not operated, no tractor traverses it.
    for (lname, _, _, _, _) in listed_legs:
        aidx = leg_to_arc[lname]
        m.addConstr(quicksum(f[(aidx, k)] for k in tractors) == x_leg[lname],
                    name=f"leg_served_once_{lname}")

    # 2) Flow conservation for each tractor at every node (closed cycles)
    for k in tractors:
        for node in nodes:
            m.addConstr(quicksum(f[(aidx, k)] for aidx in incoming[node]) ==
                        quicksum(f[(aidx, k)] for aidx in outgoing[node]),
                        name=f"flow_cons_k{k}_{node_label(node)}")

    # 3) Exactly one shipment path is chosen
    m.addConstr(quicksum(p[pname] for pname in p) == 1, name="choose_one_path")

    # 4) If a path is chosen, all listed forward legs comprising it must be opened
    for pname, legs in path_defs.items():
        for legname in legs:
            m.addConstr(x_leg[legname] >= p[pname], name=f"path_{pname}_requires_{legname}")

    # Objective: minimize weekly operating cost (sum of costs for every opened listed leg)
    m.setObjective(quicksum(x_leg[lname] * next(a["cost"] for a in arcs if a["leg"] == lname)
                             for lname in x_leg), GRB.MINIMIZE)

    # Solve
    m.optimize()

    # Print solver status and bounds
    status = m.Status
    status_str = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INF_OR_UNBD: "INFEASIBLE_OR_UNBOUNDED",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INTERRUPTED: "INTERRUPTED",
        GRB.SUBOPTIMAL: "SUBOPTIMAL"
    }.get(status, f"STATUS_{status}")

    print("\n--- SOLVER SUMMARY ---")
    print("Gurobi status:", status_str)
    if m.SolCount > 0:
        print(f"Proven objective (primal) : {m.ObjVal:.6f}")
        # ObjBound is a lower bound for minimization
        try:
            bound = m.ObjBound
        except:
            bound = None
        if bound is not None:
            # MIPGap may be None for continuous problems
            gap = m.MIPGap if hasattr(m, "MIPGap") else None
            print(f"Best bound (dual/LB)     : {bound:.6f}")
            if gap is not None:
                print(f"MIP gap                  : {gap:.6g}")
    else:
        print("No feasible solution found by the solver.")

    # Extract solution values (if available)
    if m.SolCount == 0:
        return  # nothing more to print

    # Which shipment path was selected?
    chosen_path = None
    for pname, var in p.items():
        if var.X > 0.5:
            chosen_path = pname
            break

    print("\n--- SHIPMENT PATH ---")
    if chosen_path is None:
        print("No shipment path chosen (unexpected).")
    else:
        legs_in_path = path_defs[chosen_path]
        print(f"Chosen path variable: {chosen_path}")
        print("Shipment will use listed leg(s):", " -> ".join(legs_in_path))
        # print times for those legs
        for legname in legs_in_path:
            aidx = leg_to_arc[legname]
            a = arcs[aidx]
            print(f"  {legname}: {node_label(a['origin'])} -> {node_label(a['dest'])}, cost {a['cost']}")

    # List all opened legs this week
    print("\n--- OPENED LISTED LEGS (operated at most once per week) ---")
    opened_legs = []
    for lname, var in x_leg.items():
        if var.X > 0.5:
            aidx = leg_to_arc[lname]
            a = arcs[aidx]
            opened_legs.append((lname, a['origin'], a['dest'], a['cost']))
            print(f"  {lname}: {node_label(a['origin'])} -> {node_label(a['dest'])}, cost {a['cost']:.2f}")
    if len(opened_legs) == 0:
        print("  (none)")

    # Reconstruct closed weekly tractor rotations for each tractor
    print("\n--- CLOSED WEEKLY TRACTOR ROTATIONS ---")
    for k in tractors:
        used_arc_indices = [aidx for aidx in arc_index if f[(aidx, k)].X > 0.5]
        if not used_arc_indices:
            print(f"Tractor {k}: not used this week.")
            continue

        # Build mapping origin_node -> arc_index for this tractor
        origin_to_aidx = {}
        for aidx in used_arc_indices:
            origin = arcs[aidx]['origin']
            if origin in origin_to_aidx:
                # This should not happen for a valid circulation with binary per-tractor flow
                # but guard defensively.
                print(f"Warning: tractor {k} has multiple outgoing arcs from node {origin}.")
            origin_to_aidx[origin] = aidx

        # Start at an arbitrary used arc and follow cycle
        start_aidx = used_arc_indices[0]
        start_node = arcs[start_aidx]['origin']
        current_node = start_node
        rotation = []
        visited_nodes = set()
        max_steps = len(used_arc_indices) + 5  # safety guard
        step = 0
        while True:
            step += 1
            if step > max_steps:
                # Something went wrong (shouldn't happen)
                print(f"  (Error reconstructing rotation for tractor {k}, aborting reconstruction.)")
                break
            if current_node not in origin_to_aidx:
                # Dead end -- shouldn't happen due to flow conservation
                print(f"  (Dead end while reconstructing tractor {k} rotation at node {current_node})")
                break
            aidx = origin_to_aidx[current_node]
            rotation.append(aidx)
            current_node = arcs[aidx]['dest']
            if current_node == start_node:
                # one full cycle completed
                break

        # Print rotation details
        print(f"Tractor {k} rotation (closed weekly cycle):")
        for aidx in rotation:
            a = arcs[aidx]
            if a["listed"]:
                # listed leg
                legtag = a["leg"]
                in_path = (chosen_path is not None and legtag in path_defs[chosen_path])
                note = " [shipment]" if in_path else ""
                print(f"  {a['name']}: {node_label(a['origin'])} -> {node_label(a['dest'])}, cost {a['cost']}{note}")
            else:
                # waiting arc
                print(f"  {a['name']}: {node_label(a['origin'])} -> {node_label(a['dest'])}, wait (cost 0)")
        # End tractor k

    print("\n--- END OF SOLUTION ---\n")

if __name__ == "__main__":
    build_and_solve()
