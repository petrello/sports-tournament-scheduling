#!/usr/bin/env python3
"""
CP-InstanceSolver: Simple MiniZinc CP test script
"""

import os
import json
import argparse
import pathlib
import subprocess
import jsbeautifier
import time
import math


def parse_minizinc_output(output_text, optimization=False):
    """Parse MiniZinc output to extract solution matrix and objective value"""
    try:
        if not optimization:  # Parse solution obtained in decision mode
            max_imbalance = None
            matrix = eval(''.join(c for c in output_text if c not in '-').strip())
        else:  # Parse solution obtained in decision mode
            # Clean the output text
            clean_output = output_text[:output_text.find('-')-1].strip()

            # Extract maxImbalance
            max_imbalance = int(clean_output.split('\n')[0].split(' = ')[1])

            # Extract the matrix from the last solution
            matrix = eval(clean_output[clean_output.find('['):].strip())

        return matrix, max_imbalance

    except Exception as e:
        if "=UNSATISFIABLE=" in output_text:
            print("  The instance is UNSATISFIABLE")
        else:
            print(f"  Parsing error: {e}")
        return None, None

def solve_cp_instance(instance_file, model_path, cp_solver, optimization, test_name, timeout=300):
    """Solve CP instance using MiniZinc"""
    
    # Construct command
    command = [
        'minizinc',
        '--solver', cp_solver,
        '-t', str(timeout * 1000),  # timeout in milliseconds
        str(model_path),
        instance_file
    ]
    
    # Run command and measure time
    start_time = time.time()
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        elapsed_time = time.time() - start_time
        
        if result.returncode == 0:
            solution, obj = parse_minizinc_output(result.stdout, optimization)
            optimal = (
                (solution is not None and elapsed_time < timeout and not optimization)
                or
                (solution is not None and elapsed_time < timeout and obj < 2 and optimization)
            )
            
            return {
                test_name.lower(): {
                    "time": math.floor(elapsed_time) if solution is not None else 300,
                    "optimal": optimal,
                    "obj": obj if obj is not None else "None",
                    "sol": solution if solution is not None else [],
                }
            }
        else:
            raise Exception(
                "Error occurred while running the MiniZinc solver.",
                f"CODE: {result.returncode}",
                f"DETAILS: {result.stdout}"
            )    
    except subprocess.TimeoutExpired:
        return {
            test_name.lower(): {
                "time": 300,
                "optimal": False,
                "obj": "None",
                "sol": []
            }
        }

def main():
    parser = argparse.ArgumentParser(description="CP-InstanceSolver: MiniZinc CP test script")
    
    parser.add_argument(
        "instance_path",
        help="Path to the file instance to test",
        type=pathlib.Path
    )
    parser.add_argument(
        "model_path", 
        help="Path to the MiniZinc model file", 
        type=pathlib.Path
    )
    parser.add_argument(
        "cp_solver",
        help="CP solver to use", 
        choices=['gecode', 'chuffed'],
        type=str
    )
    parser.add_argument(
        "optimization",
        help="True if the model solve the problem for optimization, False if for decision",
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
    
    # Solve instance
    result = solve_cp_instance(
        args.instance_path,
        args.model_path,
        args.cp_solver,
        args.optimization,
        args.test_name,
        args.timeout
    )

    # Save result
    res_dir = pathlib.Path(__file__).parent.parent.parent / 'res' / 'CP'
    os.makedirs(res_dir, exist_ok=True)

    # Extract instance_id from filename (remove .dzn extension)
    instance_id = os.path.splitext(os.path.basename(args.instance_path))[0]
    res_path = os.path.join(res_dir, f'{instance_id}.json')

    # Load existing data if available
    data = {}
    if os.path.exists(res_path):
        with open(res_path) as f:
            data = json.load(f)

    # Update data with new result
    data[args.test_name] = result[args.test_name]

    # Beautify JSON output to keep array indentation
    opts = jsbeautifier.default_options()
    opts.keep_array_indentation = True

    beautified_json = jsbeautifier.beautify(json.dumps(data), opts)

    # Write the beautified JSON to the destination file
    with open(res_path, 'w') as f:
        f.write(beautified_json)

    print(f"  Result saved to: {res_path}")
    return 0


if __name__ == '__main__':
    main()