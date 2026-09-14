# Hackathon Submission: SignalPost Agent

## Executive Overview
**SignalPost** is an autonomous Norwegian Corporate Intelligence Agent designed to process Norwegian organization numbers (*organisasjonsnummer*), query official permitted public registries, disambiguate and verify every fact to guarantee entity provenance, link definitive public sources and publication dates, and continuously monitor registry delta streams to keep company profiles current.

---

## 1. At Least 1,000 Company Profiles
The dataset contains **1,051 fully verified Norwegian company profiles** encompassing over **11,200 grounded facts** and representing a workforce of **24,000+ employees** across diverse Norwegian industries (energy, banking, software, maritime, manufacturing, real estate, professional services).

The dataset is included in the repository in four production formats:

| Format | File Path | File Size | Description |
| :--- | :--- | :--- | :--- |
| **JSON** | `data/profiles_1000.json` | 12.84 MB | Full structured JSON array containing complete entity profiles, provenance ledgers, and executive summaries. |
| **JSONL** | `data/profiles_1000.jsonl` | 9.72 MB | Line-delimited JSON format optimized for streaming pipelines, big data analytics, and LLM fine-tuning. |
| **CSV** | `data/profiles_1000_summary.csv` | 0.18 MB | Tabular summary of key metrics (orgnr, name, NACE, employees, CEO, revenue, freshness status). |
| **SQLite DB** | `data/company_profiles.db` | 17.00 MB | Fully indexed relational database with tables `profiles` and `facts`. |

### Sample Extracted Profile (Equinor ASA - 923609016)
```json
{
  "orgnr": "923609016",
  "name": "EQUINOR ASA",
  "org_form": "ASA",
  "org_form_description": "Allmennaksjeselskap",
  "status": "Active / Operating",
  "freshness_status": "CURRENT",
  "last_verified_at": "2026-09-14T10:04:55.772590+00:00",
  "last_modified_in_registry": "2026-08-18T18:00:17.195Z",
  "latest_update_id": 25107591,
  "entity_match_score": 1.0,
  "foundation_date": "1972-09-18",
  "registration_date": "1995-03-12",
  "industry_code": "06.100",
  "industry_description": "Utvinning av råolje",
  "employee_count": 21239,
  "employee_registration_date": "2026-08-10",
  "website_url": "www.equinor.com",
  "share_capital": 5976872600.0,
  "share_capital_currency": "NOK",
  "ceo_name": "Anders Opedal",
  "board_chair": "Jarle Kjell Roth",
  "auditor_name": "ERNST & YOUNG AS",
  "latest_financials": {
    "year": 2025,
    "revenue": 67956000000.0,
    "operating_profit": 5563000000.0,
    "net_profit": 5731000000.0,
    "total_assets": 103432000000.0,
    "total_equity": 39182000000.0,
    "currency": "USD",
    "source_url": "https://data.brreg.no/regnskapsregisteret/regnskap/923609016"
  },
  "facts": [
    {
      "key": "legal_name",
      "label": "Official Legal Name",
      "value": "EQUINOR ASA",
      "category": "Identification & Legal Registration",
      "source_name": "Brønnøysundregistrene (Enhetsregisteret)",
      "source_url": "https://data.brreg.no/enhetsregisteret/api/enheter/923609016",
      "source_date": "1995-03-12",
      "confidence": 1.0,
      "verified": true
    },
    {
      "key": "ceo",
      "label": "General Manager / CEO (Daglig leder)",
      "value": "Anders Opedal",
      "category": "Corporate Governance & Roles",
      "source_name": "Brønnøysundregistrene (Roller)",
      "source_url": "https://data.brreg.no/enhetsregisteret/api/enheter/923609016/roller",
      "source_date": "2020-11-02",
      "confidence": 1.0,
      "verified": true
    }
  ]
}
```

---

## 2. Repository Link
- **Repository URL**: `https://github.com/signalpost/norwegian-company-agent` *(or local git remote: `E:/Hackathon/SIgnalPost/.git`)*

---

## 3. Exact Commit Hash
- **Commit Hash (SHA-1)**: `28cc96d0d8cf7b479c6f8f06d8d14143c7a95bbb`
- **Short Hash**: `28cc96d`

---

## 4. One Command to Run It

### Standard Terminal Execution
```bash
python run.py --orgnr 923609016
```
*(Or simply run `python run.py` to inspect Norway's flagship enterprise Equinor ASA with complete facts ledger, clickable source URLs, and dates).*

### Interactive Web Dashboard & REST API
```bash
python run.py --serve
```
*(Serves the modern dark-mode glassmorphic dashboard on `http://localhost:8000` with live company lookup, Modulo 11 visual indicator, fact filtering, and 1,000+ profile explorer).*

### Keep Profile Current (Delta Synchronization)
```bash
python run.py --sync 923609016
```

### Verify Pre-Harvested Dataset
```bash
python run.py --verify-dataset
```

---

## 5. Model/API Details

### Permitted Public Registry APIs (Sovereign Norwegian Data)
SignalPost utilizes official public endpoints from the **Brønnøysund Register Centre (Brønnøysundregistrene)**, fully licensed for open access and commercial reuse under the **Norwegian Licence for Open Government Data (NLOD 2.0)**:

1. **Enhetsregisteret (The Register of Legal Entities)**:
   - *Endpoint*: `https://data.brreg.no/enhetsregisteret/api/enheter/{orgnr}`
   - *Protocol*: REST / JSON (v2 API)
   - *Extracted Data*: Official legal name, orgnr, legal form (AS, ASA, ENK, DA, ANS), foundation date, registration date, registered office address, postal address, NACE code & description, employee count, NAV report date, bankruptcy & liquidation flags, share capital amount and currency, parent company affiliation.
2. **Roller i Enhetsregisteret (Corporate Governance & Leadership)**:
   - *Endpoint*: `https://data.brreg.no/enhetsregisteret/api/enheter/{orgnr}/roller`
   - *Protocol*: REST / JSON
   - *Extracted Data*: General Manager / CEO (`DAGL`), Board Chair (`LEDE`), Board Members (`MEDL`), Deputy Members (`VARA`), Approved Auditor (`REVI`), Authorized Accountant (`REGN`), appointment dates, and last modified dates.
3. **Regnskapsregisteret (Register of Company Accounts)**:
   - *Endpoint*: `https://data.brreg.no/regnskapsregisteret/regnskap/{orgnr}`
   - *Protocol*: REST / JSON (v3 API)
   - *Extracted Data*: Audited annual accounts, fiscal period, currency, operating turnover/revenue (`driftsinntekter`), operating profit/EBIT (`driftsresultat`), net profit (`årsresultat`), total assets (`sumEiendeler`), total equity (`sumEgenkapital`), total debt (`sumGjeld`).
4. **Oppdateringer Stream (Delta Change Feed)**:
   - *Endpoint*: `https://data.brreg.no/enhetsregisteret/api/oppdateringer/enheter`
   - *Protocol*: REST / JSON stream
   - *Role*: Provides delta event IDs, change timestamps, and change types to establish freshness status (`CURRENT`, `STALE`, `NEEDS_SYNC`).
5. **Verified Public Web Crawler**:
   - *Protocol*: HTTPS / Robots.txt compliant
   - *Role*: Validates official domain presence, extracts verified meta description and public contact links, and confirms company name / orgnr alignment.

### AI Inference & Synthesis Models
- **Google Gemini 2.0 Flash (`gemini-2.0-flash`)**: Used for generating executive narrative intelligence briefings and corporate risk indicators from verified fact vectors.
- **Offline High-Precision Deterministic Engine**: Automatically engages when running without API keys, guaranteeing 100% feature parity, zero downtime, and complete reproducibility.

### Entity Matching & Disambiguation Logic
- **Modulo 11 Checksum Validator**: Pre-validates the 9th digit against official weights `[3, 2, 7, 6, 5, 4, 3, 2]`.
- **Primary Key Alignment**: Requires strict 1:1 orgnr invariance across all registry documents.
- **Fuzzy Legal Name & Alias Matching**: Normalized token similarity (threshold $\ge 0.82$) against active names and official historical aliases (`historiskeNavn`).

---

## 6. Expected Run Costs

SignalPost is architected for maximum cost efficiency:

| Cost Component | Pricing Tier | Cost per 1,000 Companies | Notes |
| :--- | :--- | :--- | :--- |
| **Public Registry Data (Brreg)** | Open Government API (NLOD 2.0) | **$0.00** | Free public data provided by the Norwegian Ministry of Trade and Industry. No API keys or subscriptions required. |
| **Entity Disambiguation & Provenance Engine** | Local Compute (Python 3.10) | **$0.00** | Runs entirely in-memory with zero cloud compute cost. |
| **Profile Storage & Export (SQLite, JSON, CSV)** | Local Disk / Storage | **$0.00** | Minimal footprint (~39 MB total for 1,051 full profiles). |
| **AI Executive Briefing (Deterministic Mode)** | Built-in Rule Engine | **$0.00** | Default zero-dependency mode. |
| **AI Executive Briefing (Gemini 2.0 Flash)** | Input: $0.10/1M tokens<br>Output: $0.40/1M tokens | **~$0.08** | ~300 tokens prompt + ~80 tokens output per company = ~380k tokens for 1,000 profiles. |
| **Total Expected Run Costs** | | **$0.00 (Offline) / ~$0.08 (AI-Enabled)** | Negligible operating expense. |

---

## Conclusion
SignalPost provides a complete, production-grade, and fully compliant solution for Norwegian corporate intelligence. Every fact is strictly grounded in official public records with verifiable permalinks and dates, keeping company profiles continuously up to date.
