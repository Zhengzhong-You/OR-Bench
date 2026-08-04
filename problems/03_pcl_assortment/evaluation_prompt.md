# Limited-display assortment under a calibrated PCL demand model

Our category team must choose up to four products for a limited retail display. For each product, the demand-science team has estimated a customer-attraction weight and a normalized contribution margin. It has also calibrated a standard paired combinatorial logit (PCL) choice model, with a dissimilarity estimate for every unordered product pair and an outside-option weight for customers who leave without purchasing.

Choose the assortment that maximizes expected contribution margin while accounting for substitution among the offered products according to the calibrated PCL model. The outside-option weight is `3.84538427435401`. At most four of the six products may be offered.

Please build a complete runnable Python + gurobipy optimization program. It must print the solver status, proven objective/bound/gap, the chosen products, their PCL purchase probabilities, the no-purchase probability, and a direct recomputation of expected contribution margin. Do not ask follow-up questions and do not use a known answer.

Product data:

| Product | Attraction weight | Normalized contribution margin |
|---:|---:|---:|
| 1 | 0.973424 | 0.0265755 |
| 2 | 0.698123 | 0.301877 |
| 3 | 0.267773 | 0.732227 |
| 4 | 0.864084 | 0.135916 |
| 5 | 0.288424 | 0.711576 |
| 6 | 0.136238 | 0.863762 |

Pairwise PCL dissimilarities:

| Pair | Dissimilarity | Pair | Dissimilarity | Pair | Dissimilarity |
|---|---:|---|---:|---|---:|
| 1,2 | 0.382242 | 1,3 | 0.121858 | 1,4 | 0.113422 |
| 1,5 | 0.218489 | 1,6 | 0.425957 | 2,3 | 0.236851 |
| 2,4 | 0.0577705 | 2,5 | 0.195819 | 2,6 | 0.156512 |
| 3,4 | 0.390491 | 3,5 | 0.302421 | 3,6 | 0.154003 |
| 4,5 | 0.372329 | 4,6 | 0.0689346 | 5,6 | 0.202387 |
