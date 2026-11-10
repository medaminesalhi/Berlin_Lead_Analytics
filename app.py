"""Read-only dashboard for the Berlin property-manager qualification pipeline."""
from pathlib import Path
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
LOCAL = ROOT / "data" / "processed" / "leads_all.csv"
PUBLIC = ROOT / "data" / "public" / "leads_public.csv"

st.set_page_config(page_title="Berlin Property Lead Intelligence", page_icon="🏢", layout="wide")
st.title("Berlin Property Lead Intelligence")
st.caption("Case study · Heidi Systems | Research → Validation → Lead Qualification")
st.info("Scores indicatifs. Une preuve textuelle validée par un LLM ne remplace pas une vérification humaine.")

uploaded = st.sidebar.file_uploader("Charger un CSV nettoyé (facultatif)", type=["csv"])
source = uploaded if uploaded is not None else (PUBLIC if PUBLIC.exists() else LOCAL)
if uploaded is None and not source.exists():
    st.warning("Pas encore de données. Lance `python pipeline.py`, puis relance Streamlit, ou importe un CSV.")
    st.stop()

try:
    data = pd.read_csv(source, sep=";", encoding="utf-8-sig", keep_default_na=False)
except Exception as exc:
    st.error(f"Impossible de lire le CSV : {exc}")
    st.stop()

if data.empty:
    st.warning("Le fichier ne contient aucune ligne.")
    st.stop()

for col in ("score_min", "score_max", "completeness_pct"):
    if col in data:
        data[col] = pd.to_numeric(data[col], errors="coerce")
for col in ("classification", "priority", "management_type", "company_name"):
    if col not in data:
        data[col] = ""

st.sidebar.header("Filtres")
classes = sorted(data["classification"].dropna().astype(str).unique().tolist())
statuses = st.sidebar.multiselect("Classification", options=classes, default=["LIKELY", "REVIEW"] if "LIKELY" in classes and "REVIEW" in classes else classes)
priorities = st.sidebar.multiselect("Priorité", options=sorted(data["priority"].astype(str).unique().tolist()), default=sorted(data["priority"].astype(str).unique().tolist()))
search = st.sidebar.text_input("Rechercher une société")

view = data[data["classification"].isin(statuses) & data["priority"].isin(priorities)].copy()
if search.strip():
    view = view[view["company_name"].astype(str).str.contains(search.strip(), case=False, regex=False)]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Candidats affichés", len(view))
c2.metric("Prospects probables", int((view.classification == "LIKELY").sum()))
c3.metric("Priorité haute", int((view.priority == "HIGH").sum()))
c4.metric("À examiner", int((view.classification == "REVIEW").sum()))

left, right = st.columns(2)
with left:
    st.subheader("Classification")
    st.bar_chart(view.classification.value_counts().rename_axis("Statut").reset_index(name="Sociétés").set_index("Statut"))
with right:
    st.subheader("Priorités commerciales")
    st.bar_chart(view.priority.value_counts().rename_axis("Priorité").reset_index(name="Sociétés").set_index("Priorité"))

st.subheader("Entreprises et qualification")
# Do not accidentally reveal named contacts or direct emails on a public deployment.
preferred = [
    "company_name", "website", "management_type", "units_managed", "metering_signal",
    "berlin_signal", "score_min", "score_max", "priority", "classification",
    "data_quality", "source_url", "review_status"
]
columns = [x for x in preferred if x in view.columns]
shown = view[columns].sort_values(by="score_min", ascending=False, na_position="last") if "score_min" in columns else view[columns]
st.dataframe(shown, use_container_width=True, hide_index=True, height=460)
st.download_button("Télécharger la sélection (sans emails personnels)",
    data=shown.to_csv(index=False, sep=";").encode("utf-8-sig"),
    file_name="berlin_leads_selection.csv", mime="text/csv")

with st.expander("Méthodologie et limites"):
    st.markdown("""
    - **Découverte :** recherches web, Stagehand et annuaires professionnels.
    - **Nettoyage :** noms normalisés, fusion par domaine, exclusions des annuaires.
    - **Qualification :** activité (30), portefeuille (25), Berlin (15), comptage/charges (20), contactabilité (10).
    - **Valeurs inconnues :** représentées par une fourchette (`score_min` / `score_max`).
    - **Fiabilité :** `data_quality` distinct du score commercial.
    - **Vérification :** `review_status` indique si une fiche a été confirmée manuellement.
    """)
