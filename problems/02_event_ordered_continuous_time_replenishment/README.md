# Event-Ordered Continuous-Time Tank Replenishment

This candidate tests whether repeated deliveries define one physically consistent inventory trajectory. Pairwise precedence variables are insufficient when they permit cycles or incompatible views of which deliveries occurred first.

| Item | Value |
|---|---|
| Google Form domain | Inventory management |
| Model type | Mixed-integer linear program |
| Problem source | Original synthetic challenge; continuous-time IRP literature is cited for context |
| Reference formulation | Independently implemented event-copy MILP derived from the stated business rules |
| Confirmed failure | Generated repeated-delivery precedence does not define a total order |
| Mechanical certificate | Generated solution credits four simultaneous deliveries separately; aggregate tank inventory is `105 > 100` |

## Files

- `event_ordered_continuous_time_replenishment.tex`: compact precise statement, formulation, and failure certificate.
- `business_description.md` and `.docx`: canonical source and Form-ready business document.
- `evaluation_system_prompt.md` and `evaluation_prompt.md`: exact model-screening input.
- `evidence_summary.json`: machine-readable witness and validation summary.
- `generated_run_manifest.json`: model, timestamp, hashes, and recorded solver result.
- `check_false_feasible.py`: standard-library-only certificate checker.
- `instance.csv`: original one-customer witness in the call's requested data format.
- `solve_ctirp_submission.py`: self-contained reference solver for the Form's single solver upload.
- `screened_model_output.py`, `screened_model_witness_runner.py`, and `screened_model_execution.txt`: generated formulation, exact witness runner, and cleaned execution.

## Sources and rights

The business brief, numerical witness, checker, and solver are independently written for this challenge. `instance.csv` is original synthetic data; it is not a copied or derived benchmark instance. No paper text, upstream code, paper PDF, or benchmark archive is redistributed. Lagos, Boland, and Savelsbergh (2020) and Wang et al. (2025) are cited only as related literature. Repository code is MIT licensed; the original statement and witness data are CC BY 4.0.

Public package: https://github.com/Zhengzhong-You/OR-Bench

## Build and verify

```bash
make pdf-ctirp
python3 problems/02_event_ordered_continuous_time_replenishment/check_false_feasible.py
python3 problems/02_event_ordered_continuous_time_replenishment/screened_model_witness_runner.py
```

To solve the public witness (the intended model correctly returns infeasible):

```bash
python3 problems/02_event_ordered_continuous_time_replenishment/solve_ctirp_submission.py \
  problems/02_event_ordered_continuous_time_replenishment/instance.csv
```

The reference solver requires Python, Gurobi, and `gurobipy`.
