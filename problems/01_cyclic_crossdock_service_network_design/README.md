# Cyclic Freight Service Design with Cross-Dock Handling

This candidate couples two core scheduled service network design decisions: freight must follow a time-feasible itinerary, and weekly service frequency must be coverable by the available physical tractor fleet. A closed path in a modulo-week graph is insufficient when the path winds across multiple weeks.

| Item | Value |
|---|---|
| Google Form domain | Supply chain and logistics |
| Model type | Mixed-integer linear program |
| Ground truth | Direct path `F4`; open `F4,R4`; objective `15` |
| Full-model failure | `gpt-5.4-2026-03-05` (low reasoning) reports `INFEASIBLE` because it gives demand `-1` to both destination-time nodes for one unit of source supply |
| Replicated smaller-model failure | Two `gpt-5-mini-2025-08-07` high-reasoning runs prove `11.5` with `F4,R1,R2`; the design needs three staggered tractors, exceeding the two-tractor fleet |
| Scope | GPT-5.4, GPT-5.5, and GPT-5.6 Luna high-reasoning controls returned the correct objective `15` |

## Files

- `cyclic_crossdock_service_network_design.tex`: compact precise statement, MILP, and failure certificate.
- `business_description.md` and `.docx`: canonical source and Form-ready business document.
- `evaluation_system_prompt.md` and `evaluation_prompt.md`: exact model-screening input.
- `instance.csv`: original synthetic periodic time-space instance in the call's requested data format.
- `solve_cyclic_crossdock_snd.py`: exact Gurobi model with diagnostic ablations.
- `check_cyclic_crossdock_snd.py`: standard-library exhaustive oracle and witness checker.
- `screened_model_output.py`, `screened_model_output_mini_repeat.py`, and `screened_model_output_gpt54_low.py`: three public generated programs exhibiting two distinct formulation errors.
- `screened_model_execution.txt`: commands, solver outcomes, and independent certificates for the three failed runs.
- `evidence_summary.json`, `screening_matrix.json`, and `generated_run_manifest.json`: machine-readable evidence; the checker embeds and verifies the expected oracle cases.

## Verify

```bash
python3 problems/01_cyclic_crossdock_service_network_design/check_cyclic_crossdock_snd.py
python3 problems/01_cyclic_crossdock_service_network_design/solve_cyclic_crossdock_snd.py
python3 problems/01_cyclic_crossdock_service_network_design/solve_cyclic_crossdock_snd.py --omit-handling
python3 problems/01_cyclic_crossdock_service_network_design/solve_cyclic_crossdock_snd.py --omit-fleet-limit
python3 problems/01_cyclic_crossdock_service_network_design/screened_model_output.py
python3 problems/01_cyclic_crossdock_service_network_design/screened_model_output_mini_repeat.py
python3 problems/01_cyclic_crossdock_service_network_design/screened_model_output_gpt54_low.py
```

The checker uses only the Python standard library. The solver requires Gurobi and `gurobipy`.

## Sources and rights

The statement, numerical instance, and code were created independently; no upstream data or code is copied. Periodic time-space service design and fleet balance are motivated by Gao, Jin, and Diao (2022), [doi:10.3390/pr10071373](https://doi.org/10.3390/pr10071373), published under CC BY 4.0. Cross-dock loading, unloading, and transshipment-time semantics are motivated by [Google's Shipping Network Design documentation](https://developers.google.com/optimization/service/shipping/network_design), whose page content is CC BY 4.0.

Repository code is MIT licensed. Original statements and data are CC BY 4.0.

Public package: https://github.com/Zhengzhong-You/OR-Bench
