# cyclic_freight_service.py
from gurobipy import Model, GRB, quicksum

# Data: legs in the periodic network
# Format: leg_name: (tail_terminal, tail_slot, head_terminal, head_slot, cost, shipment_eligible)
legs = {
    'F1': ('O', 0, 'H', 1, 2.0, True),
    'R1': ('H', 1, 'O', 0, 2.0, False),
    'F2': ('H', 1, 'D', 2, 2.0, True),
    'R2': ('D', 2, 'H', 1, 2.0, False),
    'F3': ('H', 2, 'D', 3, 10.0, True),
    'R3': ('D', 3, 'H', 2, 10.0, False),
    'F4': ('O', 0, 'D', 3, 7.5, True),
    'R4': ('D', 3, 'O', 0, 7.5, False),
}

terminals = ['O', 'H', 'D']
slots = [0, 1, 2, 3]

# Build the periodic tractor-rotation arcs (listed legs + waiting arcs including wrap 3->0)
# Each listed leg is an arc; waiting arcs allow tractors to remain at a terminal from slot t to t+1 (mod 4).
arc_info = {}  # name -> (tail_node, head_node, type) type in {'leg','wait'}
# Add listed legs
for name, (t_term, t_slot, h_term, h_slot, cost, ship_ok) in legs.items():
    tail = (t_term, t_slot)
    head = (h_term, h_slot)
    arc_info[name] = (tail, head, 'leg')

# Add waiting arcs for tractors (wrap-around included)
for term in terminals:
    for t in slots:
        h = (t + 1) % 4
        name = f'W_{term}_{t}_to_{h}'
        arc_info[name] = ((term, t), (term, h), 'wait')

# Build the shipment time-expanded network arcs (forward legs + non-wrap waiting arcs only)
# Shipment waiting arcs allowed from slot 0->1, 1->2, 2->3 (no wrap for shipments because delivery must be by end of slot 3)
ship_arc_info = {}  # name -> (tail_node, head_node, type)
# forward legs that can carry shipment
for leg_name, (t_term, t_slot, h_term, h_slot, cost, ship_ok) in legs.items():
    if ship_ok:
        ship_arc_info[leg_name] = ((t_term, t_slot), (h_term, h_slot), 'leg')
# shipment waiting arcs (no wrap)
for term in terminals:
    for t in [0, 1, 2]:
        name = f'SW_{term}_{t}_to_{t+1}'
        ship_arc_info[name] = ((term, t), (term, t+1), 'wait')

# Create model
m = Model('cyclic_freight_service')
m.setParam('OutputFlag', 1)  # show solver output

# Decision variables
# y[leg] = 1 if listed leg (forward or return) is operated this week
y = m.addVars(list(legs.keys()), vtype=GRB.BINARY, name='y')

# x[arc] = integer number of tractors traversing the tractor-time arc each week (forming periodic rotations)
# For listed legs the arc can be used at most once per week -> upper bound 1
# For waiting arcs, up to the total number of tractors (max 2)
x = {}
for a_name, (tail, head, atype) in arc_info.items():
    if atype == 'leg':
        # listed leg: at most one tractor can operate it in a weekly cycle
        x[a_name] = m.addVar(vtype=GRB.INTEGER, lb=0, ub=1, name=f'x_{a_name}')
    else:
        # waiting arcs: at most 2 tractors can wait simultaneously at a terminal
        x[a_name] = m.addVar(vtype=GRB.INTEGER, lb=0, ub=2, name=f'x_{a_name}')

# p[a] = 1 if the single indivisible shipment uses that shipment-arc
p = {}
for a_name, (tail, head, atype) in ship_arc_info.items():
    p[a_name] = m.addVar(vtype=GRB.BINARY, name=f'p_{a_name}')

# Number of tractors used (integer)
T = m.addVar(vtype=GRB.INTEGER, lb=0, ub=2, name='T')

m.update()

# Constraints

# 1) If a listed leg is not opened (y=0) then no tractor can traverse it; if opened, at most one tractor can traverse:
for leg_name in legs.keys():
    m.addConstr(x[leg_name] <= y[leg_name], name=f'cap_if_open_{leg_name}')

# 2) Tractor flow conservation at every periodic node (terminal, slot)
nodes = [(term, s) for term in terminals for s in slots]
for node in nodes:
    inflow = quicksum(x[a_name] for a_name, (tail, head, atype) in arc_info.items() if head == node)
    outflow = quicksum(x[a_name] for a_name, (tail, head, atype) in arc_info.items() if tail == node)
    m.addConstr(inflow == outflow, name=f'flow_cons_{node[0]}_{node[1]}')

# 3) Count tractors by counting arcs that cross the slot-3 -> slot-0 time boundary:
#    every tractor traverses exactly one arc whose tail slot == 3 during a weekly cycle.
sum_tail_slot3 = quicksum(x[a_name] for a_name, (tail, head, atype) in arc_info.items() if tail[1] == 3)
m.addConstr(sum_tail_slot3 == T, name='tractors_count')
m.addConstr(T <= 2, name='max_tractors')

# 4) Shipment flow conservation in the shipment time-expanded network
# Origin: O@0 must have net outflow = 1 (single trailer-load)
origin = ('O', 0)
sinks = [('D', 2), ('D', 3)]  # allowed arrival nodes by end of slot 3

# For nodes except origin and sinks: inflow == outflow
for node in [(term, s) for term in terminals for s in [0, 1, 2, 3]]:
    inflow_p = quicksum(p[a_name] for a_name, (tail, head, atype) in ship_arc_info.items() if head == node)
    outflow_p = quicksum(p[a_name] for a_name, (tail, head, atype) in ship_arc_info.items() if tail == node)
    if node == origin:
        m.addConstr(outflow_p - inflow_p == 1, name=f'ship_flow_origin_{node}')
    elif node in sinks:
        # sinks: allowed to have inflow 0 or 1; we'll require total inflow to sinks to be 1 below.
        # Ensure that if something arrives at sink, it does not leave (we simply never created outgoing shipment arcs from sinks)
        # So skip general conservation for sinks.
        pass
    else:
        m.addConstr(inflow_p == outflow_p, name=f'ship_flow_cons_{node}')

# Ensure exactly one unit of shipment reaches either D@2 or D@3
in_at_D2 = quicksum(p[a_name] for a_name, (tail, head, atype) in ship_arc_info.items() if head == ('D', 2))
in_at_D3 = quicksum(p[a_name] for a_name, (tail, head, atype) in ship_arc_info.items() if head == ('D', 3))
m.addConstr(in_at_D2 + in_at_D3 == 1, name='ship_reaches_destination')

# 5) Shipment may only use a forward listed leg if that leg is opened and a tractor traverses it
for leg_name, legdata in legs.items():
    _, _, _, _, _, ship_ok = legdata
    if ship_ok:
        # If shipment uses leg -> that leg's y must be 1 and a tractor must actually traverse it
        m.addConstr(p[leg_name] <= y[leg_name], name=f'ship_leg_open_{leg_name}')
        m.addConstr(p[leg_name] <= x[leg_name], name=f'ship_leg_x_lower_{leg_name}')
        # Also enforce x >= p to tie tractor usage to chosen shipment arc (redundant with last line but explicit)
        m.addConstr(x[leg_name] >= p[leg_name], name=f'ship_leg_x_ge_p_{leg_name}')

# 6) Enforce the H transshipment one-slot delay:
# The freight arriving to H in slot 1 via F1 cannot board F2 (which departs H at slot 1).
# That is, forbid the simultaneous use of F1 (arrive H1) and F2 (depart H1) by the same shipment.
if ('F1' in p) and ('F2' in p):
    m.addConstr(p['F1'] + p['F2'] <= 1, name='H_transshipment_delay')

# Objective: minimize weekly operating cost (sum of opened leg costs, forward and return)
m.setObjective(quicksum(legs[leg][4] * y[leg] for leg in legs.keys()), GRB.MINIMIZE)

# Optimize
m.optimize()

# Helper function to map status code to string
def status_to_string(st):
    if st == GRB.OPTIMAL:
        return 'OPTIMAL'
    if st == GRB.TIME_LIMIT:
        return 'TIME_LIMIT'
    if st == GRB.INFEASIBLE:
        return 'INFEASIBLE'
    if st == GRB.INF_OR_UNBD:
        return 'INF_OR_UNBD'
    if st == GRB.UNBOUNDED:
        return 'UNBOUNDED'
    if st == GRB.CUTOFF:
        return 'CUTOFF'
    return f'STATUS_{st}'

print("\n--- SOLUTION SUMMARY ---")
print("Solver status:", status_to_string(m.status))
if m.SolCount > 0:
    print("Proven objective (best found):", m.ObjVal)
    # ObjBound is the best bound on objective value
    try:
        print("Best bound:", m.ObjBound)
    except Exception:
        print("Best bound: (not available)")
    try:
        print("MIP gap (relative):", m.MIPGap)
    except Exception:
        print("MIP gap: (not available)")
else:
    print("No feasible solution found.")
    # Stop here if no solution
    import sys
    sys.exit(0)

# Shipment path: reconstruct sequence from O@0 to D@2 or D@3 using p variables
active_p = {name: var.X for name, var in p.items() if var.X > 0.5}
print("\nShipment arcs used (p = 1):")
for name in active_p:
    tail, head, atype = ship_arc_info[name]
    print(f"  {name}: {tail} -> {head} ({atype})")

# Reconstruct path order
def node_str(node):
    return f"{node[0]}@{node[1]}"

shipment_path = []
current = origin
visited = set()
while True:
    # Find outgoing active p arc from current
    outgoing = [name for name, (t, h, atype) in ship_arc_info.items() if t == current and name in active_p]
    if len(outgoing) == 0:
        # Either we've reached a sink or something's inconsistent
        if current in sinks:
            break
        else:
            print("Warning: cannot continue reconstructing shipment path from", node_str(current))
            break
    if len(outgoing) > 1:
        print("Warning: multiple outgoing shipment arcs from", node_str(current), ":", outgoing)
    arc_name = outgoing[0]
    shipment_path.append((arc_name, ship_arc_info[arc_name][0], ship_arc_info[arc_name][1]))
    current = ship_arc_info[arc_name][1]
    # Prevent infinite loops
    if (current, arc_name) in visited:
        print("Warning: loop detected in shipment path.")
        break
    visited.add((current, arc_name))
    if current in sinks:
        break

print("\nShipment path in order:")
for arc_name, tail, head in shipment_path:
    print(f"  {arc_name}: {node_str(tail)} -> {node_str(head)}")

# Opened legs (y = 1)
opened = [leg for leg, var in y.items() if var.X > 0.5]
print("\nOpened (operated) listed legs this week (y = 1):")
for leg in opened:
    t_term, t_slot, h_term, h_slot, cost, ship_ok = legs[leg]
    print(f"  {leg}: {t_term}@{t_slot} -> {h_term}@{h_slot}  cost={cost}  ship_eligible={ship_ok}")

# Tractor rotations: extract integer cycles from x[arc] flows
# Build residual counts
residual = {a_name: int(round(var.X)) for a_name, var in x.items() if var.X > 0.5}
# Build mapping arc -> (tail, head)
arc_tail_head = {a_name: (tail, head) for a_name, (tail, head, atype) in arc_info.items()}

cycles = []
while True:
    # find an arc with positive residual count
    arcs_with_flow = [a for a, cnt in residual.items() if cnt > 0]
    if not arcs_with_flow:
        break
    start_arc = arcs_with_flow[0]
    # start from its tail
    start_tail = arc_tail_head[start_arc][0]
    current_node = start_tail
    cycle = []
    # follow a trail until we return to start_tail
    while True:
        # find an outgoing arc from current_node with residual > 0
        available = [a for a, (t, h) in arc_tail_head.items() if t == current_node and residual.get(a, 0) > 0]
        if not available:
            # This should not happen because flows are balanced
            print("Error reconstructing cycles: no outgoing residual from", current_node)
            break
        a = available[0]
        # append arc to cycle and decrement residual
        cycle.append((a, arc_tail_head[a][0], arc_tail_head[a][1]))
        residual[a] -= 1
        current_node = arc_tail_head[a][1]
        # stop when we returned to start node
        if current_node == start_tail:
            break
    cycles.append(cycle)

print("\nClosed tractor rotation(s) found (each cycle = weekly rotation for one tractor):")
for i, cyc in enumerate(cycles, start=1):
    print(f" Rotation {i}:")
    for a_name, tail, head in cyc:
        # classify arc
        atype = arc_info[a_name][2]
        if atype == 'leg':
            leg = a_name
            t_term, t_slot, h_term, h_slot, cost, ship_ok = legs[leg]
            print(f"   {a_name}  (LEG)  {node_str(tail)} -> {node_str(head)}  cost={cost}  ship_eligible={ship_ok}")
        else:
            print(f"   {a_name}  (WAIT) {node_str(tail)} -> {node_str(head)}")
    # total cost for this rotation (sum costs of leg arcs in the cycle)
    rot_cost = sum(legs[a][4] for a, tail, head in cyc if arc_info[a][2] == 'leg')
    print(f"  Rotation weekly operating cost (sum of leg costs in this cycle): {rot_cost}")

print("\nTotal tractors used T =", int(round(T.X)))
print("\n--- END ---")
