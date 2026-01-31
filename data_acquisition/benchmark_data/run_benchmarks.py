"""
Benchmark Data Update Runner
Run this script to update industry benchmark data from Damodaran's website.
"""

import sys
import os
from pathlib import Path

# Setup project root path
current_dir = os.path.dirname(os.path.abspath(__file__))
# .../data_acquisition/benchmark_data
# We need to go up 2 levels to get to project root
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from data_acquisition.benchmark_data.benchmark_data_loader import BenchmarkDataLoader

def main():
    try:
        loader = BenchmarkDataLoader()
        output_file = loader.get_output_path()
        
        print(f"\nTarget Output: {output_file}")
        
        if output_file.exists():
            print(f"File already exists: {output_file}")
            # Interactive check for overwrite is appropriate for a runner script
            response = input("Overwrite? (y/N): ").strip().lower()
            if response != 'y':
                print("Operation cancelled.")
                return

        print("Running Benchmark Update...")
        result = loader.run_update(force_refresh=False)
        
        if result:
            print(f"\n[SUCCESS] Benchmark data saved to: {result}")
        else:
            print("\n[FAILED] Failed to update benchmarks. Check logs.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"\n[ERROR] An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
