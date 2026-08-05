# Event Consistency in Continuous-Time Inventory Routing

Repeated deliveries must form one physically consistent inventory trajectory. Pairwise precedence variables can describe incompatible histories unless the visits are placed in a genuine event order.

| Submission fact | Value |
|---|---|
| Google Form domain | Inventory management |
| Model type | Mixed-integer linear program |
| Source | Synthetic witness evaluated with the compact formulation of Wang et al. (2025) |
| Ground truth | Infeasible: the required delivery is `20`, but only `15` can enter without overflow |
| Observed failure | A generated formulation reports an optimum by crediting four simultaneous deliveries separately; aggregate inventory becomes `105 > 100` |

## The five files

| File | Purpose |
|---|---|
| `README.md` | Navigation, result, evidence, sources, and commands |
| `business_description.docx` | Business-level description for the Form's dedicated upload |
| `instance.csv` | Original one-customer false-feasibility witness |
| `solve_ctirp_submission.py` | Self-contained event-copy Gurobi MILP plus analytic verification |
| `event_ordered_continuous_time_replenishment.tex` | Self-contained, directly compilable source of the precise problem document |

The compiled document is centralized at `output/pdf/event_ordered_continuous_time_replenishment.pdf`.

## Verify

```bash
python3 problems/02_event_ordered_continuous_time_replenishment/solve_ctirp_submission.py \
  problems/02_event_ordered_continuous_time_replenishment/instance.csv --verify
```

The solver returns `INFEASIBLE`; its built-in certificate independently checks that all visits are forced to time 5 and that the required delivery exceeds safe tank capacity.

## Sources and rights

The reference MILP and its implementation are adapted from the mathematical formulation of Wang et al. (2025). The implementation is independently written from the published equations. Lagos, Boland, and Savelsbergh (2020) provide the original continuous-time inventory-routing context. The numerical witness and checker were developed for this challenge. No benchmark data, paper text, or upstream source code is redistributed. New code is MIT licensed, and the original statement and data are CC BY 4.0.

Public package: https://github.com/Zhengzhong-You/OR-Bench
