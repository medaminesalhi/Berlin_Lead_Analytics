"""Create a contact-free public dataset for Streamlit Community Cloud.

Does not upload or publish it. Review the file before committing it to GitHub.
"""
from pathlib import Path
import argparse
import pandas as pd

from pipeline import ROOT, csv_safe

SOURCE = ROOT / "data" / "processed" / "leads_all.csv"
DEST = ROOT / "data" / "public" / "leads_public.csv"
GOOGLE_DEST = ROOT / "data" / "public" / "leads_public_google.csv"
PUBLIC_FIELDS = [
    "company_name", "website", "domain", "management_type", "units_managed",
    "units_scope", "metering_signal", "berlin_signal", "score_min", "score_max",
    "priority", "classification", "classification_reason", "data_quality",
    "completeness_pct", "scrape_status", "ai_validation", "review_status",
    "validation_status", "source_types", "source_url", "validation_sources",
]


def create_public(source: Path = SOURCE, destination: Path = DEST):
    data = pd.read_csv(source, sep=";", encoding="utf-8-sig", keep_default_na=False, dtype=str)
    columns = [column for column in PUBLIC_FIELDS if column in data.columns]
    safe = data[columns].copy()
    destination.parent.mkdir(parents=True, exist_ok=True)
    secured = csv_safe(safe)
    secured.to_csv(destination, sep=";", encoding="utf-8-sig", index=False)
    # Google Sheets IMPORTDATA supports comma-delimited CSV, not our semicolon UI export.
    google_dest = destination.parent / "leads_public_google.csv"
    secured.to_csv(google_dest, sep=",", encoding="utf-8-sig", index=False)
    return len(safe), columns


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare CSV for public Streamlit dashboard")
    parser.add_argument("--confirm", action="store_true", help="Confirm that you will inspect the exported CSV before GitHub upload")
    args = parser.parse_args()
    if not args.confirm:
        parser.error("Ajoute --confirm après avoir décidé de préparer une copie publique sans coordonnées.")
    count, cols = create_public()
    print(f"Fichier public PRÉPARÉ (non publié) : {DEST}")
    print(f"CSV Google Sheets PRÉPARÉ : {GOOGLE_DEST}")
    print(f"{count} candidats, {len(cols)} colonnes. Vérifier avant de pousser sur GitHub.")
