# Satisfiability Modulo Theories (SMT)

The SMT encodings use the Z3 or CVC5 solvers to model the STS problem directly at the theory level.

Two main encodings are implemented:

- **Home/Away (HA)** – integer variables denote the home and away team for each slot.
- **Round Robin (RR)** – permutation based approach with an optional optimization objective to balance the schedule.

## Configured experiments

`solve_smt_all.py` defines a dictionary of experiments combining the encoding and solver:

- `ha-z3` and `ha-cvc5` – HA encoding solved with Z3 or CVC5.
- `ha-nosymm-z3` and `ha-nosymm-cvc5` – HA without symmetry breaking constraints.
- `rr-z3` and `rr-cvc5` – RR decision variant.
- `rr-opt-z3` – RR optimization with Z3.

## Running the tests

1. Run every experiment over all SMT instances:
   ```bash
   python solve_smt_all.py
   ```
   Results are saved to `../../res/SMT/`.
2. Execute a single instance:
   ```bash
   python solve_smt_instance.py <ha|rr> <z3|cvc5> <instance.txt> <use_symmetry_breaking> <optimization> <name>
   ```
3. Use the solution checker to validate outputs:
   ```bash
   python ../../solution_checker.py ../../res/SMT
   ```
