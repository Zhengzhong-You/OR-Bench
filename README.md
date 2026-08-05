# OR-Bench Modeling Case Studies

The repository contains two reproducible optimization-modeling case studies developed for OR-Bench. Each case combines a business-level description, a precise mathematical statement, a numerical instance, and an executable reference solver. The two cases focus on consistency requirements that are easy to overlook but essential for a valid formulation.

## Case Studies

| Case | Domain | Model | Modeling issue | Verified result |
|---|---|---|---|---|
| [Event Consistency in Continuous-Time Inventory Routing](problems/01_event_ordered_continuous_time_replenishment/) | Inventory routing | MILP | Repeated deliveries must follow one common event order | The reference instance is infeasible; inconsistent pairwise histories can conceal an inventory level of `105` in a tank capped at `100` |
| [Pair-State Consistency in Paired Combinatorial Logit Assortment Planning](problems/02_pcl_assortment/) | Revenue management | MILP | Every product pair must represent the two singleton states and the jointly offered state | The unique optimum is `{3,5,6}`; incomplete pair-state formulations select `{2,3,5,6}`, whose correct objective is `11.639776%` lower |

## Repository Contents

Each problem directory contains the following materials.

| File | Purpose |
|---|---|
| `README.md` | Case overview, verified result, sources, and reproduction commands |
| `business_description.docx` | Business-level problem description |
| `instance.csv` | Numerical data and provenance information |
| Python solver | Reference formulation and automated verification |
| LaTeX source | Editable source of the precise problem statement |

Compiled problem statements are available in [`output/pdf/`](output/pdf/). The shared LaTeX layout is retained in [`latex/`](latex/) as a reference copy; each problem source is also self-contained.

## Build the Problem Statements

A current TeX Live installation with `latexmk` is sufficient.

```bash
make pdf-all
```

Individual targets are `pdf-ctirp` and `pdf-pcl`. The compiled files are written to `output/pdf/`.

## Reproduce the Results

The reference solvers require Python, Gurobi, and `gurobipy`.

```bash
python3 problems/01_event_ordered_continuous_time_replenishment/solve_ctirp_submission.py \
  problems/01_event_ordered_continuous_time_replenishment/instance.csv --verify

python3 problems/02_pcl_assortment/solve_pcl_structured.py --verify
```

The first command verifies the infeasibility certificate for the continuous-time replenishment instance. The second solves the pair-state-consistent PCL formulation and compares its result with complete enumeration of all 57 feasible assortments.

## Sources and Licensing

The continuous-time inventory-routing case uses an original synthetic instance and an independently written implementation of the formulation in Wang et al. (2025). The paired combinatorial logit case is a documented derivative of the MIT-licensed artifact accompanying Feng, Che, and Chen (2026). Detailed citations and provenance information appear in the corresponding problem directories.

New code is released under the [MIT License](LICENSE). Original problem statements and derivative data are released under [CC BY 4.0](LICENSE-DATA.md), subject to any upstream notices included with individual files.
