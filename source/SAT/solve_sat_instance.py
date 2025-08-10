#!/usr/bin/env python3
"""
SAT-InstanceSolver: Run SAT models (HA/RR) through PySAT (Minisat/Glucose)
or directly in Z3 for RR optimization.
"""

import os
import json
import argparse
import pathlib
from threading import Timer
from typing import List

import jsbeautifier
import time
import math
import re
import z3
from pysat.formula import CNF
from pysat.solvers import Minisat22, Glucose42

# Import SAT models
from sat_model_ha import SATModelHA
from sat_model_rr import SATModelRR

from sat_encodings import at_most_k

def optimise_rr(n: int,
                       rr_tuple: tuple,
                       timeout_sec: int = 300) -> tuple[int | None, z3.ModelRef | None]:
    """
    Minimize max-imbalance via binary search using weekly home literals H.
    rr_tuple is (solver, pos, swap, Home, Away, H).
    For a bound B, enforce:
        L = ceil((W-B)/2)  <=  home_count[t]  <=  U = floor((W+B)/2)
    encoded via at_most_k on H[t,*] and on ~H[t,*].
    """
    from math import ceil, floor

    solver, pos, swap, Home, Away, H = rr_tuple
    assert H is not None, "SATModelRR must be built with optimization=True to get H"

    W = n - 1
    base_assertions = list(solver.assertions())

    lo, hi = 0, W
    best_val, best_model = None, None
    start_time = time.time()

    while lo <= hi:
        # budget
        elapsed = time.time() - start_time
        remaining = timeout_sec - elapsed
        if remaining <= 0:
            break

        mid = (lo + hi) // 2
        L = ceil((W - mid) / 2)
        U = floor((W + mid) / 2)

        s = z3.Solver()
        s.set("timeout", int(remaining * 1000))
        s.add(base_assertions)

        # per–team bounds
        for t in range(1, n + 1):
            # sum(H[t,*]) ≤ U
            s.add(*at_most_k(H[t], U, name=f"home_le_t{t}_U{U}"))
            # sum(H[t,*]) ≥ L  ⇔  sum(~H[t,*]) ≤ W-L
            s.add(*at_most_k([z3.Not(h) for h in H[t]], W - L, name=f"home_ge_t{t}_L{L}"))

        res = s.check()
        if res == z3.sat:
            best_val = mid
            best_model = s.model()
            hi = mid - 1
        elif res == z3.unsat:
            lo = mid + 1
        else:
            break

    return best_val, best_model


def parse_variable_mappings(dimacs_lines: list[str]) -> dict[str, int]:
    """
    Build a map from variable name (as created in Z3) to DIMACS id.
    """
    varmap = {}
    for line in dimacs_lines:
        if line.startswith('c '):
            parts = line.strip().split()
            if len(parts) >= 3:
                dimacs_id = int(parts[1])
                var_name = parts[2]
                varmap[var_name] = dimacs_id
    return varmap


# ----------------------------------------------------------
# Utility: convert Z3 constraints to DIMACS CNF
# ----------------------------------------------------------
def z3solver_to_dimacs(solver: z3.Solver):
    """
    Convert a Z3 solver's assertions into a CNF usable by PySAT.
    """
    goal = z3.Goal()
    goal.add(solver.assertions())

    tactic = z3.Then(z3.Tactic("simplify"), z3.Tactic("tseitin-cnf"))

    result = tactic(goal)

    if len(result) == 0:
        raise ValueError("Z3 did not produce any CNF clauses.")

    dimacs_str = result[0].dimacs()
    dimacs_lines = dimacs_str.splitlines()

    # Build varmap from DIMACS comments
    varmap = parse_variable_mappings(dimacs_lines)

    # Build CNF object from DIMACS string
    return CNF(from_string=dimacs_str), varmap

# ----------------------------------------------------------
# Parse decision output from PySAT
# ----------------------------------------------------------
def parse_decision_output(model_values: list[int],
                          model: str,
                          n: int,
                          varmap: dict[str, int],
                          Home=None,
                          Away=None) -> list[list[list[int]]]:
    """
    Parse PySAT model (list of true literals) into a schedule matrix.
    Returns: schedule[p][w] = [home_team, away_team].
    """
    model_set = set(v for v in model_values if v > 0)
    W = n - 1
    P = n // 2
    schedule = [[0 for _ in range(W)] for _ in range(P)]

    if model == 'ha':
        # For each period and week, find exactly one home and one away
        for p in range(P):
            for w in range(W):
                home_team = None
                away_team = None
                for t in range(n):
                    hid = varmap.get(f"H_{p+1}_{w+1}_{t+1}")
                    aid = varmap.get(f"A_{p+1}_{w+1}_{t+1}")
                    if hid is not None and hid in model_set and home_team is None:
                        home_team = t + 1
                    if aid is not None and aid in model_set and away_team is None:
                        away_team = t + 1
                    if home_team is not None and away_team is not None:
                        break
                if home_team is None or away_team is None:
                    raise RuntimeError(f"Missing assignment for period={p+1}, week={w+1}")
                schedule[p][w] = [home_team, away_team]

    elif model == 'rr':
        for p in range(P):
            for w in range(W):
                chosen_k = None
                for k in range(P):
                    lit_id = varmap.get(f"pos_{w+1}_{p+1}_{k+1}")
                    if lit_id is not None and lit_id in model_set:
                        chosen_k = k
                        break
                if chosen_k is None:
                    raise RuntimeError(f"No true pos var for week={w+1}, period={p+1}")
                schedule[p][w] = [Home[w][chosen_k], Away[w][chosen_k]]

    return schedule


# ----------------------------------------------------------
# Parse optimization output from Z3 Optimize
# ----------------------------------------------------------
def parse_optimization_output(z3_model: z3.ModelRef,
                              pos_vars: list[list[list[z3.BoolRef]]],
                              swap_vars: list[list[z3.BoolRef]],
                              Home: list[list[int]],
                              Away: list[list[int]]) -> list[list[list[int]]]:
    """
    Extract the schedule from a Z3 model
    """
    W = len(pos_vars)       # number of weeks
    P = len(pos_vars[0])    # number of periods per week
    schedule = []

    for p in range(P):
        period_matches = []
        for w in range(W):
            # find which match index k is selected
            chosen_k = None
            for k in range(P):
                if z3.is_true(z3_model.eval(pos_vars[w][p][k])):
                    chosen_k = k
                    break
            if chosen_k is None:
                raise RuntimeError(f"No valid match found for week {w+1}, period {p+1}")

            # check if swap is active
            swapped = z3.is_true(z3_model.eval(swap_vars[w][p]))
            if swapped:
                home, away = Away[w][chosen_k], Home[w][chosen_k]
            else:
                home, away = Home[w][chosen_k], Away[w][chosen_k]

            period_matches.append([home, away])
        schedule.append(period_matches)
    return schedule

# ----------------------------------------------------------
# Core solving routine
# ----------------------------------------------------------
def solve_sat_instance(model, solver_name, n_value, use_symmetry_breaking, optimization, test_name, timeout=300):
    start_time = time.time()

    # Optimization mode only valid for RR
    if optimization:
        if model.lower() != "rr":
            raise ValueError("Optimization mode is only supported for RR model.")

        # Build RR with optimization to obtain H literals
        rr_tuple = SATModelRR.build_solver(
            n_value,
            optimization=True,
            use_symmetry_breaking_constraints=use_symmetry_breaking
        )
        base_solver, pos_vars, swap_vars, Home, Away, H = rr_tuple

        start_time = time.time()
        opt_val, opt_model = optimise_rr(n_value, rr_tuple, timeout)
        elapsed_time = time.time() - start_time

        if opt_model is not None:
            solution = parse_optimization_output(opt_model, pos_vars, swap_vars, Home, Away)
            optimal = True
        else:
            solution = []
            optimal = False

        return {
            test_name.lower(): {
                "time": math.floor(elapsed_time) if solution else timeout,
                "optimal": optimal,
                "obj": opt_val if opt_val is not None else "None",
                "sol": solution,
            }
        }


    # Decision mode (HA or RR)
    if model.lower() == "ha":
        solver = SATModelHA.build_solver(n_value, use_symmetry_breaking)
        # Initialize RR-specific variables to None for consistency
        pos, Home, Away = None, None, None
    elif model.lower() == "rr":
        solver, pos, _, Home, Away, _ = SATModelRR.build_solver(
            n_value,
            optimization=False,
            use_symmetry_breaking_constraints=use_symmetry_breaking
        )
        
    else:
        raise ValueError(f"Unknown model: {model}")

    # Convert to CNF
    cnf, varmap = z3solver_to_dimacs(solver)

    # Choose backend
    pysat_cls = Minisat22 if solver_name.lower() == "minisat" else Glucose42

    with pysat_cls(bootstrap_with=cnf.clauses) as sat_solver:
        # Create a timer to interrupt after timeout seconds
        def interrupt_solver(s):
            s.interrupt()

        timer = Timer(timeout, interrupt_solver, [sat_solver])
        timer.start()

        # Use solve_limited with expect_interrupt=True
        sat = sat_solver.solve_limited(expect_interrupt=True)
        model_values = sat_solver.get_model() if sat else None

        # Cancel timer if finished early
        timer.cancel()

    elapsed_time = time.time() - start_time

    if model_values is None:
        # UNSAT
        return {
            test_name.lower(): {
                "time": timeout,
                "optimal": False,
                "obj": "None",
                "sol": [],
            }
        }

    parsed_solution = parse_decision_output(
        model_values=model_values,
        model=model.lower(),
        n=n_value,
        Home=Home,
        Away=Away,
        varmap=varmap
    )

    return {
        test_name.lower(): {
            "time": math.floor(elapsed_time),
            "optimal": True,
            "obj": "None",
            "sol": parsed_solution,
        }
    }

# ----------------------------------------------------------
# CLI Entry point
# ----------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="SAT-InstanceSolver: run SAT models with Minisat or Glucose")
    parser.add_argument("model", choices=["ha", "rr"], help="Use HA or RR encoding")
    parser.add_argument("solver_name", choices=["minisat", "glucose"], help="Underlying SAT solver")
    parser.add_argument("instance_path", type=pathlib.Path, help="Path to .dzn instance")
    parser.add_argument("use_symmetry_breaking", type=lambda x: x.lower() == 'true',
                        help="True/False for HA symmetry breaking")
    parser.add_argument("optimization", type=lambda x: x.lower() == 'true',
                        help="True/False for optimization (RR only)")
    parser.add_argument("test_name", type=str, help="Name for the test (used as JSON key)")
    parser.add_argument("-t", "--timeout", type=int, default=300, help="Timeout in seconds")
    args = parser.parse_args()

    # Extract n from instance
    with open(args.instance_path, 'r') as f:
        content = f.read()
        match = re.search(r'n\s*=\s*(\d+);', content)
        if not match:
            raise ValueError("Could not find 'n' in instance file.")
        n_value = int(match.group(1))

    # Solve
    result = solve_sat_instance(
        args.model,
        args.solver_name,
        n_value,
        args.use_symmetry_breaking,
        args.optimization,
        args.test_name,
        args.timeout
    )

    # Save JSON
    res_dir = pathlib.Path(__file__).parent.parent.parent / "res" / "SAT"
    os.makedirs(res_dir, exist_ok=True)
    instance_id = os.path.splitext(os.path.basename(args.instance_path))[0]
    res_path = os.path.join(res_dir, f"{instance_id}.json")

    data = {}
    if os.path.exists(res_path):
        with open(res_path, 'r') as f:
            data = json.load(f)

    data.update(result)

    opts = jsbeautifier.default_options()
    opts.keep_array_indentation = True
    beautified = jsbeautifier.beautify(json.dumps(data), opts)

    with open(res_path, 'w') as f:
        f.write(beautified)

    print(f"  Result saved to: {res_path}")
    return 0

if __name__ == "__main__":
    main()
