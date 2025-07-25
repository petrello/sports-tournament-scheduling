#!/usr/bin/env python3
"""
Batch SMT Solver: run multiple SMT instances automatically.
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

# ===== Experiments configuration =====
# Each entry defines:
#   - model_file: Python file containing the SMT model
#   - extra_constraints: True/False
#   - optimization: True/False
experiments_config = {
    "ha-basic": {
        "model_file": "model_ha_smt.py",
        "extra_constraints": False,
        "optimization": False,
    },
    "ha-extra": {
        "model_file": "model_ha_smt.py",
        "extra_constraints": True,
        "optimization": False,
    },
    "ha-opt": {
        "model_file": "model_ha_smt.py",
        "extra_constraints": False,
        "optimization": True,
    },
    "rr-basic": {
        "model_file": "model_rr_smt.py",
        "extra_constraints": False,
        "optimization": False,
    },
    "rr-opt": {
        "model_file": "model_rr_smt.py",
        "extra_constraints": True,
        "optimization": True,
    },
}


def main():
    # Find all instance files
    inst_files = glob.glob(os.path.join(instances_path, "*.txt"))
    if not inst_files:
        print(f"No instance files found in {instances_path}")
        return 1

    # Sort files for consistent ordering
    inst_files.sort()

    for idx, inst_path in enumerate(inst_files):
        instance_id = os.path.splitext(os.path.basename(inst_path))[0]
        print("\n" + "="*80)
        print(f"INSTANCE: {instance_id:<40} | PROGRESS: [{idx+1}/{len(inst_files)}]")
        print("="*80)

        # get previous instance data if exists
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

        for exp_idx, exp_name in enumerate(experiments_config.keys()):
            print(f"\n  EXPERIMENT: {exp_name:<35} [{exp_idx+1}/{len(experiments_config)}]")
            print("  " + "─"*60)

            # Check skip condition
            if prev_instance_data is not None:
                if exp_name not in prev_instance_data:
                    raise KeyError(
                        f"Experiment '{exp_name}' missing in previous results for {prev_instance_id}"
                    )
                prev_result = prev_instance_data[exp_name]
                if prev_result["time"] >= 500 or len(prev_result["sol"]) == 0:
                    # previous instance unsolved -> skip
                    print(f"  SKIP: {exp_name} (unsolved at instance {prev_instance_id})")

                    # write empty result for this experiment
                    res_path = res_dir / f"{instance_id}.json"
                    data = {}
                    if res_path.exists():
                        with open(res_path) as f:
                            data = json.load(f)
                    data[exp_name] = {
                        "time": 300,
                        "optimal": False,
                        "obj": "None",
                        "sol": []
                    }
                    with open(res_path, "w") as f:
                        json.dump(data, f, indent=4)
                    continue

            # Build command to run low-level solver
            cmd = [
                sys.executable,
                "solve_smt_instance.py",
                inst_path,
                str(experiments_config[exp_name]["method"]),
                str(experiments_config[exp_name]['smt_solver']),
                str(experiments_config[exp_name]["use_symmetry_breaking_constraints"]),
                str(experiments_config[exp_name]["optimization"]),
                exp_name
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

            print("  " + "─"*60)

    # Print completion message
    print("\n\n" + "*" * 50)
    print(f"* {'All SMT experiments completed!'.center(46)} *")
    print("*" * 50)
    return 0

if __name__ == "__main__":
    main()