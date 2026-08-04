#!/usr/bin/env python3
"""Self-contained solver for the OR-Bench continuous-time replenishment package.

Usage:
    python3 solve_ctirp_submission.py instance.csv

Requires Python, Gurobi, and gurobipy. This independently written code is
released under MIT; related CTIRP literature is cited in the package PDF.
"""

from __future__ import annotations


"""Parser for the package's submission-ready CSV instance."""


import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CTIRPCustomer:
    id: int
    initial_inventory: float
    final_inventory: float
    min_inventory: float
    max_inventory: float
    usage_rate: float


@dataclass(frozen=True)
class CTIRPInstance:
    name: str
    horizon: float
    vehicle_count: int
    vehicle_capacity: float
    customers: tuple[CTIRPCustomer, ...]
    travel_time: tuple[tuple[float, ...], ...]
    travel_cost: tuple[tuple[float, ...], ...]

    @property
    def customer_ids(self) -> list[int]:
        return [customer.id for customer in self.customers]

    @property
    def node_count(self) -> int:
        return len(self.customers) + 1

    def customer(self, customer_id: int) -> CTIRPCustomer:
        for customer in self.customers:
            if customer.id == customer_id:
                return customer
        raise KeyError(customer_id)


def parse_instance(path: str | Path) -> CTIRPInstance:
    """Parse the single-table CSV instance used in the Form package."""

    path = Path(path)
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    header = next((row for row in rows if row["record_type"] == "instance"), None)
    if header is None:
        raise ValueError(f"Missing instance row in {path}")
    customers = tuple(
        CTIRPCustomer(
            id=int(row["id"]),
            initial_inventory=float(row["initial_inventory"]),
            final_inventory=float(row["terminal_requirement"]),
            min_inventory=float(row["lower_inventory"]),
            max_inventory=float(row["upper_inventory"]),
            usage_rate=float(row["usage_rate"]),
        )
        for row in rows
        if row["record_type"] == "customer"
    )
    if not customers:
        raise ValueError(f"No customer rows in {path}")
    node_count = len(customers) + 1
    travel_time = [[0.0] * node_count for _ in range(node_count)]
    travel_cost = [[0.0] * node_count for _ in range(node_count)]
    seen_arcs: set[tuple[int, int]] = set()
    for row in rows:
        if row["record_type"] != "arc":
            continue
        i, j = int(row["from_node"]), int(row["to_node"])
        if i >= node_count or j >= node_count:
            raise ValueError(f"Nonconsecutive node id in {path}: {(i, j)}")
        travel_time[i][j] = float(row["travel_time"])
        travel_cost[i][j] = float(row["travel_cost"])
        seen_arcs.add((i, j))
    if len(seen_arcs) != node_count * node_count:
        raise ValueError(f"Incomplete travel matrices in {path}")
    return CTIRPInstance(
        name=header["id"],
        horizon=float(header["horizon"]),
        vehicle_count=int(header["vehicle_count"]),
        vehicle_capacity=float(header["vehicle_capacity"]),
        customers=customers,
        travel_time=tuple(tuple(row) for row in travel_time),
        travel_cost=tuple(tuple(row) for row in travel_cost),
    )

"""Ordered event-copy MILP derived from the stated business constraints."""


from dataclasses import dataclass
from math import ceil

import gurobipy as gp
from gurobipy import GRB



@dataclass
class CTIRPModelData:
    model: gp.Model
    x: dict[tuple[int, int, int, int, int], gp.Var]
    y: dict[tuple[int, int], gp.Var]
    arrival: dict[tuple[int, int], gp.Var]
    departure: dict[tuple[int, int], gp.Var]
    delivered: dict[tuple[int, int], gp.Var]
    nodes: list[tuple[int, int]]
    visit_copies: dict[int, list[int]]
    arcs_by_mode: dict[int, list[tuple[int, int, int, int]]]


@dataclass
class CTIRPSolution:
    status: int
    status_name: str
    objective_value: float | None
    mip_gap: float | None
    runtime: float
    used_vehicle_count: int | None
    used_visits: dict[int, int]
    arcs: list[tuple[int, int, int, int, int]]


def build_ctirp_model(
    instance: CTIRPInstance,
    *,
    time_limit: float | None = None,
    mip_gap: float | None = None,
    output_flag: bool = False,
    tighten_time_windows: bool = True,
    force_min_visits: bool = True,
) -> CTIRPModelData:
    """Build an ordered event-copy CTIRP MILP.

    Each customer receives enough potential visit copies for its minimum
    quantity requirement plus two slack copies. Optional valid inequalities
    tighten the independently implemented formulation.
    """

    model = gp.Model(f"ctirp_{instance.name}")
    model.Params.OutputFlag = 1 if output_flag else 0
    if time_limit is not None:
        model.Params.TimeLimit = time_limit
    if mip_gap is not None:
        model.Params.MIPGap = mip_gap

    customers = instance.customer_ids
    h = instance.horizon
    q_cap = instance.vehicle_capacity
    visit_copies: dict[int, list[int]] = {}
    min_visits: dict[int, int] = {}
    for customer in instance.customers:
        theta = customer.final_inventory + customer.usage_rate * h - customer.initial_inventory
        min_visit = max(1, ceil(max(theta, 0.0) / q_cap))
        min_visits[customer.id] = min_visit
        visit_copies[customer.id] = list(range(1, min_visit + 3))
    visit_copies[0] = [1]

    nodes = [(i, alpha) for i in [0, *customers] for alpha in visit_copies[i]]

    a0: list[tuple[int, int, int, int]] = []
    for i, alpha in nodes:
        for j, beta in nodes:
            if i == j:
                continue
            a0.append((i, alpha, j, beta))

    a1: list[tuple[int, int, int, int]] = []
    for i in customers:
        for alpha in visit_copies[i]:
            for j in customers:
                for beta in visit_copies[j]:
                    if i == j and alpha >= beta:
                        continue
                    a1.append((i, alpha, j, beta))

    arcs_by_mode = {0: a0, 1: a1}
    arc_keys = [(d, i, alpha, j, beta) for d, arcs in arcs_by_mode.items() for i, alpha, j, beta in arcs]
    unique_arc_pairs = sorted({(i, alpha, j, beta) for _, i, alpha, j, beta in arc_keys})

    incoming: dict[tuple[int, int, int], list[tuple[int, int]]] = {}
    outgoing: dict[tuple[int, int, int], list[tuple[int, int]]] = {}
    for d, arcs in arcs_by_mode.items():
        for i, alpha, j, beta in arcs:
            incoming.setdefault((d, j, beta), []).append((i, alpha))
            outgoing.setdefault((d, i, alpha), []).append((j, beta))

    unique_incoming: dict[tuple[int, int], list[tuple[int, int]]] = {}
    unique_outgoing: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for i, alpha, j, beta in unique_arc_pairs:
        unique_incoming.setdefault((j, beta), []).append((i, alpha))
        unique_outgoing.setdefault((i, alpha), []).append((j, beta))

    def cost(d: int, i: int, j: int) -> float:
        if d == 0:
            return instance.travel_cost[i][j]
        return instance.travel_cost[i][0] + instance.travel_cost[0][j]

    def travel(d: int, i: int, j: int) -> float:
        if d == 0:
            return instance.travel_time[i][j]
        return instance.travel_time[i][0] + instance.travel_time[0][j]

    window_l: dict[tuple[int, int], float] = {}
    window_u: dict[tuple[int, int], float] = {}
    for customer in instance.customers:
        i = customer.id
        for alpha in visit_copies[i]:
            if tighten_time_windows:
                lower = max(
                    instance.travel_time[0][i],
                    h - (customer.max_inventory + (len(visit_copies[i]) - alpha) * q_cap - customer.final_inventory)
                    / customer.usage_rate,
                )
                upper = min(
                    h - instance.travel_time[i][0],
                    (customer.initial_inventory + (alpha - 1) * q_cap - customer.min_inventory)
                    / customer.usage_rate,
                )
            else:
                lower = instance.travel_time[0][i]
                upper = h - instance.travel_time[i][0]
            window_l[i, alpha] = max(0.0, lower)
            window_u[i, alpha] = max(0.0, upper)

    x = model.addVars(arc_keys, vtype=GRB.BINARY, name="x")
    y = model.addVars(
        ((i, alpha) for i in customers for alpha in visit_copies[i]),
        vtype=GRB.BINARY,
        name="y",
    )
    arrival = model.addVars(y.keys(), lb=0.0, name="a")
    departure = model.addVars(y.keys(), lb=0.0, name="d")
    aux_arrival = model.addVars(unique_arc_pairs, lb=0.0, name="atilde")
    direct_flow = model.addVars(a0, lb=0.0, name="f")
    depot_reload = model.addVars(y.keys(), lb=0.0, name="ell")
    delivered = model.addVars(y.keys(), lb=0.0, name="q")

    # (1)
    model.setObjective(
        gp.quicksum(cost(d, i, j) * x[d, i, alpha, j, beta] for d, i, alpha, j, beta in arc_keys),
        GRB.MINIMIZE,
    )

    # (4)-(5)
    for j in customers:
        for beta in visit_copies[j]:
            model.addConstr(
                gp.quicksum(
                    x[d, i, alpha, j, beta]
                    for d in [0, 1]
                    for i, alpha in incoming.get((d, j, beta), [])
                )
                == y[j, beta],
                name=f"eq04_in_degree[{j},{beta}]",
            )
            model.addConstr(
                gp.quicksum(
                    x[d, j, beta, i, alpha]
                    for d in [0, 1]
                    for i, alpha in outgoing.get((d, j, beta), [])
                )
                == y[j, beta],
                name=f"eq05_out_degree[{j},{beta}]",
            )

    # (6)
    model.addConstr(
        gp.quicksum(x[0, 0, 1, j, beta] for j, beta in outgoing.get((0, 0, 1), []))
        <= instance.vehicle_count,
        name="eq06_fleet_size",
    )

    # (10)-(12)
    for j, beta in outgoing.get((0, 0, 1), []):
        model.addConstr(
            aux_arrival[0, 1, j, beta] >= window_l[j, beta] * x[0, 0, 1, j, beta],
            name=f"eq10_depot_arrival_lb[{j},{beta}]",
        )
        model.addConstr(
            aux_arrival[0, 1, j, beta] <= window_u[j, beta] * x[0, 0, 1, j, beta],
            name=f"eq10_depot_arrival_ub[{j},{beta}]",
        )
    for i, alpha in incoming.get((0, 0, 1), []):
        model.addConstr(
            aux_arrival[i, alpha, 0, 1] <= h * x[0, i, alpha, 0, 1],
            name=f"eq11_return_depot[{i},{alpha}]",
        )
    for i, alpha, j, beta in unique_arc_pairs:
        if i in customers and j in customers:
            model.addConstr(
                aux_arrival[i, alpha, j, beta]
                <= window_u[j, beta]
                * gp.quicksum(
                    x[d, i, alpha, j, beta]
                    for d in [0, 1]
                    if (d, i, alpha, j, beta) in x
                ),
                name=f"eq12_aux_active[{i},{alpha},{j},{beta}]",
            )

    # (13)-(14)
    for j in customers:
        for beta in visit_copies[j]:
            model.addConstr(
                gp.quicksum(
                    aux_arrival[i, alpha, j, beta]
                    for i, alpha in unique_incoming.get((j, beta), [])
                )
                == arrival[j, beta],
                name=f"eq13_arrival_def[{j},{beta}]",
            )
            model.addConstr(arrival[j, beta] <= departure[j, beta], name=f"eq13_arr_dep[{j},{beta}]")
    for i in customers:
        for alpha in visit_copies[i]:
            model.addConstr(
                departure[i, alpha]
                + gp.quicksum(
                    travel(d, i, j) * x[d, i, alpha, j, beta]
                    for d in [0, 1]
                    for j, beta in outgoing.get((d, i, alpha), [])
                )
                <= gp.quicksum(
                    aux_arrival[i, alpha, j, beta]
                    for j, beta in unique_outgoing.get((i, alpha), [])
                ),
                name=f"eq14_time_propagation[{i},{alpha}]",
            )

    # (15)-(16)
    for i in customers:
        copies = visit_copies[i]
        for alpha in copies[:-1]:
            next_alpha = alpha + 1
            model.addConstr(y[i, next_alpha] <= y[i, alpha], name=f"eq15_visit_order[{i},{alpha}]")
            model.addConstr(
                departure[i, alpha]
                <= arrival[i, next_alpha]
                + (h - instance.travel_time[i][0]) * (y[i, alpha] - y[i, next_alpha]),
                name=f"eq16_nonoverlap[{i},{alpha}]",
            )

    # (20)-(24)
    for i, alpha in incoming.get((0, 0, 1), []):
        model.addConstr(direct_flow[i, alpha, 0, 1] == 0.0, name=f"eq20_empty_to_depot[{i},{alpha}]")
    for i, alpha, j, beta in a0:
        model.addConstr(
            direct_flow[i, alpha, j, beta] <= q_cap * x[0, i, alpha, j, beta],
            name=f"eq21_direct_capacity[{i},{alpha},{j},{beta}]",
        )
    for j in customers:
        for beta in visit_copies[j]:
            model.addConstr(
                depot_reload[j, beta]
                <= q_cap
                * gp.quicksum(x[1, i, alpha, j, beta] for i, alpha in incoming.get((1, j, beta), [])),
                name=f"eq22_reload_capacity[{j},{beta}]",
            )
            model.addConstr(delivered[j, beta] <= q_cap * y[j, beta], name=f"eq23_delivery_active[{j},{beta}]")
            model.addConstr(
                gp.quicksum(
                    direct_flow[i, alpha, j, beta]
                    for i, alpha in incoming.get((0, j, beta), [])
                )
                + depot_reload[j, beta]
                == delivered[j, beta]
                + gp.quicksum(
                    direct_flow[j, beta, i, alpha]
                    for i, alpha in outgoing.get((0, j, beta), [])
                ),
                name=f"eq24_product_flow[{j},{beta}]",
            )

    # (25)-(27)
    for customer in instance.customers:
        i = customer.id
        copies = visit_copies[i]
        for alpha in copies:
            previous = [a for a in copies if a < alpha]
            up_to = [a for a in copies if a <= alpha]
            model.addConstr(
                customer.initial_inventory * y[i, alpha]
                + gp.quicksum(delivered[i, a] for a in previous)
                - customer.usage_rate * arrival[i, alpha]
                >= customer.min_inventory * y[i, alpha],
                name=f"eq25_inventory_arrival_lb[{i},{alpha}]",
            )
            model.addConstr(
                customer.initial_inventory * y[i, alpha]
                + gp.quicksum(delivered[i, a] for a in up_to)
                - customer.usage_rate * departure[i, alpha]
                <= customer.max_inventory * y[i, alpha]
                + gp.quicksum(q_cap * (y[i, a] - y[i, alpha]) for a in previous),
                name=f"eq26_inventory_departure_ub[{i},{alpha}]",
            )
        model.addConstr(
            customer.initial_inventory
            + gp.quicksum(delivered[i, alpha] for alpha in copies)
            - customer.usage_rate * h
            >= customer.final_inventory,
            name=f"eq27_final_inventory[{i}]",
        )

    # Tightening constraints (28)-(29) from Section 4.2.
    if force_min_visits:
        for i in customers:
            for alpha in visit_copies[i]:
                if alpha <= min_visits[i]:
                    model.addConstr(y[i, alpha] == 1, name=f"eq28_min_visit[{i},{alpha}]")
                    model.addConstr(arrival[i, alpha] >= window_l[i, alpha], name=f"eq29_arrival_lb[{i},{alpha}]")

    model.update()
    return CTIRPModelData(
        model=model,
        x=dict(x),
        y=dict(y),
        arrival=dict(arrival),
        departure=dict(departure),
        delivered=dict(delivered),
        nodes=nodes,
        visit_copies=visit_copies,
        arcs_by_mode=arcs_by_mode,
    )


def extract_solution(data: CTIRPModelData) -> CTIRPSolution:
    model = data.model
    has_solution = model.SolCount > 0
    if not has_solution:
        return CTIRPSolution(
            status=model.Status,
            status_name=_status_name(model.Status),
            objective_value=None,
            mip_gap=None,
            runtime=model.Runtime,
            used_vehicle_count=None,
            used_visits={},
            arcs=[],
        )

    arcs = [key for key, var in data.x.items() if var.X > 0.5]
    used_vehicle_count = sum(1 for d, i, alpha, _j, _beta in arcs if d == 0 and i == 0 and alpha == 1)
    used_visits = {
        customer: sum(1 for alpha in copies if data.y[customer, alpha].X > 0.5)
        for customer, copies in data.visit_copies.items()
        if customer != 0
    }
    mip_gap = None
    if model.IsMIP and model.Status in {GRB.OPTIMAL, GRB.TIME_LIMIT, GRB.SUBOPTIMAL}:
        try:
            mip_gap = model.MIPGap
        except (gp.GurobiError, AttributeError):
            mip_gap = None
    return CTIRPSolution(
        status=model.Status,
        status_name=_status_name(model.Status),
        objective_value=model.ObjVal,
        mip_gap=mip_gap,
        runtime=model.Runtime,
        used_vehicle_count=used_vehicle_count,
        used_visits=used_visits,
        arcs=arcs,
    )


def _status_name(status: int) -> str:
    names = {
        GRB.LOADED: "LOADED",
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.CUTOFF: "CUTOFF",
        GRB.ITERATION_LIMIT: "ITERATION_LIMIT",
        GRB.NODE_LIMIT: "NODE_LIMIT",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.SOLUTION_LIMIT: "SOLUTION_LIMIT",
        GRB.INTERRUPTED: "INTERRUPTED",
        GRB.NUMERIC: "NUMERIC",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.INPROGRESS: "INPROGRESS",
        GRB.USER_OBJ_LIMIT: "USER_OBJ_LIMIT",
    }
    return names.get(status, f"STATUS_{status}")

#!/usr/bin/env python3
"""Solve one CTIRP CSV instance with the ordered event-copy MILP."""


import argparse
import json
import sys
from pathlib import Path




def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("instance", type=Path)
    parser.add_argument("--time-limit", type=float, default=300.0)
    parser.add_argument("--mip-gap", type=float, default=None)
    parser.add_argument("--no-tight-windows", action="store_true")
    parser.add_argument("--no-min-visit-tightening", action="store_true")
    parser.add_argument("--gurobi-log", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    instance = parse_instance(args.instance)
    data = build_ctirp_model(
        instance,
        time_limit=args.time_limit,
        mip_gap=args.mip_gap,
        output_flag=args.gurobi_log,
        tighten_time_windows=not args.no_tight_windows,
        force_min_visits=not args.no_min_visit_tightening,
    )
    data.model.optimize()
    solution = extract_solution(data)
    payload = {
        "instance": instance.name,
        "path": str(args.instance),
        "customers": len(instance.customers),
        "vehicles": instance.vehicle_count,
        "status": solution.status_name,
        "objective_value": solution.objective_value,
        "mip_gap": solution.mip_gap,
        "runtime_seconds": solution.runtime,
        "used_vehicle_count": solution.used_vehicle_count,
        "used_visits": solution.used_visits,
        "selected_arcs": solution.arcs,
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if solution.status_name in {"OPTIMAL", "INFEASIBLE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
