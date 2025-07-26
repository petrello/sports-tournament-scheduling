#!/usr/bin/env python3
"""
SAT-InstanceSolver: Run SAT models (HA/RR) through PySAT solvers (Minisat22/Glucose42)
This script mirrors the SMT version but works in SAT paradigm using DIMACS export.
"""

import os
import json
import argparse
import pathlib
import jsbeautifier
import time
import math
import re
from pysat.formula import CNF
from pysat.solvers import Minisat22, Glucose42
import z3

# Import SAT models
from sat_model_ha import SATModelHA
from sat_model_rr import SATModelRR


def parse_variable_mappings(dimacs_lines):
    """
    Parse DIMACS comment lines to extract mapping from variable indices to original names.
    Expected comment format (from z3 dimacs): c [<index>] <name>
    """
    mapping = {}
    for line in dimacs_lines:
        if line.startswith('c'):
            # Example: c [12] H_1_3
            m = re.match(r"c\s*\[(\d+)\]\s*(\S+)", line)
            if m:
                idx, name = m.groups()
                mapping[int(idx)] = name
    return mapping


def parse_decision_model(model_list, var_mappings, model_type, n, A=None, B=None):
    """
    Parse the model (list of integers from PySAT) into a schedule.
    For HA we rebuild from H_i_j and A_i_j variables.
    For RR we rebuild from pos_i_j variables referencing A and B.
    """
    if model_list is None:
        return None

    # Convert model list (positive = True, negative = False) to assignment dict
    assignment = {}
    for lit in model_list:
        v = abs(lit)
        val = (lit > 0)
        if v in var_mappings:
            assignment[var_mappings[v]] = val

    W, P = n - 1, n // 2
    schedule = []

    if model_type == 'ha':
        for p in range(P):
            row = []
            for w in range(W):
                h_name = f"H_{p+1}_{w+1}"
                a_name = f"A_{p+1}_{w+1}"
                h_val = 1 if assignment.get(h_name, False) else 0
                a_val = 1 if assignment.get(a_name, False) else 0
                row.append([h_val, a_val])
            schedule.append(row)

    elif model_type == 'rr':
        for p in range(P):
            row = []
            for w in range(W):
                # find pos_k variable that is true
                pos_k = None
                for k in range(1, len(A[w]) + 1):
                    name = f"pos_{w+1}_{p+1}_{k}" if f"pos_{w+1}_{p+1}_{k}" in assignment else f"pos_{w+1}_{p+1}"
                    # support both encoding styles: pos_w_p or pos_w_p_k
                    if assignment.get(name, False):
                        pos_k = k-1 if '_' in name and name.count('_')==3 else 0
                        break
                if pos_k is None:
                    pos_k = 0
                row.append([A[w][pos_k], B[w][pos_k]])
            schedule.append(row)

    return schedule


def solve_sat_instance(model, solver_name, n_value, use_symmetry_breaking, optimization, test_name, timeout=300):
    """
    Main solver function for SAT. Build model, export DIMACS, solve via PySAT.
    """
    start_time = time.time()

    # Build solver for the chosen model
    if model.lower() == "rr":
        solver, pos_vars, swap_vars, A, B, obj_var = SATModelRR.build_solver(n_value, optimization)
    elif model.lower() == "ha":
        solver = SATModelHA.build_solver(n_value, {}, use_symmetry_breaking, "tseitin")
        pos_vars, swap_vars, A, B, obj_var = None, None, None, None, None
    else:
        raise ValueError(f"Unknown model: {model}")

    # Export to DIMACS
    goal = z3.Goal()
    goal.add(solver.assertions())
    tactic = z3.Then(z3.Tactic("simplify"), z3.Tactic("tseitin-cnf"))
    dimacs_goal = tactic(goal)[0]
    dimacs_string = dimacs_goal.dimacs()
    var_mappings = parse_variable_mappings(dimacs_string.splitlines())
    cnf = CNF(from_string=dimacs_string)

    # Choose PySAT solver
    pysat_solver_cls = Minisat22 if solver_name.lower() == "minisat" else Glucose42

    solution, obj, optimal = None, None, False

    try:
        # Decision problems only, optimization requires custom approach (not implemented in SAT)
        with pysat_solver_cls(bootstrap_with=cnf.clauses) as sat_solver:
            satisfiable = sat_solver.solve_limited(expect_interrupt=True, conf_budget=timeout*1000)
            elapsed_time = time.time() - start_time
            if satisfiable:
                model_list = sat_solver.get_model()
                schedule = parse_decision_model(model_list, var_mappings, model.lower(), n_value, A, B)
                solution = schedule
                optimal = True  # SAT solved implies a valid schedule
            else:
                solution = None
                optimal = False
    except Exception as e:
        elapsed_time = timeout
        raise Exception(f"An unexpected error occurred for {test_name}: {e}")

    return {
        test_name.lower(): {
            "time": math.floor(elapsed_time) if solution is not None else timeout,
            "optimal": optimal,
            "obj": obj if obj is not None else "None",
            "sol": solution if solution is not None else [],
        }
    }


def main():
    parser = argparse.ArgumentParser(description="SAT-InstanceSolver: run SAT models with PySAT solvers")

    parser.add_argument("model", help="Solve the problem with HA or RR method", choices=["ha", "rr"])
    parser.add_argument("solver_name", help="SAT solver to use", choices=["minisat", "glucose"])
    parser.add_argument(
        "instance_path",
        help="Path to the file instance to test",
        type=pathlib.Path
    )
    parser.add_argument("use_symmetry_breaking", help="True/False to add symmetry breaking constraints (for HA model)",
                        type=lambda x: x.lower() == 'true')
    parser.add_argument("optimization", help="True/False for optimization mode (for RR model)",
                        type=lambda x: x.lower() == 'true')
    parser.add_argument("test_name", help="Name for the test (used as JSON key)", type=str)
    parser.add_argument("-t", "--timeout", help="Timeout in seconds (default: 300)", type=int, default=300)

    args = parser.parse_args()

    # Extract n_value from the instance file
    with open(args.instance_path, 'r') as f:
        content = f.read()
        match = re.search(r'n\s*=\s*(\d+);', content)
        if not match:
            raise ValueError("Could not find n value in instance file")
        n_value = int(match.group(1))

    result = solve_sat_instance(
        args.model,
        args.solver_name,
        n_value,
        args.use_symmetry_breaking,
        args.optimization,
        args.test_name,
        args.timeout
    )

    # Save result JSON
    res_dir = pathlib.Path(__file__).parent.parent.parent / 'res' / 'SAT'
    os.makedirs(res_dir, exist_ok=True)

    instance_id = os.path.splitext(os.path.basename(args.instance_path))[0]
    res_path = os.path.join(res_dir, f'{instance_id}.json')

    # Load previous results if present
    data = {}
    if os.path.exists(res_path):
        with open(res_path, 'r') as f:
            data = json.load(f)

    data.update(result)

    # Beautify JSON
    opts = jsbeautifier.default_options()
    opts.keep_array_indentation = True
    beautified_json = jsbeautifier.beautify(json.dumps(data), opts)

    with open(res_path, 'w') as f:
        f.write(beautified_json)

    print(f"  Result saved to: {res_path}")
    return 0


if __name__ == "__main__":
    main()
