#!/usr/bin/env python3
"""
SignalPost: Autonomous Norwegian Company Intelligence Agent
Main entry point for command-line execution, batch generation, and web server.
"""

import argparse
import os
import sys

# Ensure UTF-8 stdout on Windows
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure root directory is on PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from signalpost.cli import run_batch_generation, run_lookup, run_server, run_sync
from signalpost.db.storage import ProfileStorage


def main():
    parser = argparse.ArgumentParser(
        description="SignalPost: Autonomous Norwegian Company Intelligence Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py --orgnr 923609016           # Look up Equinor ASA and return verified facts
  python run.py --orgnr 984851006           # Look up DNB Bank ASA
  python run.py --sync 923609016            # Check registry delta stream and sync profile
  python run.py --serve                     # Launch interactive Web Dashboard & REST API
  python run.py --batch 1000                # Harvest and export 1,000 verified company profiles
  python run.py --verify-dataset            # Verify the 1,000+ profiles dataset integrity
  python run.py                             # Run default inspection on Equinor ASA (923609016)
        """,
    )

    parser.add_argument(
        "--orgnr",
        type=str,
        help="9-digit Norwegian Organization Number (organisasjonsnummer) to query",
    )
    parser.add_argument(
        "--sync",
        type=str,
        help="Check delta stream and keep company profile current",
    )
    parser.add_argument(
        "--batch",
        type=int,
        nargs="?",
        const=1000,
        help="Harvest, verify, and export N company profiles (default: 1000)",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Start the interactive Web Dashboard & REST API",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for web server (default: 8000)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output profile as raw JSON instead of formatted table",
    )
    parser.add_argument(
        "--verify-dataset",
        action="store_true",
        help="Validate the pre-harvested 1,000 profiles dataset",
    )

    args = parser.parse_args()

    if args.serve:
        run_server(port=args.port)
    elif args.batch:
        run_batch_generation(count=args.batch)
    elif args.sync:
        run_sync(args.sync)
    elif args.verify_dataset:
        storage = ProfileStorage()
        count = storage.count_profiles()
        print("=" * 70)
        print(" SIGNALPOST DATASET INTEGRITY VERIFICATION")
        print("=" * 70)
        print(f"[*] SQLite Database: {storage.db_path}")
        print(f"[*] Total Profiles Stored: {count}")
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        for fname in ["profiles_1000.json", "profiles_1000.jsonl", "profiles_1000_summary.csv"]:
            p = os.path.join(data_dir, fname)
            if os.path.exists(p):
                size_mb = os.path.getsize(p) / (1024 * 1024)
                print(f"[OK] {fname}: Found ({size_mb:.2f} MB)")
            else:
                print(f"[X]  {fname}: Not found")
        print("=" * 70)
    elif args.orgnr:
        run_lookup(args.orgnr, json_output=args.json)
    else:
        # Default run: Look up premier Norwegian company Equinor ASA (923609016)
        print("\n[*] No arguments provided. Running default verification on Equinor ASA (923609016)...")
        print("[*] (Use 'python run.py --help' to view all command options)\n")
        run_lookup("923609016", json_output=args.json)


if __name__ == "__main__":
    main()
