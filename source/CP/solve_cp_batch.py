#!/usr/bin/env python3
"""
Batch CP Solver: Script to run multiple CP instances automatically
"""

import os
import argparse
import pathlib
import subprocess
import glob
import sys

def main():
    parser = argparse.ArgumentParser(description="Batch CP Solver: Run multiple CP instances automatically")
    
    parser.add_argument(
        "instances_path", 
        help="Path to directory containing .dzn instance files", 
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
        choices=['gecode', 'chuffed', 'ortools'],
        type=str
    )
    parser.add_argument(
        "test_name",
        help="Name for the test (used as JSON key)",
        type=str
    )
    
    args = parser.parse_args()
    
    # Find all .dzn files in the instances directory
    dzn_pattern = os.path.join(args.instances_path, "*.dzn")
    dzn_files = glob.glob(dzn_pattern)
    
    if not dzn_files:
        print(f"No .dzn files found in {args.instances_path}")
        return 1
    
    # Sort files for consistent ordering
    dzn_files.sort()
    
    # Process each instance
    for i, dzn_file in enumerate(dzn_files):
        # Extract instance_id from filename (remove .dzn extension)
        instance_id = os.path.splitext(os.path.basename(dzn_file))[0]
        
        print(f"\nProcessing instance {i+1}/{len(dzn_files)}")
        
        # Build command to call the CP solver script
        cmd = [
            "python", "solve_cp_instance.py",
            instance_id,
            str(args.model_path),
            args.cp_solver,
            args.test_name,
        ]
        
        # Execute the command
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✓ Success: {instance_id}")
                if result.stdout:
                    print(f"  {result.stdout.strip()}")
            else:
                print(f"✗ Failed: {instance_id}")
                if result.stderr:
                    print(f"  Error: {result.stderr.strip()}")
                    
        except Exception as e:
            print(f"✗ Exception for {instance_id}: {e}")
    
    print(f"\nBatch processing completed!")
    return 0

if __name__ == '__main__':
    sys.exit(main())