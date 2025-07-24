#!/usr/bin/env python3
"""
Batch CP Solver: Script to run multiple CP instances automatically
"""
import json
import os
import pathlib
import subprocess
import glob
import sys

# Define paths for instances and results
instances_path = pathlib.Path(__file__).parent.parent.parent / 'instances' / 'CP'
res_dir = pathlib.Path(__file__).parent.parent.parent / 'res' / 'CP'

experiments_config = {
    # Experiments with Home-Away method
    'ha-gecode': {
        'model_path': 'cp_model_ha.mzn',
        'cp_solver': 'gecode',
        'optimization': 'false',
    },
    'ha-nosymm-gecode': {
        'model_path': 'cp_model_ha_no_symm.mzn',
        'cp_solver': 'gecode',
        'optimization': 'false',
    },
    'ha-noglob-gecode': {
        'model_path': 'cp_model_ha_no_global.mzn',
        'cp_solver': 'gecode',
        'optimization': 'false',
    },
    'ha-chuffed': {
        'model_path': 'cp_model_ha.mzn',
        'cp_solver': 'chuffed',
        'optimization': 'false',
    },
    'ha-nosymm-chuffed': {
        'model_path': 'cp_model_ha_no_symm.mzn',
        'cp_solver': 'chuffed',
        'optimization': 'false',
    },
    'ha-noglob-chuffed': {
        'model_path': 'cp_model_ha_no_global.mzn',
        'cp_solver': 'chuffed',
        'optimization': 'false',
    },

    # Experiments with Home-Away method and restart
    'ha-restart-gecode': {
        'model_path': 'cp_model_ha_restart.mzn',
        'cp_solver': 'gecode',
        'optimization': 'false',
    },
    'ha-nosymm-restart-gecode': {
        'model_path': 'cp_model_ha_no_symm_restart.mzn',
        'cp_solver': 'gecode',
        'optimization': 'false',
    },
    'ha-noglob-restart-gecode': {
        'model_path': 'cp_model_ha_no_global_restart.mzn',
        'cp_solver': 'gecode',
        'optimization': 'false',
    },

    # Experiments with Round-Robin method
    'rr-gecode': {
        'model_path': 'cp_model_rr.mzn',
        'cp_solver': 'gecode',
        'optimization': 'false',
    },
    'rr-chuffed': {
        'model_path': 'cp_model_rr.mzn',
        'cp_solver': 'chuffed',
        'optimization': 'false',
    },
    'rr-opt-gecode': {
        'model_path': 'cp_model_rr_opt.mzn',
        'cp_solver': 'gecode',
        'optimization': 'true',
    },

    # Experiments with Round-Robin method and restart
    'rr-gecode-restart': {
        'model_path': 'cp_model_rr_restart.mzn',
        'cp_solver': 'gecode',
        'optimization': 'false',
    },
    'rr-opt-gecode-restart': {
        'model_path': 'cp_model_rr_restart_opt.mzn',
        'cp_solver': 'gecode',
        'optimization': 'true',
    },
}

def main():
    # Find all .dzn files in the instances directory
    dzn_files = glob.glob(os.path.join(instances_path, "*.dzn"))
    
    if not dzn_files:
        print(f"No .dzn files found in {instances_path}")
        return 1
    
    # Sort files for consistent ordering
    dzn_files.sort()

    # Process each instance
    for i, dzn_file in enumerate(dzn_files):
        # Extract instance_id from filename (remove .dzn extension)
        instance_id = os.path.splitext(os.path.basename(dzn_file))[0]

        # Header for new instance
        print(f"\n{'=' * 80}")
        print(
            f"INSTANCE: {instance_id:<40} | PROGRESS: [{i + 1:>3}/{len(dzn_files):<3}]")
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

        # Repeat the experiment for each CP model
        for exp_idx, exp_key in enumerate(experiments_config.keys()):
            print(f"\n  EXPERIMENT: {exp_key:<35} [{exp_idx + 1}/{len(experiments_config)}]")
            print(f"  {'─' * 60}")

            if prev_instance_data and exp_key not in prev_instance_data:
                raise KeyError(f"Experiment key '{exp_key}' missing in previous results for {prev_instance_id}")
            if prev_instance_data and len(prev_instance_data[exp_key]['sol']) == 0:
                print("  SKIP EXPERIMENT: Previous model found no solution.")

                # Save empty result for this experiment
                res_path = os.path.join(res_dir, f'{instance_id}.json')

                # Load existing data if available
                data = {}
                if os.path.exists(res_path):
                    with open(res_path) as f:
                        data = json.load(f)

                # Update data with empty result
                data[exp_key] = {
                    "time": 300,
                    "optimal": False,
                    "obj": "None",
                    "sol": []
                }

                # Write the beautified JSON to the destination file
                with open(res_path, 'w') as f:
                    json.dump(data, f, indent=4)
            else:
                # Build command to call the CP solver script
                cmd = [
                    sys.executable, "solve_cp_instance.py",
                    dzn_file,
                    experiments_config[exp_key]['model_path'],
                    experiments_config[exp_key]['cp_solver'],
                    experiments_config[exp_key]['optimization'],
                    exp_key,
                ]

                # Execute the command
                try:
                    result = subprocess.run(cmd, text=True)

                    if result.returncode == 0:
                        print(f"  STATUS: {'SUCCESS':<10}")
                    else:
                        print(f"  STATUS: {'ERROR':<10}")
                        if result.stderr:
                            print(f"  ERROR_MSG:  {result.stderr.strip()}")

                except Exception as e:
                    print(f"  STATUS: {'EXCEPTION':<10}")
                    print(f"  ERROR_MSG:  {str(e)}")

            print(f"  {'─' * 60}")

    # Print completion message
    print("\n\n" + "*" * 50)
    print(f"* {'All CP experiments completed!'.center(46)} *")
    print("*" * 50)
    return 0

if __name__ == '__main__':
    main()