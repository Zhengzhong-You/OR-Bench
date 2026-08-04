# OR-Bench Submission Checklist

Submit **one Google Form response per problem**. Each response uses the same package template but a different domain classification. The Form's main-material field accepts at most five files; the business document and solver each have their own separate upload field.

## Shared answers

- Name: Zhengzhong You
- Email: enter the address shown by the signed-in Google account
- Affiliation: University of Florida
- Model type: Mixed-integer linear program
- Rights: select the confirmation checkbox; the package-level source and license review is complete
- Co-authorship interest: Yes

## 1. Cyclic Freight Service Design with Cross-Dock Handling

- Form domain: Supply chain and logistics
- Source field: Original synthetic problem. Related methods: https://doi.org/10.3390/pr10071373 and https://developers.google.com/optimization/service/shipping/network_design
- Business upload: `problems/01_cyclic_crossdock_service_network_design/business_description.docx`
- Solver upload: `problems/01_cyclic_crossdock_service_network_design/solve_cyclic_crossdock_snd.py`
- Main files (5): `output/pdf/cyclic_crossdock_service_network_design.pdf`; `instance.csv`; `check_cyclic_crossdock_snd.py`; `evidence_summary.json`; `generated_run_manifest.json`

## 2. Event-Ordered Continuous-Time Tank Replenishment

- Form domain: Inventory management
- Source field: Original synthetic challenge; related literature: https://doi.org/10.1287/trsc.2019.0902 and https://doi.org/10.1016/j.cor.2024.106883
- Business upload: `problems/02_event_ordered_continuous_time_replenishment/business_description.docx`
- Solver upload: `problems/02_event_ordered_continuous_time_replenishment/solve_ctirp_submission.py`
- Main files (5): `output/pdf/event_ordered_continuous_time_replenishment.pdf`; `instance.csv`; `check_false_feasible.py`; `evidence_summary.json`; `generated_run_manifest.json`

## 3. Limited-Display PCL Assortment Planning

- Form domain: Revenue management and pricing
- Source field: Paper https://doi.org/10.1287/ijoc.2024.0830; MIT-licensed data artifact https://doi.org/10.1287/ijoc.2024.0830.cd; repository https://github.com/INFORMSJoC/2024.0830; commit a3920679d4725ec714af29d24034a5d6d9db6b8f
- Business upload: `problems/03_pcl_assortment/business_description.docx`
- Solver upload: `problems/03_pcl_assortment/solve_pcl_structured.py`
- Main files (5): `output/pdf/pcl_assortment.pdf`; `instance.csv` (contains the complete upstream MIT notice); `check_assortment.py`; `evidence_summary.json`; `generated_run_manifest.json`

## Final gate for every response

1. Confirm the short title matches the PDF, business document, instance, and evidence file.
2. Run the problem checker and reference solver from a clean checkout.
3. Confirm every uploaded file is below 10 MB and uses a file type accepted by the live Form.
4. Confirm the public package URL appears in the precise PDF: https://github.com/Zhengzhong-You/OR-Bench
5. Submit, save the emailed copy, and record the response timestamp.
