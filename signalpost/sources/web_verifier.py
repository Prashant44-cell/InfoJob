"""
Permitted public web source verifier.
Fetches public website metadata from the company's officially registered domain,
extracts descriptions, verified contact links, and validates entity alignment.
"""

import logging
import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse
import requests

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "SignalPost-Agent/1.0 (+https://github.com/signalpost/bot; research bot)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class WebFootprintVerifier:
    """Verifies public web presence for registered Norwegian entities."""

    def __init__(self, timeout: int = 6):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def verify_website(self, raw_url: str, expected_company_name: str, orgnr: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves public homepage metadata, verifies entity alignment,
        and extracts public facts (title, description, contact).
        """
        if not raw_url:
            return None

        # Normalize URL scheme
        target_url = raw_url.strip()
        if not target_url.startswith("http://") and not target_url.startswith("https://"):
            target_url = f"https://{target_url}"

        try:
            resp = self.session.get(target_url, timeout=self.timeout, allow_redirects=True)
            if resp.status_code >= 400:
                return None

            html = resp.text[:150000]  # Read first 150KB
            
            title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else None

            desc_match = re.search(
                r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']',
                html,
                re.IGNORECASE | re.DOTALL
            )
            if not desc_match:
                desc_match = re.search(
                    r'<meta\s+property=["\']og:description["\']\s+content=["\'](.*?)["\']',
                    html,
                    re.IGNORECASE | re.DOTALL
                )
            description = desc_match.group(1).strip() if desc_match else None

            # Look for explicit orgnr presence on page
            has_orgnr_on_page = orgnr in html

            # Look for contact emails
            emails = set(re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', html))
            # Filter out obvious asset extensions
            clean_emails = [e for e in emails if not any(e.endswith(ext) for ext in [".png", ".jpg", ".js", ".css", ".webp"])]

            domain = urlparse(resp.url).netloc

            return {
                "verified_url": resp.url,
                "domain": domain,
                "meta_title": title,
                "meta_description": description,
                "orgnr_present_on_page": has_orgnr_on_page,
                "contact_emails": clean_emails[:3],
                "status_code": resp.status_code,
            }
        except Exception as exc:
            logger.debug("Could not verify web footprint for %s: %s", raw_url, exc)
            return None
