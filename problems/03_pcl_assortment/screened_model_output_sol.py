import itertools
import math

import gurobipy as gp
from gurobipy import GRB


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

PRODUCTS = (1, 2, 3, 4, 5, 6)

ATTRACTION = {
    1: 0.973424,
    2: 0.698123,
    3: 0.267773,
    4: 0.864084,
    5: 0.288424,
    6: 0.136238,
}

MARGIN = {
    1: 0.0265755,
    2: 0.301877,
    3: 0.732227,
    4: 0.135916,
    5: 0.711576,
    6: 0.863762,
}

DISSIMILARITY = {
    (1, 2): 0.382242,
    (1, 3): 0.121858,
    (1, 4): 0.113422,
    (1, 5): 0.218489,
    (1, 6): 0.425957,
    (2, 3): 0.236851,
    (2, 4): 0.0577705,
    (2, 5): 0.195819,
    (2, 6): 0.156512,
    (3, 4): 0.390491,
    (3, 5): 0.302421,
    (3, 6): 0.154003,
    (4, 5): 0.372329,
    (4, 6): 0.0689346,
    (5, 6): 0.202387,
}

OUTSIDE_WEIGHT = 3.84538427435401
MAX_PRODUCTS = 4


# ---------------------------------------------------------------------------
# PCL calculations
# ---------------------------------------------------------------------------

def pcl_probabilities(assortment):
    """
    Compute standard offered-pair PCL probabilities.

    For assortment S:

        D(S) = v0 + sum_{i<j, i,j in S}
                    (v_i^(1/gamma_ij) + v_j^(1/gamma_ij))^gamma_ij

        P_i(S) = N_i(S) / D(S)

        N_i(S) = sum_{j in S, j != i}
                    v_i^(1/gamma_ij)
                    (v_i^(1/gamma_ij) + v_j^(1/gamma_ij))^(gamma_ij - 1)

        P_0(S) = v0 / D(S)

    Returns
    -------
    purchase_probabilities : dict
        Probability for each offered product.
    no_purchase_probability : float
    denominator : float
    """
    assortment = tuple(sorted(assortment))

    numerators = {i: 0.0 for i in assortment}
    denominator = OUTSIDE_WEIGHT

    for i, j in itertools.combinations(assortment, 2):
        gamma = DISSIMILARITY[(i, j)]

        if not (0.0 < gamma <= 1.0):
            raise ValueError(
                f"Invalid PCL dissimilarity for pair {(i, j)}: {gamma}"
            )

        # The given data are numerically safe for direct exponentiation.
        vi_power = math.exp(math.log(ATTRACTION[i]) / gamma)
        vj_power = math.exp(math.log(ATTRACTION[j]) / gamma)
        pair_sum = vi_power + vj_power

        inclusive_value = math.exp(gamma * math.log(pair_sum))
        common_factor = math.exp((gamma - 1.0) * math.log(pair_sum))

        denominator += inclusive_value
        numerators[i] += vi_power * common_factor
        numerators[j] += vj_power * common_factor

    probabilities = {
        i: numerators[i] / denominator
        for i in assortment
    }
    no_purchase_probability = OUTSIDE_WEIGHT / denominator

    # Numerical consistency check: product probabilities plus the outside
    # probability must sum to one.
    total_probability = (
        no_purchase_probability + sum(probabilities.values())
    )
    if not math.isclose(
        total_probability, 1.0, rel_tol=1e-10, abs_tol=1e-10
    ):
        raise ArithmeticError(
            f"PCL probabilities sum to {total_probability}, not 1."
        )

    return probabilities, no_purchase_probability, denominator


def expected_contribution(assortment):
    """Expected normalized contribution margin for an assortment."""
    probabilities, _, _ = pcl_probabilities(assortment)
    return sum(MARGIN[i] * probabilities[i] for i in assortment)


def status_name(status_code):
    """Return a readable Gurobi status name."""
    status_labels = [
        "LOADED",
        "OPTIMAL",
        "INFEASIBLE",
        "INF_OR_UNBD",
        "UNBOUNDED",
        "CUTOFF",
        "ITERATION_LIMIT",
        "NODE_LIMIT",
        "TIME_LIMIT",
        "SOLUTION_LIMIT",
        "INTERRUPTED",
        "NUMERIC",
        "SUBOPTIMAL",
        "INPROGRESS",
        "USER_OBJ_LIMIT",
        "WORK_LIMIT",
        "MEM_LIMIT",
    ]

    mapping = {}
    for label in status_labels:
        if hasattr(GRB, label):
            mapping[getattr(GRB, label)] = label

    return mapping.get(status_code, f"UNKNOWN_STATUS_{status_code}")


# ---------------------------------------------------------------------------
# Exact assortment optimization model
# ---------------------------------------------------------------------------

def main():
    # Include all 2^6 assortments. The explicit Gurobi cardinality constraint
    # will eliminate assortments with more than MAX_PRODUCTS products.
    assortments = [
        tuple(combination)
        for size in range(len(PRODUCTS) + 1)
        for combination in itertools.combinations(PRODUCTS, size)
    ]

    # Calculate objective coefficients from the calibrated PCL model.
    assortment_revenue = {
        k: expected_contribution(assortment)
        for k, assortment in enumerate(assortments)
    }

    model = gp.Model("limited_display_pcl_assortment")

    # z[k] = 1 if assortment k is selected.
    z = model.addVars(
        range(len(assortments)),
        vtype=GRB.BINARY,
        name="assortment",
    )

    # x[i] = 1 if product i is offered. These variables make the product
    # selection and cardinality constraint explicit.
    x = model.addVars(
        PRODUCTS,
        vtype=GRB.BINARY,
        name="offer",
    )

    # Select exactly one complete assortment.
    model.addConstr(
        gp.quicksum(z[k] for k in range(len(assortments))) == 1,
        name="select_one_assortment",
    )

    # Link product decisions to the selected assortment.
    for i in PRODUCTS:
        model.addConstr(
            x[i]
            == gp.quicksum(
                z[k]
                for k, assortment in enumerate(assortments)
                if i in assortment
            ),
            name=f"link_product_{i}",
        )

    # Limited display capacity.
    model.addConstr(
        gp.quicksum(x[i] for i in PRODUCTS) <= MAX_PRODUCTS,
        name="display_capacity",
    )

    # Maximize expected normalized contribution margin.
    model.setObjective(
        gp.quicksum(
            assortment_revenue[k] * z[k]
            for k in range(len(assortments))
        ),
        GRB.MAXIMIZE,
    )

    # Require a zero target relative gap. This instance is very small.
    model.Params.MIPGap = 0.0

    model.optimize()

    print("\n" + "=" * 72)
    print("PCL ASSORTMENT OPTIMIZATION RESULTS")
    print("=" * 72)
    print(
        f"Solver status       : "
        f"{status_name(model.Status)} ({model.Status})"
    )

    if model.SolCount == 0:
        print("No feasible incumbent solution was found.")
        try:
            print(f"Best bound          : {model.ObjBound:.12f}")
        except gp.GurobiError:
            print("Best bound          : unavailable")
        return

    print(f"Incumbent objective : {model.ObjVal:.12f}")
    print(f"Best proven bound   : {model.ObjBound:.12f}")
    print(f"Relative MIP gap    : {model.MIPGap:.12g}")

    # Identify the selected one-hot assortment variable.
    selected_index = max(
        range(len(assortments)),
        key=lambda k: z[k].X,
    )
    chosen = assortments[selected_index]

    probabilities, no_purchase_probability, denominator = (
        pcl_probabilities(chosen)
    )

    # Direct recomputation from the reported purchase probabilities.
    direct_expected_contribution = sum(
        MARGIN[i] * probabilities[i] for i in chosen
    )

    print(f"Chosen products     : {list(chosen)}")
    print(f"Number offered      : {len(chosen)}")
    print(f"PCL denominator     : {denominator:.12f}")

    print("\nProduct purchase probabilities:")
    if chosen:
        for i in chosen:
            print(
                f"  Product {i}: "
                f"P={probabilities[i]:.12f}, "
                f"margin={MARGIN[i]:.7f}, "
                f"expected contribution="
                f"{MARGIN[i] * probabilities[i]:.12f}"
            )
    else:
        print("  No products offered.")

    print(
        f"\nNo-purchase probability : "
        f"{no_purchase_probability:.12f}"
    )
    print(
        f"Probability total       : "
        f"{no_purchase_probability + sum(probabilities.values()):.12f}"
    )
    print(
        f"Direct expected margin  : "
        f"{direct_expected_contribution:.12f}"
    )
    print(
        f"Objective recompute diff: "
        f"{abs(model.ObjVal - direct_expected_contribution):.3e}"
    )


if __name__ == "__main__":
    main()
