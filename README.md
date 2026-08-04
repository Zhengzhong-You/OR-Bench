# OR-Bench Candidate Problems

Three reproducible optimization-modeling challenges for the [OR-Bench call for contributions](https://connect.informs.org/discussion/call-for-contributions-a-community-benchmark-for-llms-on-optimization-modeling). Each package starts with a natural business request, defines the intended mathematical problem, supplies an executable reference oracle, and ends with a mechanical certificate that distinguishes a valid decision from a plausible generated-model error.

The portfolio spans three Google Form domains and three distinct modeling hazards: periodic service and freight balance, repeated-delivery event order, and paired-choice demand states. Every candidate has an execution-confirmed current-model failure and an independent exact certificate. The SND package additionally records stronger configurations that solve the same prompt, making its scope explicit.

Recommended submission order is CTIRP, PCL, then SND. The first two are the highest-confidence candidates because frontier high-reasoning models fail on them. SND is a useful third-domain candidate but has lower curation confidence: GPT-5.4 low reasoning and two GPT-5-mini high-reasoning runs fail, while the recorded high-reasoning frontier controls are correct.

## Candidate Portfolio

| Candidate | Form domain | Model | Observed formulation failure | Certificate |
|---|---|---|---|---|
| [Cyclic Freight Service Design with Cross-Dock Handling](problems/01_cyclic_crossdock_service_network_design/) | Supply chain and logistics | MILP | One full model duplicates destination demand and reports infeasible; two smaller models undercount the periodic fleet | Explicit `F4,R4` solution costs 15; smaller-model decision 11.5 needs three tractors |
| [Event-Ordered Continuous-Time Tank Replenishment](problems/02_event_ordered_continuous_time_replenishment/) | Inventory management | MILP | Pairwise precedence permits incompatible histories for repeated deliveries | Generated plan reaches inventory 105 in a tank capped at 100 |
| [Limited-Display PCL Assortment Planning](problems/03_pcl_assortment/) | Revenue management and pricing | MILP | Deletes or collapses exactly-one-offered PCL pair states | Both generated models select an assortment with 11.639776% true regret |

## Common Submission Contract

Every problem folder contains:

1. `business_description.md` and `.docx` — canonical text plus the Form-ready business-level-description upload;
2. a concise LaTeX document — title, precise statement, formulation, evidence, and sources;
3. an upload-ready executable reference solver and exact checker;
4. machine-readable instance or evidence files where redistribution is permitted;
5. exact evaluation prompts, screened executable output, a cleaned execution record, and a problem-level README.

The TeX documents share [`latex/orbenchcompact.sty`](latex/orbenchcompact.sty): a neutral 10-point academic layout with compact spacing, restrained rules, readable mathematics, and no borrowed publisher branding or class code.

## Repository Layout

```text
.
├── latex/                              # Shared compact document style
├── problems/
│   ├── 01_cyclic_crossdock_service_network_design/
│   ├── 02_event_ordered_continuous_time_replenishment/
│   └── 03_pcl_assortment/
├── output/pdf/                         # Compiled candidate documents
└── SUBMISSION_CHECKLIST.md             # One-response-per-problem upload map
```

## Build the Documents

A current TeX Live installation with `latexmk` is sufficient.

```bash
make pdf-all
```

Individual targets are `pdf-snd`, `pdf-ctirp`, and `pdf-pcl`. Finished PDFs are written to `output/pdf/`.

## Verify the Exact Certificates

The three mechanical checkers use only the Python standard library:

```bash
python3 problems/01_cyclic_crossdock_service_network_design/check_cyclic_crossdock_snd.py
python3 problems/02_event_ordered_continuous_time_replenishment/check_false_feasible.py
python3 problems/03_pcl_assortment/check_assortment.py 2 3 5 6
```

The three reference formulations require Python, Gurobi, and `gurobipy`:

```bash
python3 problems/01_cyclic_crossdock_service_network_design/solve_cyclic_crossdock_snd.py
python3 problems/02_event_ordered_continuous_time_replenishment/solve_ctirp_submission.py \
  problems/02_event_ordered_continuous_time_replenishment/instance.csv
python3 problems/03_pcl_assortment/solve_pcl_structured.py
```

## Evidence Standard

A candidate enters this repository only when the intended model has an independent oracle and the generated-model error has an objective gap or feasibility witness. A solver status alone is not treated as evidence of correctness.

- The SND checker independently generates time-feasible shipment paths, enumerates all 256 service-leg designs, and verifies five structural cases (the correct model plus four ablations).
- The replenishment witness proves reference infeasibility analytically while the generated formulation reports an optimum.
- The PCL instance is exhaustively enumerable: 57 feasible assortments, one unique optimum, and direct probability recomputation.

All three associated-data files use the CSV format requested by the official call.

## Sources and Licensing

New code is released under the [MIT License](LICENSE). Original problem statements and derivative data are released under [CC BY 4.0](LICENSE-DATA.md). The SND instance is original and synthetic; the PCL instance includes an upstream provenance notice and MIT license.

Third-party paper PDFs and benchmark archives are not redistributed. Each problem README links directly to the paper, official artifact, or documentation needed to reproduce the result.

The packages are organized one problem per OR-Bench form response.

Superseded research material is kept outside the public Git history in the local ZIP documented by [`LOCAL_ARCHIVE.md`](LOCAL_ARCHIVE.md).
