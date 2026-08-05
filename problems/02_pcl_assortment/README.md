# Pair-State Consistency in Paired Combinatorial Logit Assortment Planning

A valid paired combinatorial logit model must preserve every active state of each product pair. A pair continues to contribute demand mass when exactly one member is offered, so removing or merging the singleton states changes the choice probabilities and may change the optimal assortment.

## Summary

| Property | Value |
|---|---|
| Domain | Revenue management |
| Model type | Mixed-integer linear program |
| Source | Feng, Che, and Chen (2026), [paper](https://doi.org/10.1287/ijoc.2024.0830) and [MIT-licensed artifact](https://doi.org/10.1287/ijoc.2024.0830.cd) at commit `a3920679d4725ec714af29d24034a5d6d9db6b8f` |
| Instance | Six-product derivative instance with a display limit of four |
| Verified result | Unique optimum `{3,5,6}` with objective `0.323647238294198` |
| Incomplete-formulation result | Two incomplete pair-state systems select `{2,3,5,6}`; its correct objective is `0.285975423739680`, corresponding to `11.639776%` regret |

## Files

| File | Purpose |
|---|---|
| `README.md` | Case overview and reproduction instructions |
| `business_description.docx` | Business-level problem description |
| `instance.csv` | Six-product derivative instance, source mapping, and upstream MIT notice |
| `solve_pcl_structured.py` | Exact Gurobi MILP and complete-enumeration verifier |
| `pcl_assortment.tex` | Self-contained source of the precise problem statement |

The compiled problem statement is available at [`../../output/pdf/pcl_assortment.pdf`](../../output/pdf/pcl_assortment.pdf).

## Reproduce the Result

Solve the MILP and compare it with complete enumeration.

```bash
python3 problems/02_pcl_assortment/solve_pcl_structured.py --verify
```

The command verifies the Gurobi solution, objective bound, direct probability calculation, and all 57 feasible assortments. It also reproduces the decisions returned by the two incomplete pair-state systems and evaluates those decisions under the reference PCL model.

Complete enumeration can run without Gurobi.

```bash
python3 problems/02_pcl_assortment/solve_pcl_structured.py --enumerate-only
```

## Sources and Licensing

The instance is a documented derivative of the cited MIT-licensed artifact. Its CSV file contains the source mapping and complete upstream notice. The formulation and verification code were written independently.

New code is MIT licensed. The problem statement and derivative data are CC BY 4.0, subject to the embedded upstream notice.
