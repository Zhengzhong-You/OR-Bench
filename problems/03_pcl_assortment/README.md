# Limited-Display PCL Assortment Planning

This candidate tests whether a generated optimization model preserves every state of each paired combinatorial logit nest. A pair contributes demand mass when exactly one member is offered; deleting or collapsing that state changes both purchase probabilities and the optimal assortment.

| Item | Value |
|---|---|
| Google Form domain | Revenue management and pricing |
| Model type | Mixed-integer linear program |
| Source | Feng, Che, and Chen (2026), [paper](https://doi.org/10.1287/ijoc.2024.0830) and [MIT-licensed artifact](https://doi.org/10.1287/ijoc.2024.0830.cd) at commit `a3920679d4725ec714af29d24034a5d6d9db6b8f` |
| Ground truth | Unique optimum `{3,5,6}`, objective `0.323647238294198` |
| Confirmed failure | Two model runs encode different incorrect PCL pair-state systems |
| Mechanical certificate | Both choose `{2,3,5,6}`; its correct objective is `0.285975423739680`, a regret of `11.639776%` |

## Files

- `pcl_assortment.tex`: compact precise statement, structured MILP, and failure certificate.
- `business_description.md` and `.docx`: canonical source and Form-ready business document.
- `evaluation_system_prompt.md` and `evaluation_prompt.md`: exact model-screening input.
- `instance.csv`: six-product derivative instance with source mapping and complete upstream MIT notice, in the call's requested data format.
- `solve_pcl_structured.py`: exact Charnes--Cooper MILP with pair-state variables.
- `check_assortment.py`: standard-library evaluator and exhaustive oracle.
- `evidence_summary.json` and `generated_run_manifest.json`: machine-readable certificates and provenance used directly by the checker.
- `screened_model_output_luna.py`, `screened_model_output_sol.py`, and `screened_model_execution.txt`: two failed executable formulations and their audit summary.
- `NOTICE.md` and `UPSTREAM_LICENSE`: data provenance and upstream MIT terms.

## Build and verify

```bash
make pdf-pcl
python3 problems/03_pcl_assortment/check_assortment.py 2 3 5 6
python3 problems/03_pcl_assortment/solve_pcl_structured.py
```

The structured solver requires Python, Gurobi, and `gurobipy`. The checker uses only the Python standard library.

Public package: https://github.com/Zhengzhong-You/OR-Bench
