"""Berlin Property Lead Intelligence — light Times New Roman Streamlit dashboard.

Four pages: executive overview, KPI methodology, full explorer, data quality.
Public deployments read only curated data/public/leads_public.csv.
"""
from __future__ import annotations

import html
import os
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from pipeline import compute_score_from_fields, csv_safe

ROOT = Path(__file__).resolve().parent
LOCAL = ROOT / "data" / "processed" / "leads_all.csv"
PUBLIC = ROOT / "data" / "public" / "leads_public.csv"
REPORT = ROOT / "data" / "processed" / "quality_report.json"

NAVY = "#142E55"
TEAL = "#1754AB"
BLUE = "#4B8CE4"
AMBER = "#86ACDD"
ROSE = "#B3BBC9"
SLATE = "#94A7C1"
PALETTE = {
    "LIKELY": TEAL, "REVIEW": AMBER, "EXCLUDED": ROSE,
    "HIGH": TEAL, "MEDIUM": BLUE, "RESEARCH_MORE": SLATE,
    "VERIFY_COMPANY": AMBER, "EXCLUDED_PRIORITY": ROSE,
}
CLASS_FR = {"LIKELY": "Prospect probable", "REVIEW": "À vérifier", "EXCLUDED": "Hors cible"}
PRIORITY_FR = {
    "HIGH": "Haute", "MEDIUM": "Moyenne", "RESEARCH_MORE": "À enrichir",
    "VERIFY_COMPANY": "Vérifier l'entreprise", "EXCLUDED": "Exclu",
}
TYPE_FR = {
    "residential": "Résidentiel / WEG", "mixed": "Mixte", "commercial": "Commercial",
    "management_unspecified": "Gestion non précisée", "sales_only": "Transaction uniquement",
    "unknown": "Inconnu", "": "Inconnu",
}
KPI = [
    {"title": "Adéquation métier", "points": 30, "why": "La société gère-t-elle réellement des immeubles ?", "how": "WEG / résidentiel : 30 · mixte : 25 · gestion générale : 20 · commercial : 10 · vente seule : 0"},
    {"title": "Portefeuille géré", "points": 25, "why": "Nombre d'unités administrées, indicateur de potentiel commercial.", "how": "> 1 000 : 25 · 501–1 000 : 19 · 101–500 : 13 · 1–100 : 5 · non publié : inconnu"},
    {"title": "Présence à Berlin", "points": 15, "why": "Un prospect pertinent doit gérer des biens dans le marché visé.", "how": "Site ou revue web : 15 · adresse d'annuaire seulement : 7–15 · non démontré : 0–15"},
    {"title": "Comptage et charges", "points": 20, "why": "Décomptes de chauffage, charges et suivi des consommations sont des signaux de besoin.", "how": "Preuve de comptage : 20 · mention de décompte de charges : 12–20 · inconnu : 0–20"},
    {"title": "Contactabilité", "points": 10, "why": "Facilité à joindre l'entreprise pour la prospection B2B.", "how": "Email nominatif professionnel : 8–10 · email générique : 5–10 · téléphone : 3–10 · inconnu : 0–10"},
]

st.set_page_config(page_title="Berlin Property Lead Intelligence | Heidi Systems", page_icon="🏙️", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
/* Berlin Property Lead Intelligence — light editorial theme */
:root {
  color-scheme: light;
  --bpli-ink: #142E55;
  --bpli-secondary: #435C7A;
  --bpli-border: #DCE5EF;
  --bpli-paper: #FFFFFF;
  --bpli-page: #F5F8FF;
  --bpli-accent: #1768C8;
}
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
  font-family: "Times New Roman", Times, serif !important;
  color: var(--bpli-ink) !important;
}
.stApp, [data-testid="stAppViewContainer"] {
  background: radial-gradient(ellipse 860px 410px at 92% 4%, #EAF3FA 0%, transparent 70%), var(--bpli-page) !important;
  color: var(--bpli-ink) !important;
}
/* Native Streamlit text and widgets */
.stApp p, .stApp label, .stApp input, .stApp textarea, .stApp button,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5,
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label,
[data-testid="stSidebar"] button, [data-testid="stSidebar"] input,
[data-testid="stMetricLabel"], [data-testid="stMetricValue"],
[data-testid="stMarkdownContainer"] {
  font-family: "Times New Roman", Times, serif !important;
}
.stApp h1, .stApp h2, .stApp h3, .stApp h4,
[data-testid="stMarkdownContainer"] strong {color: #142E55;}
.stApp p, .stApp label {color: #2E4359;}
.stApp small, [data-testid="stCaptionContainer"] {color: #516B88 !important;}
.block-container {padding-top: 1.6rem; padding-bottom: 4rem; max-width: 1500px;}
/* Sidebar: readable contrast in all navigation and input states */
[data-testid="stSidebar"] {
  background: #FFFFFF !important;
  border-right: 1px solid #D5E1ED !important;
  box-shadow: 3px 0 24px rgba(30,64,103,.035);
}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {padding-top: 1.05rem;}
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] {
  color: #253B52 !important;
  opacity: 1 !important;
}
[data-testid="stSidebarNav"]::before {
  content: "BERLIN LEAD INTELLIGENCE";
  display: block;
  margin: 0 14px 7px;
  font-family: "Times New Roman", Times, serif;
  font-size: 18px;
  line-height: 1.22;
  letter-spacing: .35px;
  font-weight: 700;
  color: #153C70;
}
[data-testid="stSidebarNav"]::after {
  content: "HEIDI SYSTEMS  ·  CASE STUDY";
  display: block;
  margin: 12px 14px 17px;
  font-family: "Times New Roman", Times, serif;
  font-size: 11px;
  letter-spacing: 1.15px;
  font-weight: 700;
  color: #647991;
}
[data-testid="stSidebarNav"] a, [data-testid="stSidebarNav"] button {
  color: #233B55 !important;
  font-family: "Times New Roman", Times, serif !important;
  font-size: 16px !important;
  font-weight: 600;
  border-radius: 10px !important;
  opacity: 1 !important;
}
[data-testid="stSidebarNav"] a:hover, [data-testid="stSidebarNav"] button:hover {
  background: #E9F3FF !important;
  color: #1353A3 !important;
}
[data-testid="stSidebarNav"] a[aria-current="page"],
[data-testid="stSidebarNav"] a[aria-selected="true"],
[data-testid="stSidebarNav"] a[data-active="true"] {
  background: #E4F0FF !important;
  color: #1353A3 !important;
  font-weight: 700 !important;
  border-left: 3px solid #1768C8;
}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
  background: #F7FAFD !important;
  border: 1px dashed #ADC4D7 !important;
  border-radius: 12px;
}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] * {color:#304760 !important;}
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-baseweb="input"] > div {
  background: #FFFFFF !important;
  color: #20384F !important;
  border: 1px solid #C8D8E7 !important;
}
[data-testid="stSidebar"] hr {border-color: #DCE6EF !important;}
/* Editorial header and readable statistics */
.hero {
  padding: 29px 33px 28px;
  border: 1px solid #C8DBEA;
  border-radius: 18px;
  background: linear-gradient(120deg, #FFFFFF 0%, #F1F7FF 52%, #E0EDFF 100%);
  box-shadow: 0 7px 26px rgba(37,76,117,.06);
  margin: 0 0 24px;
}
.eyebrow {font-size:12px; letter-spacing:1.7px; color:#1768C8; text-transform:uppercase; font-weight:700;}
.hero h1 {font-size:clamp(30px,3.3vw,43px); font-weight:700; color:#153C70; line-height:1.15; margin:12px 0 12px;}
.hero p {color:#49627A; font-size:16px; line-height:1.55; max-width:880px; margin-bottom:0;}
.stat {
  background:#FFFFFF;
  border:1px solid #D8E3ED;
  padding:18px 20px 17px;
  border-radius:14px;
  min-height:130px;
  box-shadow: 0 4px 14px rgba(28,64,101,.04);
}
.stat .label {font-size:14px; color:#496078; letter-spacing:.1px; font-weight:600;}
.stat .number {font-size:35px; font-weight:700; color:#183C70; line-height:1.45;}
.stat .note {font-size:12px; color:#657B92; line-height:1.45;}
.section-eyebrow {font-size:12px; color:#135CB5; font-weight:700; letter-spacing:1.5px; margin:16px 0 8px;}
.inline-panel {background:#FFFFFF; border:1px solid #D8E3ED; padding:17px 21px; border-radius:13px; margin:11px 0;}
.inline-panel p {color:#405971; font-size:15px; line-height:1.52; margin:8px 0;}
.kpi-card {background:#FFFFFF; border:1px solid #D8E3ED; padding:18px; border-radius:13px; margin-bottom:12px; min-height:148px;}
.kpi-card h4 {margin:0 0 8px; font-size:19px; color:#143862;}
.kpi-card p {font-size:14px; line-height:1.55; color:#4B627A; margin:5px 0;}
.kpi-card .score {font-weight:700; font-size:21px; color:#1768C8; float:right;}
.small-muted {font-size:13px; color:#546B81; margin:8px 0 21px;}
[data-testid="stMetric"] {background:#FFFFFF; border:1px solid #D8E3ED; border-radius:13px; padding:16px;}
[data-testid="stMetricValue"] {color:#183C70 !important;}
[data-testid="stMetricLabel"] {color:#435C7A !important;}
[data-testid="stDataFrame"] {background:#FFFFFF; border:1px solid #D9E4EF; border-radius:12px; overflow:hidden;}
[data-testid="stForm"], [data-testid="stVerticalBlockBorderWrapper"] {border-color:#D9E4EF;}
/* Buttons, menus and form controls */
[data-testid="stBaseButton-primary"] {
  background-color:#1768C8 !important; border-color:#1768C8 !important; color:#FFFFFF !important;
}
[data-testid="stBaseButton-primary"]:hover {background-color:#0F4FA6 !important;}
[data-testid="stBaseButton-primary"] p,
[data-testid="stBaseButton-primary"] span {color:#FFFFFF !important;}
[data-testid="stDownloadButton"] button {border-radius:10px; font-weight:700; min-height:44px;}
[data-testid="stDownloadButton"] button[kind="primary"] {background:#1768C8 !important; color:#FFFFFF !important; border-color:#1768C8 !important;}
[data-testid="stDownloadButton"] button[kind="primary"] p {color:#FFFFFF !important;}
[data-testid="stFileUploader"] {margin-bottom:.45rem;}
.export-panel {background:#FFFFFF; border:1px solid #C9DBF4; border-radius:14px; padding:12px 17px; margin:11px 0 13px;}
.export-panel strong {color:#154785; font-size:17px;}
.export-panel p {color:#4E6581; margin:4px 0 0; font-size:14px;}
[data-baseweb="select"] div, [data-baseweb="input"] input {color:#23394F;}
/* Retain Streamlit icon glyph fonts; do not override Material Symbols. */
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def read_local(path: str, last_mtime: int) -> pd.DataFrame:
    return pd.read_csv(path, sep=";", encoding="utf-8-sig", keep_default_na=False, dtype=str)


def load_data() -> tuple[pd.DataFrame, bool, str]:
    st.sidebar.markdown("**Importer un tableau déjà qualifié**")
    uploaded = st.sidebar.file_uploader(
        "CSV préparé par pipeline.py (facultatif)",
        type=["csv"],
        help="Le CSV remplace temporairement le tableau affiché. Le scraping, Groq et pipeline.py ne sont PAS lancés.",
    )
    st.sidebar.caption("Aucune analyse n'est déclenchée : import = visualisation uniquement. Pour recalculer les scores, exécuter `python pipeline.py` dans le terminal.")
    safe_mode = os.environ.get("PUBLIC_MODE", "false").lower() == "true"
    if uploaded is not None:
        try:
            imported = pd.read_csv(uploaded, sep=";", encoding="utf-8-sig", keep_default_na=False, dtype=str)
            required = {"company_name", "website", "classification", "priority", "score_min", "score_max"}
            missing = required.difference(imported.columns)
            if missing:
                st.sidebar.error("CSV non qualifié : champs absents — " + ", ".join(sorted(missing)) + ". Lance d'abord `python pipeline.py`.")
            else:
                st.sidebar.success(f"CSV importé : {len(imported)} fiches affichées. Aucun pipeline exécuté.")
                return canonicalize(imported), True, "CSV importé (lecture seule)"
        except Exception as exc:
            st.sidebar.error(f"Impossible de lire le CSV : {exc}")
    # Local development sees the newest processed results; a cloud deployment
    # containing only the curated public CSV automatically uses that safe copy.
    path = LOCAL if LOCAL.exists() and not safe_mode else PUBLIC
    if not path.exists() and LOCAL.exists():
        path = LOCAL
    if not path.exists():
        st.error("Aucune donnée trouvée. Lance d'abord `python pipeline.py` ou crée `data/public/leads_public.csv`.")
        st.stop()
    # For automatic deployment, force safe mode whenever the curated public dataset is used.
    safe_mode = safe_mode or path == PUBLIC
    return canonicalize(read_local(str(path), path.stat().st_mtime_ns)), safe_mode, "Publication contrôlée" if path == PUBLIC else "Données locales"


def canonicalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    cols = ["company_name", "website", "domain", "address", "email", "phone", "management_type", "units_managed",
            "units_scope", "metering_signal", "berlin_signal", "score_min", "score_max", "priority", "classification",
            "data_quality", "completeness_pct", "scrape_status", "ai_validation", "review_status", "validation_status",
            "source_types", "source_url", "validation_sources", "validation_notes", "classification_reason", "contact_person"]
    for col in cols:
        if col not in df:
            df[col] = ""
    for col in ["score_min", "score_max", "units_managed", "completeness_pct"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["classification", "priority", "review_status", "management_type"]:
        df[col] = df[col].fillna("").astype(str)
    return df


def metric_card(title: str, value: int | str, info: str):
    # Title/info are authored constants; value is a computed numeric aggregate.
    st.markdown(f'<div class="stat"><div class="label">{html.escape(title)}</div><div class="number">{html.escape(str(value))}</div><div class="note">{html.escape(info)}</div></div>', unsafe_allow_html=True)


def hero(kicker: str, heading: str, desc: str):
    st.markdown(f'<div class="hero"><div class="eyebrow">{html.escape(kicker)}</div><h1>{html.escape(heading)}</h1><p>{html.escape(desc)}</p></div>', unsafe_allow_html=True)


def plot_style(fig, height=310):
    fig.update_layout(
        template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Times New Roman, Times, serif", color="#243C56", size=14), height=height,
        margin=dict(l=16, r=15, t=20, b=20), legend=dict(orientation="h", y=-.15, x=0),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, color="#516A83")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(74,107,145,.16)", zeroline=False, color="#516A83")
    return fig


def counts_bar(series: pd.Series, color_lookup: dict[str, str]):
    table = series.rename_axis("Statut").reset_index(name="Nombre")
    table = table.sort_values("Nombre", ascending=True)
    fig = go.Figure(go.Bar(
        x=table["Nombre"], y=table["Statut"], orientation="h",
        marker_color=[color_lookup.get(str(c), BLUE) for c in table["Statut"]],
        text=table["Nombre"], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: %{x}<extra></extra>",
    ))
    fig.update_layout(showlegend=False)
    return plot_style(fig, 320)


def value_count(series: pd.Series, names: dict):
    return series.fillna("").astype(str).map(lambda x: names.get(x, x or "Non renseigné")).value_counts()


def overview():
    hero("HEIDI SYSTEMS · B2B MARKET INTELLIGENCE", "Berlin Property Lead Intelligence",
         "De la recherche automatisée au classement des gestionnaires immobiliers : couverture, fiabilité, adéquation commerciale et pistes de prospection — avec traçabilité des sources.")
    total = len(df)
    probable = int((df.classification == "LIKELY").sum())
    reviewed = int(df.review_status.str.startswith("WEB_REVIEWED").sum())
    scraped = int((df.scrape_status == "OK").sum())
    cols = st.columns(4, gap="medium")
    for c, content in zip(cols, [
        ("Candidats consolidés", total, "Après fusion et déduplication"),
        ("Prospects probables", probable, "Qualification automatique ou revue web"),
        ("Sites effectivement visités", scraped, "Navigation Stagehand / Chromium"),
        ("Fiches revues sur le Web", reviewed, "Revue documentée, réserves possibles"),
    ]):
        with c:
            metric_card(*content)
    st.markdown('<div class="export-panel"><strong>Exporter les résultats de la recherche</strong><p>Télécharge un CSV compatible Excel (UTF-8, séparateur ;). Les coordonnées individuelles sont exclues de ces exports.</p></div>', unsafe_allow_html=True)
    export_all, export_likely = st.columns([1, 1], gap="medium")
    with export_all:
        st.download_button(
            "📥 Télécharger tous les résultats (CSV)",
            data=prepare_csv(df), file_name="berlin_tous_les_candidats.csv",
            mime="text/csv", type="primary", use_container_width=True,
            key="overview_export_all",
        )
    with export_likely:
        likely = df[df.classification == "LIKELY"].copy()
        st.download_button(
            f"📥 Télécharger les {len(likely)} prospects probables (CSV)",
            data=prepare_csv(likely), file_name="berlin_prospects_probables.csv",
            mime="text/csv", use_container_width=True,
            key="overview_export_likely",
        )
    st.markdown('<div class="section-eyebrow">PORTFOLIO SNAPSHOT</div>', unsafe_allow_html=True)
    left, right = st.columns([1.03, .97], gap="large")
    with left:
        st.subheader("Répartition des candidats")
        breakdown = value_count(df.classification, CLASS_FR)
        fig = go.Figure(go.Pie(labels=breakdown.index.tolist(), values=breakdown.values.tolist(),
                               hole=.67, marker=dict(colors=[{"Prospect probable":TEAL, "À vérifier":AMBER, "Hors cible":ROSE}.get(n,BLUE) for n in breakdown.index]),
                               textinfo="label+percent", textposition="outside"))
        fig = plot_style(fig, 315)
        fig.update_layout(showlegend=False, annotations=[dict(text=f"<b>{total}</b><br>fiches", x=.5,y=.5,showarrow=False, font=dict(size=21))])
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader("Priorités commerciales")
        st.plotly_chart(counts_bar(value_count(df.priority, PRIORITY_FR),
                                  {"Haute": TEAL, "Moyenne": BLUE, "À enrichir": SLATE, "Vérifier l'entreprise": AMBER, "Exclu": ROSE}), use_container_width=True)

    st.subheader("Couverture et maturité des données")
    a,b,c,d = st.columns(4)
    a.metric("Taux de scraping", f"{scraped / total:.1%}" if total else "0%")
    b.metric("Preuves IA retrouvées", int((df.ai_validation == "EVIDENCE_CHECKED").sum()))
    c.metric("Portefeuilles chiffrés", int(df.units_managed.notna().sum()))
    d.metric("À revoir", int((df.classification == "REVIEW").sum()))
    st.markdown("<div class='small-muted'>Une preuve Groq retrouvée n'est pas une vérification humaine. Une adresse berlinoise ne prouve pas à elle seule la gestion de biens à Berlin.</div>", unsafe_allow_html=True)

    st.subheader("Prospects à examiner en priorité")
    top = df[(df.classification == "LIKELY")].sort_values(["score_min", "score_max"], ascending=False).head(12)
    show = top[["company_name", "management_type", "score_min", "score_max", "priority", "review_status", "website"]].copy()
    show["management_type"] = show.management_type.map(lambda x: TYPE_FR.get(x, x))
    st.dataframe(show, use_container_width=True, hide_index=True, height=370, column_config={
        "company_name": "Entreprise", "management_type": "Type de gestion", "score_min": st.column_config.NumberColumn("Score minimum", format="%d / 100"),
        "score_max": st.column_config.NumberColumn("Potentiel max.", format="%d / 100"),
        "priority": "Priorité", "review_status": "Revue web", "website": st.column_config.LinkColumn("Site officiel")
    })


def methodology():
    hero("TRANSPARENT LEAD QUALIFICATION", "KPIs & méthodologie",
         "Comment chaque société est découverte, nettoyée, classée et notée — avec des règles explicites et des inconnues traitées comme de l'incertitude, pas comme des zéros.")
    st.subheader("Les cinq étapes du pipeline")
    steps = [
        ("01", "Discovery", "SearXNG, annuaires VDIV et recherche Stagehand pour découvrir les sociétés candidates."),
        ("02", "Scraping", "Chromium ouvre les pages autorisées : accueil, contact, services, à propos et mentions légales."),
        ("03", "Enrichissement", "Groq extrait des catégories et des chiffres uniquement lorsqu'un extrait justificatif est retrouvé."),
        ("04", "Consolidation", "Python corrige les titres génériques, fusionne les domaines, exclut annuaires et sites hors cible."),
        ("05", "Qualification", "Un scoring de 0 à 100 et un niveau de confiance distinct servent à prioriser la vérification."),
    ]
    for no, name, desc in steps:
        st.markdown(f'<div class="inline-panel"><span class="eyebrow">{no} / {html.escape(name)}</span><p>{html.escape(desc)}</p></div>', unsafe_allow_html=True)

    st.subheader("Modèle de scoring · 100 points")
    chart = go.Figure(go.Bar(x=[x["points"] for x in KPI], y=[x["title"] for x in KPI], orientation="h",
                             marker_color=[TEAL, BLUE, "#80ACE8", AMBER, SLATE],
                             text=[f'{x["points"]} pts' for x in KPI], textposition="inside"))
    chart.update_layout(yaxis=dict(autorange="reversed"), showlegend=False)
    st.plotly_chart(plot_style(chart, 340), use_container_width=True)
    c1,c2 = st.columns(2, gap="medium")
    for i, k in enumerate(KPI):
        with (c1 if i%2==0 else c2):
            st.markdown(f'<div class="kpi-card"><span class="score">{k["points"]} pts</span><h4>{html.escape(k["title"])}</h4><p>{html.escape(k["why"])}</p><p><strong>Règle : </strong>{html.escape(k["how"])}</p></div>', unsafe_allow_html=True)

    st.subheader("Comment lire le score ?")
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        st.markdown("**Score minimum (`score_min`)** : points attribués selon les informations présentes dans les sources, parfois encore à vérifier.")
        st.markdown("**Score maximum (`score_max`)** : score que la société pourrait obtenir si les données manquantes étaient favorables.")
        st.info("Exemple : **65–90 / 100** indique 65 points soutenus par les données et 25 points encore incertains, pas une note définitive de 90.")
    with c2:
        st.markdown("**Priorité commerciale**, uniquement pour les sociétés classées `LIKELY` :")
        st.markdown("- **HIGH** : score minimum ≥ 75\n- **MEDIUM** : score minimum de 45 à 74\n- **RESEARCH_MORE** : score minimum inférieur à 45")
        st.warning("`REVIEW` signifie « Vérifier l'entreprise » quel que soit son score, et `EXCLUDED` est hors cible.")

    st.subheader("Simulateur pédagogique du scoring")
    with st.container(border=True):
        aa,bb,cc = st.columns(3)
        with aa:
            sim_type = st.selectbox("Activité", ["residential", "mixed", "commercial", "unknown"], format_func=lambda v: TYPE_FR.get(v, v))
            sim_units = st.selectbox("Portefeuille", ["unknown", "small", "medium", "large"], format_func=lambda v: {"unknown":"Non publié", "small":"50 unités", "medium":"350 unités", "large":"2 000 unités"}[v])
        with bb:
            sim_berlin = st.selectbox("Présence Berlin", ["WEB_REVIEW_BERLIN", "DIRECTORY_ADDRESS", "UNKNOWN"], format_func=lambda v: {"WEB_REVIEW_BERLIN":"Confirmée", "DIRECTORY_ADDRESS":"Adresse annuaire uniquement", "UNKNOWN":"Inconnue"}[v])
            sim_meter = st.selectbox("Services", ["CONFIRMED_TEXT", "BILLING_TEXT", "UNKNOWN"], format_func=lambda v: {"CONFIRMED_TEXT":"Comptage confirmé", "BILLING_TEXT":"Décomptes/charges", "UNKNOWN":"Non documenté"}[v])
        with cc:
            sim_contact = st.selectbox("Contact", ["named", "generic", "phone", "none"], format_func=lambda v: {"named":"Email professionnel nominatif", "generic":"Email générique", "phone":"Téléphone seulement", "none":"Non disponible"}[v])
        fake = {
            "management_type": sim_type, "units_managed": {"unknown":None,"small":50,"medium":350,"large":2000}[sim_units],
            "units_scope": "SIMULATION" if sim_units!="unknown" else "NOT_VERIFIED", "berlin_signal":sim_berlin,
            "metering_signal":sim_meter, "email":"prenom@example.com" if sim_contact=="named" else "info@example.com" if sim_contact=="generic" else "",
            "phone":"+49 30 000000" if sim_contact=="phone" else "",
        }
        lo,hi,factors = compute_score_from_fields(fake)
        st.metric("Score estimé pour cet exemple", f"{lo}–{hi} / 100" if lo!=hi else f"{lo} / 100")
        st.progress(lo/100)
        st.caption("Exemple fictif : les catégories et les points sont modifiables par les sélecteurs.")

    st.subheader("Limites et garanties")
    st.markdown("""
    - **Aucune donnée absente n'est inventée :** les champs inconnus restent vides.
    - **Les unités sont accompagnées de leur périmètre :** Allemagne, Berlin + environs, ou non documenté. Nous ne confondons pas bâtiments et logements.
    - **Une preuve IA n'est pas une confirmation humaine :** `EVIDENCE_CHECKED` valide uniquement la présence d'une citation dans le texte collecté.
    - **La classification est distincte du score :** une société hors cible n'est jamais promue uniquement grâce à sa taille.
    - **Les 10 premières revues web** portent un statut spécifique et peuvent inclure des réserves sur le registre juridique ou la portée géographique.
    """)


def prepare_csv(table: pd.DataFrame, include_contacts: bool = False) -> bytes:
    sensitive = {"email", "phone", "contact_person"}
    if not include_contacts:
        table = table.drop(columns=[x for x in table.columns if x in sensitive], errors="ignore")
    # Remove fields which can contain very long raw text / unrelated content.
    table = table.drop(columns=[x for x in ["page_text"] if x in table.columns], errors="ignore")
    return csv_safe(table).to_csv(index=False, sep=";").encode("utf-8-sig")


def explorer():
    hero("FULL RESEARCH DATABASE", "Explorateur des entreprises",
         "Toutes les fiches consolidées (y compris celles à vérifier et les exclusions), leurs statuts, scores et URLs sources. Filtre puis exporte la sélection en CSV.")
    a,b,c,d = st.columns([1.5,1,1,1], gap="medium")
    with a: search = st.text_input("Rechercher", placeholder="Nom, domaine, localisation...")
    with b: class_filter = st.multiselect("Classification", sorted(df.classification.unique()), default=list(sorted(df.classification.unique())), format_func=lambda x:CLASS_FR.get(x,x))
    with c: pri_filter = st.multiselect("Priorité", sorted(df.priority.unique()), default=list(sorted(df.priority.unique())), format_func=lambda x:PRIORITY_FR.get(x,x))
    with d: reviewed_only = st.checkbox("Revue web uniquement", value=False)
    col_e,col_f,col_g = st.columns([1.3,1.1,1.2])
    with col_e: types = st.multiselect("Type de gestion", sorted(df.management_type.unique()), default=list(sorted(df.management_type.unique())), format_func=lambda x:TYPE_FR.get(x,x))
    with col_f: minimum = st.slider("Score minimum", 0, 100, 0, step=5)
    with col_g: order = st.selectbox("Trier par", ["Score minimum décroissant", "Score maximum décroissant", "Entreprise A–Z", "Qualité (revues d'abord)"])
    view = df[df.classification.isin(class_filter) & df.priority.isin(pri_filter) & df.management_type.isin(types) & (df.score_min.fillna(0)>=minimum)].copy()
    if reviewed_only:
        view = view[view.review_status.str.startswith("WEB_REVIEWED")]
    if search.strip():
        term = search.casefold().strip()
        mask = (view.company_name.astype(str) + " " + view.domain.astype(str) + " " + view.address.astype(str)).str.casefold().str.contains(term,regex=False)
        view = view[mask]
    if order == "Score minimum décroissant": view = view.sort_values(["score_min", "score_max"], ascending=False)
    elif order == "Score maximum décroissant": view = view.sort_values("score_max",ascending=False)
    elif order == "Entreprise A–Z": view = view.sort_values("company_name")
    else: view = view.assign(_review=view.review_status.str.startswith("WEB_REVIEWED")).sort_values(["_review","score_min"],ascending=False).drop(columns="_review")

    st.caption(f"**{len(view):,} fiches** sélectionnées sur {len(df):,} · Filtres appliqués immédiatement · L'ensemble des candidats est disponible en sélectionnant tous les statuts".replace(",", " "))
    exp_selection, exp_complete = st.columns(2, gap="medium")
    with exp_selection:
        st.download_button(
            f"📥 Télécharger la sélection filtrée — {len(view)} fiches (CSV)",
            data=prepare_csv(view), file_name="berlin_selection_filtree.csv", mime="text/csv",
            type="primary", use_container_width=True, key="explorer_export_filtered",
        )
    with exp_complete:
        st.download_button(
            f"📥 Télécharger la base complète — {len(df)} fiches (CSV)",
            data=prepare_csv(df), file_name="berlin_resultats_complets.csv", mime="text/csv",
            use_container_width=True, key="explorer_export_all",
        )
    table_cols = ["company_name", "website", "management_type", "units_managed", "units_scope", "score_min", "score_max", "priority", "classification", "review_status", "source_url"]
    table = view[table_cols].copy()
    table["management_type"] = table.management_type.map(lambda x: TYPE_FR.get(x,x))
    table["classification"] = table.classification.map(lambda x: CLASS_FR.get(x,x))
    table["priority"] = table.priority.map(lambda x: PRIORITY_FR.get(x,x))
    table["source_url"] = table.source_url.str.split(" | ", regex=False).str[0]
    st.dataframe(table, use_container_width=True, hide_index=True, height=570, column_config={
        "company_name":st.column_config.TextColumn("Entreprise",width="large"),
        "website":st.column_config.LinkColumn("Site officiel",width="medium"),
        "management_type":st.column_config.TextColumn("Gestion",width="medium"),
        "units_managed":st.column_config.NumberColumn("Unités gérées*",format="%.0f"),
        "units_scope":st.column_config.TextColumn("Périmètre",width="medium"),
        "score_min":st.column_config.NumberColumn("Min.",format="%d"),
        "score_max":st.column_config.NumberColumn("Max.",format="%d"),
        "priority":"Priorité", "classification":"Qualification", "review_status":"Vérification",
        "source_url":st.column_config.LinkColumn("Source")
    })
    st.caption("* Les unités sont déclarées avec leur périmètre; des chiffres nationaux ne représentent pas nécessairement les logements berlinois.")

    if not public_mode:
        with st.expander("Export interne avec coordonnées professionnelles (usage privé)", expanded=False):
            st.caption("Conserver ce fichier en interne : il peut contenir des emails professionnels directs. Ne pas le publier sur GitHub.")
            st.download_button(
                "📥 Export interne avec coordonnées (CSV)",
                data=prepare_csv(view, include_contacts=True), file_name="berlin_export_interne.csv",
                mime="text/csv", use_container_width=True, key="explorer_internal_export",
            )
    else:
        st.caption("Export public : les emails et contacts individuels ne sont pas inclus.")

    st.subheader("Fiche entreprise détaillée")
    if view.empty:
        st.info("Aucune entreprise pour ces filtres.")
        return
    options = list(view.index)
    selected = st.selectbox("Sélectionner une entreprise", options, format_func=lambda idx: f"{view.loc[idx, 'company_name']} · {view.loc[idx, 'domain']}")
    r = view.loc[selected]
    w1,w2 = st.columns([1.2,.8], gap="large")
    with w1:
        st.markdown(f"### {r['company_name']}")
        st.write(f"**Activité :** {TYPE_FR.get(r['management_type'], r['management_type'])}")
        st.write(f"**Classement :** {CLASS_FR.get(r['classification'],r['classification'])} · {PRIORITY_FR.get(r['priority'],r['priority'])}")
        st.write(f"**Justification :** {r.get('classification_reason','') or 'Non documentée'}")
        st.write(f"**Périmètre d'unités :** {r.get('units_scope','') or 'Non publié'}")
        st.write(f"**État de la revue web :** {r.get('review_status','') or 'Non vérifié'}")
        if str(r.get("validation_notes", "")).strip():
            st.warning(str(r["validation_notes"]))
    with w2:
        st.metric("Score minimum calculé", f"{int(r['score_min']) if pd.notna(r['score_min']) else 0} / 100")
        st.metric("Score maximum possible", f"{int(r['score_max']) if pd.notna(r['score_max']) else 100} / 100")
        official = str(r["website"])
        if official.startswith(("https://", "http://")):
            st.link_button("Ouvrir le site de l'entreprise", official, use_container_width=True)
        sources = str(r.get("validation_sources", "") or r.get("source_url", "")).split(" | ")
        urls = [v for v in sources if v.startswith(("https://", "http://"))]
        if urls:
            st.link_button("Consulter la source justificative", urls[0], use_container_width=True)


def quality():
    hero("DATA PROVENANCE & VALIDATION", "Qualité des données",
         "Une vue transparente sur les données manquantes, les pages réellement visitées, les vérifications web et les résultats qui exigent encore un contrôle humain.")
    total = len(df)
    checked = int((df.ai_validation=="EVIDENCE_CHECKED").sum())
    reviewed = int(df.review_status.str.startswith("WEB_REVIEWED").sum())
    excluded = int((df.classification=="EXCLUDED").sum())
    cc = st.columns(4)
    for c, metric in zip(cc, [
        ("Preuves Groq retrouvées",checked,"Références de texte, pas validation humaine"),
        ("Fiches revues sur le Web",reviewed,"Certaines avec réserves explicites"),
        ("Sites exclus",excluded,"Annuaires, articles ou sites hors cible"),
        ("En attente de revue",total-reviewed,"Au moins une vérification nécessaire")
    ]):
        with c: metric_card(*metric)
    l,r = st.columns(2, gap="large")
    with l:
        st.subheader("Qualité et provenance")
        counts = df.data_quality.fillna("").replace("", "NON_RÉPERTORIÉ").value_counts()
        st.plotly_chart(counts_bar(counts, {"HIGH":TEAL,"MEDIUM":BLUE,"LOW":SLATE,"WEB_REVIEWED":TEAL,"WEB_REVIEWED_WITH_RESERVATIONS":AMBER}), use_container_width=True)
    with r:
        st.subheader("État des analyses IA")
        counts = df.ai_validation.fillna("").replace("", "NON_ANALYSÉ").value_counts()
        st.plotly_chart(counts_bar(counts, {"EVIDENCE_CHECKED":TEAL,"NEEDS_REVIEW":AMBER,"NOT_ANALYZED":SLATE,"FAILED":ROSE}), use_container_width=True)

    st.subheader("Couverture des informations essentielles")
    cols = [
        ("Nom", df.company_name.astype(str).str.strip().ne("").sum()),
        ("Site", df.website.astype(str).str.startswith("http").sum()),
        ("Email professionnel", df.email.astype(str).str.contains("@", regex=False).sum()),
        ("Périmètre chiffré", df.units_managed.notna().sum()),
        ("Source", df.source_url.astype(str).str.strip().ne("").sum()),
    ]
    chart = go.Figure(go.Bar(
        x=[n for n,_ in cols], y=[int(v)/total*100 if total else 0 for _,v in cols],
        marker_color=[TEAL, BLUE, AMBER, "#7599CD", SLATE],
        text=[f"{int(v)}/{total}" for _,v in cols], textposition="outside"
    ))
    chart.update_yaxes(range=[0,112], ticksuffix="%")
    st.plotly_chart(plot_style(chart, 300), use_container_width=True)

    st.subheader("Anomalies nécessitant une action")
    flags = df[(df.classification=="REVIEW") | (df.review_status=="WEB_REVIEWED_WITH_RESERVATIONS")].copy()
    st.dataframe(flags[["company_name","domain","classification_reason","review_status","validation_notes","website"]].head(120),
                 use_container_width=True, hide_index=True, height=420,
                 column_config={"website":st.column_config.LinkColumn("Site")})
    st.caption("Les lignes à vérifier restent dans la base pour éviter les exclusions erronées. Les revues web documentent les sources mais ne remplacent pas un contrôle légal approfondi.")


df, public_mode, source_label = load_data()
with st.sidebar:
    st.markdown("**Export rapide**")
    st.download_button(
        "📥 Télécharger les résultats CSV",
        data=prepare_csv(df), file_name="berlin_leads_resultats.csv",
        mime="text/csv", type="primary", use_container_width=True,
        key="sidebar_export_all",
    )
    st.caption("Téléchargement uniquement : aucune modification des données.")
    st.divider()
    st.markdown('<div class="section-eyebrow">RESEARCH WORKSPACE</div>', unsafe_allow_html=True)
    st.caption("Navigation · Données consolidées · KPIs")
    st.divider()
    st.caption(f"Source : {source_label}")
    st.caption(f"Base : {len(df):,} candidats".replace(",", " "))
    st.markdown("---")
    st.caption("**Source des résultats** : Stagehand / SearXNG + annuaires + Groq + revues web. Les scores sont indicatifs.")

navigation = st.navigation([
    st.Page(overview, title="Vue d'ensemble", icon="📊", default=True),
    st.Page(methodology, title="Méthodologie & KPIs", icon="🎯"),
    st.Page(explorer, title="Entreprises & Export", icon="🏢"),
    st.Page(quality, title="Qualité & Validation", icon="🔎"),
], position="sidebar")
navigation.run()
