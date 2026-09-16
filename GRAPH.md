# SignalPost Architecture Knowledge Graph (/graphify)
> Token-optimized knowledge graph for AI agents and LLMs. Compresses full repository architecture, data flows, and constraints into minimal tokens.

## 1. Relational Graph (Mermaid DSL)

```mermaid
graph TD
    CLI[run.py] -->|1-Command Entry| AGENT[signalpost.agent.orchestrator.SignalPostAgent]
    API[signalpost.api:FastAPI] -->|REST /api/company| AGENT
    UI[web/index.html & app.js] -->|Fetches| API
    
    subgraph Core [Validation & Models]
        VAL[validator.py: Modulo 11]
        MOD[models.py: CompanyProfile, Fact]
    end
    
    subgraph Sources [Permitted Public Sources Layer]
        ENH[brreg_enhet.py: Enhetsregisteret API]
        ROL[brreg_roller.py: Roller API]
        REG[brreg_regnskap.py: Regnskapsregisteret API]
        UPD[brreg_updates.py: Oppdateringer Stream]
        WEB[web_verifier.py: Domain Crawler]
        APF[apify_source.py: Real-time Scraper]
    end

    subgraph AgentEngine [Agent Core]
        RES[entity_resolver.py: Provenance & Matching]
        BLD[profile_builder.py: Fact Aggregator]
        SYN[syncer.py: Delta Freshness Tracker]
        AIS[ai_synthesizer.py: Briefing & Risks]
    end

    subgraph Data [Persistent Layer]
        DB[(data/company_profiles.db: SQLite)]
        JSON[data/profiles_1000.json: 1,054 Profiles]
        JSONL[data/profiles_1000.jsonl: Stream JSON]
        CSV[data/profiles_1000_summary.csv: Metrics]
    end

    AGENT --> VAL
    AGENT --> ENH & ROL & REG & UPD & WEB
    ENH & ROL & REG & UPD & WEB --> RES
    RES --> BLD
    BLD --> MOD
    AGENT --> SYN
    AGENT --> AIS
    AGENT --> DB
    DB --> JSON & JSONL & CSV
```

---

## 2. Dense Entity-Relation Index (Token-Optimized)

```json
{
  "project": "SignalPost",
  "domain": "Norwegian Corporate Intelligence",
  "license": "NLOD 2.0 / CC BY 4.0 (Free Norwegian Open Data)",
  "nodes": {
    "run.py": {"type": "cli_entry", "exec": "python run.py --serve | --orgnr <id> | --batch 1000"},
    "validator": {"weights": [3,2,7,6,5,4,3,2], "algorithm": "Modulo 11", "target": "9-digit orgnr"},
    "enhetsregisteret": {"endpoint": "https://data.brreg.no/enhetsregisteret/api/enheter/{orgnr}", "output": "name, form, address, NACE, employees, status"},
    "roller": {"endpoint": "https://data.brreg.no/enhetsregisteret/api/enheter/{orgnr}/roller", "output": "CEO, Chair, Board, Auditor"},
    "regnskap": {"endpoint": "https://data.brreg.no/regnskapsregisteret/regnskap/{orgnr}", "output": "revenue, EBIT, net_profit, assets, equity"},
    "oppdateringer": {"endpoint": "https://data.brreg.no/enhetsregisteret/api/oppdateringer/enheter", "output": "update_id, timestamp, delta_events"},
    "entity_resolver": {"rules": ["orgnr_primary_key_invariance", "levenshtein_name_similarity>=0.82", "historical_name_matching"]},
    "syncer": {"evaluates": ["latest_update_id > cached_id", "registry_timestamp > cached_timestamp", "ttl_hours=48"]},
    "dataset": {"records": 1054, "facts": 11837, "formats": ["json", "jsonl", "csv", "db"]}
  },
  "edges": [
    ["run.py", "CALLS", "SignalPostAgent"],
    ["SignalPostAgent", "VALIDATES_WITH", "validator"],
    ["SignalPostAgent", "QUERIES", "enhetsregisteret"],
    ["SignalPostAgent", "QUERIES", "roller"],
    ["SignalPostAgent", "QUERIES", "regnskap"],
    ["SignalPostAgent", "MONITORS_DELTA", "oppdateringer"],
    ["enhetsregisteret", "DISAMBIGUATED_BY", "entity_resolver"],
    ["entity_resolver", "GROUNDS_INTO", "profile_builder"],
    ["profile_builder", "STORES_INTO", "data/company_profiles.db"]
  ]
}
```

---

## 3. Operational Invariants
- `INV-01`: Every fact MUST carry `source_name`, `source_url`, `source_date`, and `confidence`.
- `INV-02`: Orgnr must pass Modulo 11 check before any network request is issued.
- `INV-03`: Zero external data costs — all registry queries target sovereign Norwegian open APIs.
- `INV-04`: Frontend presentation remains clean & retro-editorial; backend telemetry is segregated into `/api/stats` and dedicated inspector views.
