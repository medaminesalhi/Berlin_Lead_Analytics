"""Task 1 -> Task 2: merge, clean, classify and score Berlin property leads.

No network requests, no LLM calls, and no writes to the Stagehand checkpoint.
Input: checkpoint JSON from Stagehand + previous directory candidate CSV.
Output: transparent CSVs and a quality report for review / Streamlit.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

# Search results pointing to directories, comparison articles or unrelated services
# must NOT be treated as the official website of a distinct property manager.
DIRECTORY_HOSTS = {
    "dastelefonbuch.de", "gelbeseiten.de", "hausverwalterscout.de",
    "hausverwalterfinder.de", "das-hausverwalterportal.de",
    "top-100-hausverwaltungen.de", "finderr.de", "cylex.de",
    "web2.cylex.de", "immobilienscout24.de", "vdiv-bb.de",
    "11880.com", "werkenntdenbesten.de",
}
UNRELATED_HOSTS = {"telekom.de", "immocation.de"}
BAD_NAME = re.compile(
    r"^(kontakt(?:\s|$|\s*/|:)|startseite$|home$|impressum(?:\s|$|:)|"
    r"hausverwaltungen berlin \d{4}$|top\s*\d+\s+hausverwaltungen|"
    r"alle hausverwaltungen|immobilien-\s*&\s*weg-verwaltung$|"
    r"kontakt(?:daten|formular)|wir kümmern uns$|angebot anfragen$)", re.I
)
MANAGEMENT = re.compile(
    r"hausverwaltung|immobilienverwaltung|weg[-\s]?verwaltung|"
    r"mietverwaltung|property management|wohnungsverwaltung|"
    r"grundst[uü]cksverwaltung|liegenschaftsverwaltung|"
    r"sondereigentumsverwaltung", re.I
)
RESIDENTIAL = re.compile(
    r"weg[-\s]?verwaltung|mietverwaltung|wohnungsverwaltung|"
    r"wohneinheiten|wohnimmobilien|sondereigentum", re.I
)
BILLING = re.compile(
    r"nebenkostenabrechnung|betriebskostenabrechnung|"
    r"heizkostenabrechnung|verbrauchsabrechnung|hausgeldabrechnung", re.I
)
METERING = re.compile(
    r"heizkostenabrechnung|verbrauchserfassung|verbrauchsabrechnung|"
    r"fernablesung|wärmemengenzähler|warmwasserzähler|submetering", re.I
)
GENERIC_EMAIL = re.compile(r"^(info|kontakt|office|service|verwaltung|hausverwaltung|mail|post|team|anfrage)@", re.I)


def clean(value) -> str:
    if value is None or isinstance(value, (dict, list)):
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def normalize_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", clean(value)).encode("ascii", "ignore").decode()
    text = re.sub(r"\b(gmbh|mbh|ug|e\.k\.|kg|ag|co|haftungsbeschrankt)\b", " ", text.lower())
    return re.sub(r"[^a-z0-9]+", "", text)


def as_url(value: str) -> str:
    url = clean(value)
    if not url:
        return ""
    if not re.match(r"^https?://", url, flags=re.I):
        url = "https://" + url
    try:
        parsed = urlsplit(url)
        if not parsed.hostname:
            return ""
        return parsed.geturl()
    except ValueError:
        return ""


def host(value: str) -> str:
    url = as_url(value)
    try:
        return (urlsplit(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def is_host_in(domain: str, collection: set[str]) -> bool:
    return bool(domain and any(domain == h or domain.endswith("." + h) for h in collection))


def site_home(url: str) -> str:
    u = as_url(url)
    if not u:
        return ""
    p = urlsplit(u)
    return f"{p.scheme}://{p.netloc}/"


def parse_units(value):
    if value is None or value == "" or value is False:
        return None
    try:
        n = int(float(str(value).strip().replace(" ", "").replace(",", "")))
        return n if n >= 0 else None
    except (ValueError, TypeError):
        return None


def valid_name(name: str) -> bool:
    n = clean(name)
    if not n or BAD_NAME.search(n) or "nom à vérifier" in n.lower():
        return False
    if len(n) > 105 or n.lower().startswith(("http://", "https://", "www.")):
        return False
    if n.endswith(".de") or n.endswith(".com") or n.endswith(".net"):
        return False
    return True


def split_sources(value) -> list[str]:
    if isinstance(value, list):
        raw = value
    else:
        raw = clean(value).split(" | ") if clean(value) else []
    return [as_url(x) for x in raw if as_url(x)]


def load_checkpoint(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Checkpoint absent : {path}")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    rows = data.get("items", []) if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise ValueError("Format checkpoint attendu : objet JSON avec items[]")
    return [x for x in rows if isinstance(x, dict)]


def load_directory(path: Path) -> list[dict]:
    if not path.exists():
        print(f"AVERTISSEMENT : annuaire absent ({path}), fusion sans cette source.")
        return []
    # The packaged research export uses comma-delimited UTF-8 with a header.
    data = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    return data.to_dict(orient="records")


def new_record(key: str) -> dict:
    return {
        "key": key, "company_name": "", "website": "", "domain": "",
        "address": "", "postal_code": "", "city": "", "email": "", "phone": "",
        "management_type": "", "units_managed": None, "units_evidence": "",
        "type_evidence": "", "berlin_presence": None, "scrape_status": "",
        "ai_validation": "", "page_text": "", "source_urls": set(),
        "sources": set(), "name_conflicts": set(), "units_external": "",
        "listing_only": False,
        "notes": "", "directory_name": "", "scraped_name": "",
    }


def identity_key(row: dict) -> str:
    domain = host(row.get("website", ""))
    if domain and not is_host_in(domain, DIRECTORY_HOSTS):
        return "D:" + domain
    name = normalize_name(row.get("company_name") or row.get("name") or "")
    postcode = clean(row.get("postal_code", ""))
    if name and postcode:
        return "NP:" + name + ":" + postcode
    if name:
        return "N:" + name
    return "U:" + (domain or clean(row.get("website", "")))


def ingest_scraped(merged: dict, item: dict):
    name = clean(item.get("name"))
    website = as_url(item.get("website"))
    domain = host(website)
    key = identity_key({"name": name, "website": website})
    rec = merged.setdefault(key, new_record(key))
    rec["sources"].add("Stagehand")
    rec["domain"] = domain or rec["domain"]
    rec["website"] = rec["website"] or site_home(website)
    rec["scraped_name"] = name
    if (re.search(r"/blog/|/beste[-_]|/branchen/|/firmen/", website, re.I)
            and re.search(r"top\s*\d+|beste hausverwaltungen|hausverwaltungen berlin \d{4}|/branchen/|/firmen/", name + " " + website, re.I)):
        rec["listing_only"] = True
    if valid_name(name):
        if rec["company_name"] and normalize_name(rec["company_name"]) != normalize_name(name):
            rec["name_conflicts"].add(name)
        if not valid_name(rec["company_name"]):
            rec["company_name"] = name
    for dst, src in [
        ("address", "address"), ("email", "email"),
        ("phone", "phone"), ("management_type", "management_type"),
        ("units_evidence", "units_evidence"), ("type_evidence", "type_evidence"),
        ("ai_validation", "ai_validation"), ("scrape_status", "scrape_status"),
    ]:
        val = clean(item.get(src))
        if val:
            rec[dst] = val
    if isinstance(item.get("berlin_presence"), bool):
        rec["berlin_presence"] = item["berlin_presence"]
    if isinstance(item.get("units_managed"), int) and item.get("units_managed") >= 0:
        rec["units_managed"] = item["units_managed"]
    rec["page_text"] = clean(item.get("page_text")) or rec["page_text"]
    for url in split_sources(item.get("source_pages")) + split_sources(item.get("source_url")):
        rec["source_urls"].add(url)
    if website:
        rec["source_urls"].add(website)
    if not rec["company_name"] and domain:
        rec["company_name"] = domain + " (nom à vérifier)"


def ingest_directory(merged: dict, item: dict):
    name = clean(item.get("company_name"))
    website = as_url(item.get("website"))
    key = identity_key(item)
    rec = merged.setdefault(key, new_record(key))
    rec["sources"].add("VDIV / other directories")
    rec["directory_name"] = name
    if valid_name(name):
        # Source directory usually carries a legal company name, more useful
        # than generic SERP titles, but is not necessarily up-to-date.
        if rec["company_name"] and valid_name(rec["company_name"]) and normalize_name(rec["company_name"]) != normalize_name(name):
            rec["name_conflicts"].add(rec["company_name"])
        rec["company_name"] = name
    if website and not rec["website"]:
        rec["website"] = site_home(website)
    rec["domain"] = rec["domain"] or host(website)
    for dest in ["address", "postal_code", "city", "email", "phone"]:
        if not rec[dest] and clean(item.get(dest)):
            rec[dest] = clean(item.get(dest))
    if clean(item.get("units_managed")):
        rec["units_external"] = clean(item.get("units_managed"))
    if clean(item.get("notes")):
        rec["notes"] = clean(item.get("notes"))
    for url in split_sources(item.get("source_url")) + split_sources(item.get("units_source_url")):
        rec["source_urls"].add(url)


def reconcile_keys(merged: dict) -> dict:
    """Merge strong name+postcode directory-only rows with known-domain rows if unique."""
    named = {}
    for key, rec in merged.items():
        if not rec["domain"] and valid_name(rec["company_name"]):
            ident = normalize_name(rec["company_name"])
            named.setdefault(ident, []).append(key)
    # Intentionally no automatic name-only merge: different legal entities can
    # share similar names. Their possible duplicates remain in manual review.
    return merged


def infer_management(rec: dict):
    t = rec["page_text"] if rec["scrape_status"] == "OK" else ""
    declared = rec["management_type"].lower()
    if rec["ai_validation"] == "EVIDENCE_CHECKED" and rec["type_evidence"] and rec["type_evidence"].lower() in t.lower():
        if declared in {"residential", "mixed", "commercial", "sales_only"}:
            return declared, "Groq + official-page quote"
    if MANAGEMENT.search(t):
        if RESIDENTIAL.search(t):
            return "residential", "Official-page keywords"
        return "management_unspecified", "Official-page keywords"
    return "unknown", "Not established"


def company_classification(rec: dict, management: str):
    domain = rec["domain"]
    if is_host_in(domain, DIRECTORY_HOSTS):
        return "EXCLUDED", "Directory / comparison site, not the company website"
    if is_host_in(domain, UNRELATED_HOSTS):
        return "EXCLUDED", "Known unrelated service / training website"
    if rec["listing_only"] and not rec["directory_name"]:
        return "EXCLUDED", "Search-result listing / article, not an individual company profile"
    if not valid_name(rec["company_name"]):
        return "REVIEW", "Company legal name missing"
    if rec["name_conflicts"]:
        return "REVIEW", "Conflicting names on same domain"
    if management == "sales_only":
        return "REVIEW", "Sales-only; check whether property management is also offered"
    if management in {"residential", "mixed", "management_unspecified", "commercial"}:
        return "LIKELY", "Property management stated on site"
    if "VDIV / other directories" in rec["sources"] and MANAGEMENT.search(rec["company_name"]):
        return "LIKELY", "Named property manager from professional directory; verify site"
    return "REVIEW", "Insufficient evidence of actual property management"


def kpi_score(rec: dict, management: str, classification: str):
    """Range scoring. Unknown is an interval, never a fabricated zero.

    Model: activity 30; units 25; Berlin operation 15; metering relevance 20;
    contactability 10. Data quality is displayed separately.
    """
    low = high = 0
    factors = {}

    types = {"residential": 30, "mixed": 25, "management_unspecified": 20, "commercial": 10, "sales_only": 0}
    if management in types:
        x = types[management]; low += x; high += x; factors["activity_points"] = x
    else:
        high += 30; factors["activity_points"] = None

    count = rec["units_managed"]
    quote = rec["units_evidence"]
    text = rec["page_text"]
    units_valid = (rec["ai_validation"] == "EVIDENCE_CHECKED" and
                   isinstance(count, int) and bool(quote) and quote.lower() in text.lower())
    if units_valid:
        x = 25 if count > 1000 else 19 if count > 500 else 13 if count > 100 else 5 if count > 0 else 0
        low += x; high += x; factors["units_points"] = x
        factors["units_confirmed"] = count
    else:
        high += 25; factors["units_points"] = None
        factors["units_confirmed"] = None

    # Berlin operational presence on the official site is stronger than an office
    # address in a directory (which does not prove local managed properties).
    text_berlin = rec["scrape_status"] == "OK" and "berlin" in text.lower()
    directory_berlin = "berlin" in rec["city"].lower()
    if text_berlin:
        low += 15; high += 15; factors["berlin_points"] = 15
    elif directory_berlin:
        low += 7; high += 15; factors["berlin_points"] = 7
    elif rec["berlin_presence"] is False:
        factors["berlin_points"] = 0
    else:
        high += 15; factors["berlin_points"] = None

    if rec["scrape_status"] == "OK" and METERING.search(text):
        low += 20; high += 20; factors["metering_points"] = 20
    elif rec["scrape_status"] == "OK" and BILLING.search(text):
        low += 12; high += 20; factors["metering_points"] = 12
    else:
        high += 20; factors["metering_points"] = None

    email = clean(rec["email"])
    if email:
        x = 5 if GENERIC_EMAIL.search(email) else 8
        low += x; high += 10; factors["contact_points"] = x
    elif clean(rec["phone"]):
        low += 3; high += 10; factors["contact_points"] = 3
    else:
        high += 10; factors["contact_points"] = None

    if classification == "EXCLUDED":
        priority = "EXCLUDED"
    elif classification == "REVIEW":
        priority = "VERIFY_COMPANY"
    elif low >= 75:
        priority = "HIGH"
    elif low >= 45:
        priority = "MEDIUM"
    else:
        priority = "RESEARCH_MORE"
    return low, min(high, 100), priority, factors


def public_fields() -> list[str]:
    # Deliberately excludes email, phone and any individual contact details.
    return ["company_name", "website", "domain", "management_type", "units_managed",
            "score_min", "score_max", "priority", "classification", "data_quality",
            "source_url", "review_status"]


def build_rows(checkpoint_rows: list[dict], directory_rows: list[dict]):
    merged = {}
    for row in checkpoint_rows:
        ingest_scraped(merged, row)
    for row in directory_rows:
        ingest_directory(merged, row)
    reconcile_keys(merged)
    result = []
    for rec in merged.values():
        management, rule = infer_management(rec)
        classification, reason = company_classification(rec, management)
        lower, upper, priority, factors = kpi_score(rec, management, classification)
        quality = "HIGH" if rec["scrape_status"] == "OK" and rec["ai_validation"] == "EVIDENCE_CHECKED" else "MEDIUM" if rec["scrape_status"] == "OK" else "LOW"
        known = [bool(rec[x]) for x in ["website", "address", "email", "phone", "page_text", "type_evidence", "units_evidence"]]
        source_url = " | ".join(sorted(rec["source_urls"]))
        result.append({
            "company_name": rec["company_name"], "website": rec["website"], "domain": rec["domain"],
            "address": rec["address"], "postal_code": rec["postal_code"], "city": rec["city"],
            "email": rec["email"], "phone": rec["phone"],
            "management_type": management, "units_managed": factors["units_confirmed"],
            "units_reported_unverified": rec["units_external"],
            "metering_signal": "CONFIRMED_TEXT" if factors["metering_points"] == 20 else "BILLING_TEXT" if factors["metering_points"] == 12 else "UNKNOWN",
            "berlin_signal": "OFFICIAL_PAGE" if factors["berlin_points"] == 15 else "DIRECTORY_ADDRESS" if factors["berlin_points"] == 7 else "UNKNOWN",
            "score_min": lower, "score_max": upper, "priority": priority,
            "classification": classification, "classification_reason": reason,
            "data_quality": quality, "completeness_pct": round(sum(known) / len(known) * 100),
            "scrape_status": rec["scrape_status"] or "NOT_SCRAPED",
            "ai_validation": rec["ai_validation"] or "NOT_ANALYZED",
            "name_conflict": " | ".join(sorted(rec["name_conflicts"])),
            "type_evidence": rec["type_evidence"], "units_evidence": rec["units_evidence"],
            "source_types": " | ".join(sorted(rec["sources"])),
            "source_url": source_url,
            "review_status": "NOT_MANUALLY_VERIFIED", "notes": rec["notes"],
            "classification_method": rule,
        })
    result.sort(key=lambda r: (0 if r["classification"] == "LIKELY" else 1 if r["classification"] == "REVIEW" else 2, -r["score_min"], r["company_name"].lower()))
    return result


def csv_safe(df: pd.DataFrame) -> pd.DataFrame:
    copy = df.copy()
    # Strings beginning with Excel formula triggers must be escaped.
    for col in copy.select_dtypes(include=["object"]).columns:
        copy[col] = copy[col].map(lambda x: "'" + x if isinstance(x, str) and x.startswith(("=", "+", "-", "@")) else x)
    return copy


def save_results(rows: list[dict], folder: Path):
    folder.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("Aucun résultat exploitable.")
    for name, select in [
        ("leads_all", df),
        ("leads_qualified", df[df.classification == "LIKELY"]),
        ("leads_review", df[df.classification == "REVIEW"]),
        ("leads_excluded", df[df.classification == "EXCLUDED"]),
    ]:
        csv_safe(select).to_csv(folder / f"{name}.csv", sep=";", encoding="utf-8-sig", index=False)
    # Public preview is NOT auto-written to GitHub. User must manually review
    # and select a publishable subset before deployment.
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "unique_candidates": len(df),
        "classification": df.classification.value_counts().to_dict(),
        "priority": df.priority.value_counts().to_dict(),
        "scraped_ok": int((df.scrape_status == "OK").sum()),
        "ai_evidence_checked": int((df.ai_validation == "EVIDENCE_CHECKED").sum()),
        "companies_with_email": int(df.email.fillna("").astype(str).ne("").sum()),
        "unverified_directory_only": int((df.scrape_status == "NOT_SCRAPED").sum()),
        "manual_review_remaining": int((df.review_status != "VERIFIED").sum()),
        "note": "Automated qualification only. Evidence status does not imply human verification."
    }
    (folder / "quality_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def run(checkpoint: Path, directory: Path, out: Path):
    cp = load_checkpoint(checkpoint)
    dr = load_directory(directory)
    rows = build_rows(cp, dr)
    report = save_results(rows, out)
    print(f"Checkpoint Stagehand: {len(cp)} candidats")
    print(f"Annuaire initial: {len(dr)} candidats")
    print(f"Entreprises/candidats fusionnés: {report['unique_candidates']}")
    print(f"Classification: {report['classification']}")
    print(f"Fichiers créés dans : {out}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean, merge and qualify Berlin property leads")
    parser.add_argument("--checkpoint", type=Path, default=RAW / "checkpoint_latest.json")
    parser.add_argument("--directory", type=Path, default=RAW / "directory_candidates.csv")
    parser.add_argument("--out", type=Path, default=PROCESSED)
    args = parser.parse_args()
    run(args.checkpoint, args.directory, args.out)
