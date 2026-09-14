"""
Client for Brønnøysundregistrene Regnskapsregisteret (Register of Company Accounts).
Endpoint: https://data.brreg.no/regnskapsregisteret/regnskap/{orgnr}
License: Norwegian Licence for Open Government Data (NLOD 2.0)
"""

import logging
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://data.brreg.no/regnskapsregisteret/regnskap"
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "SignalPost-Agent/1.0",
}


class BrregRegnskapSource:
    """Client for retrieving audited annual financial statements."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def fetch_accounts(self, orgnr: str) -> Optional[List[Dict[str, Any]]]:
        """Fetches annual accounts for the organization."""
        url = f"{BASE_URL}/{orgnr}"
        try:
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                # If wrapped in list or dict with 'value'
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return data.get("value", [data])
                return []
            elif response.status_code == 404:
                return None
            else:
                logger.debug("Regnskap fetch returned HTTP %s for %s", response.status_code, orgnr)
                return None
        except Exception as exc:
            logger.debug("Exception fetching regnskap for %s: %s", orgnr, exc)
            return None

    async def fetch_accounts_async(self, session, orgnr: str) -> Optional[List[Dict[str, Any]]]:
        """Asynchronous fetch for batch ingestion."""
        url = f"{BASE_URL}/{orgnr}"
        try:
            async with session.get(url, headers=HEADERS, timeout=self.timeout) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict):
                        return data.get("value", [data])
                    return []
                return None
        except Exception as exc:
            logger.debug("Async regnskap fetch failed for %s: %s", orgnr, exc)
            return None

    @staticmethod
    def parse_latest_financials(accounts_list: Optional[List[Dict[str, Any]]], orgnr: str) -> Optional[Dict[str, Any]]:
        """Extracts key financial figures from the latest submitted annual statement."""
        if not accounts_list or not isinstance(accounts_list, list):
            return None

        # Take first (latest submitted) account
        latest = accounts_list[0]
        periode = latest.get("regnskapsperiode", {})
        start_date = periode.get("fraDato", "")
        end_date = periode.get("tilDato", "")
        year = int(end_date[:4]) if end_date and len(end_date) >= 4 else 0
        currency = latest.get("valuta", "NOK")

        # Revenue & profit
        res = latest.get("resultatregnskapResultat", {})
        driftsresultat_obj = res.get("driftsresultat", {})
        revenue = driftsresultat_obj.get("driftsinntekter") or driftsresultat_obj.get("salgsinntekter")
        operating_profit = driftsresultat_obj.get("driftsresultat")
        net_profit = res.get("aarsresultat") or res.get("ordinaertResultatEtterSkattekostnad")

        # Balance sheet
        eiendeler_obj = latest.get("eiendeler", {})
        total_assets = eiendeler_obj.get("sumEiendeler")

        eq_debt_obj = latest.get("egenkapitalGjeld", {})
        egenkapital_obj = eq_debt_obj.get("egenkapital", {})
        total_equity = egenkapital_obj.get("sumEgenkapital")

        gjeld_obj = eq_debt_obj.get("gjeldOversikt", {})
        total_debt = gjeld_obj.get("sumGjeld")

        source_url = f"{BASE_URL}/{orgnr}"

        return {
            "year": year,
            "period_start": start_date,
            "period_end": end_date,
            "currency": currency,
            "revenue": float(revenue) if revenue is not None else None,
            "operating_profit": float(operating_profit) if operating_profit is not None else None,
            "net_profit": float(net_profit) if net_profit is not None else None,
            "total_assets": float(total_assets) if total_assets is not None else None,
            "total_equity": float(total_equity) if total_equity is not None else None,
            "total_debt": float(total_debt) if total_debt is not None else None,
            "source_url": source_url,
            "submission_id": str(latest.get("journalnr") or latest.get("id") or ""),
        }
