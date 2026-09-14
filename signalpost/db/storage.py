"""
SQLite and File-based Storage Engine for SignalPost company profiles.
Supports indexing, querying, and bulk export to JSON, JSONL, and CSV.
"""

import csv
import json
import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional

from signalpost.core.models import CompanyProfile, Fact

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "company_profiles.db")


class ProfileStorage:
    """Manages SQLite persistent storage and export formats for company profiles."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initializes database schema and indexes."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS profiles (
                    orgnr TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    org_form TEXT,
                    status TEXT,
                    freshness_status TEXT,
                    industry_code TEXT,
                    industry_description TEXT,
                    employee_count INTEGER,
                    ceo_name TEXT,
                    board_chair TEXT,
                    revenue REAL,
                    currency TEXT,
                    latest_financial_year INTEGER,
                    last_verified_at TEXT,
                    last_modified_in_registry TEXT,
                    profile_json TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    orgnr TEXT NOT NULL,
                    fact_key TEXT NOT NULL,
                    label TEXT NOT NULL,
                    value_text TEXT,
                    category TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    source_date TEXT,
                    confidence REAL DEFAULT 1.0,
                    retrieved_at TEXT NOT NULL,
                    FOREIGN KEY(orgnr) REFERENCES profiles(orgnr) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_profiles_name ON profiles(name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_profiles_industry ON profiles(industry_code)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_facts_orgnr ON facts(orgnr)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_facts_key ON facts(fact_key)")
            conn.commit()

    def save_profile(self, profile: CompanyProfile) -> None:
        """Saves or updates a company profile and its associated facts ledger."""
        revenue = None
        fin_year = None
        curr = "NOK"
        if profile.latest_financials:
            revenue = profile.latest_financials.revenue
            fin_year = profile.latest_financials.year
            curr = profile.latest_financials.currency

        # Support Pydantic v1 and v2
        if hasattr(profile, "model_dump_json"):
            profile_json = profile.model_dump_json()
        else:
            profile_json = profile.json()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO profiles (
                    orgnr, name, org_form, status, freshness_status,
                    industry_code, industry_description, employee_count,
                    ceo_name, board_chair, revenue, currency,
                    latest_financial_year, last_verified_at,
                    last_modified_in_registry, profile_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(orgnr) DO UPDATE SET
                    name=excluded.name,
                    org_form=excluded.org_form,
                    status=excluded.status,
                    freshness_status=excluded.freshness_status,
                    industry_code=excluded.industry_code,
                    industry_description=excluded.industry_description,
                    employee_count=excluded.employee_count,
                    ceo_name=excluded.ceo_name,
                    board_chair=excluded.board_chair,
                    revenue=excluded.revenue,
                    currency=excluded.currency,
                    latest_financial_year=excluded.latest_financial_year,
                    last_verified_at=excluded.last_verified_at,
                    last_modified_in_registry=excluded.last_modified_in_registry,
                    profile_json=excluded.profile_json
            """, (
                profile.orgnr,
                profile.name,
                profile.org_form,
                profile.status,
                profile.freshness_status,
                profile.industry_code,
                profile.industry_description,
                profile.employee_count,
                profile.ceo_name,
                profile.board_chair,
                revenue,
                curr,
                fin_year,
                profile.last_verified_at,
                profile.last_modified_in_registry,
                profile_json,
            ))

            # Replace facts
            cursor.execute("DELETE FROM facts WHERE orgnr = ?", (profile.orgnr,))
            facts_to_insert = [
                (
                    profile.orgnr,
                    f.key,
                    f.label,
                    str(f.value) if f.value is not None else "",
                    f.category,
                    f.source_name,
                    f.source_url,
                    f.source_date or "",
                    f.confidence,
                    f.retrieved_at,
                )
                for f in profile.facts
            ]
            cursor.executemany("""
                INSERT INTO facts (
                    orgnr, fact_key, label, value_text, category,
                    source_name, source_url, source_date, confidence, retrieved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, facts_to_insert)

            conn.commit()

    @staticmethod
    def _parse_profile_json(json_str: str) -> CompanyProfile:
        if hasattr(CompanyProfile, "model_validate_json"):
            return CompanyProfile.model_validate_json(json_str)
        return CompanyProfile.parse_raw(json_str)

    def get_profile(self, orgnr: str) -> Optional[CompanyProfile]:
        """Loads a single profile by orgnr from database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT profile_json FROM profiles WHERE orgnr = ?", (orgnr,))
            row = cursor.fetchone()
            if row:
                return self._parse_profile_json(row["profile_json"])
            return None

    def count_profiles(self) -> int:
        """Returns total count of stored profiles."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM profiles")
            return cursor.fetchone()[0]

    def list_profiles(self, limit: int = 50, offset: int = 0, search: Optional[str] = None) -> List[CompanyProfile]:
        """Lists profiles with optional search and pagination."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if search:
                term = f"%{search}%"
                cursor.execute("""
                    SELECT profile_json FROM profiles
                    WHERE name LIKE ? OR orgnr LIKE ? OR industry_description LIKE ?
                    ORDER BY employee_count DESC NULLS LAST
                    LIMIT ? OFFSET ?
                """, (term, term, term, limit, offset))
            else:
                cursor.execute("""
                    SELECT profile_json FROM profiles
                    ORDER BY employee_count DESC NULLS LAST
                    LIMIT ? OFFSET ?
                """, (limit, offset))

            rows = cursor.fetchall()
            return [self._parse_profile_json(r["profile_json"]) for r in rows]

    def export_to_json(self, output_path: str) -> int:
        """Exports all profiles to a single JSON array file."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT profile_json FROM profiles ORDER BY name ASC")
            rows = cursor.fetchall()
            profiles_data = [json.loads(r["profile_json"]) for r in rows]

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(profiles_data, f, ensure_ascii=False, indent=2)

        return len(profiles_data)

    def export_to_jsonl(self, output_path: str) -> int:
        """Exports all profiles to a line-delimited JSONL file."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        count = 0
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT profile_json FROM profiles ORDER BY name ASC")
            with open(output_path, "w", encoding="utf-8") as f:
                for row in cursor:
                    f.write(row["profile_json"] + "\n")
                    count += 1
        return count

    def export_to_csv(self, output_path: str) -> int:
        """Exports key metrics from all profiles to CSV."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT orgnr, name, org_form, status, freshness_status,
                       industry_code, industry_description, employee_count,
                       ceo_name, board_chair, revenue, currency,
                       latest_financial_year, last_verified_at
                FROM profiles
                ORDER BY employee_count DESC NULLS LAST
            """)
            rows = cursor.fetchall()

        fieldnames = [
            "orgnr", "name", "org_form", "status", "freshness_status",
            "industry_code", "industry_description", "employee_count",
            "ceo_name", "board_chair", "revenue", "currency",
            "latest_financial_year", "last_verified_at"
        ]

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows:
                writer.writerow(dict(r))

        return len(rows)
