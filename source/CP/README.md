# Constraint Programming (CP)

This directory contains MiniZinc models to solve the STS problem using constraint programming. Two modelling styles are provided:

- **Home/Away (HA)**: games are scheduled by directly assigning home and away teams.
- **Round Robin (RR)**: uses position variables to generate a schedule via the circle method, optionally minimizing the home/away imbalance.

## Configured experiments

`solve_cp_all.py` enumerates a set of experiments defined in `EXPERIMENTS_CONFIG`. Each experiment selects a model and solver:

- `ha-gecode` – `cp_model_ha.mzn` solved with Gecode.
- `ha-nosymm-gecode` – `cp_model_ha_no_symm.mzn` solved with Gecode.
- `ha-noglob-gecode` – `cp_model_ha_no_global.mzn` solved with Gecode.
- `ha-chuffed` – same as `ha-gecode` but using Chuffed.
- `ha-nosymm-chuffed` – HA without symmetry breaking and using Chuffed.
- `ha-noglob-chuffed` – HA without global constraints using Chuffed.
- `ha-restart-gecode` – HA model with restart strategy in Gecode.
- `ha-nosymm-restart-gecode` – HA without symmetry breaking with restart.
- `ha-noglob-restart-gecode` – HA without globals with restart.
- `rr-gecode` – round-robin model solved with Gecode.
- `rr-chuffed` – round-robin model solved with Chuffed.
- `rr-opt-gecode` – optimization version of the RR model with Gecode.
- `rr-gecode-restart` – RR model with restart.
- `rr-opt-gecode-restart` – optimization RR model with restart.

## Running the tests

1. Execute all experiments on the provided `.dzn` instances:
   ```bash
   python solve_cp_all.py
   ```
   Results are written to `../../res/CP/` as JSON files.
2. To solve a single instance manually:
   ```bash
   python solve_cp_instance.py <instance.dzn> <model> <solver> <optimization> <name>
   ```
3. Solutions can be checked with:
   ```bash
   python ../../solution_checker.py ../../res/CP
   ```
