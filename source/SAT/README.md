# Propositional SAT

This folder contains SAT encodings of the STS problem. Z3 is used to build the formulas which are then solved either with PySAT (Minisat/Glucose) or directly with Z3 for optimization.

Two encodings are available:

- **Home/Away (HA)** – variables represent home/away assignments in each slot.
- **Round Robin (RR)** – uses permutation variables to generate matchups, with an optional optimization objective.

## Configured experiments

`solve_sat_all.py` lists the following experiment configurations:

- `ha-minisat` and `ha-glucose` – HA encoding solved with Minisat or Glucose.
- `ha-nosymm-minisat` and `ha-nosymm-glucose` – HA without symmetry breaking.
- `rr-minisat` and `rr-glucose` – RR decision variant.
- `rr-opt-z3` – RR optimization via the Z3 solver.

## Running the tests

1. Launch all experiments for every instance:
   ```bash
   python solve_sat_all.py
   ```
   Results are produced in `../../res/SAT/`.
2. Solve a specific instance manually:
   ```bash
   python solve_sat_instance.py <ha|rr> <minisat|glucose> <instance.txt> <use_symmetry_breaking> <optimization> <name>
   ```
   For the optimization experiment (`rr-opt-z3`) the solver parameter is ignored.
3. Verify the generated schedules:
   ```bash
   python ../../solution_checker.py ../../res/SAT
   ```
