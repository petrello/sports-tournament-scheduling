#!/usr/bin/env python3
"""
CP-InstanceSolver: Simple MiniZinc CP test script
"""

import os
import json
import argparse
import pathlib
import subprocess
import sys
import time
import math

def parse_minizinc_output(output_text):
    """Parse MiniZinc output to extract solution matrix"""
    try:
        return eval(''.join(c for c in output_text if c not in '-').strip())
    except:
        return None

def solve_cp_instance(instance_id, model_path, cp_solver, test_name, timeout=300):
    """Solve CP instance using MiniZinc"""
    
    # Construct paths
    instance_file = os.path.join('..', '..', 'instances', 'CP', f'{instance_id}.dzn')
    
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
            solution = parse_minizinc_output(result.stdout)
            optimal = solution is not None and elapsed_time < timeout
            
            return {
                test_name.lower(): {
                    "time": math.floor(elapsed_time),
                    "optimal": optimal,
                    "obj": "None",
                    "sol": solution
                }
            }
        else:
            raise Exception(
                "Error occoured while running the MiniZinc solver.",
                f"CODE: {result.returncode}"
            )    
    except subprocess.TimeoutExpired:
        elapsed_time = time.time() - start_time
        return {
            test_name.lower(): {
                "time": 300,
                "optimal": False,
                "obj": "None",
                "sol": "None"
            }
        }

def main():
    parser = argparse.ArgumentParser(description="CP-InstanceSolver: MiniZinc CP test script")
    
    parser.add_argument(
        "instance_id", 
        help="Name of the instance to test", 
        type=str
    )
    parser.add_argument(
        "model_path", 
        help="Path to the MiniZinc model file", 
        type=pathlib.Path
    )
    parser.add_argument(
        "cp_solver",
        help="CP solver to use", 
        choices=['gecode', 'chuffed', 'ortools'], 
        type=str
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
        args.instance_id,
        args.model_path,
        args.cp_solver, 
        args.test_name,
        args.timeout
    )

    # Save result
    output_dir = os.path.join('..', '..', 'res', 'CP')
    os.makedirs(output_dir, exist_ok=True)
    
    dest_path = os.path.join(output_dir, f'{args.instance_id}.json')

    data = {}
    if os.path.exists(dest_path):
        with open(dest_path) as f:
            data = json.load(f)

    data[args.test_name] = result[args.test_name]
    
    with open(dest_path, 'w') as f:
        json.dump(result, f)
    
    print(f"Result saved to: {dest_path}")
    return 0






if __name__ == '__main__':
    sys.exit(main())