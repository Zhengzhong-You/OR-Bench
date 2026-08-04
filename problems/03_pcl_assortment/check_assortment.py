#!/usr/bin/env python3
"""Evaluate a proposed assortment under the standard PCL semantics."""

from __future__ import annotations

import argparse
import csv
import json
import math
from itertools import combinations
from pathlib import Path


INSTANCE = Path(__file__).with_name("instance.csv")
EVIDENCE = Path(__file__).with_name("evidence_summary.json")


def load_data() -> dict:
    data = {
        "source": {"license": {}},
        "products": [],
        "pairwise_dissimilarity": [],
    }
    with INSTANCE.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            kind = row["record_type"]
            if kind == "metadata":
                value = row["value"]
                if row["key"] == "max_products":
                    value = int(value)
                elif row["key"] == "outside_weight":
                    value = float(value)
                data[row["key"]] = value
            elif kind == "source":
                data["source"][row["key"]] = row["value"]
            elif kind == "license":
                data["source"]["license"][row["key"]] = row["value"]
            elif kind == "product":
                data["products"].append({
                    "id": int(row["id"]),
                    "source_id": int(row["source_id"]),
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
            total = vi + vj
            nest = math.exp(gamma * math.log(total))
            denominator += nest
            product_mass[i] += nest * vi / total
            product_mass[j] += nest * vj / total

    probability = {
        product: product_mass[product] / denominator for product in assortment
    }
    outside = data["outside_weight"] / denominator
    objective = sum(margin[i] * probability[i] for i in assortment)
    if abs(outside + sum(probability.values()) - 1.0) > 1e-10:
        raise ArithmeticError("PCL probabilities do not sum to one")
    return objective, probability, outside


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("products", nargs="*", type=int, default=[2, 3, 5, 6])
    args = parser.parse_args()
    data = load_data()
    products = tuple(row["id"] for row in data["products"])
    proposed = tuple(sorted(args.products))
    if len(proposed) != len(set(proposed)) or not set(proposed).issubset(products):
        raise ValueError("Products must be unique valid IDs")
    if len(proposed) > data["max_products"]:
        raise ValueError("Assortment exceeds display capacity")

    feasible = [
        s
        for size in range(data["max_products"] + 1)
        for s in combinations(products, size)
    ]
    ranked = sorted(
        ((pcl_metrics(frozenset(s), data)[0], s) for s in feasible), reverse=True
    )
    optimum, optimal = ranked[0]
    value, probability, outside = pcl_metrics(frozenset(proposed), data)
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    expected_optimal = tuple(evidence["ground_truth"]["unique_optimum"])
    if len(feasible) != evidence["feasible_assortments"]:
        raise AssertionError("Feasible-assortment count disagrees with evidence")
    if optimal != expected_optimal or not math.isclose(
        optimum, evidence["ground_truth"]["objective"], rel_tol=0.0, abs_tol=1e-12
    ):
        raise AssertionError("Enumeration disagrees with evidence_summary.json")
    if not optimum > ranked[1][0] + 1e-12:
        raise AssertionError("Claimed optimum is not unique")
    recorded = evidence["correct_evaluation_of_model_selection"]
    recorded_llm = tuple(recorded["selected_products"])
    if proposed == recorded_llm:
        if not math.isclose(
            value, recorded["objective"],
            rel_tol=0.0, abs_tol=1e-12
        ):
            raise AssertionError("Recorded failed decision value disagrees")
    result = {
        "proposed": proposed,
        "true_objective": value,
        "optimal_assortment": optimal,
        "optimal_objective": optimum,
        "absolute_regret": optimum - value,
        "relative_regret": (optimum - value) / optimum,
        "is_optimal": proposed == optimal,
        "purchase_probabilities": probability,
        "outside_probability": outside,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
