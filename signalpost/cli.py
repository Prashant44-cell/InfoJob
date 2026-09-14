"""
Command Line Interface for SignalPost Agent.
Formatted terminal output displaying verified company facts, official source links, and dates.
"""

import argparse
import asyncio
import json
import sys
from typing import Optional

from signalpost.agent.orchestrator import SignalPostAgent
from signalpost.batch.generator import BatchProfileGenerator
from signalpost.core.validator import validate_norwegian_orgnr
from signalpost.db.storage import ProfileStorage


def format_currency(val: Optional[float], curr: str = "NOK") -> str:
    if val is None:
        return "N/A"
    return f"{val:,.2f} {curr}"


def print_banner():
    print("=" * 78)
    print("  SIGNALPOST // AUTONOMOUS NORWEGIAN COMPANY INTELLIGENCE AGENT")
    print("  Permitted Public Sources: Brønnøysundregistrene (Enhet, Roller, Regnskap)")
    print("=" * 78)


def display_profile(profile):
    print("\n" + "=" * 78)
    print(f" COMPANY PROFILE: {profile.name} (Org.nr: {profile.orgnr})")
    print("=" * 78)
    print(f" Legal Form:      {profile.org_form} - {profile.org_form_description}")
    print(f" Status:          {profile.status}")
    print(f" Freshness:       {profile.freshness_status} (Last verified: {profile.last_verified_at[:19]}Z)")
    if profile.last_modified_in_registry:
        print(f" Registry Delta:  {profile.last_modified_in_registry} (Update #{profile.latest_update_id})")
    print(f" Industry (NACE): {profile.industry_code or 'N/A'} - {profile.industry_description or 'N/A'}")
    print(f" Employees:       {profile.employee_count:,} (Reported: {profile.employee_registration_date or 'N/A'})" if profile.employee_count else " Employees:       N/A")
    print(f" Registered Office: {profile.business_address.get('adresse', [''])[0] if profile.business_address else 'N/A'}, {profile.business_address.get('postnummer', '') if profile.business_address else ''} {profile.business_address.get('poststed', '') if profile.business_address else ''}")
    print(f" CEO / Leader:    {profile.ceo_name or 'N/A'}")
    print(f" Board Chair:     {profile.board_chair or 'N/A'}")
    print(f" Auditor:         {profile.auditor_name or 'N/A'}")
    if profile.latest_financials:
        f = profile.latest_financials
        print(f" Financials ({f.year}): Revenue: {format_currency(f.revenue, f.currency)} | Net Profit: {format_currency(f.net_profit, f.currency)} | Assets: {format_currency(f.total_assets, f.currency)}")

    if profile.executive_summary:
        print("-" * 78)
        print(" EXECUTIVE BRIEFING:")
        print(f" {profile.executive_summary}")

    print("\n" + "-" * 78)
    print(" VERIFIED FACTS LEDGER (WITH PERMITTED SOURCE LINKS & DATES):")
    print("-" * 78)
    print(f"{'CATEGORY':<24} | {'FACT & VALUE':<32} | {'SOURCE DATE':<10}")
    print(f"{'  -> OFFICIAL SOURCE URL':<78}")
    print("-" * 78)

    for fact in profile.facts:
        val_str = str(fact.value)
        if len(val_str) > 30:
            val_str = val_str[:27] + "..."
        cat_short = fact.category.split("&")[0].strip()[:23]
        date_str = (fact.source_date or "N/A")[:10]

        print(f"{cat_short:<24} | {fact.label[:18]}: {val_str:<12} | {date_str:<10}")
        print(f"  -> {fact.source_url}")

    print("=" * 78 + "\n")


def run_lookup(orgnr: str, json_output: bool = False):
    agent = SignalPostAgent()
    storage = ProfileStorage()

    print_banner()
    print(f"[*] Analyzing Norwegian Organization Number: {orgnr}")

    # Checksum verification
    is_valid, reason = validate_norwegian_orgnr(orgnr)
    print(f"[*] Modulo 11 Checksum: {'PASSED [OK]' if is_valid else 'FAILED [ERROR]'} ({reason})")

    if not is_valid:
        print(f"[!] Aborting: {reason}")
        sys.exit(1)

    print("[*] Querying permitted public sources...")
    print("    - Brønnøysundregistrene Enhetsregisteret (Core Legal Entity)")
    print("    - Brønnøysundregistrene Roller (Corporate Governance & Leadership)")
    print("    - Brønnøysundregistrene Regnskapsregisteret (Audited Accounts)")
    print("    - Brønnøysundregistrene Oppdateringer (Delta Update Stream)")
    print("    - Official Domain Web Footprint")

    ok, profile, msg = agent.process_orgnr(orgnr)
    if not ok or not profile:
        print(f"[!] Agent error: {msg}")
        sys.exit(1)

    storage.save_profile(profile)
    print(f"[+] Provenance and entity matching verified! Total facts extracted: {len(profile.facts)}")

    if json_output:
        print(profile.json(indent=2))
    else:
        display_profile(profile)


def run_sync(orgnr: str):
    agent = SignalPostAgent()
    storage = ProfileStorage()

    print_banner()
    print(f"[*] Checking profile freshness and update stream for: {orgnr}")
    cached = storage.get_profile(orgnr)

    if not cached:
        print("[*] Profile not in local database. Performing full agent query...")
        run_lookup(orgnr)
        return

    updated_profile, was_updated, reason = agent.sync_existing_profile(cached)
    storage.save_profile(updated_profile)

    print(f"[+] Freshness check complete:")
    print(f"    - Status: {updated_profile.freshness_status}")
    print(f"    - Result: {reason}")
    print(f"    - Updated: {'YES (profile synchronized)' if was_updated else 'NO (already current)'}")
    display_profile(updated_profile)


def run_batch_generation(count: int = 1000):
    print_banner()
    print(f"[*] Launching batch harvester for {count} company profiles...")
    storage = ProfileStorage()
    generator = BatchProfileGenerator(storage=storage)
    asyncio.run(generator.run_batch(target_count=count))
    exported = generator.export_all_formats()
    print("[+] Batch processing finished successfully!")
    print(f"    Total profiles stored: {exported['count']}")
    print(f"    JSON dataset:  {exported['json']}")
    print(f"    JSONL dataset: {exported['jsonl']}")
    print(f"    CSV summary:   {exported['csv']}")


def run_server(port: int = 8000):
    import uvicorn
    print_banner()
    print(f"[*] Starting SignalPost Web Dashboard & REST API on http://localhost:{port}")
    uvicorn.run("signalpost.api:app", host="0.0.0.0", port=port, reload=False)
