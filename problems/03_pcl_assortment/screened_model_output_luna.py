import math
from itertools import combinations

import gurobipy as gp
from gurobipy import GRB


# ---------------------------------------------------------------------
# Input data
# ---------------------------------------------------------------------

products = [1, 2, 3, 4, 5, 6]

# Attraction weights v_i
attraction = {
    1: 0.973424,
    2: 0.698123,
    3: 0.267773,
    4: 0.864084,
    5: 0.288424,
    6: 0.136238,
}

# Normalized contribution margins
margin = {
    1: 0.0265755,
    2: 0.301877,
    3: 0.732227,
    4: 0.135916,
    5: 0.711576,
    6: 0.863762,
}

outside_weight = 3.84538427435401

# PCL pairwise dissimilarities rho_ij
dissimilarity = {
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


def rho(i, j):
    """Return the pairwise dissimilarity using an ordered key."""
    return dissimilarity[tuple(sorted((i, j)))]


# ---------------------------------------------------------------------
# Standard PCL demand calculation
# ---------------------------------------------------------------------

def pcl_probabilities(assortment):
    """
    Compute PCL purchase probabilities and no-purchase probability.

    For an offered assortment S:

        I_ij = (v_i^(1/rho_ij) + v_j^(1/rho_ij))^rho_ij

        D(S) = v0 + sum_i(v_i) + sum_{i<j}(I_ij)

        P_i(S) =
            [v_i + sum_{j != i} I_ij *
             v_i^(1/rho_ij) /
             (v_i^(1/rho_ij) + v_j^(1/rho_ij))]
            / D(S)

        P_0(S) = v0 / D(S)

    The singleton term v_i represents the singleton nest for product i,
    and the outside option is a singleton nest with weight v0.
    """
    S = tuple(sorted(assortment))

    probabilities = {i: 0.0 for i in products}

    if len(S) == 0:
        return probabilities, 1.0

    numerator = {
        i: float(attraction[i])
        for i in S
    }

    denominator = outside_weight + sum(attraction[i] for i in S)

    for i, j in combinations(S, 2):
        r = rho(i, j)

        vi_power = attraction[i] ** (1.0 / r)
        vj_power = attraction[j] ** (1.0 / r)
        power_sum = vi_power + vj_power

        # Inclusive value of the pair nest
        inclusive_value = power_sum ** r

        denominator += inclusive_value

        # Allocation of the pair-nest probability to each product
        numerator[i] += inclusive_value * vi_power / power_sum
        numerator[j] += inclusive_value * vj_power / power_sum

    for i in S:
        probabilities[i] = numerator[i] / denominator

    no_purchase_probability = outside_weight / denominator

    # Numerical validation of the probability calculation
    probability_total = (
        no_purchase_probability + sum(probabilities.values())
    )
    if not math.isclose(probability_total, 1.0, rel_tol=0.0, abs_tol=1e-10):
        raise RuntimeError(
            f"PCL probabilities do not sum to one for assortment {S}: "
            f"{probability_total}"
        )

    return probabilities, no_purchase_probability


# ---------------------------------------------------------------------
# Enumerate all feasible assortments
# ---------------------------------------------------------------------

# "Up to four" includes the empty assortment. It will not be optimal here
# because all contribution margins are positive, but it is included for
# completeness.
assortments = []

for k in range(0, 5):
    assortments.extend(combinations(products, k))

# Precompute PCL demand and expected margin for every feasible assortment
assortment_probabilities = {}
assortment_no_purchase = {}
assortment_value = {}

for S in assortments:
    probabilities, no_purchase_probability = pcl_probabilities(S)

    expected_margin = sum(
        probabilities[i] * margin[i]
        for i in products
    )

    assortment_probabilities[S] = probabilities
    assortment_no_purchase[S] = no_purchase_probability
    assortment_value[S] = expected_margin


# ---------------------------------------------------------------------
# Exact Gurobi optimization model
# ---------------------------------------------------------------------

model = gp.Model("limited_display_pcl_assortment")

# z[k] = 1 if assortment k is selected
z = model.addVars(
    len(assortments),
    vtype=GRB.BINARY,
    name="select_assortment"
)

# x[i] = 1 if product i is offered
x = model.addVars(
    products,
    vtype=GRB.BINARY,
    name="offer"
)

# Select exactly one feasible assortment
model.addConstr(
    gp.quicksum(z[k] for k in range(len(assortments))) == 1,
    name="one_assortment"
)

# Link product-offer variables to the selected assortment
for i in products:
    model.addConstr(
        x[i] == gp.quicksum(
            z[k]
            for k, S in enumerate(assortments)
            if i in S
        ),
        name=f"offer_link_{i}"
    )

# Display capacity
model.addConstr(
    gp.quicksum(x[i] for i in products) <= 4,
    name="display_capacity"
)

# Expected contribution margin
model.setObjective(
    gp.quicksum(
        assortment_value[S] * z[k]
        for k, S in enumerate(assortments)
    ),
    GRB.MAXIMIZE
)

# Suppress the standard Gurobi log; required solver results are printed below.
model.Params.OutputFlag = 0

model.optimize()


# ---------------------------------------------------------------------
# Solver results
# ---------------------------------------------------------------------

status_names = {
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
    GRB.USER_OBJ_LIMIT: "USER_OBJ_LIMIT",
}

status_name = status_names.get(model.Status, str(model.Status))

print("=" * 72)
print("PCL limited-display assortment optimization")
print("=" * 72)
print(f"Solver status: {status_name} (code {model.Status})")

if model.SolCount == 0:
    print("No feasible solution was found.")
else:
    print(f"Proven objective: {model.ObjVal:.12f}")
    print(f"Proven bound:    {model.ObjBound:.12f}")
    print(f"Proven gap:      {model.MIPGap:.12g}")

    # Recover the selected assortment directly from the assortment variables
    selected_index = max(
        range(len(assortments)),
        key=lambda k: z[k].X
    )
    chosen = assortments[selected_index]

    # Directly recompute PCL probabilities for the chosen assortment
    probabilities, no_purchase_probability = pcl_probabilities(chosen)

    direct_expected_margin = sum(
        probabilities[i] * margin[i]
        for i in products
    )

    print()
    print(f"Chosen products: {list(chosen)}")
    print(f"Number of chosen products: {len(chosen)}")

    print()
    print("Chosen products and their PCL purchase probabilities:")
    if len(chosen) == 0:
        print("  No products offered.")
    else:
        for i in chosen:
            print(
                f"  Product {i}: "
                f"probability = {probabilities[i]:.12f}, "
                f"margin = {margin[i]:.12f}, "
                f"contribution = "
                f"{probabilities[i] * margin[i]:.12f}"
            )

    print()
    print(f"No-purchase probability: {no_purchase_probability:.12f}")

    total_probability = (
        no_purchase_probability
        + sum(probabilities[i] for i in products)
    )
    print(f"Probability total check: {total_probability:.12f}")

    print()
    print(
        "Direct recomputation of expected contribution margin: "
        f"{direct_expected_margin:.12f}"
    )
    print(
        "Difference from Gurobi objective: "
        f"{direct_expected_margin - model.ObjVal:.12e}"
    )
