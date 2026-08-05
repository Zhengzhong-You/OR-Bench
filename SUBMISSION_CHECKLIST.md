# OR-Bench Submission Checklist

Submit **one Google Form response per problem**. Each response uses the same package template but a different domain classification. The Form's main-material field accepts at most five files; the business document and solver each have their own separate upload field.

## Official benchmark reference

- Official call: https://connect.informs.org/discussion/call-for-contributions-a-community-benchmark-for-llms-on-optimization-modeling
- Contributor Form: https://forms.gle/SYQRNo7jLzBqBuXc8
- Official example repository: https://github.com/CoraLiang01/OR-Bench
- The repository contained 41 problem instances when checked on August 4, 2026. Each row is one problem instance with a precise description, domain, data address, optimal value, and optimal solution. Thirteen rows also contained a vague business-level description.
- The call requests one precise statement and its data, one ground-truth formulation with working solver code, and one vague business description for each problem. It does not require multiple numerical examples inside one contribution.
- Our two candidates should therefore remain two separate Form responses. Each response should present one canonical, mechanically verifiable instance with a complete operational story.

## Shared answers

- Name: Zhengzhong Ricky You
- Email: ricky.you.or@gmail.com
- Affiliation: Tsinghua University
- Model type: Mixed-integer linear program
- Rights: select the confirmation checkbox; the package-level source and license review is complete
- Co-authorship interest: Yes

## 1. Event Consistency in Continuous-Time Inventory Routing

- Form domain: Inventory management
- Source field: Reference formulation adapted from Wang et al. (2025), https://doi.org/10.1016/j.cor.2024.106883; continuous-time inventory-routing context from Lagos et al. (2020), https://doi.org/10.1287/trsc.2019.0902. The one-customer instance is original and synthetic.
- Business upload: `problems/01_event_ordered_continuous_time_replenishment/business_description.docx`
- Solver upload: `problems/01_event_ordered_continuous_time_replenishment/solve_ctirp_submission.py`
- Main files (2): `output/pdf/event_ordered_continuous_time_replenishment.pdf`; `problems/01_event_ordered_continuous_time_replenishment/instance.csv`

## 2. Pair-State Consistency in Paired Combinatorial Logit Assortment Planning

- Form domain: Revenue management and pricing
- Source field: Adapted from Feng, Che, and Chen (2026), https://doi.org/10.1287/ijoc.2024.0830. The six-product synthetic instance is derived from the corresponding MIT-licensed code and data repository, https://doi.org/10.1287/ijoc.2024.0830.cd; https://github.com/INFORMSJoC/2024.0830 at commit a3920679d4725ec714af29d24034a5d6d9db6b8f.
- Business upload: `problems/02_pcl_assortment/business_description.docx`
- Solver upload: `problems/02_pcl_assortment/solve_pcl_structured.py`
- Main files (2): `output/pdf/pcl_assortment.pdf`; `problems/02_pcl_assortment/instance.csv` (contains the complete upstream MIT notice)

## Final gate for every response

1. Confirm the title agrees wherever it is stated and that the PDF, business document, instance, and solver identify the same problem.
2. Run the reference solver with `--verify` from a clean checkout.
3. Confirm every uploaded file is below 10 MB and uses a file type accepted by the live Form.
4. Confirm the public package URL appears in the precise PDF: https://github.com/Zhengzhong-You/OR-Bench
5. Submit, save the emailed copy, and record the response timestamp.
