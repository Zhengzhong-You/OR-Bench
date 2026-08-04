#!/usr/bin/env python3
"""Standard-library oracle and failure checker for the cyclic cross-dock SND case."""

from __future__ import annotations

import csv
import itertools
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent
EXPECTED = {
    "correct_model": {
        "objective": 15.0,
        "cargo_path": "direct",
        "opened_legs": ["F4", "R4"],
        "minimum_tractors": 1,
    },
    "ablations": {
        "omit_handling_keep_assets": {
            "objective": 8.0,
            "cargo_path": "zero_handling_relaxation_only",
            "opened_legs": ["F1", "F2", "R1", "R2"],
            "minimum_tractors": 2,
        },
        "keep_handling_omit_fleet_limit": {
            "objective": 11.5,
            "cargo_path": "direct",
            "opened_legs": ["F4", "R1", "R2"],
            "minimum_tractors": 3,
        },
        "keep_handling_omit_all_asset_constraints": {
            "objective": 7.5,
            "cargo_path": "direct",
            "opened_legs": ["F4"],
        },
        "omit_handling_and_all_asset_constraints": {
            "objective": 4.0,
            "cargo_path": "zero_handling_relaxation_only",
            "opened_legs": ["F1", "F2"],
        },
    },
}


def load_instance() -> dict:
    data = {"legs": {}, "shipment": {}, "crossdock": {}}
    with (ROOT / "instance.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            kind = row["record_type"]
            if kind == "parameter" and row["key"] in {"period_slots", "tractor_fleet_size"}:
                data[row["key"]] = int(row["value"])
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
    return data


def minimum_tractors(opened: set[str], data: dict) -> int | None:
    legs = data["legs"]
    horizon = data["period_slots"]
    terminals = sorted(
        {leg["tail_terminal"] for leg in legs.values()}
        | {leg["head_terminal"] for leg in legs.values()}
    )
    total_wait = 0
    for terminal in terminals:
        imbalance = []
        for slot in range(horizon):
            node = f"{terminal}{slot}"
            incoming = sum(a in opened for a, leg in legs.items() if leg["head"] == node)
            outgoing = sum(a in opened for a, leg in legs.items() if leg["tail"] == node)
            imbalance.append(incoming - outgoing)
        if sum(imbalance) != 0:
            return None
        cumulative = list(itertools.accumulate(imbalance))
        base = max(0, -min(cumulative))
        waits = [base + value for value in cumulative]
        total_wait += sum(waits)

    service_time = sum(data["legs"][a]["duration_slots"] for a in opened)
    fleet_time = service_time + total_wait
    if fleet_time % horizon != 0:
        raise AssertionError("Periodic circulation did not use an integer fleet")
    return fleet_time // horizon


def generate_cargo_paths(data: dict, handling_slots: int) -> dict[str, set[str]]:
    """Generate all acyclic shipment paths from leg timing, not a supplied path list."""
    shipment = data["shipment"]
    legs = data["legs"]
    origin = shipment["origin"][:-1]
    release = shipment["release_slot"]
    destination = shipment["destination"]
    due = shipment["due_slot"]
    hub = data["crossdock"]["terminal"]
    found: list[tuple[str, ...]] = []

    def extend(location: str, ready_slot: int, used: tuple[str, ...]) -> None:
        for leg_id, leg in legs.items():
            if leg_id in used or not leg["cargo_eligible"]:
                continue
            if leg["tail_terminal"] != location:
                continue
            if leg["departure_slot"] < ready_slot:
                continue
            if leg["arrival_slot"] > due:
                continue
            new_path = (*used, leg_id)
            next_location = leg["head_terminal"]
            if next_location == destination:
                found.append(new_path)
                continue
            next_ready = leg["arrival_slot"]
            if next_location == hub:
                next_ready += handling_slots
            extend(next_location, next_ready, new_path)

    extend(origin, release, ())
    if not found:
        raise AssertionError("No time-feasible shipment path generated")
    return {"+".join(path): set(path) for path in sorted(found)}


def oracle(
    omit_handling: bool,
    omit_asset_circulation: bool,
    omit_fleet_limit: bool,
) -> dict:
    data = load_instance()
    legs = data["legs"]
    paths = generate_cargo_paths(
        data,
        handling_slots=0 if omit_handling else data["crossdock"]["handling_slots"],
    )
    path_labels = {
        "F4": "direct",
        "F1+F3": "late_transfer",
        "F1+F2": "zero_handling_relaxation_only",
    }

    best: tuple[float, str, list[str], float] | None = None
    leg_ids = sorted(legs)
    for bits in itertools.product((0, 1), repeat=len(leg_ids)):
        opened = {a for a, bit in zip(leg_ids, bits) if bit}
        fleet = None if omit_asset_circulation else minimum_tractors(opened, data)
        if not omit_asset_circulation and fleet is None:
            continue
        if not omit_asset_circulation and not omit_fleet_limit and fleet > data["tractor_fleet_size"]:
            continue
        for path_name, required in paths.items():
            if not required <= opened:
                continue
            cost = sum(legs[a]["cost"] for a in opened)
            fleet_key = math.inf if fleet is None else fleet
            row = (cost, path_labels[path_name], sorted(opened), fleet_key)
            if best is None or row < best:
                best = row
    if best is None:
        raise AssertionError("No feasible design found")
    return {
        "objective": best[0],
        "cargo_path": best[1],
        "opened_legs": best[2],
        "minimum_tractors": None if math.isinf(best[3]) else int(best[3]),
    }


def main() -> None:
    truth = EXPECTED
    cases = {
        "correct_model": (False, False, False),
        "omit_handling_keep_assets": (True, False, False),
        "keep_handling_omit_fleet_limit": (False, False, True),
        "keep_handling_omit_all_asset_constraints": (False, True, True),
        "omit_handling_and_all_asset_constraints": (True, True, True),
    }
    checked = {}
    for name, flags in cases.items():
        result = oracle(*flags)
        expected = truth["correct_model"] if name == "correct_model" else truth["ablations"][name]
        assert abs(result["objective"] - expected["objective"]) <= 1e-9
        assert result["cargo_path"] == expected["cargo_path"]
        assert result["opened_legs"] == sorted(expected["opened_legs"])
        if "minimum_tractors" in expected:
            assert result["minimum_tractors"] == expected["minimum_tractors"]
        checked[name] = result

    handling_failure = checked["omit_handling_keep_assets"]
    fleet_failure = checked["keep_handling_omit_fleet_limit"]
    certificate = {
        "handling_failure": {
            "arrival_at_h": 1,
            "handling_slots": 1,
            "earliest_legal_onward_departure": 2,
            "generated_onward_departure": 1,
            "handling_feasible": False,
            "minimum_tractors": handling_failure["minimum_tractors"],
            "absolute_gap": 7.0
        },
        "fleet_failure": {
            "available_tractors": load_instance()["tractor_fleet_size"],
            "minimum_required_tractors": fleet_failure["minimum_tractors"],
            "fleet_feasible": False,
            "absolute_gap": 3.5
        }
    }
    assert certificate["handling_failure"]["generated_onward_departure"] < certificate["handling_failure"]["earliest_legal_onward_departure"]
    assert certificate["fleet_failure"]["minimum_required_tractors"] > certificate["fleet_failure"]["available_tractors"]
    print(json.dumps({"oracle_cases": checked, "failure_certificates": certificate}, indent=2))


if __name__ == "__main__":
    main()
