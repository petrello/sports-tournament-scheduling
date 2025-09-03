# Mixed Integer Programming (MIP)

The models in this folder solve the STS problem using PuLP. Two formulations are implemented:

- **Home/Away (HA)** – directly assigns home and away teams to slots.
- **Round Robin (RR)** – uses position variables similar to the circle method, with an optional objective to minimize imbalance.

## Configured experiments

`solve_mip_all.py` defines a set of experiments that combine the model type with different solvers and options:

- `ha-glpk`, `ha-highs` – HA model solved with GLPK or HiGHS.
- `ha-nosymm-glpk`, `ha-nosymm-highs` – HA model without symmetry breaking constraints.
- `rr-glpk`, `rr-highs` – RR decision variant.
- `rr-opt-glpk`, `rr-opt-highs` – RR optimization variant.

## Running the tests

1. Run all experiments on every instance:
   ```bash
   python solve_mip_all.py
   ```
   Output files are stored in `../../res/MIP/`.
2. To solve a single instance:
   ```bash
   python solve_mip_instance.py <ha|rr> <glpk|highs> <instance.txt> <use_symmetry_breaking> <optimization> <name>
   ```
3. Validate produced solutions using:
   ```bash
   python ../../solution_checker.py ../../res/MIP
   ```
