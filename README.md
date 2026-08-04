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

Every problem folder now contains exactly five files:

1. `README.md` — the compact navigation, evidence, source, and command record;
2. `business_description.docx` — the Form-ready business-level-description upload;
3. `instance.csv` — the associated data and provenance;
4. one Python solver — the reference formulation and its built-in verification;
5. one self-contained LaTeX source — the editable precise problem document, compilable without a repository-specific style file.

Compiled PDFs are kept together in `output/pdf/`, outside the problem folders. Detailed screening prompts, raw generated programs, execution logs, and superseded checkers are preserved in the local research archive instead of cluttering the submission packages.

Each TeX document embeds the same neutral 10-point academic layout with compact spacing, restrained rules, readable mathematics, and no borrowed publisher branding or class code. This small duplication makes every paper independently compilable after download or Form review.

## Repository Layout

```text
.
├── latex/                              # Reference copy of the embedded layout
├── problems/
│   ├── 01_cyclic_crossdock_service_network_design/
│   ├── 02_event_ordered_continuous_time_replenishment/
│   └── 03_pcl_assortment/
├── output/pdf/                         # Compiled candidate documents
└── SUBMISSION_CHECKLIST.md             # One-response-per-problem upload map
```

## Build the Documents

A current TeX Live installation with `latexmk` is sufficient.

The three standalone sources are also compatible with Texifier's built-in TexpadTeX LIVE typesetter; Auto-Sense keeps them in LIVE mode.

```bash
make pdf-all
```

Individual targets are `pdf-snd`, `pdf-ctirp`, and `pdf-pcl`. Finished PDFs are written to `output/pdf/`.

## Verify the Exact Certificates

Each solver has one `--verify` command that checks both the reference formulation and its compact failure certificate:

```bash
python3 problems/01_cyclic_crossdock_service_network_design/solve_cyclic_crossdock_snd.py --verify
python3 problems/02_event_ordered_continuous_time_replenishment/solve_ctirp_submission.py \
  problems/02_event_ordered_continuous_time_replenishment/instance.csv --verify
python3 problems/03_pcl_assortment/solve_pcl_structured.py --verify
```

The solvers require Python, Gurobi, and `gurobipy`.

## Evidence Standard

A candidate enters this repository only when the intended model has an exact reproducible certificate and the generated-model error has an objective gap or feasibility witness. A solver status alone is not treated as evidence of correctness.

- The SND solver verifies the correct model plus four structural ablations, including handling-time and fleet-count failures.
- The replenishment solver proves reference infeasibility analytically: all visits occur at time 5, while required delivery exceeds safe capacity.
- The PCL solver enumerates all 57 feasible assortments, proves a unique optimum, and directly recomputes the failed selection.

The public README and precise PDF retain the decision-relevant failure evidence. Raw model-screening artifacts remain available in the local archive and prior Git history for audit.

All three associated-data files use the CSV format requested by the official call.

## Sources and Licensing

New code is released under the [MIT License](LICENSE). Original problem statements and derivative data are released under [CC BY 4.0](LICENSE-DATA.md). The SND instance is original and synthetic; the PCL instance includes an upstream provenance notice and MIT license.

Third-party paper PDFs and benchmark archives are not redistributed. Each problem README links directly to the paper, official artifact, or documentation needed to reproduce the result.

The packages are organized one problem per OR-Bench form response.

Superseded research material is kept outside the public Git history in the local ZIP documented by [`LOCAL_ARCHIVE.md`](LOCAL_ARCHIVE.md).
