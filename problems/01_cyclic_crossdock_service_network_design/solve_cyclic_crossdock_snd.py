#!/usr/bin/env python3
"""Exact Gurobi model for the cyclic cross-dock SND micro-instance."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import gurobipy as gp
from gurobipy import GRB


ROOT = Path(__file__).resolve().parent


def load_instance() -> dict:
    data = {
        "legs": {},
        "candidate_cargo_paths": {},
        "shipment": {},
        "crossdock": {},
    }
    with (ROOT / "instance.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            kind = row["record_type"]
            if kind == "metadata" and row["key"] == "title":
                data["title"] = row["value"]
            elif kind == "parameter":
                value = row["value"]
                data[row["key"]] = int(value) if value.isdigit() else value
            elif kind in {"shipment", "crossdock"}:
                value = row["value"]
                if value.isdigit():
                    value = int(value)
                elif value.lower() in {"true", "false"}:
                    value = value.lower() == "true"
                data[kind][row["key"]] = value
            elif kind == "leg":
                departure = int(row["departure_slot"])
                arrival = int(row["arrival_slot"])
                tail_terminal = row["tail_terminal"]
                head_terminal = row["head_terminal"]
                data["legs"][row["id"]] = {
                    "tail": f"{tail_terminal}{departure}",
                    "head": f"{head_terminal}{arrival}",
                    "tail_terminal": tail_terminal,
                    "departure_slot": departure,
                    "head_terminal": head_terminal,
                    "arrival_slot": arrival,
                    "duration_slots": int(row["duration_slots"]),
                    "cost": float(row["cost"]),
                    "cargo_eligible": row["cargo_eligible"].lower() == "true",
                }
            elif kind == "path":
                data["candidate_cargo_paths"][row["id"]] = row["path_legs"].split("|")
    return data


def solve(
    omit_handling: bool = False,
    omit_asset_circulation: bool = False,
    omit_fleet_limit: bool = False,
) -> dict:
    data = load_instance()
    legs = data["legs"]
    horizon = data["period_slots"]
    fleet_size = data["tractor_fleet_size"]
    paths = {
        "direct": data["candidate_cargo_paths"]["direct"],
        "late_transfer": data["candidate_cargo_paths"]["late_transfer"],
    }
    if omit_handling:
        paths["zero_handling_relaxation_only"] = data["candidate_cargo_paths"][
            "zero_handling_relaxation_only"
        ]

    model = gp.Model("cyclic_crossdock_service_network_design")
    opened = model.addVars(legs, vtype=GRB.BINARY, name="open")
    choose = model.addVars(paths, vtype=GRB.BINARY, name="path")

    model.addConstr(gp.quicksum(choose[p] for p in paths) == 1, name="choose_path")
    for path_name, path_legs in paths.items():
        for leg in path_legs:
            model.addConstr(
                choose[path_name] <= opened[leg],
                name=f"path_link[{path_name},{leg}]",
            )

    fleet_time = None
    if not omit_asset_circulation:
        terminals = sorted({leg["tail"][:-1] for leg in legs.values()} | {leg["head"][:-1] for leg in legs.values()})
        nodes = [(terminal, slot) for terminal in terminals for slot in range(horizon)]
        wait_ub = fleet_size if not omit_fleet_limit else len(legs)
        wait = model.addVars(nodes, lb=0, ub=wait_ub, vtype=GRB.INTEGER, name="wait")

        for terminal, slot in nodes:
            node = f"{terminal}{slot}"
            previous = (slot - 1) % horizon
            model.addConstr(
                gp.quicksum(opened[a] for a, leg in legs.items() if leg["tail"] == node)
                + wait[terminal, slot]
                == gp.quicksum(opened[a] for a, leg in legs.items() if leg["head"] == node)
                + wait[terminal, previous],
                name=f"tractor_flow[{terminal},{slot}]",
            )

        fleet_time = (
            gp.quicksum(legs[a]["duration_slots"] * opened[a] for a in legs)
            + gp.quicksum(wait[node] for node in nodes)
        )
        if not omit_fleet_limit:
            model.addConstr(fleet_time <= horizon * fleet_size, name="fleet_limit")

    service_cost = gp.quicksum(legs[a]["cost"] * opened[a] for a in legs)
    model.setObjective(service_cost, GRB.MINIMIZE)
    model.optimize()
    if model.Status != GRB.OPTIMAL:
        raise RuntimeError(f"Expected OPTIMAL, received status {model.Status}")

    primary_objective = model.ObjVal
    primary_bound = model.ObjBound
    primary_gap = model.MIPGap
    if fleet_time is not None:
        model.addConstr(service_cost <= primary_objective + 1e-8, name="fix_primary_cost")
        model.setObjective(fleet_time, GRB.MINIMIZE)
        model.optimize()
        if model.Status != GRB.OPTIMAL:
            raise RuntimeError("Fleet-minimization tie break failed")

    result = {
        "status": "OPTIMAL",
        "objective": primary_objective,
        "bound": primary_bound,
        "gap": primary_gap,
        "cargo_path": next(p for p in paths if choose[p].X > 0.5),
        "opened_legs": sorted(a for a in legs if opened[a].X > 0.5),
        "minimum_tractors": None if fleet_time is None else fleet_time.getValue() / horizon,
        "omit_handling": omit_handling,
        "omit_asset_circulation": omit_asset_circulation,
        "omit_fleet_limit": omit_fleet_limit,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--omit-handling", action="store_true")
    parser.add_argument("--omit-asset-circulation", action="store_true")
    parser.add_argument("--omit-fleet-limit", action="store_true")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="solve the reference case and four diagnostic ablations",
    )
    args = parser.parse_args()
    if not args.verify:
        solve(
            omit_handling=args.omit_handling,
            omit_asset_circulation=args.omit_asset_circulation,
            omit_fleet_limit=args.omit_fleet_limit,
        )
        return

    expected = {
        "correct_model": ((False, False, False), 15.0, "direct", ["F4", "R4"], 1),
        "omit_handling": (
            (True, False, False), 8.0, "zero_handling_relaxation_only",
            ["F1", "F2", "R1", "R2"], 2,
        ),
        "omit_fleet_limit": (
            (False, False, True), 11.5, "direct", ["F4", "R1", "R2"], 3,
        ),
        "omit_all_assets": ((False, True, True), 7.5, "direct", ["F4"], None),
        "omit_handling_and_assets": (
            (True, True, True), 4.0, "zero_handling_relaxation_only",
            ["F1", "F2"], None,
        ),
    }
    for name, (flags, objective, path, legs, tractors) in expected.items():
        result = solve(*flags)
        assert abs(result["objective"] - objective) <= 1e-9, name
        assert result["cargo_path"] == path, name
        assert result["opened_legs"] == legs, name
        if tractors is not None:
            assert abs(result["minimum_tractors"] - tractors) <= 1e-9, name
    print("VERIFICATION=PASS")


if __name__ == "__main__":
    main()
