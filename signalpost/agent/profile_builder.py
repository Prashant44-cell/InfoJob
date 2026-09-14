"""
Profile Builder: Aggregates multi-source public data into a unified,
provenance-grounded CompanyProfile with verified facts, source URLs, and dates.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from signalpost.agent.entity_resolver import EntityResolver
from signalpost.core.models import (
    CompanyProfile,
    Fact,
    FactCategory,
    FinancialYearData,
    RoleItem,
)

logger = logging.getLogger(__name__)


class ProfileBuilder:
    """Builds comprehensive company profiles with complete fact-level provenance."""

    def __init__(self, resolver: Optional[EntityResolver] = None):
        self.resolver = resolver or EntityResolver()

    def build(
        self,
        orgnr: str,
        enhet_raw: Dict[str, Any],
        roller_raw: Optional[Dict[str, Any]] = None,
        regnskap_raw: Optional[List[Dict[str, Any]]] = None,
        update_raw: Optional[Dict[str, Any]] = None,
        web_raw: Optional[Dict[str, Any]] = None,
    ) -> CompanyProfile:
        """
        Synthesizes raw data from all permitted public sources into a CompanyProfile.
        Decorates every individual fact with an exact source URL, date, and verification status.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        facts: List[Fact] = []
        source_url_enhet = enhet_raw.get("_source_url", f"https://data.brreg.no/enhetsregisteret/api/enheter/{orgnr}")

        # 1. Base Entity Details
        name = enhet_raw.get("navn", f"Entity {orgnr}")
        org_form_dict = enhet_raw.get("organisasjonsform", {})
        org_form = org_form_dict.get("kode", "AS")
        org_form_desc = org_form_dict.get("beskrivelse", "Aksjeselskap")

        # Legal Name
        reg_date = enhet_raw.get("registreringsdatoEnhetsregisteret")
        facts.append(
            self.resolver.build_verified_fact(
                key="legal_name",
                label="Official Legal Name",
                value=name,
                category=FactCategory.IDENTIFICATION,
                source_name="Brønnøysundregistrene (Enhetsregisteret)",
                source_url=source_url_enhet,
                source_date=reg_date,
                notes="Official name registered in Enhetsregisteret",
            )
        )

        # Organization Number
        facts.append(
            self.resolver.build_verified_fact(
                key="orgnr",
                label="Organization Number",
                value=orgnr,
                category=FactCategory.IDENTIFICATION,
                source_name="Brønnøysundregistrene (Enhetsregisteret)",
                source_url=source_url_enhet,
                source_date=reg_date,
                notes="Primary national identifier verified via Modulo 11",
            )
        )

        # Organization Form
        facts.append(
            self.resolver.build_verified_fact(
                key="org_form",
                label="Organization Form",
                value=f"{org_form} ({org_form_desc})",
                category=FactCategory.IDENTIFICATION,
                source_name="Brønnøysundregistrene (Enhetsregisteret)",
                source_url=source_url_enhet,
                source_date=reg_date,
            )
        )

        # Foundation & Registration Dates
        foundation_date = enhet_raw.get("stiftelsesdato")
        if foundation_date:
            facts.append(
                self.resolver.build_verified_fact(
                    key="foundation_date",
                    label="Foundation Date",
                    value=foundation_date,
                    category=FactCategory.IDENTIFICATION,
                    source_name="Brønnøysundregistrene (Enhetsregisteret)",
                    source_url=source_url_enhet,
                    source_date=foundation_date,
                )
            )

        if reg_date:
            facts.append(
                self.resolver.build_verified_fact(
                    key="registration_date",
                    label="Registration Date in Enhetsregisteret",
                    value=reg_date,
                    category=FactCategory.IDENTIFICATION,
                    source_name="Brønnøysundregistrene (Enhetsregisteret)",
                    source_url=source_url_enhet,
                    source_date=reg_date,
                )
            )

        # 2. Location & Address
        business_addr = enhet_raw.get("forretningsadresse")
        if business_addr:
            street = ", ".join(business_addr.get("adresse", []))
            postcode = business_addr.get("postnummer", "")
            city = business_addr.get("poststed", "")
            municipality = business_addr.get("kommune", "")
            full_addr = f"{street}, {postcode} {city} ({municipality})".strip(", ")
            facts.append(
                self.resolver.build_verified_fact(
                    key="business_address",
                    label="Registered Business Address",
                    value=full_addr,
                    category=FactCategory.LOCATION,
                    source_name="Brønnøysundregistrene (Enhetsregisteret)",
                    source_url=source_url_enhet,
                    source_date=reg_date,
                )
            )

        postal_addr = enhet_raw.get("postadresse")
        if postal_addr and postal_addr != business_addr:
            p_street = ", ".join(postal_addr.get("adresse", []))
            p_postcode = postal_addr.get("postnummer", "")
            p_city = postal_addr.get("poststed", "")
            full_postal = f"{p_street}, {p_postcode} {p_city}".strip(", ")
            facts.append(
                self.resolver.build_verified_fact(
                    key="postal_address",
                    label="Registered Postal Address",
                    value=full_postal,
                    category=FactCategory.LOCATION,
                    source_name="Brønnøysundregistrene (Enhetsregisteret)",
                    source_url=source_url_enhet,
                    source_date=reg_date,
                )
            )

        # 3. Industry & Activities
        nace1 = enhet_raw.get("naeringskode1", {})
        industry_code = nace1.get("kode")
        industry_desc = nace1.get("beskrivelse")
        if industry_code:
            facts.append(
                self.resolver.build_verified_fact(
                    key="industry_primary",
                    label="Primary Industry (NACE)",
                    value=f"{industry_code} - {industry_desc}",
                    category=FactCategory.INDUSTRY,
                    source_name="Brønnøysundregistrene (Enhetsregisteret / SSB SN2007)",
                    source_url=source_url_enhet,
                    source_date=reg_date,
                )
            )

        purpose_list = enhet_raw.get("vedtektsfestetFormaal", [])
        if purpose_list:
            purpose_text = " ".join(purpose_list)
            facts.append(
                self.resolver.build_verified_fact(
                    key="purpose",
                    label="Statutory Business Purpose",
                    value=purpose_text,
                    category=FactCategory.INDUSTRY,
                    source_name="Brønnøysundregistrene (Enhetsregisteret)",
                    source_url=source_url_enhet,
                    source_date=enhet_raw.get("vedtektsdato", reg_date),
                )
            )

        # 4. Workforce
        emp_count = enhet_raw.get("antallAnsatte")
        emp_date = enhet_raw.get("registreringsdatoAntallAnsatteNAVAaregisteret")
        if emp_count is not None:
            facts.append(
                self.resolver.build_verified_fact(
                    key="employee_count",
                    label="Registered Employees",
                    value=emp_count,
                    category=FactCategory.WORKFORCE,
                    source_name="NAV Aa-registeret via Enhetsregisteret",
                    source_url=source_url_enhet,
                    source_date=emp_date or reg_date,
                    notes=f"Reported to NAV Aa-registeret on {emp_date}" if emp_date else "Official count",
                )
            )

        # 5. Legal Solvency Status
        is_bankrupt = enhet_raw.get("konkurs", False)
        is_liquidating = enhet_raw.get("underAvvikling", False)
        is_compulsory = enhet_raw.get("underTvangsavviklingEllerTvangsopplosning", False)

        status_text = "Active / Operating"
        if is_bankrupt:
            status_text = "In Bankruptcy"
        elif is_liquidating:
            status_text = "In Liquidation"
        elif is_compulsory:
            status_text = "Compulsory Dissolution"

        facts.append(
            self.resolver.build_verified_fact(
                key="legal_status",
                label="Legal Operating Status",
                value=status_text,
                category=FactCategory.LEGAL_STATUS,
                source_name="Brønnøysundregistrene (Konkurs-/Foretaksregisteret)",
                source_url=source_url_enhet,
                source_date=reg_date,
            )
        )

        # Share Capital
        kapital_obj = enhet_raw.get("kapital", {})
        share_capital = kapital_obj.get("belop")
        capital_curr = kapital_obj.get("valuta", "NOK")
        if share_capital is not None:
            formatted_cap = f"{share_capital:,.2f} {capital_curr}"
            facts.append(
                self.resolver.build_verified_fact(
                    key="share_capital",
                    label="Registered Share Capital",
                    value=formatted_cap,
                    category=FactCategory.IDENTIFICATION,
                    source_name="Brønnøysundregistrene (Foretaksregisteret)",
                    source_url=source_url_enhet,
                    source_date=kapital_obj.get("innfortDato", reg_date),
                )
            )

        # 6. Corporate Governance & Roles
        key_roles: List[RoleItem] = []
        ceo_name = None
        chair_name = None
        auditor_name = None

        if roller_raw:
            source_url_roller = roller_raw.get("_source_url", f"https://data.brreg.no/enhetsregisteret/api/enheter/{orgnr}/roller")
            groups = roller_raw.get("rollegrupper", [])

            for grp in groups:
                grp_date = grp.get("sistEndret")
                for r in grp.get("roller", []):
                    if r.get("avregistrert", False):
                        continue

                    r_type = r.get("type", {})
                    r_code = r_type.get("kode", "")
                    r_desc = r_type.get("beskrivelse", "")

                    p_name = None
                    o_name = None
                    o_orgnr = None

                    if "person" in r:
                        p = r["person"]
                        name_dict = p.get("navn", {})
                        if isinstance(name_dict, dict):
                            parts = [name_dict.get("fornavn", ""), name_dict.get("mellomnavn", ""), name_dict.get("etternavn", "")]
                            p_name = " ".join(pt for pt in parts if pt).strip()
                        elif isinstance(name_dict, str):
                            p_name = name_dict
                    elif "enhet" in r:
                        e = r["enhet"]
                        o_orgnr = e.get("organisasjonsnummer")
                        raw_names = e.get("navn", [])
                        if isinstance(raw_names, list) and raw_names:
                            o_name = " ".join(raw_names)
                        elif isinstance(raw_names, str):
                            o_name = raw_names

                    assigned_name = p_name or o_name
                    if not assigned_name:
                        continue

                    role_item = RoleItem(
                        role_code=r_code,
                        role_description=r_desc,
                        person_name=p_name,
                        organization_name=o_name,
                        organization_orgnr=o_orgnr,
                        last_updated=grp_date,
                    )
                    key_roles.append(role_item)

                    # Check for CEO (Daglig leder)
                    if r_code == "DAGL" and not ceo_name:
                        ceo_name = assigned_name
                        facts.append(
                            self.resolver.build_verified_fact(
                                key="ceo",
                                label="General Manager / CEO (Daglig leder)",
                                value=ceo_name,
                                category=FactCategory.GOVERNANCE,
                                source_name="Brønnøysundregistrene (Roller)",
                                source_url=source_url_roller,
                                source_date=grp_date,
                                notes="Registered general manager with Brønnøysundregistrene",
                            )
                        )

                    # Check for Board Chair (Styreleder)
                    elif r_code == "LEDE" and not chair_name:
                        chair_name = assigned_name
                        facts.append(
                            self.resolver.build_verified_fact(
                                key="board_chair",
                                label="Chairman of the Board (Styreleder)",
                                value=chair_name,
                                category=FactCategory.GOVERNANCE,
                                source_name="Brønnøysundregistrene (Roller)",
                                source_url=source_url_roller,
                                source_date=grp_date,
                                notes="Registered chair of the board",
                            )
                        )

                    # Check for Auditor (Revisor)
                    elif r_code == "REVI" and not auditor_name:
                        auditor_name = assigned_name
                        facts.append(
                            self.resolver.build_verified_fact(
                                key="auditor",
                                label="Registered Auditor (Revisor)",
                                value=auditor_name,
                                category=FactCategory.GOVERNANCE,
                                source_name="Brønnøysundregistrene (Roller)",
                                source_url=source_url_roller,
                                source_date=grp_date,
                                notes="Approved public auditing entity",
                            )
                        )

        # 7. Financial Statements (Regnskapsregisteret)
        fin_model: Optional[FinancialYearData] = None
        if regnskap_raw and isinstance(regnskap_raw, list) and len(regnskap_raw) > 0:
            latest_acc = regnskap_raw[0]
            # Disambiguate financial statement
            is_valid_stmt, conf, reason = self.resolver.verify_financial_statement(latest_acc, orgnr, name)
            if is_valid_stmt:
                periode = latest_acc.get("regnskapsperiode", {})
                start_date = periode.get("fraDato", "")
                end_date = periode.get("tilDato", "")
                year = int(end_date[:4]) if end_date and len(end_date) >= 4 else 0
                currency = latest_acc.get("valuta", "NOK")

                def _extract_float(val: Any) -> Optional[float]:
                    if val is None:
                        return None
                    if isinstance(val, (int, float)):
                        return float(val)
                    if isinstance(val, dict):
                        for k in ["sumDriftsinntekter", "sumSalgsinntekter", "driftsinntekter", "salgsinntekter",
                                  "sumEiendeler", "sumEgenkapital", "sumGjeld", "belop", "verdi", "sum"]:
                            if k in val and val[k] is not None:
                                return _extract_float(val[k])
                        for v in val.values():
                            ext = _extract_float(v)
                            if ext is not None:
                                return ext
                    if isinstance(val, str):
                        try:
                            return float(val.replace(" ", "").replace(",", "."))
                        except ValueError:
                            return None
                    return None

                res_obj = latest_acc.get("resultatregnskapResultat", {})
                driftsresultat_obj = res_obj.get("driftsresultat", {})
                revenue = _extract_float(driftsresultat_obj.get("driftsinntekter") or driftsresultat_obj.get("salgsinntekter"))
                operating_profit = _extract_float(driftsresultat_obj.get("driftsresultat"))
                net_profit = _extract_float(res_obj.get("aarsresultat") or res_obj.get("ordinaertResultatEtterSkattekostnad"))

                eiendeler_obj = latest_acc.get("eiendeler", {})
                total_assets = _extract_float(eiendeler_obj.get("sumEiendeler"))

                eq_debt_obj = latest_acc.get("egenkapitalGjeld", {})
                egenkapital_obj = eq_debt_obj.get("egenkapital", {})
                total_equity = _extract_float(egenkapital_obj.get("sumEgenkapital"))

                gjeld_obj = eq_debt_obj.get("gjeldOversikt", {})
                total_debt = _extract_float(gjeld_obj.get("sumGjeld"))

                source_url_regnskap = f"https://data.brreg.no/regnskapsregisteret/regnskap/{orgnr}"

                fin_model = FinancialYearData(
                    year=year,
                    period_start=start_date,
                    period_end=end_date,
                    currency=currency,
                    revenue=revenue,
                    operating_profit=operating_profit,
                    net_profit=net_profit,
                    total_assets=total_assets,
                    total_equity=total_equity,
                    total_debt=total_debt,
                    source_url=source_url_regnskap,
                    submission_id=str(latest_acc.get("journalnr") or ""),
                )

                if revenue is not None:
                    facts.append(
                        self.resolver.build_verified_fact(
                            key="financial_revenue",
                            label=f"Annual Revenue ({year})",
                            value=f"{revenue:,.2f} {currency}",
                            category=FactCategory.FINANCIALS,
                            source_name="Brønnøysundregistrene (Regnskapsregisteret)",
                            source_url=source_url_regnskap,
                            source_date=end_date,
                            confidence=conf,
                            notes=reason,
                        )
                    )

                if operating_profit is not None:
                    facts.append(
                        self.resolver.build_verified_fact(
                            key="operating_profit",
                            label=f"Operating Profit / EBIT ({year})",
                            value=f"{operating_profit:,.2f} {currency}",
                            category=FactCategory.FINANCIALS,
                            source_name="Brønnøysundregistrene (Regnskapsregisteret)",
                            source_url=source_url_regnskap,
                            source_date=end_date,
                            confidence=conf,
                        )
                    )

                if net_profit is not None:
                    facts.append(
                        self.resolver.build_verified_fact(
                            key="net_profit",
                            label=f"Net Profit / Årsresultat ({year})",
                            value=f"{net_profit:,.2f} {currency}",
                            category=FactCategory.FINANCIALS,
                            source_name="Brønnøysundregistrene (Regnskapsregisteret)",
                            source_url=source_url_regnskap,
                            source_date=end_date,
                            confidence=conf,
                        )
                    )

                if total_assets is not None:
                    facts.append(
                        self.resolver.build_verified_fact(
                            key="total_assets",
                            label=f"Total Assets ({year})",
                            value=f"{total_assets:,.2f} {currency}",
                            category=FactCategory.FINANCIALS,
                            source_name="Brønnøysundregistrene (Regnskapsregisteret)",
                            source_url=source_url_regnskap,
                            source_date=end_date,
                            confidence=conf,
                        )
                    )

                if total_equity is not None:
                    facts.append(
                        self.resolver.build_verified_fact(
                            key="total_equity",
                            label=f"Total Equity ({year})",
                            value=f"{total_equity:,.2f} {currency}",
                            category=FactCategory.FINANCIALS,
                            source_name="Brønnøysundregistrene (Regnskapsregisteret)",
                            source_url=source_url_regnskap,
                            source_date=end_date,
                            confidence=conf,
                        )
                    )

        # 8. Web Presence Grounding
        raw_website = enhet_raw.get("hjemmeside")
        if raw_website:
            facts.append(
                self.resolver.build_verified_fact(
                    key="website_url",
                    label="Official Website URL",
                    value=raw_website,
                    category=FactCategory.ONLINE,
                    source_name="Brønnøysundregistrene (Enhetsregisteret)",
                    source_url=source_url_enhet,
                    source_date=reg_date,
                    notes="Registered website on file in Enhetsregisteret",
                )
            )

        if web_raw:
            historical_names = [h.get("navn") for h in enhet_raw.get("historiskeNavn", []) if h.get("navn")]
            is_valid_web, w_conf, w_reason = self.resolver.verify_website_source(
                web_raw, orgnr, name, historical_names
            )
            if is_valid_web and web_raw.get("meta_description"):
                facts.append(
                    self.resolver.build_verified_fact(
                        key="web_description",
                        label="Verified Web Description",
                        value=web_raw["meta_description"],
                        category=FactCategory.ONLINE,
                        source_name=f"Official Homepage ({web_raw.get('domain')})",
                        source_url=web_raw.get("verified_url", f"https://{raw_website}"),
                        source_date=now_iso[:10],
                        confidence=w_conf,
                        notes=w_reason,
                    )
                )

        # 9. Freshness Tracking (Oppdateringer)
        last_modified_date = None
        latest_update_id = None
        if update_raw:
            latest_update_id = update_raw.get("oppdateringsid")
            last_modified_date = update_raw.get("dato")
            facts.append(
                self.resolver.build_verified_fact(
                    key="last_registry_update",
                    label="Latest Registry Update Event",
                    value=f"Update #{latest_update_id} ({update_raw.get('endringstype', 'Endring')})",
                    category=FactCategory.LEGAL_STATUS,
                    source_name="Brønnøysundregistrene (Oppdateringer)",
                    source_url=update_raw.get("_source_url", f"https://data.brreg.no/enhetsregisteret/api/oppdateringer/enheter?organisasjonsnummer={orgnr}"),
                    source_date=last_modified_date,
                    notes="Verified event from official delta stream",
                )
            )

        # Assess risk indicators
        risk_indicators = []
        if is_bankrupt:
            risk_indicators.append("Entity is currently in bankruptcy proceedings.")
        if is_liquidating:
            risk_indicators.append("Entity is currently undergoing liquidation.")
        if is_compulsory:
            risk_indicators.append("Entity is subject to compulsory dissolution.")
        if fin_model and fin_model.total_equity is not None and fin_model.total_equity < 0:
            risk_indicators.append(f"Negative recorded equity ({fin_model.total_equity:,.0f} {fin_model.currency}).")

        # Synthesize concise profile
        profile = CompanyProfile(
            orgnr=orgnr,
            name=name,
            org_form=org_form,
            org_form_description=org_form_desc,
            status=status_text,
            freshness_status="CURRENT",
            last_verified_at=now_iso,
            last_modified_in_registry=last_modified_date,
            latest_update_id=latest_update_id,
            entity_match_score=1.0,
            foundation_date=foundation_date,
            registration_date=reg_date,
            business_address=business_addr,
            postal_address=postal_addr,
            industry_code=industry_code,
            industry_description=industry_desc,
            employee_count=emp_count,
            employee_registration_date=emp_date,
            website_url=raw_website,
            phone=enhet_raw.get("telefon"),
            is_vat_registered=enhet_raw.get("registrertIMvaregisteret"),
            share_capital=share_capital,
            share_capital_currency=capital_curr,
            is_part_of_group=enhet_raw.get("erIKonsern"),
            ceo_name=ceo_name,
            board_chair=chair_name,
            auditor_name=auditor_name,
            key_roles=key_roles,
            latest_financials=fin_model,
            facts=facts,
            risk_indicators=risk_indicators,
        )

        return profile
