"""
Apify Source Adapter for Real-Time Company Intelligence.
Allows querying Apify Store Actors or custom Apify crawlers to extract
real-time company facts, public web footprints, or registry mirrors.
"""

import logging
import os
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)

# Replace with your actual Apify API Token or set via environment variable:
# export APIFY_API_TOKEN="apify_api_XXXXXXXXXXXXXXX"
DEFAULT_APIFY_TOKEN = os.environ.get("APIFY_API_TOKEN", "YOUR_APIFY_API_TOKEN_HERE")

# Replace with your target Apify Actor ID (e.g., a company scraper, web scraper, or LinkedIn crawler)
# Examples:
# - "apify/web-scraper"
# - "compass/crawler-google-places"
# - "curious_coder/linkedin-company-scraper"
# - "YOUR_USERNAME/norway-company-actor"
DEFAULT_ACTOR_ID = os.environ.get("APIFY_ACTOR_ID", "YOUR_ACTOR_ID_HERE")


class ApifyCompanySource:
    """
    Client for triggering and retrieving real-time company intelligence
    via Apify's synchronous actor execution API.
    """

    def __init__(
        self,
        api_token: Optional[str] = None,
        actor_id: Optional[str] = None,
        timeout: int = 60,
    ):
        self.api_token = api_token or DEFAULT_APIFY_TOKEN
        self.actor_id = actor_id or DEFAULT_ACTOR_ID
        self.timeout = timeout
        self.session = requests.Session()

    def fetch_company_realtime(
        self,
        company_query: str,
        country_code: str = "NO",
        custom_input: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Executes an Apify actor synchronously and returns the output dataset items directly.
        
        Endpoint: POST https://api.apify.com/v2/acts/{actorId}/run-sync-get-dataset-items?token={token}
        """
        if not self.api_token or "YOUR_APIFY_API_TOKEN" in self.api_token:
            logger.warning("Apify API Token not configured. Please provide a valid APIFY_API_TOKEN.")
            return [{
                "status": "placeholder",
                "message": "Please set APIFY_API_TOKEN environment variable or pass api_token to ApifyCompanySource.",
                "query": company_query,
            }]

        # Endpoint that starts the actor, waits for completion, and returns the dataset
        url = f"https://api.apify.com/v2/acts/{self.actor_id}/run-sync-get-dataset-items"
        
        params = {
            "token": self.api_token,
            "timeout": self.timeout,
        }

        # Actor input payload placeholder: customize to match your chosen actor's schema
        actor_input = custom_input or {
            "search": company_query,
            "country": country_code,
            "maxItems": 1,
            # For general scrapers like apify/web-scraper:
            # "startUrls": [{"url": f"https://www.google.com/search?q={company_query}+norway"}],
        }

        try:
            response = self.session.post(
                url,
                params=params,
                json=actor_input,
                timeout=self.timeout + 10,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code in (200, 201):
                items = response.json()
                logger.info("Successfully received %d items from Apify actor %s", len(items), self.actor_id)
                return items
            else:
                logger.error(
                    "Apify API error: HTTP %s - %s", response.status_code, response.text
                )
                return []

        except Exception as exc:
            logger.error("Exception occurred while communicating with Apify API: %s", exc)
            return []


# Example usage & verification block
if __name__ == "__main__":
    print("=" * 70)
    print("  APIFY REAL-TIME COMPANY FETCHER PLACEHOLDER")
    print("=" * 70)
    
    # 1. Initialize client with your token and actor
    client = ApifyCompanySource(
        api_token=os.environ.get("APIFY_API_TOKEN", "YOUR_APIFY_API_TOKEN_HERE"),
        actor_id="YOUR_ACTOR_ID_HERE",
    )

    # 2. Example lookup: Norwegian company number or name
    test_orgnr = "923609016"  # Equinor ASA
    print(f"[*] Querying Apify for: {test_orgnr}")
    
    results = client.fetch_company_realtime(test_orgnr)
    print(f"[+] Response: {results}")
