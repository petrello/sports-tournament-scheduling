#!/usr/bin/env python3
"""
SMT-InstanceSolver: Run SMTModelRR (Z3 Python model) through Z3 or CVC5 CLI
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

# Import SMT models
from smt_model_ha import SMTModelHA
from smt_model_rr import SMTModelRR


def parse_smt_output(output_text: str):
    """Parse solver output text and extract solution/optimality"""
    output_lower = output_text.lower()
    if "unsat" in output_lower:
        return None, False
    if "sat" not in output_lower:
        return None, False

    # basic model parsing (Z3/CVC5 both print (define-fun ...)):
    model = {}
    for match in re.finditer(r"\(define-fun\s+(\S+)\s+\(\)\s+\S+\s+([^)]+)\)", output_text):
        var, val = match.groups()
        model[var] = val.strip()

    return model, True


def solve_smt_instance(model, solver_name, n_value, add_constraints, optimization, test_name, timeout=300):
    """Solve one SMT instance by generating SMT-LIB and running Z3 or CVC5"""
    # Build solver from your class
    solver, pos, swap, A, B, max_imbalance = (
        SMTModelHA.build_solver(n_value, add_constraints)
        if model.lower() == "ha"
        else SMTModelRR.build_solver(n_value, optimization)
    )

    start = time.time()
    # Convert solver to SMT-LIB
    smtlib_str = solver.to_smt()

    # Decide solver CLI
    cmd = (
        ["z3", "-in"] if solver_name.lower() == "z3" else ["cvc5", "--lang", "smt2", "--incremental"]
    )

    try:
        proc = subprocess.run(
            cmd,
            input=smtlib_str,
            text=True,
            capture_output=True,
            timeout=timeout
        )
        elapsed = time.time() - start

        if proc.returncode == 0:
            sol, ok = parse_smt_output(proc.stdout)
            return {
                test_name.lower(): {
                    "time": math.floor(elapsed) if sol is not None else timeout,
                    "optimal": ok,
                    "obj": str(max_imbalance) if (optimization and ok) else "None",
                    "sol": sol if sol is not None else []
                }
            }
        else:
            raise Exception(
                f"Solver error {proc.returncode}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
            )

    except subprocess.TimeoutExpired:
        return {
            test_name.lower(): {
                "time": timeout,
                "optimal": False,
                "obj": "None",
                "sol": []
            }
        }


def main():
    parser = argparse.ArgumentParser(description="SMT-InstanceSolver: run SMT models with Z3 or CVC5")

    parser.add_argument(
        "model",
        help="Solve the problem with HA or RR method",
        choices=["ha", "rr"]
    )
    parser.add_argument(
        "solver_name",
        help="SMT solver to use",
        choices=["z3", "cvc5"]
    )
    parser.add_argument(
        "n_value",
        help="Input n for the model",
        type=int
    )
    parser.add_argument(
        "use_symmetry_breaking_constraints",
        help="True/False to add symmetry breaking constraints",
        type=lambda x: x.lower() == 'true'
    )
    parser.add_argument(
        "optimization",
        help="True/False for optimization mode",
        type=lambda x: x.lower() == 'true'
    )
    parser.add_argument(
        "test_name",
        help="Name for the test (used as JSON key)",
        type=str
    )
    parser.add_argument(
        "-t",
        "--timeout",
        help="Timeout in seconds (default: 300)",
        type=int,
        default=300
    )

    args = parser.parse_args()

    result = solve_smt_instance(
        args.model,
        args.solver_name,
        args.n_value,
        args.use_symmetry_breaking_constraints,
        args.optimization,
        args.test_name,
        args.timeout
    )

    # Save result
    res_dir = pathlib.Path(__file__).parent.parent.parent / "res" / "SMT"
    os.makedirs(res_dir, exist_ok=True)

    res_path = res_dir / f"n{args.n_value}.json"
    data = {}
    if res_path.exists():
        with open(res_path) as f:
            data = json.load(f)

    data[args.test_name] = result[args.test_name.lower()]

    opts = jsbeautifier.default_options()
    opts.keep_array_indentation = True
    with open(res_path, "w") as f:
        f.write(jsbeautifier.beautify(json.dumps(data), opts))

    print(f"  Result saved to: {res_path}")


if __name__ == "__main__":
    main()