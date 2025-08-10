#!/usr/bin/env python3
"""
Batch SMT Solver: Script to run multiple SMT instances automatically.
"""
import json
import os
import pathlib
import subprocess
import sys
import glob

# Define paths for instances and results
instances_path = pathlib.Path(__file__).parent.parent.parent / 'instances' / 'SMT'
res_dir = pathlib.Path(__file__).parent.parent.parent / 'res' / 'SMT'

EXPERIMENTS_CONFIG = {
    # Experiments with Home-Away method
    'ha-z3': {
        'model': 'ha',
        'smt_solver': 'z3',
        'use_symmetry_breaking': 'true',
        'optimization': 'false',
    },
    'ha-cvc5': {
        'model': 'ha',
        'smt_solver': 'cvc5',
        'use_symmetry_breaking': 'true',
        'optimization': 'false',
    },
    'ha-nosymm-z3': {
        'model': 'ha',
        'smt_solver': 'z3',
        'use_symmetry_breaking': 'false',
        'optimization': 'false',
    },
    'ha-nosymm-cvc5': {
        'model': 'ha',
        'smt_solver': 'cvc5',
        'use_symmetry_breaking': 'false',
        'optimization': 'false',
    },

    # Experiments with Round-Robin method
    'rr-z3': {
        'model': 'rr',
        'smt_solver': 'z3',
        'use_symmetry_breaking': 'true',
        'optimization': 'false',
    },
    'rr-cvc5': {
        'model': 'rr',
        'smt_solver': 'cvc5',
        'use_symmetry_breaking': 'true',
        'optimization': 'false',
    },
    'rr-opt-z3': {
        'model': 'rr',
        'smt_solver': 'z3',
        'use_symmetry_breaking': 'true',
        'optimization': 'true',
    },
    'rr-nosymm-z3': {
        'model': 'rr',
        'smt_solver': 'z3',
        'use_symmetry_breaking': 'false',
        'optimization': 'false',
    },
    'rr-nosymm-cvc5': {
        'model': 'rr',
        'smt_solver': 'cvc5',
        'use_symmetry_breaking': 'false',
        'optimization': 'false',
    },
    'rr-nosymm-opt-z3': {
        'model': 'rr',
        'smt_solver': 'z3',
        'use_symmetry_breaking': 'false',
        'optimization': 'true',
    },
}


def main():
    # Find all .txt files in the instances directory
    instance_files = glob.glob(os.path.join(instances_path, "*.txt"))

    if not instance_files:
        print(f"No .txt files found in {instances_path}")
        return 1

    # Sort files for consistent ordering
    instance_files.sort()

    # Process each instance
    for i, instance_file in enumerate(instance_files):
        # Extract instance_id from filename
        instance_id = os.path.splitext(os.path.basename(instance_file))[0]

        # Header for new instance
        print(f"\n{'=' * 80}")
        print(
            f"INSTANCE: {instance_id:<40} | PROGRESS: [{i + 1:>3}/{len(instance_files):<3}]")
        print(f"{'=' * 80}")

        # Read the results obtained from the previous instance
        prev_instance_id = int(instance_id) - 1
        prev_instance_data = None
        if prev_instance_id > 0:
            prev_res_path = os.path.join(res_dir, f'{prev_instance_id}.json')
            try:
                with open(prev_res_path) as f:
                    prev_instance_data = json.load(f)
            except Exception as e:
                print(f"  WARNING: Could not read previous results for {prev_instance_id}: {e}")
                raise e

        # Iterate over each defined experiment
        for exp_idx, exp_name in enumerate(EXPERIMENTS_CONFIG.keys()):
            print(f"\n  EXPERIMENT: {exp_name:<35} [{exp_idx + 1}/{len(EXPERIMENTS_CONFIG)}]")
            print(f"  {'─' * 60}")

            # Check if we should skip this experiment based on previous results
            if prev_instance_data and exp_name not in prev_instance_data:
                raise KeyError(f"Experiment key '{exp_name}' missing in previous results for {prev_instance_id}")
            if prev_instance_data and len(prev_instance_data[exp_name]['sol']) == 0:
                print("  SKIP EXPERIMENT: Previous model found no solution.")

                # Save empty result for this experiment
                res_path = os.path.join(res_dir, f'{instance_id}.json')

                # Load existing data if available
                data = {}
                if os.path.exists(res_path):
                    with open(res_path) as f:
                        data = json.load(f)

                # Update data with empty result
                data[exp_name] = {
                    "time": 300,
                    "optimal": False,
                    "obj": "None",
                    "sol": []
                }

                # Write the JSON to the destination file
                with open(res_path, 'w') as f:
                    json.dump(data, f, indent=4)

            else:
                # Build the command to call the SMT solver script
                cmd = [
                    sys.executable,
                    "solve_smt_instance.py",
                    str(EXPERIMENTS_CONFIG[exp_name]['model']),
                    str(EXPERIMENTS_CONFIG[exp_name]['smt_solver']),
                    instance_file,
                    str(EXPERIMENTS_CONFIG[exp_name]['use_symmetry_breaking']),
                    str(EXPERIMENTS_CONFIG[exp_name]['optimization']),
                    exp_name,
                ]

                # Execute the command
                try:
                    result = subprocess.run(cmd, text=True)

                    if result.returncode == 0:
                        print(f"  STATUS: {'SUCCESS':<10}")
                    else:
                        print(f"  STATUS: {'ERROR':<10}")
                        if result.stderr:
                            print(f"  ERROR_MSG: {result.stderr.strip()}")

                except Exception as e:
                    print(f"  STATUS: {'EXCEPTION':<10}")
                    print(f"  ERROR_MSG: Failed to execute subprocess: {e}")

            print(f"  {'─' * 60}")

    # Print completion message
    print("\n\n" + "*" * 50)
    print(f"* {'All SMT experiments completed!'.center(46)} *")
    print("*" * 50)
    return 0


if __name__ == '__main__':
    main()
