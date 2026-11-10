"""Berlin Property Lead Intelligence — bilingual, read-only Streamlit dashboard.

Public mode always uses a curated contact-free CSV. No uploading or scraping.
Google Sheets: open a preconfigured live Sheet, or import a publicly hosted CSV
via =IMPORTDATA(). Creating Sheets in the visitor's Drive needs OAuth and is
intentionally not attempted by this application.
"""
from __future__ import annotations

import html
import os
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pipeline import compute_score_from_fields, csv_safe

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "data/public/leads_public.csv"
LOCAL = ROOT / "data/processed/leads_all.csv"
BLUE = "#1768C8"
DARK = "#163967"
LIGHT = "#9DBDE8"
PALE = "#DAE8F9"
MUTED = "#7D9CC2"
GREY = "#BDC9D8"
COLORS = {
    "LIKELY": BLUE, "REVIEW": LIGHT, "EXCLUDED": GREY,
    "HIGH": BLUE, "MEDIUM": "#4A86CF", "RESEARCH_MORE": MUTED,
    "VERIFY_COMPANY": LIGHT,
}

I18N = {
 "en": {
    "language": "Language / Sprache", "nav_overview": "Overview", "nav_kpis": "Methodology & KPIs",
    "nav_explorer": "Companies & Export", "nav_quality": "Data Quality & Validation",
    "project": "BERLIN PROPERTY LEAD INTELLIGENCE", "case": "HEIDI SYSTEMS · CASE STUDY",
    "source": "Dataset", "public_dataset": "Curated public dataset", "private_dataset": "Local processed dataset",
    "total_base": "Records", "sidebar_export": "DOWNLOAD RESEARCH RESULTS",
    "sidebar_caption": "Read-only dashboard. No CSV upload, scraping or API calls.",
    "sidebar_csv": "Download all results (CSV)", "method_note": "Automated candidate assessment; not an independently verified client list.",
    "overview_kicker": "HEIDI SYSTEMS · B2B MARKET INTELLIGENCE",
    "overview_title": "Berlin Property Lead Intelligence",
    "overview_desc": "From web discovery to property-manager qualification: commercial fit, evidence, data coverage and transparent research sources.",
    "candidates": "Consolidated candidates", "candidates_note": "After merging and deduplication",
    "likely": "Likely property managers", "likely_note": "Automated qualification or web review",
    "visited": "Websites visited", "visited_note": "Stagehand / Chromium browsing",
    "reviewed": "Web-reviewed records", "reviewed_note": "Documented checks, some with reservations",
    "exports": "EXPORT RESEARCH DATA", "exports_desc": "Download a spreadsheet-ready CSV. Personal contacts are excluded from public exports.",
    "download_all": "Download full dataset (CSV)", "download_likely": "Download likely leads (CSV)",
    "snapshot": "RESEARCH SNAPSHOT", "classification_breakdown": "Candidate classification",
    "priority_chart": "Commercial priorities", "records": "records",
    "coverage": "Data coverage & completeness", "scraping_rate": "Website coverage",
    "ai_evidence": "LLM text evidence", "units_count": "Portfolio figures available",
    "review_count": "Requires company review", "caution": "A text quote matched by an LLM is not human verification. A Berlin address alone does not prove Berlin property operations.",
    "top_companies": "High-potential candidates to examine",
    "kpis_kicker": "TRANSPARENT LEAD QUALIFICATION", "kpis_title": "Methodology & KPIs",
    "kpis_desc": "How candidates are discovered, cleaned, classified and scored. Missing information increases uncertainty instead of being treated as zero.",
    "steps_title": "Five-stage research workflow", "steps": [
      ("Discovery", "SearXNG and public directories discover candidate property-management firms in Berlin."),
      ("Browser research", "Stagehand/Chromium visit permitted pages, including About, Contact and Services."),
      ("AI enrichment", "Groq extracts management categories and figures; evidence text is checked against captured pages."),
      ("Data consolidation", "Python standardizes names, merges domains, and separates directory listings from real companies."),
      ("Lead qualification", "Explicit commercial KPIs produce a minimum–maximum score alongside separate verification statuses."),
    ],
    "kpi_score_title": "Lead scoring framework · 100 points", "kpi_cards": [
      ("Property-management fit", 30, "Does the firm actually manage buildings?", "Residential / WEG: 30; mixed: 25; general: 20; commercial: 10; sales-only: 0."),
      ("Managed portfolio", 25, "Number of managed units indicates potential scale.", ">1,000: 25; 501–1,000: 19; 101–500: 13; 1–100: 5; unpublished: unknown."),
      ("Berlin operations", 15, "Does it manage properties in the target geography?", "Confirmed service area: 15; directory address only: 7–15; unknown: 0–15."),
      ("Metering / billing fit", 20, "Heating, utility allocation and charges are relevant needs.", "Explicit metering: 20; service-charge billing: 12–20; unknown: 0–20."),
      ("Business contactability", 10, "How easily can the team reach the firm?", "Named work contact: 8–10; generic email: 5–10; phone: 3–10; unknown: 0–10."),
    ],
    "rule": "Rule", "reading_scores": "Understanding the score range",
    "min_explain": "Minimum score: points supported by the available information (which can still require review).",
    "max_explain": "Maximum score: the upper bound if currently missing data prove favorable.",
    "score_example": "Example: 65–90 / 100 reflects 65 currently supported points and 25 uncertain points, not a confirmed score of 90.",
    "priority_rules": "HIGH: minimum score ≥75; MEDIUM: 45–74; RESEARCH_MORE: below 45. REVIEW always requires a company check.",
    "sim_title": "Interactive scoring example", "sim_type": "Management type", "sim_units": "Portfolio size",
    "sim_berlin": "Berlin operations", "sim_meter": "Metering / billing evidence", "sim_contact": "Contact availability",
    "sim_score": "Estimated score", "simulation_note": "Illustrative inputs, not an actual company record.",
    "limits_title": "What this model does not claim", "limits": [
       "Unknown values are not invented or automatically converted to zero.",
       "Portfolio figures may refer to Germany rather than Berlin; scope must be checked.",
       "EVIDENCE_CHECKED indicates a matching text excerpt, not independent verification.",
       "Directories and non-target businesses must not be counted as property managers.",
       "Web reviews can still contain legal-name or geographic reservations.",
    ],
    "explorer_kicker": "COMPLETE RESEARCH DATABASE", "explorer_title": "Companies & Export",
    "explorer_desc": "Explore all consolidated records, including uncertain and excluded candidates. Filter by score or status, review sources, and export data.",
    "search": "Search", "search_ph": "Company, domain, address...", "classification": "Classification",
    "priority": "Priority", "reviewed_only": "Web-reviewed only", "management": "Management type",
    "minimum": "Minimum score", "sort": "Sort by", "sort_options": ["Highest minimum score", "Highest maximum score", "Company A–Z", "Web-reviewed first"],
    "showing": "{n} selected records out of {total}; filters are applied immediately.",
    "download_selection": "Download filtered results (CSV)", "download_complete": "Download complete results (CSV)",
    "sheet_section": "GOOGLE SHEETS", "sheet_title": "Open the dataset in Google Sheets",
    "sheet_desc": "The shared Google Sheet contains the full public dataset, not the current filtered selection.",
    "sheet_open": "Open in Google Sheets", "sheet_create": "Create a Google Sheet",
    "sheet_ready": "Download Google Sheets-compatible CSV", "sheet_instructions": "First-time setup: open a blank Sheet and import the downloaded CSV with File → Import → Upload, or paste the formula below into cell A1 to load the public dataset.",
    "sheet_formula": "Paste this into cell A1 in a new Google Sheet:",
    "sheet_config": "For a one-click link on future visits, set GOOGLE_SHEET_URL in your deployment settings to the URL of your prepared Google Sheet.",
    "sheet_url_missing": "No public CSV URL configured yet. Upload the Google Sheets-compatible CSV manually, or set PUBLIC_CSV_URL to the public raw CSV URL in GitHub.",
    "sheet_public_note": "Only the sanitized public dataset is used for Google Sheets. Private work emails and contacts are never transferred by this feature.",
    "all_data": "Company results", "units_note": "* Managed-unit numbers are reported with scope; nationwide figures are not Berlin-only counts.",
    "private_export": "Private internal export with business contacts", "private_note": "For local authorized use only; do not publish on GitHub.",
    "private_button": "Download internal contacts (CSV)", "public_note": "Public downloads exclude direct email addresses and individual contacts.",
    "details": "Company profile", "pick_company": "Choose a company", "no_companies": "No records match these filters.",
    "activity": "Activity", "reason": "Classification rationale", "scope": "Portfolio scope",
    "review_state": "Web review status", "min_metric": "Minimum score", "max_metric": "Maximum possible score",
    "open_website": "Visit official website", "open_source": "Review supporting source",
    "not_documented": "Not documented", "unverified": "Not verified",
    "quality_kicker": "DATA PROVENANCE & VALIDATION", "quality_title": "Data Quality & Validation",
    "quality_desc": "See missing data, actual site coverage, AI evidence status and records that still require human verification.",
    "checks": "Groq evidence matches", "checks_note": "Text evidence, not a human check",
    "exclusions": "Out-of-scope records", "exclusions_note": "Directories, articles or non-target sites",
    "waiting": "Not web-reviewed", "waiting_note": "Still require a review if used commercially",
    "quality_provenance": "Source quality", "ai_status": "AI analysis status",
    "field_coverage": "Coverage of essential fields", "fields": ["Company", "Website", "Business email", "Portfolio size", "Source URL"],
    "anomalies": "Records requiring attention", "review_caution": "Uncertain records remain visible to avoid incorrectly excluding valid companies.",
    "not_available": "Not provided", "col_company": "Company", "col_website": "Official website", "col_type": "Management",
    "col_units": "Managed units*", "col_scope": "Geographic scope", "col_min": "Min. score", "col_max": "Max. score",
    "col_priority": "Priority", "col_class": "Classification", "col_review": "Review status", "col_source": "Evidence source",
    "types": {"residential": "Residential / WEG", "mixed": "Mixed", "commercial": "Commercial", "sales_only": "Sales only", "management_unspecified": "General management", "unknown": "Unknown", "": "Unknown"},
    "classes": {"LIKELY": "Likely property manager", "REVIEW": "Needs verification", "EXCLUDED": "Out of scope"},
    "priorities": {"HIGH": "High", "MEDIUM": "Medium", "RESEARCH_MORE": "Research more", "VERIFY_COMPANY": "Verify company", "EXCLUDED": "Excluded"},
    "sim_units_options": {"unknown": "Unpublished", "small": "50 units", "medium": "350 units", "large": "2,000 units"},
    "sim_berlin_options": {"WEB_REVIEW_BERLIN": "Confirmed", "DIRECTORY_ADDRESS": "Directory address only", "UNKNOWN": "Unknown"},
    "sim_meter_options": {"CONFIRMED_TEXT": "Metering evidence", "BILLING_TEXT": "Service-charge billing", "UNKNOWN": "Unknown"},
    "sim_contact_options": {"named": "Named work email", "generic": "General business email", "phone": "Phone only", "none": "Unavailable"},
 },
 "de": {
    "language": "Sprache / Language", "nav_overview": "Übersicht", "nav_kpis": "Methodik & KPIs",
    "nav_explorer": "Unternehmen & Export", "nav_quality": "Datenqualität & Prüfung",
    "project": "BERLIN PROPERTY LEAD INTELLIGENCE", "case": "HEIDI SYSTEMS · FALLSTUDIE",
    "source": "Datensatz", "public_dataset": "Öffentlicher Forschungsdatensatz", "private_dataset": "Lokaler Arbeitsdatensatz",
    "total_base": "Datensätze", "sidebar_export": "ERGEBNISSE HERUNTERLADEN",
    "sidebar_caption": "Nur Lesezugriff. Kein CSV-Upload, Scraping oder API-Aufruf.",
    "sidebar_csv": "Alle Ergebnisse als CSV", "method_note": "Automatische Vorqualifizierung; keine vollständig unabhängig bestätigte Kundenliste.",
    "overview_kicker": "HEIDI SYSTEMS · B2B-MARKTANALYSE",
    "overview_title": "Berlin Property Lead Intelligence",
    "overview_desc": "Von der Websuche zur Qualifizierung von Hausverwaltungen: Marktpotenzial, Belege, Datenabdeckung und nachvollziehbare Quellen.",
    "candidates": "Zusammengeführte Kandidaten", "candidates_note": "Nach Zusammenführung und Dublettenabgleich",
    "likely": "Wahrscheinliche Hausverwaltungen", "likely_note": "Automatische Einstufung oder Webprüfung",
    "visited": "Besuchte Websites", "visited_note": "Navigation mit Stagehand / Chromium",
    "reviewed": "Im Web geprüfte Einträge", "reviewed_note": "Dokumentierte Prüfungen, teilweise mit Vorbehalt",
    "exports": "RECHERCHEERGEBNISSE EXPORTIEREN", "exports_desc": "CSV für Tabellenkalkulationen herunterladen; persönliche Kontaktdaten sind im öffentlichen Export nicht enthalten.",
    "download_all": "Gesamte Datenbank als CSV", "download_likely": "Wahrscheinliche Leads als CSV",
    "snapshot": "RECHERCHEÜBERBLICK", "classification_breakdown": "Kandidaten nach Kategorie",
    "priority_chart": "Vertriebliche Prioritäten", "records": "Einträge",
    "coverage": "Datenabdeckung und Reifegrad", "scraping_rate": "Website-Abdeckung",
    "ai_evidence": "KI-Textbelege", "units_count": "Portfolioangaben verfügbar",
    "review_count": "Unternehmen prüfen", "caution": "Ein von der KI gefundener Textbeleg ist keine unabhängige Prüfung. Eine Adresse in Berlin beweist nicht die Verwaltung von Objekten vor Ort.",
    "top_companies": "Vorrangige Kandidaten zur Prüfung",
    "kpis_kicker": "TRANSPARENTE LEAD-QUALIFIZIERUNG", "kpis_title": "Methodik & KPIs",
    "kpis_desc": "So werden Unternehmen gefunden, bereinigt, klassifiziert und bewertet. Fehlende Informationen erzeugen Unsicherheit statt automatisch null Punkte.",
    "steps_title": "Fünf Phasen des Workflows", "steps": [
      ("Recherche", "SearXNG und öffentliche Verzeichnisse identifizieren potenzielle Berliner Hausverwaltungen."),
      ("Browser-Recherche", "Stagehand/Chromium besucht zulässige Webseiten, zum Beispiel Über uns, Kontakt und Leistungen."),
      ("KI-Anreicherung", "Groq extrahiert Kategorien und Zahlen. Textbelege werden mit dem Seiteninhalt abgeglichen."),
      ("Datenkonsolidierung", "Python standardisiert Namen, führt Domains zusammen und trennt Verzeichnisse von Unternehmen."),
      ("Lead-Qualifizierung", "Transparente KPIs liefern einen Mindest- und Höchstwert sowie einen separaten Prüfstatus."),
    ],
    "kpi_score_title": "Scoring-Modell · 100 Punkte", "kpi_cards": [
      ("Passung der Verwaltung", 30, "Verwaltet das Unternehmen tatsächlich Gebäude?", "Wohnen / WEG: 30; gemischt: 25; allgemein: 20; gewerblich: 10; nur Verkauf: 0."),
      ("Verwalteter Bestand", 25, "Anzahl verwalteter Einheiten als Indikator für das Potenzial.", ">1.000: 25; 501–1.000: 19; 101–500: 13; 1–100: 5; unbekannt: offen."),
      ("Tätigkeit in Berlin", 15, "Betreut die Gesellschaft Objekte im Zielmarkt?", "Bestätigte Tätigkeit: 15; nur Verzeichnisadresse: 7–15; unbekannt: 0–15."),
      ("Verbrauch / Abrechnung", 20, "Heizkosten, Betriebskosten und Verbrauchserfassung zeigen mögliche Bedarfe.", "Direkte Belege: 20; Nebenkostenabrechnung: 12–20; unbekannt: 0–20."),
      ("Geschäftlicher Kontakt", 10, "Wie leicht kann die Gesellschaft kontaktiert werden?", "Namentlicher Kontakt: 8–10; allgemeine E-Mail: 5–10; Telefon: 3–10; unbekannt: 0–10."),
    ],
    "rule": "Regel", "reading_scores": "So lesen Sie den Score",
    "min_explain": "Mindestwert: Punkte, die durch vorhandene Informationen gestützt werden (ggf. noch prüfpflichtig).",
    "max_explain": "Höchstwert: erreichbarer Wert, wenn die noch fehlenden Angaben günstig ausfallen.",
    "score_example": "Beispiel: 65–90 / 100 bedeutet 65 aktuell gestützte und 25 unsichere Punkte, keinen bestätigten Wert von 90.",
    "priority_rules": "HIGH: Mindestwert ≥75; MEDIUM: 45–74; RESEARCH_MORE: unter 45. REVIEW erfordert unabhängig vom Score eine Prüfung.",
    "sim_title": "Interaktives Scoring-Beispiel", "sim_type": "Verwaltungsart", "sim_units": "Bestandsgröße",
    "sim_berlin": "Tätigkeit in Berlin", "sim_meter": "Belege zu Abrechnung / Verbrauch", "sim_contact": "Kontaktmöglichkeiten",
    "sim_score": "Geschätzter Score", "simulation_note": "Beispieldaten, keine echte Gesellschaft.",
    "limits_title": "Grenzen der Auswertung", "limits": [
       "Fehlende Angaben werden nicht erfunden oder automatisch mit null bewertet.",
       "Bestandszahlen können bundesweit statt nur in Berlin gelten; der Geltungsbereich muss geprüft werden.",
       "EVIDENCE_CHECKED bedeutet Textabgleich, nicht unabhängige Faktenprüfung.",
       "Verzeichnisse und fachfremde Websites dürfen nicht als Hausverwaltungen gezählt werden.",
       "Webprüfungen können weiterhin Vorbehalte zur Firma oder zum Geschäftsgebiet enthalten.",
    ],
    "explorer_kicker": "VOLLSTÄNDIGE RECHERCHE-DATENBANK", "explorer_title": "Unternehmen & Export",
    "explorer_desc": "Alle zusammengeführten Datensätze mit Unsicherheiten und Ausschlüssen. Nach Scores und Status filtern, Quellen prüfen und CSV exportieren.",
    "search": "Suche", "search_ph": "Firma, Domain, Adresse...", "classification": "Klassifikation",
    "priority": "Priorität", "reviewed_only": "Nur Web-geprüfte Einträge", "management": "Verwaltungsart",
    "minimum": "Mindest-Score", "sort": "Sortieren nach", "sort_options": ["Höchster Mindest-Score", "Höchster Höchst-Score", "Unternehmen A–Z", "Web-geprüfte zuerst"],
    "showing": "{n} von {total} Einträgen ausgewählt; Filter wirken sofort.",
    "download_selection": "Gefilterte Auswahl als CSV", "download_complete": "Vollständige Datenbank als CSV",
    "sheet_section": "GOOGLE TABELLEN", "sheet_title": "Datensatz in Google Tabellen öffnen",
    "sheet_desc": "Die freigegebene Tabelle enthält den vollständigen öffentlichen Datensatz, nicht die aktuelle Filterauswahl.",
    "sheet_open": "In Google Tabellen öffnen", "sheet_create": "Google-Tabelle erstellen",
    "sheet_ready": "Google-Tabellen-kompatible CSV laden", "sheet_instructions": "Ersteinrichtung: Leere Tabelle öffnen und die CSV über Datei → Importieren → Hochladen laden, oder die Formel unten in Zelle A1 einfügen.",
    "sheet_formula": "Diese Formel in Zelle A1 einer neuen Tabelle einfügen:",
    "sheet_config": "Für einen Direktlink bei zukünftigen Besuchen GOOGLE_SHEET_URL in den Deployment-Einstellungen auf die vorbereitete Google-Tabelle setzen.",
    "sheet_url_missing": "Noch keine öffentliche CSV-URL eingestellt. CSV manuell importieren oder PUBLIC_CSV_URL auf die öffentliche Raw-CSV-URL im GitHub-Repository setzen.",
    "sheet_public_note": "Google Tabellen erhält nur die bereinigten öffentlichen Daten. Private E-Mails und persönliche Kontaktdaten werden von dieser Funktion nicht übertragen.",
    "all_data": "Unternehmensübersicht", "units_note": "* Bestandszahlen enthalten ihren Geltungsbereich; bundesweite Werte sind keine reinen Berliner Zahlen.",
    "private_export": "Interner Export mit Geschäftskontakten", "private_note": "Nur für berechtigte lokale Nutzung; nicht auf GitHub veröffentlichen.",
    "private_button": "Internen Kontakt-CSV herunterladen", "public_note": "Öffentliche Downloads enthalten keine direkten E-Mails oder persönlichen Ansprechpartner.",
    "details": "Unternehmensprofil", "pick_company": "Unternehmen auswählen", "no_companies": "Keine Einträge für diese Filter.",
    "activity": "Tätigkeit", "reason": "Begründung der Einstufung", "scope": "Geltungsbereich",
    "review_state": "Status der Webprüfung", "min_metric": "Mindest-Score", "max_metric": "Maximaler Score",
    "open_website": "Offizielle Website öffnen", "open_source": "Belegquelle öffnen",
    "not_documented": "Nicht dokumentiert", "unverified": "Nicht geprüft",
    "quality_kicker": "DATENHERKUNFT & PRÜFUNG", "quality_title": "Datenqualität & Prüfung",
    "quality_desc": "Transparenter Überblick über fehlende Daten, besuchte Websites, KI-Belege und verbleibende manuelle Prüfungen.",
    "checks": "Abgeglichene Groq-Belege", "checks_note": "Textbeleg statt unabhängiger Prüfung",
    "exclusions": "Nicht passende Datensätze", "exclusions_note": "Verzeichnisse, Artikel oder fachfremde Seiten",
    "waiting": "Nicht im Web geprüft", "waiting_note": "Vor geschäftlicher Nutzung weiterhin prüfen",
    "quality_provenance": "Quellenqualität", "ai_status": "Status der KI-Analyse",
    "field_coverage": "Abdeckung zentraler Felder", "fields": ["Firmenname", "Website", "Geschäfts-E-Mail", "Bestandsgröße", "Quellenlink"],
    "anomalies": "Einträge mit Handlungsbedarf", "review_caution": "Unklare Einträge bleiben sichtbar, damit valide Unternehmen nicht vorschnell ausgeschlossen werden.",
    "not_available": "Keine Angabe", "col_company": "Unternehmen", "col_website": "Offizielle Website", "col_type": "Verwaltung",
    "col_units": "Verwaltete Einheiten*", "col_scope": "Geltungsbereich", "col_min": "Min. Score", "col_max": "Max. Score",
    "col_priority": "Priorität", "col_class": "Einstufung", "col_review": "Prüfstatus", "col_source": "Belegquelle",
    "types": {"residential": "Wohnen / WEG", "mixed": "Gemischt", "commercial": "Gewerblich", "sales_only": "Nur Verkauf", "management_unspecified": "Allgemeine Verwaltung", "unknown": "Unbekannt", "": "Unbekannt"},
    "classes": {"LIKELY": "Wahrscheinliche Hausverwaltung", "REVIEW": "Prüfung erforderlich", "EXCLUDED": "Nicht passend"},
    "priorities": {"HIGH": "Hoch", "MEDIUM": "Mittel", "RESEARCH_MORE": "Mehr recherchieren", "VERIFY_COMPANY": "Unternehmen prüfen", "EXCLUDED": "Ausgeschlossen"},
    "sim_units_options": {"unknown": "Nicht veröffentlicht", "small": "50 Einheiten", "medium": "350 Einheiten", "large": "2.000 Einheiten"},
    "sim_berlin_options": {"WEB_REVIEW_BERLIN": "Bestätigt", "DIRECTORY_ADDRESS": "Nur Verzeichnisadresse", "UNKNOWN": "Unbekannt"},
    "sim_meter_options": {"CONFIRMED_TEXT": "Verbrauchsbelege", "BILLING_TEXT": "Nebenkostenabrechnung", "UNKNOWN": "Unbekannt"},
    "sim_contact_options": {"named": "Personalisierte Geschäfts-E-Mail", "generic": "Allgemeine Geschäfts-E-Mail", "phone": "Nur Telefon", "none": "Nicht verfügbar"},
 }
}

st.set_page_config(page_title="Berlin Property Lead Intelligence | Heidi Systems", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
:root {--ink:#142E55;--muted:#4B6480;--accent:#1768C8;--paper:#FFF;--page:#F4F8FF;}
html,body,.stApp,[data-testid="stSidebar"],.stApp p,.stApp label,.stApp input,
.stApp button,.stApp h1,.stApp h2,.stApp h3,.stApp h4,
[data-testid="stMetricValue"],[data-testid="stMetricLabel"] {
  font-family:"Inter","Segoe UI",Arial,sans-serif !important;
}
.stApp, [data-testid="stAppViewContainer"] {background:var(--page);color:var(--ink);}
[data-testid="stSidebar"] {background:#fff !important;border-right:1px solid #D9E5F3;}
[data-testid="stSidebar"] p,[data-testid="stSidebar"] label,
[data-testid="stSidebar"] button,[data-testid="stSidebar"] [data-testid="stMarkdownContainer"]{color:#203C5B !important;opacity:1 !important;}
[data-testid="stSidebarNav"] a {border-radius:10px !important;color:#274866 !important;font-weight:600;}
[data-testid="stSidebarNav"] a:hover {background:#EAF3FF !important;}
[data-testid="stSidebarNav"] a[aria-current="page"],
[data-testid="stSidebarNav"] a[aria-selected="true"] {background:#E1EEFE !important;color:#1558AD !important;border-left:3px solid #1768C8;}
.block-container {max-width:1480px;padding-top:1.7rem;padding-bottom:4rem;}
.hero {background:linear-gradient(120deg,#fff,#EEF5FF 75%,#E5F0FF);
 border:1px solid #C9DCF3;border-radius:18px;padding:28px 32px;margin-bottom:23px;
 box-shadow:0 7px 24px rgba(34,77,129,.045);}
.hero h1 {font-size:clamp(28px,3.5vw,44px);color:#173E71;line-height:1.17;margin:10px 0 11px;font-weight:750;}
.hero p {font-size:16px;line-height:1.55;color:#44617F;margin:0;max-width:950px;}
.eyebrow {font-size:11px;font-weight:750;letter-spacing:1.4px;color:#1768C8;}
.stat {background:#fff;border:1px solid #D9E5F3;border-radius:14px;padding:19px 20px;
 min-height:136px;box-shadow:0 4px 14px rgba(28,74,122,.04);}
.stat .label {font-size:13px;font-weight:650;color:#4D6480;}
.stat .number {font-size:36px;font-weight:760;color:#163D74;line-height:1.45;}
.stat .note {font-size:12px;color:#67809D;line-height:1.43;}
.section-label {font-size:11px;font-weight:750;letter-spacing:1.45px;color:#1768C8;margin:18px 0 9px;}
.info-card,.kpi-card {background:white;border:1px solid #D9E5F3;border-radius:13px;padding:18px 20px;margin:10px 0;}
.kpi-card h4 {margin:0 0 7px;font-size:17px;color:#163D72;}
.kpi-card p,.info-card p {font-size:14px;line-height:1.55;color:#4C6281;margin:6px 0;}
.kpi-card .score {font-size:20px;font-weight:700;color:#1768C8;float:right;}
.small-print {font-size:13px;color:#607892;margin:13px 0 21px;}
[data-testid="stMetric"] {background:white;border:1px solid #D9E5F3;border-radius:13px;padding:15px;}
[data-testid="stMetricValue"] {color:#163D74 !important;}
[data-testid="stDataFrame"] {border:1px solid #D9E5F3;border-radius:11px;overflow:hidden;}
[data-testid="stDownloadButton"] button {min-height:44px;border-radius:10px;font-weight:680;}
[data-testid="stBaseButton-primary"] {background:#1768C8 !important;border-color:#1768C8 !important;color:white !important;}
[data-testid="stBaseButton-primary"] p {color:white !important;}
</style>""", unsafe_allow_html=True)


def config_value(name: str) -> str:
    """Read deployment settings without requiring a secrets.toml file."""
    env = os.environ.get(name, "").strip()
    try:
        secret = st.secrets.get(name, "")
    except Exception:
        secret = ""
    return str(secret or env).strip()


@st.cache_data(show_spinner=False)
def read_csv(path: str, stamp: int) -> pd.DataFrame:
    return pd.read_csv(path, sep=";", encoding="utf-8-sig", dtype=str, keep_default_na=False)


def load_data() -> tuple[pd.DataFrame, bool, str]:
    public_mode = config_value("PUBLIC_MODE").lower() != "false"
    filename = PUBLIC if public_mode else (LOCAL if LOCAL.exists() else PUBLIC)
    if not filename.exists():
        st.error("Public dataset missing: data/public/leads_public.csv")
        st.stop()
    data = read_csv(str(filename), filename.stat().st_mtime_ns).copy()
    defaults = ["company_name", "website", "domain", "address", "email", "phone", "management_type", "units_managed",
                "units_scope", "metering_signal", "berlin_signal", "score_min", "score_max", "priority", "classification",
                "classification_reason", "data_quality", "completeness_pct", "scrape_status", "ai_validation", "review_status",
                "validation_status", "source_url", "validation_sources", "validation_notes", "source_types", "contact_person"]
    for key in defaults:
        if key not in data:
            data[key] = ""
    for key in ["units_managed", "score_min", "score_max", "completeness_pct"]:
        data[key] = pd.to_numeric(data[key], errors="coerce")
    safe = public_mode or filename == PUBLIC
    label = L["public_dataset"] if safe else L["private_dataset"]
    return data, safe, label


def fmt_num(num: int) -> str:
    return f"{num:,}".replace(",", " ")


def status_count(column: str, status: str) -> int:
    return int((df[column].astype(str) == status).sum())


def card(label: str, number: int | str, note: str) -> None:
    st.markdown(
        '<div class="stat"><div class="label">'+html.escape(label)+'</div><div class="number">'+
        html.escape(fmt_num(number) if isinstance(number, int) else str(number))+'</div><div class="note">'+
        html.escape(note)+'</div></div>', unsafe_allow_html=True)


def hero(kicker: str, title: str, subtitle: str) -> None:
    st.markdown('<div class="hero"><div class="eyebrow">'+html.escape(kicker)+'</div><h1>'+
                html.escape(title)+'</h1><p>'+html.escape(subtitle)+'</p></div>', unsafe_allow_html=True)


def chart_style(fig, height: int = 315):
    fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Inter, Segoe UI, Arial", size=13, color=DARK),
                      height=height, margin=dict(l=15, r=20, t=16, b=25),
                      legend=dict(orientation="h", x=0, y=-0.17))
    fig.update_xaxes(showgrid=False, zeroline=False, color="#54708D")
    fig.update_yaxes(gridcolor="#E4EDF6", zeroline=False, color="#54708D")
    return fig


def bar_chart(values: pd.Series, mapping: dict[str, str]):
    items = values.sort_values()
    labels = [mapping.get(str(v), str(v)) for v in items.index]
    fig = go.Figure(go.Bar(y=labels, x=items.values, orientation="h", text=items.values,
                           marker_color=[COLORS.get(str(i), MUTED) for i in items.index],
                           textposition="outside", cliponaxis=False))
    fig.update_layout(showlegend=False)
    return chart_style(fig, 330)


def export_csv(table: pd.DataFrame, *, sep: str = ";", include_contacts: bool = False) -> bytes:
    selected = table.copy()
    if not include_contacts:
        selected = selected.drop(columns=["email", "phone", "contact_person"], errors="ignore")
    selected = selected.drop(columns=["page_text"], errors="ignore")
    return csv_safe(selected).to_csv(index=False, sep=sep).encode("utf-8-sig")


def google_sheets_panel() -> None:
    """Never suggests that a local download auto-opens in Sheets.

    One click is enabled if GOOGLE_SHEET_URL already points to an existing
    Google Sheet. Otherwise Sheets is opened and a comma CSV or IMPORTDATA
    formula is offered for first-time setup.
    """
    st.markdown('<div class="section-label">'+html.escape(L["sheet_section"])+"</div>", unsafe_allow_html=True)
    st.subheader(L["sheet_title"])
    st.caption(L["sheet_desc"])
    sheet_url = config_value("GOOGLE_SHEET_URL")
    public_csv_url = config_value("PUBLIC_CSV_URL")
    valid_sheet = sheet_url.startswith("https://docs.google.com/spreadsheets/")
    if valid_sheet:
        st.link_button(L["sheet_open"], sheet_url, use_container_width=True, type="primary")
    else:
        left, right = st.columns(2, gap="medium")
        with left:
            st.link_button(L["sheet_create"], "https://sheets.new", use_container_width=True)
        with right:
            # Export only curated public columns even in local/private mode.
            google_data = pd.read_csv(PUBLIC, sep=";", encoding="utf-8-sig", dtype=str, keep_default_na=False)
            st.download_button(L["sheet_ready"], export_csv(google_data, sep=","),
                               "berlin_property_leads_google_sheets.csv", "text/csv", use_container_width=True,
                               key="google_sheets_comma_csv")
        st.info(L["sheet_instructions"])
        if public_csv_url.startswith("https://") and public_csv_url.lower().endswith(".csv"):
            st.caption(L["sheet_formula"])
            st.code(f'=IMPORTDATA("{public_csv_url}")', language="text")
        else:
            st.caption(L["sheet_url_missing"])
        with st.expander(L["sheet_config"], expanded=False):
            st.code("GOOGLE_SHEET_URL = https://docs.google.com/spreadsheets/d/.../edit\n"
                    "PUBLIC_CSV_URL = https://raw.githubusercontent.com/USERNAME/REPO/main/data/public/leads_public_google.csv",
                    language="text")
    st.caption(L["sheet_public_note"])


def overview() -> None:
    hero(L["overview_kicker"], L["overview_title"], L["overview_desc"])
    total = len(df)
    probable = status_count("classification", "LIKELY")
    visited = status_count("scrape_status", "OK")
    reviewed = int(df.review_status.astype(str).str.startswith("WEB_REVIEWED").sum())
    for col, info in zip(st.columns(4, gap="medium"), [
        (L["candidates"], total, L["candidates_note"]),
        (L["likely"], probable, L["likely_note"]),
        (L["visited"], visited, L["visited_note"]),
        (L["reviewed"], reviewed, L["reviewed_note"]),
    ]):
        with col:
            card(*info)
    st.markdown('<div class="info-card"><div class="eyebrow">'+html.escape(L["exports"])+
                '</div><p>'+html.escape(L["exports_desc"])+"</p></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(L["download_all"], export_csv(df), "berlin_property_leads_all.csv", "text/csv",
                           use_container_width=True, type="primary", key="overview_all")
    with c2:
        likely = df[df.classification == "LIKELY"]
        st.download_button(f'{L["download_likely"]} ({len(likely)})', export_csv(likely), "berlin_property_leads_likely.csv",
                           "text/csv", use_container_width=True, key="overview_likely")
    st.markdown('<div class="section-label">'+html.escape(L["snapshot"])+"</div>", unsafe_allow_html=True)
    a, b = st.columns(2, gap="large")
    with a:
        st.subheader(L["classification_breakdown"])
        ct = df.classification.value_counts()
        fig = go.Figure(go.Pie(labels=[L["classes"].get(v, v) for v in ct.index], values=ct.values,
                               hole=.64, textinfo="label+percent", textposition="outside",
                               marker_colors=[COLORS.get(v, LIGHT) for v in ct.index]))
        fig.update_layout(showlegend=False, annotations=[dict(text=f'<b>{total}</b><br>{L["records"]}',x=.5,y=.5,showarrow=False)])
        st.plotly_chart(chart_style(fig, 320), use_container_width=True)
    with b:
        st.subheader(L["priority_chart"])
        st.plotly_chart(bar_chart(df.priority.value_counts(), L["priorities"]), use_container_width=True)
    st.subheader(L["coverage"])
    m1,m2,m3,m4 = st.columns(4)
    m1.metric(L["scraping_rate"], f"{visited/total:.1%}" if total else "0%")
    m2.metric(L["ai_evidence"], status_count("ai_validation","EVIDENCE_CHECKED"))
    m3.metric(L["units_count"], int(df.units_managed.notna().sum()))
    m4.metric(L["review_count"], status_count("classification","REVIEW"))
    st.caption(L["caution"])
    st.subheader(L["top_companies"])
    top = df[df.classification == "LIKELY"].sort_values(["score_min","score_max"], ascending=False).head(12)
    st.dataframe(top[["company_name", "website", "management_type", "score_min", "score_max", "priority", "review_status"]],
                 hide_index=True, use_container_width=True, height=360, column_config={
                    "company_name":L["col_company"], "website":st.column_config.LinkColumn(L["col_website"]),
                    "management_type":L["col_type"], "score_min":L["col_min"], "score_max":L["col_max"],
                    "priority":L["col_priority"], "review_status":L["col_review"]})


def methodology() -> None:
    hero(L["kpis_kicker"], L["kpis_title"], L["kpis_desc"])
    st.subheader(L["steps_title"])
    for i,(name, description) in enumerate(L["steps"], 1):
        st.markdown('<div class="info-card"><div class="eyebrow">'+f'{i:02d} / '+html.escape(name)+
                    '</div><p>'+html.escape(description)+"</p></div>",unsafe_allow_html=True)
    st.subheader(L["kpi_score_title"])
    cards = L["kpi_cards"]
    fig = go.Figure(go.Bar(x=[x[1] for x in cards], y=[x[0] for x in cards], orientation="h",
                           marker_color=[BLUE, "#477FCC", "#78A4E2", LIGHT, MUTED],
                           text=[f"{x[1]} / 100" for x in cards], textposition="inside"))
    fig.update_layout(yaxis=dict(autorange="reversed"),showlegend=False)
    st.plotly_chart(chart_style(fig, 310), use_container_width=True)
    a,b = st.columns(2)
    for idx,(name, points, why, rule) in enumerate(cards):
        with (a if idx%2==0 else b):
            st.markdown('<div class="kpi-card"><span class="score">'+f'{points} / 100'+
                        '</span><h4>'+html.escape(name)+'</h4><p>'+html.escape(why)+
                        '</p><p><b>'+html.escape(L["rule"])+':</b> '+html.escape(rule)+"</p></div>", unsafe_allow_html=True)
    st.subheader(L["reading_scores"])
    st.write(L["min_explain"])
    st.write(L["max_explain"])
    st.info(L["score_example"])
    st.caption(L["priority_rules"])
    st.subheader(L["sim_title"])
    with st.container(border=True):
        c1,c2,c3 = st.columns(3)
        with c1:
            management = st.selectbox(L["sim_type"], ["residential","mixed","commercial","unknown"],
                                      format_func=lambda k:L["types"].get(k,k))
            units = st.selectbox(L["sim_units"], ["unknown","small","medium","large"],
                                 format_func=lambda k:L["sim_units_options"].get(k,k))
        with c2:
            berlin = st.selectbox(L["sim_berlin"], ["WEB_REVIEW_BERLIN","DIRECTORY_ADDRESS","UNKNOWN"],
                                  format_func=lambda k:L["sim_berlin_options"].get(k,k))
            meter = st.selectbox(L["sim_meter"], ["CONFIRMED_TEXT","BILLING_TEXT","UNKNOWN"],
                                 format_func=lambda k:L["sim_meter_options"].get(k,k))
        with c3:
            contact = st.selectbox(L["sim_contact"], ["named","generic","phone","none"],
                                   format_func=lambda k:L["sim_contact_options"].get(k,k))
        example = {"management_type":management,"units_managed":{"unknown":None,"small":50,"medium":350,"large":2000}[units],
                   "units_scope":"SIMULATION" if units != "unknown" else "NOT_VERIFIED", "berlin_signal":berlin,
                   "metering_signal":meter, "email":"name@example.com" if contact == "named" else "info@example.com" if contact=="generic" else "",
                   "phone":"+49 30 000000" if contact=="phone" else ""}
        minimum, maximum, _ = compute_score_from_fields(example)
        st.metric(L["sim_score"], f"{minimum}–{maximum} / 100")
        st.progress(minimum / 100)
        st.caption(L["simulation_note"])
    st.subheader(L["limits_title"])
    for note in L["limits"]:
        st.markdown("- "+note)


def explorer() -> None:
    hero(L["explorer_kicker"], L["explorer_title"], L["explorer_desc"])
    a,b,c,d = st.columns([1.6,1,1,1],gap="medium")
    with a: search = st.text_input(L["search"], placeholder=L["search_ph"])
    with b:
        available_classes = sorted(df.classification.unique())
        allowed_classes = st.multiselect(L["classification"], available_classes, default=available_classes,
                                         format_func=lambda v:L["classes"].get(v,v))
    with c:
        available_priorities = sorted(df.priority.unique())
        allowed_priorities = st.multiselect(L["priority"], available_priorities, default=available_priorities,
                                            format_func=lambda v:L["priorities"].get(v,v))
    with d: only_reviewed = st.checkbox(L["reviewed_only"])
    e,f,g = st.columns([1.4,1,1.2])
    with e:
        available_types = sorted(df.management_type.unique())
        allowed_types = st.multiselect(L["management"],available_types,default=available_types,
                                      format_func=lambda v:L["types"].get(v,v))
    with f: minimum = st.slider(L["minimum"],0,100,0,5)
    with g: sort_index = st.selectbox(L["sort"], list(range(4)),format_func=lambda v:L["sort_options"][v])
    view = df[df.classification.isin(allowed_classes)&df.priority.isin(allowed_priorities)&
              df.management_type.isin(allowed_types)&(df.score_min.fillna(0)>=minimum)].copy()
    if only_reviewed:
        view = view[view.review_status.astype(str).str.startswith("WEB_REVIEWED")]
    if search.strip():
        combined = view["company_name"].astype(str)+" "+view["domain"].astype(str)+" "+view["address"].astype(str)
        view = view[combined.str.casefold().str.contains(search.casefold().strip(),regex=False)]
    if sort_index == 0: view = view.sort_values(["score_min","score_max"],ascending=False)
    elif sort_index == 1: view = view.sort_values("score_max",ascending=False)
    elif sort_index == 2: view = view.sort_values("company_name")
    else:
        view = view.assign(_has_review=view.review_status.str.startswith("WEB_REVIEWED")).sort_values(
            ["_has_review","score_min"],ascending=False).drop(columns="_has_review")
    st.caption(L["showing"].format(n=fmt_num(len(view)),total=fmt_num(len(df))))
    dl1,dl2 = st.columns(2)
    with dl1:
        st.download_button(L["download_selection"]+f" ({len(view)})", export_csv(view),
                           "berlin_filtered_results.csv", "text/csv", type="primary", use_container_width=True,key="export_filtered")
    with dl2:
        st.download_button(L["download_complete"]+f" ({len(df)})", export_csv(df),
                           "berlin_complete_results.csv", "text/csv", use_container_width=True,key="export_complete")
    google_sheets_panel()
    st.subheader(L["all_data"])
    table_columns = ["company_name","website","management_type","units_managed","units_scope","score_min","score_max","priority","classification","review_status","source_url"]
    table = view[table_columns].copy()
    table["management_type"] = table.management_type.map(lambda x:L["types"].get(x,x))
    table["classification"] = table.classification.map(lambda x:L["classes"].get(x,x))
    table["priority"] = table.priority.map(lambda x:L["priorities"].get(x,x))
    table["source_url"] = table.source_url.str.split(" | ",regex=False).str[0]
    st.dataframe(table,use_container_width=True,hide_index=True,height=535,column_config={
        "company_name":st.column_config.TextColumn(L["col_company"],width="large"),
        "website":st.column_config.LinkColumn(L["col_website"]),
        "management_type":L["col_type"],
        "units_managed":st.column_config.NumberColumn(L["col_units"],format="%.0f"),
        "units_scope":L["col_scope"],
        "score_min":L["col_min"],"score_max":L["col_max"],
        "priority":L["col_priority"],"classification":L["col_class"],"review_status":L["col_review"],
        "source_url":st.column_config.LinkColumn(L["col_source"]),
    })
    st.caption(L["units_note"])
    if not public_mode:
        with st.expander(L["private_export"]):
            st.caption(L["private_note"])
            st.download_button(L["private_button"],export_csv(view,include_contacts=True),
                               "berlin_internal_contacts.csv","text/csv",use_container_width=True,key="private_csv")
    else:
        st.caption(L["public_note"])
    st.subheader(L["details"])
    if view.empty:
        st.info(L["no_companies"])
        return
    idx = st.selectbox(L["pick_company"], list(view.index),
                       format_func=lambda i:f'{view.loc[i,"company_name"]} · {view.loc[i,"domain"]}')
    row = view.loc[idx]
    a,b = st.columns([1.2,.8],gap="large")
    with a:
        st.subheader(str(row["company_name"]))
        st.write(f'**{L["activity"]}:** {L["types"].get(str(row["management_type"]),row["management_type"])}')
        st.write(f'**{L["classification"]}:** {L["classes"].get(row["classification"],row["classification"])}')
        st.write(f'**{L["reason"]}:** {row["classification_reason"] or L["not_documented"]}')
        st.write(f'**{L["scope"]}:** {row["units_scope"] or L["not_documented"]}')
        st.write(f'**{L["review_state"]}:** {row["review_status"] or L["unverified"]}')
        if row["validation_notes"]:
            st.warning(str(row["validation_notes"]))
    with b:
        low = int(row["score_min"]) if pd.notna(row["score_min"]) else 0
        high = int(row["score_max"]) if pd.notna(row["score_max"]) else 100
        st.metric(L["min_metric"],f"{low} / 100")
        st.metric(L["max_metric"],f"{high} / 100")
        web = str(row["website"])
        if web.startswith(("https://","http://")):
            st.link_button(L["open_website"],web,use_container_width=True)
        sources = str(row["validation_sources"] or row["source_url"]).split(" | ")
        links = [s for s in sources if s.startswith(("https://","http://"))]
        if links:
            st.link_button(L["open_source"],links[0],use_container_width=True)


def quality() -> None:
    hero(L["quality_kicker"],L["quality_title"],L["quality_desc"])
    evidence = status_count("ai_validation","EVIDENCE_CHECKED")
    reviewed = int(df.review_status.str.startswith("WEB_REVIEWED").sum())
    excluded = status_count("classification","EXCLUDED")
    metrics = [
        (L["checks"],evidence,L["checks_note"]),
        (L["reviewed"],reviewed,L["reviewed_note"]),
        (L["exclusions"],excluded,L["exclusions_note"]),
        (L["waiting"],len(df)-reviewed,L["waiting_note"]),
    ]
    for column,data in zip(st.columns(4),metrics):
        with column: card(*data)
    a,b = st.columns(2,gap="large")
    with a:
        st.subheader(L["quality_provenance"])
        st.plotly_chart(bar_chart(df.data_quality.replace("", "UNKNOWN").value_counts(), {}),use_container_width=True)
    with b:
        st.subheader(L["ai_status"])
        st.plotly_chart(bar_chart(df.ai_validation.replace("", "NOT_ANALYZED").value_counts(),{}),use_container_width=True)
    st.subheader(L["field_coverage"])
    fields = [
        int(df.company_name.str.strip().ne("").sum()),
        int(df.website.str.startswith("http").sum()),
        int(df.email.str.contains("@",regex=False).sum()),
        int(df.units_managed.notna().sum()),
        int(df.source_url.str.strip().ne("").sum()),
    ]
    fig = go.Figure(go.Bar(x=L["fields"],y=[100*n/len(df) if len(df) else 0 for n in fields],
                           marker_color=[BLUE,"#4E86CE",LIGHT,MUTED,GREY],
                           text=[f'{n}/{len(df)}' for n in fields],textposition="outside"))
    fig.update_yaxes(range=[0,115],ticksuffix="%")
    st.plotly_chart(chart_style(fig,305),use_container_width=True)
    st.subheader(L["anomalies"])
    flagged = df[(df.classification=="REVIEW") | (df.review_status=="WEB_REVIEWED_WITH_RESERVATIONS")].head(120)
    st.dataframe(flagged[["company_name","domain","classification_reason","review_status","validation_notes","website"]],
                 use_container_width=True,hide_index=True,height=390,
                 column_config={"company_name":L["col_company"],"website":st.column_config.LinkColumn(L["col_website"])})
    st.caption(L["review_caution"])


language_label = st.sidebar.selectbox("Language / Sprache", ["English", "Deutsch"], index=0)
LANG = "de" if language_label == "Deutsch" else "en"
L = I18N[LANG]
df, public_mode, source_label = load_data()

with st.sidebar:
    st.markdown("**"+L["project"]+"**")
    st.caption(L["case"])
    st.divider()
    st.markdown("**"+L["sidebar_export"]+"**")
    st.caption(L["sidebar_caption"])
    st.download_button(L["sidebar_csv"],export_csv(df),"berlin_property_leads.csv","text/csv",
                       use_container_width=True,type="primary",key="sidebar_csv")
    st.divider()
    st.caption(f'{L["source"]}: {source_label}')
    st.caption(f'{L["total_base"]}: {fmt_num(len(df))}')
    st.caption(L["method_note"])

pages = [
    st.Page(overview,title=L["nav_overview"],default=True),
    st.Page(methodology,title=L["nav_kpis"]),
    st.Page(explorer,title=L["nav_explorer"]),
    st.Page(quality,title=L["nav_quality"]),
]
st.navigation(pages,position="sidebar").run()
