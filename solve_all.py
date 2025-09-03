#!/usr/bin/env python3
"""
Root Script: Runs all solver experiments (CP, SAT, SMT, MIP) in parallel or sequential.
"""
import subprocess
import sys
import pathlib
from concurrent.futures import ThreadPoolExecutor

# Define the solver scripts and their paths in execution order
SOLVER_SCRIPTS = [
    pathlib.Path(__file__).parent / 'source' / 'CP' / 'solve_cp_all.py',
    pathlib.Path(__file__).parent / 'source' / 'SAT' / 'solve_sat_all.py',
    pathlib.Path(__file__).parent / 'source' / 'SMT' / 'solve_smt_all.py',
    pathlib.Path(__file__).parent / 'source' / 'MIP' / 'solve_mip_all.py',
]


def run_solver(script_path):
    """Run a single solver script."""
    subprocess.run([sys.executable, str(script_path)], cwd=script_path.parent)


def run_sequential():
    """Run all solver scripts sequentially."""
    for script_path in SOLVER_SCRIPTS:
        run_solver(script_path)


def run_parallel():
    """Run all solver scripts in parallel."""
    with ThreadPoolExecutor(max_workers=len(SOLVER_SCRIPTS)) as executor:
        futures = [executor.submit(run_solver, script_path) for script_path in SOLVER_SCRIPTS]

        # Wait for all tasks to complete
        for future in futures:
            future.result()


def main():
    """Main function to run all solver scripts."""
    # Check for sequential flag
    if len(sys.argv) > 1 and sys.argv[1] == '--sequential':
        run_sequential()
    else:
        run_parallel()


if __name__ == '__main__':
    sys.exit(main())