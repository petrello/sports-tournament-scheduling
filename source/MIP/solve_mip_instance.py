#!/usr/bin/env python3
"""
MIP-InstanceSolver: Run MIP models (HA/RR) through PuLP.
"""

import argparse
import json
import math
import os
import pathlib
import re
import time
from typing import Dict, Optional, List, Any

import jsbeautifier
import pulp as pl

# Import MIP models from other files
from mip_model_ha import MIPModelHA
from mip_model_rr import MIPModelRR


def _parse_mip_solution(
    model: pl.LpProblem,
    model_type: str,
    n: int,
    model_vars: Dict[str, Any]
) -> Optional[List[List[List[int]]]]:
    """
    Parse a solved PuLP model and reconstruct the schedule.
    This function handles both HA and RR models by accessing the
    variable values from the solved model object.

    Args:
        model: The solved PuLP model object.
        model_type: The type of model ('ha' or 'rr').
        n: The number of teams.
        model_vars: A dictionary containing the PuLP variable objects.

    Returns:
        The schedule as a nested list, or None if parsing fails.
    """
    if model.status not in [pl.LpStatusOptimal]:
        return None

    W, P = n - 1, n // 2
    schedule = []

    try:
        if model_type == 'ha':
            Home, Away = model_vars['Home'], model_vars['Away']
            for p_idx in range(P):
                row = []
                for w_idx in range(W):
                    # PuLP keys are 1-based, so p_idx+1 and w_idx+1
                    p, w = p_idx + 1, w_idx + 1
                    home_team = int(round(Home[p][w].varValue))
                    away_team = int(round(Away[p][w].varValue))
                    row.append([home_team, away_team])
                schedule.append(row)

        elif model_type == 'rr':
            pos, swap = model_vars['pos'], model_vars.get('swap')
            A, B = model_vars['A'], model_vars['B']
            for p_idx in range(P):
                row = []
                for w_idx in range(W):
                    p, w = p_idx + 1, w_idx + 1
                    k = int(round(pos[w][p].varValue)) - 1  # to 0-based index
                    home, away = A[w_idx][k], B[w_idx][k]

                    if swap and int(round(swap[w][p].varValue)) == 1:
                        home, away = away, home
                    row.append([home, away])
                schedule.append(row)

    except (KeyError, AttributeError, TypeError):
        # This can happen if a variable is missing or has no value
        return None

    return schedule


def solve_mip_instance(
    model_type: str,
    solver_name: str,
    n_value: int,
    use_symmetry_breaking: bool,
    is_optimization: bool,
    test_name: str,
    timeout: int
) -> Dict:
    """
    Main solver function. It builds the PuLP model, selects a solver,
    runs the optimization/feasibility problem, and parses the output.
    """
    # --- 1. Build the appropriate PuLP model ---
    if model_type.lower() == "ha":
        model, Home, Away, *_ = MIPModelHA.build_model(n_value, use_symmetry_breaking)
        model_vars = {'Home': Home, 'Away': Away}
    elif model_type.lower() == "rr":
        model, pos, swap, x, A, B, *_ = MIPModelRR.build_model(n_value, is_optimization)
        model_vars = {'pos': pos, 'swap': swap, 'A': A, 'B': B}
    else:
        raise ValueError(f"Unknown model type: {model_type}")

    # --- 2. Select the MIP solver engine ---
    if solver_name.lower() == 'glpk':
        solver = pl.GLPK_CMD(msg=False, options=['--tmlim', str(timeout)])
    elif solver_name.lower() == 'highs':
        solver = pl.HiGHS_CMD(msg=False, timeLimit=timeout)
    else:  # Default to CBC
        solver = pl.PULP_CBC_CMD(msg=False, timeLimit=timeout)

    # --- 3. Solve the instance ---
    start_time = time.time()
    model.solve(solver)
    elapsed_time = time.time() - start_time

    # --- 4. Parse results and format output ---
    solution = _parse_mip_solution(model, model_type.lower(), n_value, model_vars)
    is_optimal = (model.status == pl.LpStatusOptimal)
    obj_val = None
    if is_optimal and is_optimization:
        obj_val = int(round(pl.value(model.objective)))

    final_time = math.floor(elapsed_time) if solution is not None else timeout

    return {
        test_name.lower(): {
            "time": final_time,
            "optimal": is_optimal and (final_time < timeout),
            "obj": obj_val if obj_val is not None else "None",
            "sol": solution if solution is not None else [],
        }
    }


def main():
    """Defines and parses command-line arguments to run the solver."""
    parser = argparse.ArgumentParser(description="MIP-InstanceSolver: run MIP models with PuLP")
    parser.add_argument("model", choices=["ha", "rr"], help="Use HA or RR encoding")
    parser.add_argument("solver_name", choices=["cbc", "glpk", "highs"], help="Underlying MIP solver")
    parser.add_argument("instance_path", type=pathlib.Path, help="Path to instance file (e.g., '0.txt')")
    parser.add_argument("use_symmetry_breaking", type=lambda x: x.lower() == 'true', help="Enable/disable symmetry breaking for HA model")
    parser.add_argument("optimization", type=lambda x: x.lower() == 'true', help="Enable/disable optimization mode for RR model")
    parser.add_argument("test_name", type=str, help="A unique name for the test run (used as JSON key)")
    parser.add_argument("-t", "--timeout", type=int, default=300, help="Timeout in seconds for the solver")
    args = parser.parse_args()

    # Extract 'n' from the instance file content (e.g., "n=4;")
    try:
        content = args.instance_path.read_text()
        match = re.search(r'n\s*=\s*(\d+)', content)
        n_value = int(match.group(1))
    except (IOError, AttributeError, ValueError) as e:
        print(f"Error: Could not read 'n' from instance file {args.instance_path}. Details: {e}")
        return 1

    # Run the main solving logic
    result = solve_mip_instance(
        model_type=args.model,
        solver_name=args.solver_name,
        n_value=n_value,
        use_symmetry_breaking=args.use_symmetry_breaking,
        is_optimization=args.optimization,
        test_name=args.test_name,
        timeout=args.timeout
    )

    # Save result
    res_dir = pathlib.Path(__file__).parent.parent.parent / 'res' / 'MIP'
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


def get_available_solvers() -> List[str]:
    """
    Returns a list of available MIP solvers on the system.

    Returns:
        List[str]: List of available solver names
    """
    available = []

    # Check common solvers
    solvers_to_check = [
        "PULP_CBC_CMD",
        "GUROBI_CMD",
        "CPLEX_CMD",
        "GLPK_CMD",
        "SCIP_CMD"
    ]

    for solver_name in solvers_to_check:
        try:
            solver = pl.getSolver(solver_name)
            if solver.available():
                available.append(solver_name)
        except:
            pass

    return available
if __name__ == "__main__":
    # main()
    print(get_available_solvers())