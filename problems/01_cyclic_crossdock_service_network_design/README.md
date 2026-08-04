# Cyclic Freight Service Design with Cross-Dock Handling

Freight must follow a time-feasible itinerary while the repeated weekly services remain coverable by the physical tractor fleet. A modulo-week flow can look balanced yet require more simultaneous tractors than are available.

| Submission fact | Value |
|---|---|
| Google Form domain | Supply chain and logistics |
| Model type | Mixed-integer linear program |
| Ground truth | Direct path `F4`; open `F4,R4`; objective `15`; one tractor |
| Observed failure | Generated models either duplicate destination demand or accept a design requiring three tractors when only two exist |
| Scope | Recorded frontier high-reasoning controls solve it; lower/smaller configurations fail, so this is the third-priority submission |

## The five files

| File | Purpose |
|---|---|
| `README.md` | Navigation, result, evidence, sources, and commands |
| `business_description.docx` | Business-level description for the Form's dedicated upload |
| `instance.csv` | Original synthetic periodic time-space data |
| `solve_cyclic_crossdock_snd.py` | Gurobi formulation plus built-in five-case verification |
| `cyclic_crossdock_service_network_design.tex` | Self-contained, directly compilable source of the precise problem document |

The compiled document is centralized at `output/pdf/cyclic_crossdock_service_network_design.pdf`.

## Verify

```bash
python3 problems/01_cyclic_crossdock_service_network_design/solve_cyclic_crossdock_snd.py --verify
```

The verification recovers the correct optimum and four diagnostic ablations, including the handling-time and fleet-count failure certificates.

## Sources and rights

The statement, numerical instance, and code were created independently. Periodic time-space service design and fleet balance are motivated by Gao, Jin, and Diao (2022), [doi:10.3390/pr10071373](https://doi.org/10.3390/pr10071373). Cross-dock semantics are informed by [Google's Shipping Network Design documentation](https://developers.google.com/optimization/service/shipping/network_design). New code is MIT licensed; the original statement and data are CC BY 4.0.

Public package: https://github.com/Zhengzhong-You/OR-Bench
