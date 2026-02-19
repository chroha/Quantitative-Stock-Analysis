import os
import shutil
import sys
import stat
import errno
from pathlib import Path

# Setup project root path to import internal modules
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.constants import (
    DATA_CACHE_STOCK,
    DATA_CACHE_MACRO,
    DATA_CACHE_BENCHMARK,
    DATA_REPORTS
)
from utils.console_utils import print_header, print_step, ICON

def handle_remove_readonly(func, path, exc):
    """
    Error handler for shutil.rmtree to clean up read-only files on Windows.
    """
    excvalue = exc[1]
    if func in (os.rmdir, os.remove, os.unlink) and excvalue.errno == errno.EACCES:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    else:
        raise

def clean_directory(path_str: str, file_pattern: str = "*", exclude_extensions: list = None, description: str = ""):
    """
    Cleans a directory of files and subdirectories, optionally excluding some file extensions.
    Uses iterdir() to ensure hidden files/directories (like .cache) are included.
    """
    path = Path(project_root) / path_str
    if not path.exists():
        print(f"  {ICON.INFO} Directory not found (skipped): {path_str}")
        return

    print(f"  Cleaning {description} in {path_str}...")
    
    files_deleted = 0
    dirs_deleted = 0
    skipped_items = 0
    
    # Use iterdir to get all items including hidden ones
    for item in path.iterdir():
        # Filter by pattern if it's not "*" logic (simple glob check manually if needed, 
        # but for cleanup usually we want everything unless excluded)
        # Verify strict pattern matching if user provided something other than "*"
        if file_pattern != "*" and not item.match(file_pattern):
            continue

        if item.is_file():
            # Check exclusions
            if exclude_extensions and item.suffix.lower() in exclude_extensions:
                skipped_items += 1
                continue
                
            try:
                item.unlink()
                files_deleted += 1
            except Exception as e:
                print(f"    {ICON.FAIL} Failed to delete file {item.name}: {e}")
                
        elif item.is_dir():
             # Recursive delete for directories
             # We assume if we are cleaning a cache dir, we kill subdirs too 
             # (unless they contain excluded extensions? Hard to check deeply efficiently. 
             # Usually exclude_extensions applies to top level files in this context).
             
             # Safety: Don't delete if we are in a mode where we might want to keep things?
             # For Benchmark CSVs, they are files. 
             # user requested .cache folder to be deleted.
             
             try:
                 shutil.rmtree(item, onerror=handle_remove_readonly)
                 dirs_deleted += 1
             except Exception as e:
                 print(f"    {ICON.FAIL} Failed to delete directory {item.name}: {e}")

    if files_deleted > 0:
        print(f"    {ICON.TRASH} Deleted {files_deleted} files.")
    if dirs_deleted > 0:
        print(f"    {ICON.TRASH} Deleted {dirs_deleted} directories.")
    if skipped_items > 0:
        print(f"    {ICON.INFO} Preserved {skipped_items} items.")

def main():
    print_header("System Cleaner")
    print(f"  Project Root: {project_root}")
    print("")

    # ==============================================================================
    # STEP 1: Cache Cleanup Selection
    # ==============================================================================
    print_step(1, 2, "Cache Cleanup")
    print("  Select cleanup mode:")
    print("  [1] Normal Clean (Default)")
    print("      - Deletes Stock & Macro JSONs")
    print("      - Deletes Benchmark JSONs")
    print("      - KEEPS Benchmark CSVs (e.g., betas_data.csv)")
    print("  [2] Full Clean")
    print("      - Deletes EVERYTHING in cache")
    print("      - Forces re-download of all industry data")
    print("")
    
    choice = input("  Choose option (1/2) [Default: 1]: ").strip()
    
    full_clean = choice == '2'
    
    # 1.1 Stock Cache
    clean_directory(DATA_CACHE_STOCK, "*", description="Stock Data")
    
    # 1.2 Macro Cache
    clean_directory(DATA_CACHE_MACRO, "*", description="Macro Data")
    
    # 1.3 Benchmark Cache
    if full_clean:
         clean_directory(DATA_CACHE_BENCHMARK, "*", description="Benchmark Data (Full)")
    else:
         # Exclude CSV
         clean_directory(DATA_CACHE_BENCHMARK, "*", exclude_extensions=['.csv'], description="Benchmark Data (Preserving CSVs)")
    
    # 1.4 Audit Logs (Always Clean)
    audit_dir = "devtools/audit_output"
    clean_directory(audit_dir, "*", description="Audit Logs")
         
    print(f"\n  {ICON.OK} Cache & Audit cleanup complete.")

    # ==============================================================================
    # STEP 2: Reports Cleanup
    # ==============================================================================
    print_step(2, 2, "Reports Cleanup")
    
    print(f"  Targets:")
    print(f"  - {DATA_REPORTS}")
    print("  This will delete ALL AI-generated analysis reports.")
    
    confirm = input("  Delete all generated reports? (y/N): ").strip().lower()
    
    if confirm in ('y', 'yes'):
        clean_directory(DATA_REPORTS, "*", description="Generated Reports")
        print(f"\n  {ICON.OK} Reports cleanup complete.")
    else:
        print(f"  {ICON.INFO} Skipped reports cleanup.")

    print("\n" + "="*60)
    print("  CLEANUP FINISHED")
    print("="*60)

if __name__ == "__main__":
    main()
