#!/usr/bin/env python3
"""Verify the one-customer CTIRP false-feasibility certificate."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def load_witness() -> dict:
    with (ROOT / "instance.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    header = next(row for row in rows if row["record_type"] == "instance")
    customer = next(row for row in rows if row["record_type"] == "customer")
    outbound = next(
        row for row in rows
        if row["record_type"] == "arc" and row["from_node"] == "0" and row["to_node"] == "1"
    )
    return {
        "horizon": float(header["horizon"]),
        "vehicle_count": int(header["vehicle_count"]),
        "vehicle_capacity": float(header["vehicle_capacity"]),
        "initial_inventory": float(customer["initial_inventory"]),
        "terminal_requirement": float(customer["terminal_requirement"]),
        "lower_inventory": float(customer["lower_inventory"]),
        "upper_inventory": float(customer["upper_inventory"]),
        "usage_rate": float(customer["usage_rate"]),
        "one_way_travel_time": float(outbound["travel_time"]),
        "one_way_travel_cost": float(outbound["travel_cost"]),
    }


def main() -> None:
    data = load_witness()
    horizon = data["horizon"]
    initial_inventory = data["initial_inventory"]
    usage_rate = data["usage_rate"]
    lower_inventory = data["lower_inventory"]
    upper_inventory = data["upper_inventory"]
    terminal_requirement = data["terminal_requirement"]
    vehicle_count = data["vehicle_count"]
    vehicle_capacity = data["vehicle_capacity"]
    service_time = 0.0
    one_way_travel_time = data["one_way_travel_time"]
    one_way_travel_cost = data["one_way_travel_cost"]
    earliest_arrival = one_way_travel_time
    latest_arrival = horizon - one_way_travel_time - service_time
    arrival_time = earliest_arrival
    deliveries = [vehicle_capacity for _ in range(vehicle_count)]

    before = initial_inventory - usage_rate * arrival_time
    after = before + sum(deliveries)
    terminal = initial_inventory - usage_rate * horizon + sum(deliveries)
    required_delivery = (
        terminal_requirement + usage_rate * horizon - initial_inventory
    )
    maximum_safe_delivery = upper_inventory - before
    reference_feasible = required_delivery <= maximum_safe_delivery
    recorded_generated_objective = (
        vehicle_count * 2.0 * one_way_travel_cost
    )

    result = {
        "instance": {
            "horizon": horizon,
            "initial_inventory": initial_inventory,
            "usage_rate": usage_rate,
            "lower_inventory": lower_inventory,
            "upper_inventory": upper_inventory,
            "terminal_requirement": terminal_requirement,
            "vehicle_count": vehicle_count,
            "vehicle_capacity": vehicle_capacity,
            "service_time": service_time,
            "one_way_travel_time": one_way_travel_time,
            "one_way_travel_cost": one_way_travel_cost,
        },
        "earliest_arrival": earliest_arrival,
        "latest_arrival": latest_arrival,
        "all_visits_must_arrive_at": arrival_time,
        "inventory_before": before,
        "aggregate_delivery": sum(deliveries),
        "inventory_after": after,
        "upper_inventory": upper_inventory,
        "overflow": after - upper_inventory,
        "terminal_inventory": terminal,
        "required_delivery": required_delivery,
        "maximum_safe_delivery": maximum_safe_delivery,
        "reference_feasible": reference_feasible,
        "recorded_generated_result": {
            "model": "gpt-5.5-2026-04-23",
            "status": "OPTIMAL",
            "objective": recorded_generated_objective,
            "deliveries": deliveries,
        },
        "certificate_valid": (
            earliest_arrival == latest_arrival
            and
            not reference_feasible
            and after > upper_inventory
            and terminal >= terminal_requirement
            and before >= lower_inventory
            and all(delivery <= vehicle_capacity for delivery in deliveries)
            and recorded_generated_objective == 8.0
        ),
    }
    print(json.dumps(result, indent=2))
    if not result["certificate_valid"]:
        raise SystemExit("False-feasibility certificate did not validate")


if __name__ == "__main__":
    main()
