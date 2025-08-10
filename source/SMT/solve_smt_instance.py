#!/usr/bin/env python3
"""
SMT-InstanceSolver: Run SMT models (HA/RR) through Z3 or CVC5 CLI
"""

import os
import json
import argparse
import pathlib
import subprocess
import jsbeautifier
import time
import math
import re
import z3

# Import SMT models
from smt_model_ha import SMTModelHA
from smt_model_rr import SMTModelRR


def parse_decision_output(output_text: str, model: str, n: int, A=None, B=None):
    """
    Parse the text output from a CLI solver (z3/cvc5) for decision problems.
    It reconstructs the schedule from the variable assignments.
    """
    # Check if the problem was satisfiable (for CVC5, while Z3 would throw an error)
    out_lower = output_text.lower()
    if "unsat" in out_lower or "sat" not in out_lower:
        print("  The instance is UNSATISFIABLE")
        return None

    # Parse all model variable assignments from the solver's output
    values = {}
    # This regex captures variable names and their integer values
    for match in re.finditer(r"\(define-fun\s+(\S+)\s+\(\)\s+\S+\s+([^)]+)\)", output_text):
        var, val_str = match.groups()
        values[var] = int(val_str.strip())

    W, P = n - 1, n // 2
    schedule = []

    # Reconstruct the schedule based on the model used
    if model == 'ha':
        for p in range(P):
            row = []
            for w in range(W):
                h_var, a_var = f"H_{p + 1}_{w + 1}", f"A_{p + 1}_{w + 1}"
                row.append([values[h_var], values[a_var]])
            schedule.append(row)

    elif model == 'rr':
        for p in range(P):
            row = []
            for w in range(W):
                pos_var = f"pos_{w + 1}_{p + 1}"
                k = values[pos_var] - 1
                row.append([A[w][k], B[w][k]])
            schedule.append(row)

    return schedule


def parse_optimization_output(z3_model, pos_vars, swap_vars, A, B, obj_var):
    """
    Parse a Z3 model object from the Python API for RR optimization problems.
    It extracts the schedule and the objective value.
    """
    # Extract the objective value from the model
    obj_value = z3_model.eval(obj_var).as_long()

    W, P = len(pos_vars), len(pos_vars[0])
    schedule = []

    # Reconstruct the schedule by evaluating variables in the Z3 model
    for p in range(P):
        row = []
        for w in range(W):
            # Get the value for the position variable 'pos'
            k = z3_model.eval(pos_vars[w][p]).as_long() - 1
            # Check if the 'swap' variable is true
            is_swapped = z3.is_true(z3_model.eval(swap_vars[w][p]))

            home, away = (B[w][k], A[w][k]) if is_swapped else (A[w][k], B[w][k])
            row.append([home, away])
        schedule.append(row)

    return schedule, obj_value

def solve_smt_instance(model, solver_name, n_value, use_symmetry_breaking, optimization, test_name, timeout=300):
    """
    Main solver function. It orchestrates the solving process by choosing
    between the Python API (for optimization) and a CLI solver (for decision).
    """
    # --- 1. Build the appropriate solver from the model file ---
    if model.lower() == "rr":
        solver, pos_vars, swap_vars, A, B, obj_var = SMTModelRR.build_solver(n_value, optimization, use_symmetry_breaking)
    elif model.lower() == "ha":
        solver = SMTModelHA.build_solver(n_value, use_symmetry_breaking)
        # Initialize RR-specific variables to None for consistency
        pos_vars, swap_vars, A, B, obj_var = None, None, None, None, None
    else:
        raise ValueError(f"Unknown model: {model}")

    # --- 2. Solve the instance using the correct method ---
    start_time = time.time()
    solution, obj, optimal = None, None, False

    try:
        if optimization:
            # --- API-based execution for RR Optimization ---
            solver.set("timeout", timeout * 1000)  # Z3 timeout is in milliseconds
            status = solver.check()
            elapsed_time = time.time() - start_time

            if status == z3.sat:
                z3_model = solver.model()
                solution, obj = parse_optimization_output(z3_model, pos_vars, swap_vars, A, B, obj_var)
                optimal = (solution is not None and elapsed_time < timeout and obj < 2)


        else:
            # --- CLI-based execution for Decision Problems (HA and RR) ---
            smtlib_str = solver.to_smt2() + "\n(check-sat)\n(get-model)\n"
            cmd = (
                ["z3", "-in"]
                if solver_name.lower() == "z3"
                else ["cvc5", "--lang=smt2", "--produce-models", "--incremental"]
            )

            result = subprocess.run(cmd, input=smtlib_str, text=True, capture_output=True, timeout=timeout)
            elapsed_time = time.time() - start_time

            if result.returncode == 0:
                solution = parse_decision_output(result.stdout, model.lower(), n_value, A, B)
                optimal = (solution is not None and elapsed_time < timeout)

            else:
                if "unsat" in result.stdout.lower():
                    print("  The instance is UNSATISFIABLE")
                else:
                    raise Exception(
                        f"Error occurred while running the {'Z3' if solver_name.lower() == "z3" else 'CVC5'} SMT solver.",
                        f"CODE: {result.returncode}",
                        f"DETAILS: {result.stdout}"
                    )

    except subprocess.TimeoutExpired:
        elapsed_time = timeout
    except Exception as e:
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
    parser = argparse.ArgumentParser(description="SMT-InstanceSolver: run SMT models with Z3 or CVC5")

    parser.add_argument("model", help="Solve the problem with HA or RR method", choices=["ha", "rr"])
    parser.add_argument("solver_name", help="SMT solver to use", choices=["z3", "cvc5"])
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

    # Extract n_value from the file content
    with open(args.instance_path, 'r') as f:
        content = f.read()
        match = re.search(r'n\s*=\s*(\d+);', content)
        n_value = int(match.group(1))

    # Solve the instance with the given parameters
    result = solve_smt_instance(
        args.model,
        args.solver_name,
        n_value,
        args.use_symmetry_breaking,
        args.optimization,
        args.test_name,
        args.timeout
    )

    # Save result
    res_dir = pathlib.Path(__file__).parent.parent.parent / 'res' / 'SMT'
    os.makedirs(res_dir, exist_ok=True)

    # Extract instance_id from filename (remove .dzn extension)
    instance_id = os.path.splitext(os.path.basename(args.instance_path))[0]
    res_path = os.path.join(res_dir, f'{instance_id}.json')

    # Load existing data if available
    data = {}
    if os.path.exists(res_path):
        with open(res_path, 'r') as f:
            data = json.load(f)

    # Update data with the new result
    data.update(result)

    # Beautify and save the JSON output
    opts = jsbeautifier.default_options()
    opts.keep_array_indentation = True

    beautified_json = jsbeautifier.beautify(json.dumps(data), opts)

    # Write the beautified JSON to the destination file
    with open(res_path, 'w') as f:
        f.write(beautified_json)

    print(f"  Result saved to: {res_path}")
    return 0


if __name__ == "__main__":
    main()
