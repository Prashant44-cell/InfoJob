"""
Client for Brønnøysundregistrene Corporate Governance & Roles API.
Endpoint: https://data.brreg.no/enhetsregisteret/api/enheter/{orgnr}/roller
License: Norwegian Licence for Open Government Data (NLOD 2.0)
"""

import logging
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://data.brreg.no/enhetsregisteret/api/enheter"
HEADERS = {
    "Accept": "application/vnd.brreg.enhetsregisteret.enhet.v2+json, application/json",
    "User-Agent": "SignalPost-Agent/1.0",
}


class BrregRollerSource:
    """Client for retrieving corporate leadership, board members, and auditors."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def fetch_roller(self, orgnr: str) -> Optional[Dict[str, Any]]:
        """Fetches raw role structure for a given organization number."""
        url = f"{BASE_URL}/{orgnr}/roller"
        try:
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                data["_source_url"] = url
                return data
            elif response.status_code == 404:
                # Some legal entity types (like simple associations or sole traders) might have no separate role registry
                return None
            else:
                logger.debug("Roller fetch returned HTTP %s for %s", response.status_code, orgnr)
                return None
        except Exception as exc:
            logger.debug("Exception fetching roller for %s: %s", orgnr, exc)
            return None

    async def fetch_roller_async(self, session, orgnr: str) -> Optional[Dict[str, Any]]:
        """Asynchronous fetch for batch ingestion."""
        url = f"{BASE_URL}/{orgnr}/roller"
        try:
            async with session.get(url, headers=HEADERS, timeout=self.timeout) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    data["_source_url"] = url
                    return data
                return None
        except Exception as exc:
            logger.debug("Async roller fetch failed for %s: %s", orgnr, exc)
            return None

    @staticmethod
    def parse_roles(raw_data: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extracts structured role items from raw API response.
        Filters out deregistered roles unless historical.
        """
        if not raw_data:
            return []

        parsed = []
        source_url = raw_data.get("_source_url", "")
        rollegrupper = raw_data.get("rollegrupper", [])

        for group in rollegrupper:
            group_last_changed = group.get("sistEndret")
            roles_in_group = group.get("roller", [])

            for r in roles_in_group:
                # Check if role is active
                if r.get("avregistrert", False):
                    continue

                role_type = r.get("type", {})
                code = role_type.get("kode", "")
                desc = role_type.get("beskrivelse", "")

                person_name = None
                birth_date = None
                is_deceased = False
                org_name = None
                org_nr = None

                if "person" in r:
                    p = r["person"]
                    name_obj = p.get("navn", {})
                    if isinstance(name_obj, dict):
                        parts = [
                            name_obj.get("fornavn", ""),
                            name_obj.get("mellomnavn", ""),
                            name_obj.get("etternavn", ""),
                        ]
                        person_name = " ".join(p for p in parts if p).strip()
                    elif isinstance(name_obj, str):
                        person_name = name_obj
                    birth_date = p.get("fodselsdato")
                    is_deceased = p.get("erDoed", False)

                elif "enhet" in r:
                    e = r["enhet"]
                    org_nr = e.get("organisasjonsnummer")
                    raw_names = e.get("navn", [])
                    if isinstance(raw_names, list) and raw_names:
                        org_name = " ".join(raw_names)
                    elif isinstance(raw_names, str):
                        org_name = raw_names

                parsed.append({
                    "role_code": code,
                    "role_description": desc,
                    "person_name": person_name,
                    "birth_date": birth_date,
                    "is_deceased": is_deceased,
                    "organization_name": org_name,
                    "organization_orgnr": org_nr,
                    "last_updated": group_last_changed,
                    "source_url": source_url,
                })

        return parsed
