# Limited-Display PCL Assortment Planning

A valid paired combinatorial logit model must preserve every state of each pair. In particular, a pair still contributes demand mass when exactly one member is offered; deleting that state changes both probabilities and the optimal assortment.

| Submission fact | Value |
|---|---|
| Google Form domain | Revenue management and pricing |
| Model type | Mixed-integer linear program |
| Source | Feng, Che, and Chen (2026), [paper](https://doi.org/10.1287/ijoc.2024.0830) and [MIT-licensed artifact](https://doi.org/10.1287/ijoc.2024.0830.cd) at commit `a3920679d4725ec714af29d24034a5d6d9db6b8f` |
| Ground truth | Unique optimum `{3,5,6}`; objective `0.323647238294198` |
| Observed failure | Two generated models choose `{2,3,5,6}`; its correct objective is `0.285975423739680`, or `11.639776%` regret |

## The five files

| File | Purpose |
|---|---|
| `README.md` | Navigation, result, evidence, sources, and commands |
| `business_description.docx` | Business-level description for the Form's dedicated upload |
| `instance.csv` | Six-product derivative instance with source mapping and complete upstream MIT notice |
| `solve_pcl_structured.py` | Exact Gurobi MILP plus exhaustive 57-assortment verification |
| `pcl_assortment.tex` | Editable source of the precise problem document |

The compiled document is centralized at `output/pdf/pcl_assortment.pdf`.

## Verify

```bash
python3 problems/03_pcl_assortment/solve_pcl_structured.py --verify
```

The built-in enumeration proves uniqueness, recomputes the failed decision under the correct choice probabilities, and reports its regret.

## Sources and rights

The instance is a documented derivative of the cited MIT-licensed artifact; its CSV embeds the source mapping and complete upstream notice. The formulation and verification code are independently written. New code is MIT licensed; statements and derivative data are CC BY 4.0 subject to the embedded notice.

Public package: https://github.com/Zhengzhong-You/OR-Bench
