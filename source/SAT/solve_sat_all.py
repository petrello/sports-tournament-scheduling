#!/usr/bin/env python3
"""
Batch SAT Solver: Script to run multiple SAT instances automatically.
"""
import json
import os
import pathlib
import subprocess
import sys
import glob

# Define paths for instances and results
instances_path = pathlib.Path(__file__).parent.parent.parent / 'instances' / 'SAT'
res_dir = pathlib.Path(__file__).parent.parent.parent / 'res' / 'SAT'

EXPERIMENTS_CONFIG = {
    # Experiments with Home-Away method
    'ha-minisat': {
        'model': 'ha',
        'sat_solver': 'minisat',
        'use_symmetry_breaking': 'true',
        'optimization': 'false',
    },
    'ha-glucose': {
        'model': 'ha',
        'sat_solver': 'glucose',
        'use_symmetry_breaking': 'true',
        'optimization': 'false',
    },
    'ha-nosymm-minisat': {
        'model': 'ha',
        'sat_solver': 'minisat',
        'use_symmetry_breaking': 'false',
        'optimization': 'false',
    },
    'ha-nosymm-glucose': {
        'model': 'ha',
        'sat_solver': 'glucose',
        'use_symmetry_breaking': 'false',
        'optimization': 'false',
    },

    # Experiments with Round-Robin method
    'rr-minisat': {
        'model': 'rr',
        'sat_solver': 'minisat',
        'use_symmetry_breaking': 'false',
        'optimization': 'false',
    },
    'rr-glucose': {
        'model': 'rr',
        'sat_solver': 'glucose',
        'use_symmetry_breaking': 'false',
        'optimization': 'false',
    },
    'rr-opt-z3': {
        'model': 'rr',
        'sat_solver': 'minisat',           # ignored for optimization
        'use_symmetry_breaking': 'false',  # ignored for optimization
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
                print(f"  Experiment key '{exp_name}' missing in previous results for {prev_instance_id}")
                # Define default 'sol' as a list with one element to re-try the experiment
                prev_instance_data[exp_name] = {'sol': [0]}
                print(f"  Re-trying experiment '{exp_name}'...")

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
                # Build the command to call the SAT solver script
                cmd = [
                    sys.executable,
                    "solve_sat_instance.py",
                    str(EXPERIMENTS_CONFIG[exp_name]['model']),
                    str(EXPERIMENTS_CONFIG[exp_name]['sat_solver']),
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
                        else:
                            # We save a default result for current experiment
                            # since it is likely an error in the (MiniSAT) solver

                            res_path = os.path.join(res_dir, f'{instance_id}.json')
                            data = {}
                            if os.path.exists(res_path):
                                with open(res_path) as f: data = json.load(f)
                            data[exp_name] = {"time": 300, "optimal": False, "obj": "None", "sol": []}
                            with open(res_path, 'w') as f: json.dump(data, f, indent=4)
                except Exception as e:
                    print(f"  STATUS: {'EXCEPTION':<10}")
                    print(f"  ERROR_MSG: Failed to execute subprocess: {e}")

            print(f"  {'─' * 60}")

    # Print completion message
    print("\n\n" + "*" * 50)
    print(f"* {'All SAT experiments completed!'.center(46)} *")
    print("*" * 50)
    return 0


if __name__ == '__main__':
    main()
