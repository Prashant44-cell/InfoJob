"""
Client for Brønnøysundregistrene Oppdateringer (Delta Update Stream).
Endpoint: https://data.brreg.no/enhetsregisteret/api/oppdateringer/enheter
Used to track delta modifications, change events, and keep profiles current.
"""

import logging
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://data.brreg.no/enhetsregisteret/api/oppdateringer/enheter"
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "SignalPost-Agent/1.0",
}


class BrregUpdatesSource:
    """Client for monitoring registry delta events and change history."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def get_latest_update_for_entity(self, orgnr: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the latest update event for a given entity.
        Queries the last page of the updates stream for this specific orgnr.
        """
        url = f"{BASE_URL}?organisasjonsnummer={orgnr}&size=1"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code != 200:
                return None
            data = resp.json()
            page = data.get("page", {})
            total_pages = page.get("totalPages", 0)

            if total_pages == 0:
                return None

            # Fetch the last page which contains the newest update event
            last_page_num = max(0, total_pages - 1)
            last_page_url = f"{BASE_URL}?organisasjonsnummer={orgnr}&page={last_page_num}&size=1"
            last_resp = self.session.get(last_page_url, timeout=self.timeout)
            if last_resp.status_code == 200:
                last_data = last_resp.json()
                events = last_data.get("_embedded", {}).get("oppdaterteEnheter", [])
                if events:
                    event = events[-1]
                    event["_source_url"] = last_page_url
                    return event
            return None
        except Exception as exc:
            logger.debug("Exception fetching updates for %s: %s", orgnr, exc)
            return None

    def get_recent_stream_updates(self, size: int = 50) -> List[Dict[str, Any]]:
        """
        Fetches the latest registered events across all Norwegian entities.
        """
        try:
            # First fetch page 0 to know the totalPages
            resp = self.session.get(f"{BASE_URL}?size={size}", timeout=self.timeout)
            if resp.status_code != 200:
                return []
            data = resp.json()
            total_pages = data.get("page", {}).get("totalPages", 0)
            if total_pages == 0:
                return []

            # Fetch the last page of updates
            last_page_num = max(0, total_pages - 1)
            last_url = f"{BASE_URL}?page={last_page_num}&size={size}"
            last_resp = self.session.get(last_url, timeout=self.timeout)
            if last_resp.status_code == 200:
                return last_resp.json().get("_embedded", {}).get("oppdaterteEnheter", [])
            return []
        except Exception as exc:
            logger.error("Failed to fetch recent update stream: %s", exc)
            return []
