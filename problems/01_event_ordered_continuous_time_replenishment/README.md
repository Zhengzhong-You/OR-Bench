# Event Consistency in Continuous-Time Inventory Routing

Repeated deliveries must define one physically consistent inventory trajectory. Pairwise precedence variables can describe incompatible delivery histories unless all visits belong to a common event order.

## Summary

| Property | Value |
|---|---|
| Domain | Inventory routing |
| Model type | Mixed-integer linear program |
| Reference formulation | [Wang et al. (2025)](https://doi.org/10.1016/j.cor.2024.106883), with continuous-time inventory-routing context from [Lagos et al. (2020)](https://doi.org/10.1287/trsc.2019.0902) |
| Instance | Original one-customer synthetic example |
| Verified result | Infeasible because the required delivery is `20`, while at most `15` units can enter without exceeding tank capacity |
| Inconsistent-formulation result | Four simultaneous deliveries of five units appear feasible when evaluated against incompatible histories, although aggregate inventory reaches `105 > 100` |

## Files

| File | Purpose |
|---|---|
| `README.md` | Case overview and reproduction instructions |
| `business_description.docx` | Business-level problem description |
| `instance.csv` | One-customer false-feasibility instance |
| `solve_ctirp_submission.py` | Event-copy Gurobi MILP and analytic verification |
| `event_ordered_continuous_time_replenishment.tex` | Self-contained source of the precise problem statement |

The compiled problem statement is available at [`../../output/pdf/event_ordered_continuous_time_replenishment.pdf`](../../output/pdf/event_ordered_continuous_time_replenishment.pdf).

## Reproduce the Result

```bash
python3 problems/01_event_ordered_continuous_time_replenishment/solve_ctirp_submission.py \
  problems/01_event_ordered_continuous_time_replenishment/instance.csv --verify
```

The command solves the reference model and returns `INFEASIBLE`. The built-in analytic check independently verifies that every visit is forced to time 5 and that the required delivery exceeds the available tank capacity.

## Sources and Licensing

The reference MILP and its implementation are based on the mathematical formulation of [Wang et al. (2025)](https://doi.org/10.1016/j.cor.2024.106883). The implementation was written independently from the published equations. [Lagos, Boland, and Savelsbergh (2020)](https://doi.org/10.1287/trsc.2019.0902) provide the continuous-time inventory-routing context. No paper text, benchmark data, or upstream source code is redistributed.

New code is MIT licensed. The original problem statement and data are CC BY 4.0.
