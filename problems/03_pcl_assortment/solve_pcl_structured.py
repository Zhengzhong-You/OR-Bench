#!/usr/bin/env python3
"""Structured exact MILP for the six-product PCL assortment instance."""

from __future__ import annotations

import argparse
import csv
import math
from itertools import combinations
from pathlib import Path

import gurobipy as gp
from gurobipy import GRB

INSTANCE = Path(__file__).with_name("instance.csv")
STATES = ("10", "01", "11")


def load_data() -> dict:
    data = {"products": [], "pairwise_dissimilarity": []}
    with INSTANCE.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            kind = row["record_type"]
            if kind == "metadata" and row["key"] == "max_products":
                data["max_products"] = int(row["value"])
            elif kind == "metadata" and row["key"] == "outside_weight":
                data["outside_weight"] = float(row["value"])
            elif kind == "product":
                data["products"].append({
                    "id": int(row["id"]),
                    "attraction": float(row["attraction"]),
                    "margin": float(row["margin"]),
                })
            elif kind == "pair":
                data["pairwise_dissimilarity"].append({
                    "i": int(row["i"]),
                    "j": int(row["j"]),
                    "gamma": float(row["gamma"]),
                })
    return data


def pcl_metrics(
    assortment: frozenset[int], data: dict
) -> tuple[float, dict[int, float], float]:
    attraction = {row["id"]: row["attraction"] for row in data["products"]}
    margin = {row["id"]: row["margin"] for row in data["products"]}
    product_mass = {product: 0.0 for product in attraction}
    denominator = data["outside_weight"]
    for pair in data["pairwise_dissimilarity"]:
        i, j, gamma = pair["i"], pair["j"], pair["gamma"]
        i_on, j_on = i in assortment, j in assortment
        if not i_on and not j_on:
            continue
        if i_on and not j_on:
            product_mass[i] += attraction[i]
            denominator += attraction[i]
        elif j_on and not i_on:
            product_mass[j] += attraction[j]
            denominator += attraction[j]
        else:
            vi = math.exp(math.log(attraction[i]) / gamma)
            vj = math.exp(math.log(attraction[j]) / gamma)
            nest = math.exp(gamma * math.log(vi + vj))
            denominator += nest
            product_mass[i] += nest * vi / (vi + vj)
            product_mass[j] += nest * vj / (vi + vj)
    probability = {i: product_mass[i] / denominator for i in assortment}
    outside = data["outside_weight"] / denominator
    return sum(margin[i] * probability[i] for i in assortment), probability, outside


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verify",
        action="store_true",
        help="enumerate all feasible assortments and verify the failure witness",
    )
    args = parser.parse_args()
    data = load_data()
    products = tuple(row["id"] for row in data["products"])
    attraction = {row["id"]: row["attraction"] for row in data["products"]}
    margin = {row["id"]: row["margin"] for row in data["products"]}
    pairs = [(row["i"], row["j"]) for row in data["pairwise_dissimilarity"]]
    gamma = {
        (row["i"], row["j"]): row["gamma"]
        for row in data["pairwise_dissimilarity"]
    }

    denominator_coefficient: dict[tuple[int, int, str], float] = {}
    numerator_coefficient: dict[tuple[int, int, str], float] = {}
    for i, j in pairs:
        g = gamma[i, j]
        vi_power = math.exp(math.log(attraction[i]) / g)
        vj_power = math.exp(math.log(attraction[j]) / g)
        power_sum = vi_power + vj_power
        nest = math.exp(g * math.log(power_sum))
        mass_i = nest * vi_power / power_sum
        mass_j = nest * vj_power / power_sum
        denominator_coefficient[i, j, "10"] = attraction[i]
        denominator_coefficient[i, j, "01"] = attraction[j]
        denominator_coefficient[i, j, "11"] = nest
        numerator_coefficient[i, j, "10"] = margin[i] * attraction[i]
        numerator_coefficient[i, j, "01"] = margin[j] * attraction[j]
        numerator_coefficient[i, j, "11"] = (
            margin[i] * mass_i + margin[j] * mass_j
        )

    outside = data["outside_weight"]
    denominator_upper = outside + sum(
        max(denominator_coefficient[i, j, state] for state in STATES)
        for i, j in pairs
    )
    scale_lb = 1.0 / denominator_upper
    scale_ub = 1.0 / outside

    model = gp.Model("structured_pcl_assortment")
    model.Params.OutputFlag = 0
    model.Params.MIPGap = 0.0
    offer = model.addVars(products, vtype=GRB.BINARY, name="offer")
    state = model.addVars(
        [(i, j, s) for i, j in pairs for s in STATES],
        vtype=GRB.BINARY,
        name="pair_state",
    )
    scale = model.addVar(lb=scale_lb, ub=scale_ub, name="scale")
    scaled_state = model.addVars(
        [(i, j, s) for i, j in pairs for s in STATES],
        lb=0.0,
        name="scaled_pair_state",
    )

    model.addConstr(offer.sum() <= data["max_products"], name="display_capacity")
    for i, j in pairs:
        model.addConstr(state[i, j, "11"] <= offer[i])
        model.addConstr(state[i, j, "11"] <= offer[j])
        model.addConstr(state[i, j, "11"] >= offer[i] + offer[j] - 1)
        model.addConstr(state[i, j, "10"] == offer[i] - state[i, j, "11"])
        model.addConstr(state[i, j, "01"] == offer[j] - state[i, j, "11"])

        for s in STATES:
            y = state[i, j, s]
            w = scaled_state[i, j, s]
            model.addConstr(w >= scale_lb * y)
            model.addConstr(w <= scale_ub * y)
            model.addConstr(w >= scale - scale_ub * (1 - y))
            model.addConstr(w <= scale - scale_lb * (1 - y))

    model.addConstr(
        outside * scale
        + gp.quicksum(
            denominator_coefficient[key] * scaled_state[key]
            for key in denominator_coefficient
        )
        == 1.0,
        name="normalized_pcl_denominator",
    )
    model.setObjective(
        gp.quicksum(
            numerator_coefficient[key] * scaled_state[key]
            for key in numerator_coefficient
        ),
        GRB.MAXIMIZE,
    )
    model.optimize()

    chosen = tuple(i for i in products if offer[i].X > 0.5)
    direct, probabilities, outside_probability = pcl_metrics(
        frozenset(chosen), data
    )
    status = "OPTIMAL" if model.Status == GRB.OPTIMAL else str(model.Status)
    print(f"STATUS={status}")
    print(f"OBJECTIVE={model.ObjVal:.15f}")
    print(f"BOUND={model.ObjBound:.15f}")
    print(f"GAP={model.MIPGap:.15g}")
    print(f"CHOSEN={chosen}")
    for product in chosen:
        print(f"P({product})={probabilities[product]:.15f}")
    print(f"P(OUTSIDE)={outside_probability:.15f}")
    print(f"DIRECT_OBJECTIVE={direct:.15f}")
    print(f"RECOMPUTE_DIFF={abs(model.ObjVal - direct):.3e}")

    if args.verify:
        feasible = [
            assortment
            for size in range(data["max_products"] + 1)
            for assortment in combinations(products, size)
        ]
        ranked = sorted(
            (
                (pcl_metrics(frozenset(assortment), data)[0], assortment)
                for assortment in feasible
            ),
            reverse=True,
        )
        optimum, optimal = ranked[0]
        failed_assortment = (2, 3, 5, 6)
        failed_value = pcl_metrics(frozenset(failed_assortment), data)[0]
        relative_regret = (optimum - failed_value) / optimum
        assert len(feasible) == 57
        assert optimal == (3, 5, 6)
        assert optimum > ranked[1][0] + 1e-12
        assert math.isclose(optimum, 0.323647238294198, abs_tol=1e-12)
        assert math.isclose(failed_value, 0.285975423739680, abs_tol=1e-12)
        assert math.isclose(relative_regret, 0.116397763, abs_tol=1e-9)
        print(f"FAILED_ASSORTMENT={failed_assortment}")
        print(f"FAILED_TRUE_OBJECTIVE={failed_value:.15f}")
        print(f"RELATIVE_REGRET={relative_regret:.9%}")
        print("VERIFICATION=PASS")


if __name__ == "__main__":
    main()
