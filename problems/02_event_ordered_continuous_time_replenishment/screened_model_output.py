import math
import gurobipy as gp
from gurobipy import GRB


def solve_replenishment_routing(data, output_flag=True):
    # -------------------------
    # Data
    # -------------------------
    C = list(data["customers"])
    depot = data.get("depot", 0)
    N = [depot] + C

    H = float(data["horizon"])
    vehicle_cap = float(data["vehicle_capacity"])
    num_vehicles = int(data["num_vehicles"])
    max_trips_per_vehicle = int(data["max_trips_per_vehicle"])

    K = range(num_vehicles)
    P = range(max_trips_per_vehicle)
    events = [(k, p) for k in K for p in P]  # potential trip-event per vehicle/trip slot

    rate = data["consumption_rate"]
    init = data["initial_inventory"]
    lower = data["lower_inventory"]
    upper = data["upper_inventory"]
    reserve = data["terminal_reserve"]

    travel_time = data["travel_time"]
    travel_cost = data["travel_cost"]
    service_time = data.get("service_time", {i: 0.0 for i in C})

    arcs = [(i, j) for i in N for j in N if i != j]

    # Basic validation
    for i in C:
        if init[i] < lower[i] - 1e-9:
            raise ValueError(f"Customer {i}: initial inventory is below lower bound.")
        if init[i] > upper[i] + 1e-9:
            raise ValueError(f"Customer {i}: initial inventory is above upper bound.")
        if max(reserve[i], lower[i]) > upper[i] + 1e-9:
            raise ValueError(f"Customer {i}: terminal reserve/lower bound exceeds tank capacity.")

    max_travel = max(travel_time[i, j] for i, j in arcs)
    max_service = max(service_time.get(i, 0.0) for i in C) if C else 0.0
    M_time = H + max_travel + max_service

    # Inventory big-M values, customer-specific
    M_inv = {
        i: vehicle_cap * len(events) + rate[i] * H + upper[i] + abs(init[i]) + abs(lower[i]) + 1.0
        for i in C
    }

    # -------------------------
    # Model
    # -------------------------
    m = gp.Model("continuous_time_replenishment_routing")
    m.Params.OutputFlag = 1 if output_flag else 0

    # Routing variables
    x = m.addVars(
        [(k, p, i, j) for k in K for p in P for i, j in arcs],
        vtype=GRB.BINARY,
        name="x"
    )
    use_trip = m.addVars(K, P, vtype=GRB.BINARY, name="use_trip")
    visit = m.addVars(
        [(k, p, i) for k in K for p in P for i in C],
        vtype=GRB.BINARY,
        name="visit"
    )

    # Delivery quantity
    qty = m.addVars(
        [(k, p, i) for k in K for p in P for i in C],
        lb=0.0,
        ub=vehicle_cap,
        vtype=GRB.CONTINUOUS,
        name="qty"
    )

    # Timing variables
    depart = m.addVars(K, P, lb=0.0, ub=H, vtype=GRB.CONTINUOUS, name="depart")
    ret = m.addVars(K, P, lb=0.0, ub=H, vtype=GRB.CONTINUOUS, name="return")
    arrive = m.addVars(
        [(k, p, i) for k in K for p in P for i in C],
        lb=0.0,
        ub=H,
        vtype=GRB.CONTINUOUS,
        name="arrive"
    )

    # MTZ order variables for subtour elimination
    nC = len(C)
    mtz = m.addVars(
        [(k, p, i) for k in K for p in P for i in C],
        lb=0.0,
        ub=nC,
        vtype=GRB.CONTINUOUS,
        name="mtz"
    )

    # Customer-specific ordering variables for repeated deliveries.
    # before[i,e,f] = 1 if event e delivers to customer i before event f.
    before_idx = []
    for i in C:
        for e in events:
            for f in events:
                if e != f:
                    before_idx.append((i, e[0], e[1], f[0], f[1]))

    before = m.addVars(before_idx, vtype=GRB.BINARY, name="before")

    # lin_qty_before = qty[e,i] * before[i,e,f]
    lin_qty_before = m.addVars(
        before_idx,
        lb=0.0,
        ub=vehicle_cap,
        vtype=GRB.CONTINUOUS,
        name="lin_qty_before"
    )

    # -------------------------
    # Routing constraints
    # -------------------------
    for k in K:
        for p in P:
            # Trip starts at depot if used
            m.addConstr(
                gp.quicksum(x[k, p, depot, j] for j in C) == use_trip[k, p],
                name=f"depot_out_{k}_{p}"
            )
            m.addConstr(
                gp.quicksum(x[k, p, i, depot] for i in C) == use_trip[k, p],
                name=f"depot_in_{k}_{p}"
            )

            # Customer flow conservation
            for h in C:
                m.addConstr(
                    gp.quicksum(x[k, p, i, h] for i in N if i != h) == visit[k, p, h],
                    name=f"inflow_{k}_{p}_{h}"
                )
                m.addConstr(
                    gp.quicksum(x[k, p, h, j] for j in N if j != h) == visit[k, p, h],
                    name=f"outflow_{k}_{p}_{h}"
                )
                m.addConstr(visit[k, p, h] <= use_trip[k, p], name=f"visit_implies_trip_{k}_{p}_{h}")
                m.addConstr(qty[k, p, h] <= vehicle_cap * visit[k, p, h], name=f"qty_visit_{k}_{p}_{h}")
                m.addConstr(arrive[k, p, h] <= H * visit[k, p, h], name=f"arrive_visit_{k}_{p}_{h}")

                # MTZ linking
                m.addConstr(mtz[k, p, h] <= nC * visit[k, p, h], name=f"mtz_ub_{k}_{p}_{h}")
                m.addConstr(mtz[k, p, h] >= visit[k, p, h], name=f"mtz_lb_{k}_{p}_{h}")

            # Vehicle capacity per trip
            m.addConstr(
                gp.quicksum(qty[k, p, i] for i in C) <= vehicle_cap * use_trip[k, p],
                name=f"vehicle_capacity_{k}_{p}"
            )

            # Return cannot precede departure
            m.addConstr(ret[k, p] >= depart[k, p], name=f"return_after_depart_{k}_{p}")

            # MTZ subtour elimination among customers
            for i in C:
                for j in C:
                    if i != j:
                        m.addConstr(
                            mtz[k, p, i] - mtz[k, p, j] + nC * x[k, p, i, j] <= nC - 1,
                            name=f"mtz_{k}_{p}_{i}_{j}"
                        )

            # Time propagation: depot to first customer
            for j in C:
                m.addConstr(
                    arrive[k, p, j] >= depart[k, p] + travel_time[depot, j]
                    - M_time * (1 - x[k, p, depot, j]),
                    name=f"time_depot_to_{k}_{p}_{j}"
                )

            # Time propagation: customer to customer
            for i in C:
                for j in C:
                    if i != j:
                        m.addConstr(
                            arrive[k, p, j] >= arrive[k, p, i] + service_time.get(i, 0.0) + travel_time[i, j]
                            - M_time * (1 - x[k, p, i, j]),
                            name=f"time_{k}_{p}_{i}_{j}"
                        )

            # Time propagation: last customer back to depot
            for i in C:
                m.addConstr(
                    ret[k, p] >= arrive[k, p, i] + service_time.get(i, 0.0) + travel_time[i, depot]
                    - M_time * (1 - x[k, p, i, depot]),
                    name=f"time_back_{k}_{p}_{i}"
                )

    # Vehicle trip sequencing and prefix use
    for k in K:
        for p in range(max_trips_per_vehicle - 1):
            m.addConstr(use_trip[k, p] >= use_trip[k, p + 1], name=f"trip_prefix_{k}_{p}")
            m.addConstr(depart[k, p + 1] >= ret[k, p], name=f"trip_sequence_{k}_{p}")

    # -------------------------
    # Inventory ordering constraints
    # -------------------------
    for i in C:
        # Pairwise order and linearization for all event pairs for this customer
        for e in events:
            ke, pe = e
            for f in events:
                if e == f:
                    continue
                kf, pf = f
                key = (i, ke, pe, kf, pf)

                # before can be 1 only if both events visit customer i
                m.addConstr(before[key] <= visit[ke, pe, i], name=f"before_visit_e_{key}")
                m.addConstr(before[key] <= visit[kf, pf, i], name=f"before_visit_f_{key}")

                # If e is before f, then arrival_e <= arrival_f
                m.addConstr(
                    arrive[ke, pe, i] <= arrive[kf, pf, i] + H * (1 - before[key]),
                    name=f"before_time_{key}"
                )

                # Linearize lin_qty_before[key] = qty[ke,pe,i] * before[key]
                m.addConstr(lin_qty_before[key] <= qty[ke, pe, i], name=f"lin1_{key}")
                m.addConstr(lin_qty_before[key] <= vehicle_cap * before[key], name=f"lin2_{key}")
                m.addConstr(
                    lin_qty_before[key] >= qty[ke, pe, i] - vehicle_cap * (1 - before[key]),
                    name=f"lin3_{key}"
                )

        # If two events both visit i, exactly one precedes the other
        for idx_e, e in enumerate(events):
            ke, pe = e
            for f in events[idx_e + 1:]:
                kf, pf = f
                key_ef = (i, ke, pe, kf, pf)
                key_fe = (i, kf, pf, ke, pe)

                m.addConstr(
                    before[key_ef] + before[key_fe] >= visit[ke, pe, i] + visit[kf, pf, i] - 1,
                    name=f"one_order_lb_{i}_{ke}_{pe}_{kf}_{pf}"
                )
                m.addConstr(
                    before[key_ef] + before[key_fe] <= 1,
                    name=f"one_order_ub_{i}_{ke}_{pe}_{kf}_{pf}"
                )

        # Inventory before/after every possible delivery event
        for f in events:
            kf, pf = f

            inv_before = (
                init[i]
                - rate[i] * arrive[kf, pf, i]
                + gp.quicksum(
                    lin_qty_before[i, ke, pe, kf, pf]
                    for ke, pe in events
                    if (ke, pe) != (kf, pf)
                )
            )

            # No stockout immediately before delivery
            m.addConstr(
                inv_before >= lower[i] - M_inv[i] * (1 - visit[kf, pf, i]),
                name=f"inv_lower_before_{i}_{kf}_{pf}"
            )

            # No overflow immediately after delivery
            m.addConstr(
                inv_before + qty[kf, pf, i] <= upper[i] + M_inv[i] * (1 - visit[kf, pf, i]),
                name=f"inv_upper_after_{i}_{kf}_{pf}"
            )

        # Terminal inventory requirement
        terminal_inventory = init[i] - rate[i] * H + gp.quicksum(qty[k, p, i] for k, p in events)
        m.addConstr(
            terminal_inventory >= max(reserve[i], lower[i]),
            name=f"terminal_reserve_{i}"
        )
        m.addConstr(
            terminal_inventory <= upper[i],
            name=f"terminal_upper_{i}"
        )

    # -------------------------
    # Objective: minimize travel cost
    # -------------------------
    m.setObjective(
        gp.quicksum(travel_cost[i, j] * x[k, p, i, j] for k in K for p in P for i, j in arcs),
        GRB.MINIMIZE
    )

    # -------------------------
    # Solve
    # -------------------------
    m.optimize()

    if m.Status == GRB.INFEASIBLE:
        print("\nModel is infeasible. Computing IIS...")
        m.computeIIS()
        m.write("infeasible_model.ilp")
        print("IIS written to infeasible_model.ilp")
        return None

    if m.Status not in [GRB.OPTIMAL, GRB.TIME_LIMIT, GRB.SUBOPTIMAL]:
        print(f"Solver ended with status {m.Status}")
        return None

    # -------------------------
    # Report solution
    # -------------------------
    print("\n================ SOLUTION ================")
    print(f"Objective travel cost: {m.ObjVal:.3f}")

    for k in K:
        for p in P:
            if use_trip[k, p].X > 0.5:
                route = []
                current = depot
                visited_guard = set()

                while True:
                    nxt = None
                    for j in N:
                        if j != current and (k, p, current, j) in x and x[k, p, current, j].X > 0.5:
                            nxt = j
                            break

                    if nxt is None or nxt == depot:
                        break

                    if nxt in visited_guard:
                        raise RuntimeError("Route extraction encountered a cycle.")
                    visited_guard.add(nxt)

                    route.append(nxt)
                    current = nxt

                print(f"\nVehicle {k}, trip {p}")
                print(f"  depart {depart[k, p].X:.3f}, return {ret[k, p].X:.3f}")
                print(f"  route: {depot} -> " + " -> ".join(map(str, route)) + f" -> {depot}")
                for i in route:
                    print(
                        f"    customer {i}: arrive {arrive[k, p, i].X:.3f}, "
                        f"deliver {qty[k, p, i].X:.3f}"
                    )

    print("\nInventory trajectories:")
    for i in C:
        deliveries = []
        for k, p in events:
            if visit[k, p, i].X > 0.5:
                deliveries.append((arrive[k, p, i].X, k, p, qty[k, p, i].X))

        deliveries.sort()
        inv = init[i]
        last_t = 0.0

        print(f"\nCustomer {i}:")
        print(f"  initial inventory = {init[i]:.3f}")
        for t, k, p, qval in deliveries:
            inv_before = inv - rate[i] * (t - last_t)
            inv_after = inv_before + qval
            print(
                f"  t={t:.3f}: before={inv_before:.3f}, "
                f"deliver={qval:.3f}, after={inv_after:.3f} "
                f"(vehicle {k}, trip {p})"
            )
            inv = inv_after
            last_t = t

        terminal = inv - rate[i] * (H - last_t)
        print(
            f"  terminal inventory at H={H:.3f}: {terminal:.3f} "
            f"required >= {max(reserve[i], lower[i]):.3f}"
        )

    return m


if __name__ == "__main__":
    # -------------------------
    # Example runnable instance
    # Replace this section with your real data.
    # Units: time in hours, quantities in tank units, rates in units/hour.
    # -------------------------
    depot = 0
    customers = [1, 2, 3, 4]

    coords = {
        0: (0.0, 0.0),
        1: (2.0, 1.0),
        2: (3.0, 4.0),
        3: (-1.0, 3.0),
        4: (-3.0, -2.0),
    }

    nodes = [depot] + customers
    travel_time = {}
    travel_cost = {}
    speed = 3.0  # distance units per hour

    for i in nodes:
        for j in nodes:
            if i == j:
                continue
            dist = math.hypot(coords[i][0] - coords[j][0], coords[i][1] - coords[j][1])
            travel_cost[i, j] = dist
            travel_time[i, j] = dist / speed

    data = {
        "depot": depot,
        "customers": customers,
        "horizon": 12.0,
        "num_vehicles": 2,
        "max_trips_per_vehicle": 3,
        "vehicle_capacity": 100.0,

        "consumption_rate": {
            1: 6.0,
            2: 5.0,
            3: 4.0,
            4: 7.0,
        },
        "initial_inventory": {
            1: 45.0,
            2: 60.0,
            3: 30.0,
            4: 80.0,
        },
        "lower_inventory": {
            1: 10.0,
            2: 15.0,
            3: 8.0,
            4: 20.0,
        },
        "upper_inventory": {
            1: 90.0,
            2: 100.0,
            3: 70.0,
            4: 120.0,
        },
        "terminal_reserve": {
            1: 25.0,
            2: 20.0,
            3: 15.0,
            4: 30.0,
        },
        "service_time": {
            1: 0.15,
            2: 0.15,
            3: 0.15,
            4: 0.15,
        },
        "travel_time": travel_time,
        "travel_cost": travel_cost,
    }

    solve_replenishment_routing(data, output_flag=True)
