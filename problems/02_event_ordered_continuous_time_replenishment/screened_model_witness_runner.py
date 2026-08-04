#!/usr/bin/env python3
"""Run the screened model on the exact public false-feasibility witness."""

from screened_model_output import solve_replenishment_routing


def main() -> None:
    depot = 0
    customer = 1
    data = {
        "depot": depot,
        "customers": [customer],
        "horizon": 10.0,
        "num_vehicles": 4,
        "max_trips_per_vehicle": 1,
        "vehicle_capacity": 5.0,
        "consumption_rate": {customer: 1.0},
        "initial_inventory": {customer: 90.0},
        "lower_inventory": {customer: 0.0},
        "upper_inventory": {customer: 100.0},
        "terminal_reserve": {customer: 100.0},
        "service_time": {customer: 0.0},
        "travel_time": {(depot, customer): 5.0, (customer, depot): 5.0},
        "travel_cost": {(depot, customer): 1.0, (customer, depot): 1.0},
    }
    model = solve_replenishment_routing(data, output_flag=False)
    if model is None:
        raise SystemExit("Screened model did not return the recorded solution")
    if abs(model.ObjVal - 8.0) > 1e-8:
        raise SystemExit(f"Unexpected screened-model objective: {model.ObjVal}")


if __name__ == "__main__":
    main()
