# SignalPost 🇳🇴
### Autonomous Norwegian Corporate Intelligence Agent

> **Live Company Verification • Strict Entity Disambiguation • Source Grounding • Delta Freshness Synchronization**

SignalPost is an autonomous corporate intelligence agent specifically built for Norwegian enterprises (*organisasjonsnummer*). Given any 9-digit Norwegian company number, the agent searches permitted public sources, disambiguates each fact to guarantee entity provenance, anchors every claim with official source links and publication dates, and monitors registry delta streams to keep company profiles continuously up to date.

---

## ⚡ Quick Start: One Command to Run It

```bash
# Query Equinor ASA (923609016)
python run.py --orgnr 923609016

# Or simply run default inspection:
python run.py
```

### Launch Interactive Web Dashboard & REST API
```bash
python run.py --serve
# Open http://localhost:8000
```

### Synchronize Freshness via Registry Delta Stream
```bash
python run.py --sync 923609016
```

### Verify Pre-Harvested 1,000+ Company Dataset
```bash
python run.py --verify-dataset
```

---

## 🏛️ Permitted Public Sources & Grounding

SignalPost strictly adheres to permitted open data frameworks under the **Norwegian Licence for Open Government Data (NLOD 2.0)** and **Creative Commons Attribution 4.0 (CC BY 4.0)**:

| Source Name | Official Authority | Protocol & License | Key Facts Extracted |
| :--- | :--- | :--- | :--- |
| **Enhetsregisteret** | Brønnøysund Register Centre | Open REST API (NLOD 2.0) | Legal name, orgnr, org form, foundation date, registration date, business/postal address, NACE codes, employee count, NAV report date, solvency & bankruptcy status, share capital. |
| **Roller i Enhetsregisteret** | Brønnøysund Register Centre | Open REST API (NLOD 2.0) | Corporate governance, CEO (Daglig leder), Board Chair (Styreleder), Board members, Registered Auditor (Revisor), appointment dates. |
| **Regnskapsregisteret** | Brønnøysund Register Centre | Open REST API (NLOD 2.0) | Audited annual financial statements, revenue/turnover, operating profit (EBIT), net income (årsresultat), total assets, equity, debt, currency. |
| **Oppdateringer Stream** | Brønnøysund Register Centre | Open REST API (NLOD 2.0) | Real-time delta update stream with update IDs, modification timestamps, and change types to detect staleness and keep profiles current. |
| **Official Domains** | Company Websites & norid.no | Public Web (Robots compliant) | Official web description, domain ownership alignment, contact details. |

---

## 🎯 Strict Entity Disambiguation Engine
> *"Make sure each fact belongs to the right company"*

To prevent data contamination, hallucination, or cross-entity misattribution, SignalPost implements a multi-tier resolution pipeline:

1. **Modulo 11 Checksum Pre-validation**: Mathematically checks the 9th control digit using weights `[3, 2, 7, 6, 5, 4, 3, 2]`. Any illegal or corrupted organization number is discarded before querying.
2. **Primary Key Invariance**: Every record from `enheter`, `roller`, `regnskap`, and `oppdateringer` is pinned to the target `organisasjonsnummer`.
3. **Legal Name & Historical Alias Alignment**: Computes token and character similarity against both active legal names and historical aliases from the official `historiskeNavn` registry (e.g. recognizing *Statoil* / *StatoilHydro* as legitimate historical aliases of *Equinor*).
4. **Fact-Level Provenance Ledger**: Every single extracted fact is decorated with:
   - Fact title & value
   - Permitted public source name & URL
   - Official registration or publication date
   - Retrieval timestamp (ISO 8601)
   - Verification status & confidence score (1.0 = 100%)

---

## 🔄 Keeping Profiles Current
> *"keep profiles current"*

SignalPost connects to the official Brønnøysundregistrene delta stream (`https://data.brreg.no/enhetsregisteret/api/oppdateringer/enheter`):
- Records the latest `oppdateringsid` and timestamp during each retrieval.
- Evaluates profile freshness (`CURRENT`, `STALE`, `NEEDS_SYNC`).
- When a new registry update event is published for an entity, the delta sync engine detects the advancement, fetches modified fields, updates the profile, and appends an entry to `change_history`.

---

## 📦 1,000+ Company Profiles Dataset

SignalPost includes a verified dataset of **1,051 real Norwegian companies** across diverse industries (Energy, Banking, Technology, Maritime, Manufacturing, Retail, Healthcare):

- **Structured JSON Array**: `data/profiles_1000.json` (12.8 MB)
- **Line-delimited JSONL**: `data/profiles_1000.jsonl` (9.7 MB)
- **Tabular Metrics CSV**: `data/profiles_1000_summary.csv` (187 KB)
- **Indexed SQLite Database**: `data/company_profiles.db` (17.0 MB)

---

## 💰 Run Costs & Model Details

- **Base Public Data Costs**: **$0.00** (Brønnøysundregistrene APIs are completely free open government services).
- **AI Executive Briefing**:
  - Offline High-Precision Deterministic Engine: **$0.00**
  - Optional Google Gemini 2.0 Flash API: **~$0.0001 per profile summary**
- **Total Expected Run Costs for 1,000 Profiles**: **$0.00 to <$0.10**.

---

## 🧪 Automated Testing
```bash
python -m unittest discover tests
```
Runs 11 test suites covering Modulo 11 validation, entity disambiguation, cross-source provenance, and persistence.
