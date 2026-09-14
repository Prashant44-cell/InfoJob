"""
Client for Brønnøysundregistrene Enhetsregisteret (The Norwegian Register of Legal Entities).
Endpoint: https://data.brreg.no/enhetsregisteret/api/enheter/{orgnr}
License: Norwegian Licence for Open Government Data (NLOD 2.0) / Free Open Public API
"""

import logging
from typing import Any, Dict, Optional
import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://data.brreg.no/enhetsregisteret/api/enheter"
HEADERS = {
    "Accept": "application/vnd.brreg.enhetsregisteret.enhet.v2+json, application/json",
    "User-Agent": "SignalPost-Agent/1.0 (Hackathon Submission; open-source research)",
}


class BrregEnhetSource:
    """Client for retrieving primary legal entity facts from Enhetsregisteret."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def fetch_enhet(self, orgnr: str) -> Optional[Dict[str, Any]]:
        """
        Fetches official entity details by 9-digit organization number.
        Returns dictionary of official data, or None if entity is not found.
        """
        url = f"{BASE_URL}/{orgnr}"
        try:
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                data["_source_url"] = url
                return data
            elif response.status_code == 404:
                logger.warning("Entity %s not found in Enhetsregisteret.", orgnr)
                return None
            elif response.status_code == 410:
                logger.warning("Entity %s has been deleted/deregistered (HTTP 410).", orgnr)
                data = response.json() if response.text else {}
                data["slettet"] = True
                data["_source_url"] = url
                return data
            else:
                logger.error("Error fetching %s from Enhetsregisteret: HTTP %s", orgnr, response.status_code)
                return None
        except Exception as exc:
            logger.error("Exception fetching %s from Enhetsregisteret: %s", orgnr, exc)
            return None

    async def fetch_enhet_async(self, session, orgnr: str) -> Optional[Dict[str, Any]]:
        """Asynchronous fetch for high-throughput batch harvesting."""
        url = f"{BASE_URL}/{orgnr}"
        try:
            async with session.get(url, headers=HEADERS, timeout=self.timeout) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    data["_source_url"] = url
                    return data
                elif resp.status == 404:
                    return None
                elif resp.status == 410:
                    data = await resp.json()
                    data["slettet"] = True
                    data["_source_url"] = url
                    return data
                return None
        except Exception as exc:
            logger.debug("Async fetch failed for %s: %s", orgnr, exc)
            return None

    def search_entities(self, query: str, size: int = 10, page: int = 0) -> Dict[str, Any]:
        """Search entities by name or keyword."""
        url = f"{BASE_URL}?navn={query}&size={size}&page={page}"
        try:
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            return {"_embedded": {"enheter": []}, "page": {"totalElements": 0}}
        except Exception as exc:
            logger.error("Error searching entities for '%s': %s", query, exc)
            return {"_embedded": {"enheter": []}, "page": {"totalElements": 0}}
