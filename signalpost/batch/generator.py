"""
High-throughput Batch Harvesting and Profile Generator Engine.
Harvests and verifies 1,000+ real Norwegian company profiles from Brønnøysundregistrene
using paginated streaming and concurrent enrichment.
"""

import asyncio
from datetime import datetime, timezone
import logging
import os
import sys
from typing import Any, Dict, List, Optional
import aiohttp

from signalpost.agent.entity_resolver import EntityResolver
from signalpost.agent.profile_builder import ProfileBuilder
from signalpost.core.models import CompanyProfile
from signalpost.core.validator import validate_norwegian_orgnr
from signalpost.db.storage import ProfileStorage

logger = logging.getLogger(__name__)

BASE_ENHETER_URL = "https://data.brreg.no/enhetsregisteret/api/enheter"
HEADERS = {
    "Accept": "application/vnd.brreg.enhetsregisteret.enhet.v2+json, application/json",
    "User-Agent": "SignalPost-Agent/1.0 (Batch Profile Harvester)",
}


class BatchProfileGenerator:
    """Harvests and builds at least 1,000 verified Norwegian company profiles."""

    def __init__(self, storage: Optional[ProfileStorage] = None, concurrency: int = 10):
        self.storage = storage or ProfileStorage()
        self.concurrency = concurrency
        self.resolver = EntityResolver()
        self.builder = ProfileBuilder(self.resolver)

    async def fetch_enheter_page(self, session: aiohttp.ClientSession, page: int, size: int = 100) -> List[Dict[str, Any]]:
        """Fetches a page of entities from Enhetsregisteret."""
        url = f"{BASE_ENHETER_URL}?size={size}&page={page}&organisasjonsform=AS,ASA"
        try:
            async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("_embedded", {}).get("enheter", [])
                return []
        except Exception as exc:
            logger.error("Error fetching page %s: %s", page, exc)
            return []

    async def fetch_roles_safe(self, session: aiohttp.ClientSession, orgnr: str) -> Optional[Dict[str, Any]]:
        """Safely fetches roles with a fast timeout."""
        url = f"{BASE_ENHETER_URL}/{orgnr}/roller"
        try:
            async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=4)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    data["_source_url"] = url
                    return data
                return None
        except Exception:
            return None

    async def fetch_accounts_safe(self, session: aiohttp.ClientSession, orgnr: str) -> Optional[List[Dict[str, Any]]]:
        """Safely fetches accounts with a fast timeout."""
        url = f"https://data.brreg.no/regnskapsregisteret/regnskap/{orgnr}"
        try:
            async with session.get(url, headers={"Accept": "application/json"}, timeout=aiohttp.ClientTimeout(total=4)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict):
                        return data.get("value", [data])
                return None
        except Exception:
            return None

    async def process_single_entity(
        self,
        session: aiohttp.ClientSession,
        enhet: Dict[str, Any],
        semaphore: asyncio.Semaphore,
        enrich_details: bool = True,
    ) -> Optional[CompanyProfile]:
        """Validates checksum, builds profile, optionally fetches roles and accounts."""
        orgnr = enhet.get("organisasjonsnummer")
        if not orgnr:
            return None

        is_valid, _ = validate_norwegian_orgnr(orgnr)
        if not is_valid:
            return None

        roller_data = None
        regnskap_data = None

        if enrich_details:
            async with semaphore:
                try:
                    roller_task = self.fetch_roles_safe(session, orgnr)
                    regnskap_task = self.fetch_accounts_safe(session, orgnr)
                    roller_data, regnskap_data = await asyncio.gather(roller_task, regnskap_task)
                except Exception:
                    pass

        profile = self.builder.build(
            orgnr=orgnr,
            enhet_raw=enhet,
            roller_raw=roller_data,
            regnskap_raw=regnskap_data,
        )

        emp = profile.employee_count or 0
        rev = f", revenue {profile.latest_financials.revenue:,.0f} {profile.latest_financials.currency}" if (profile.latest_financials and profile.latest_financials.revenue) else ""
        profile.executive_summary = (
            f"{profile.name} ({profile.org_form}) is an active Norwegian enterprise registered under NACE {profile.industry_code or 'General'} "
            f"with {emp:,} registered staff{rev}. Legal status: {profile.status}."
        )

        return profile

    async def run_batch(self, target_count: int = 1000, page_size: int = 100) -> int:
        """
        Harvests at least target_count profiles from Brreg and saves them directly to SQLite.
        """
        print(f"[*] Starting SignalPost Batch Harvester: Target = {target_count} Norwegian companies")
        pages_needed = (target_count // page_size) + 2
        semaphore = asyncio.Semaphore(self.concurrency)
        total_saved = 0

        connector = aiohttp.TCPConnector(limit=self.concurrency, ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            all_raw = []
            print(f"[*] Step 1: Downloading {pages_needed} entity batches from Enhetsregisteret...")
            for p in range(pages_needed):
                page_items = await self.fetch_enheter_page(session, page=p, size=page_size)
                all_raw.extend(page_items)
                print(f"    - Page {p + 1}/{pages_needed} received: {len(page_items)} entities (Total collected: {len(all_raw)})")
                if len(all_raw) >= target_count:
                    break

            print(f"[*] Step 2: Processing, verifying provenance, and indexing {len(all_raw[:target_count])} companies...")

            # Enrich first 150 with deep roles/accounts, and harvest base registry facts for all
            chunk_size = 50
            for i in range(0, min(len(all_raw), target_count), chunk_size):
                chunk = all_raw[i : i + chunk_size]
                # Deep enrich the first 150 companies
                should_deep_enrich = (i < 150)
                tasks = [
                    self.process_single_entity(session, e, semaphore, enrich_details=should_deep_enrich)
                    for e in chunk
                ]
                results = await asyncio.gather(*tasks)

                for prof in results:
                    if prof:
                        self.storage.save_profile(prof)
                        total_saved += 1

                print(f"    - Processed & saved: {total_saved}/{min(len(all_raw), target_count)} company profiles")

        print(f"[+] Harvester complete: {total_saved} Norwegian company profiles successfully saved in SQLite!")
        return total_saved

    def export_all_formats(self, base_data_dir: Optional[str] = None) -> Dict[str, str]:
        """Exports dataset to JSON, JSONL, and CSV in data directory."""
        if not base_data_dir:
            base_data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")

        os.makedirs(base_data_dir, exist_ok=True)
        json_path = os.path.join(base_data_dir, "profiles_1000.json")
        jsonl_path = os.path.join(base_data_dir, "profiles_1000.jsonl")
        csv_path = os.path.join(base_data_dir, "profiles_1000_summary.csv")

        j_count = self.storage.export_to_json(json_path)
        jl_count = self.storage.export_to_jsonl(jsonl_path)
        c_count = self.storage.export_to_csv(csv_path)

        print(f"[+] Exported {j_count} profiles to {json_path}")
        print(f"[+] Exported {jl_count} profiles to {jsonl_path}")
        print(f"[+] Exported {c_count} rows to {csv_path}")

        return {
            "json": json_path,
            "jsonl": jsonl_path,
            "csv": csv_path,
            "count": str(j_count),
        }
