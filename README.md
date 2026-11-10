# Berlin Property Lead Intelligence

**Heidi Systems case study** — bilingual Streamlit dashboard (English / Deutsch), Inter typeface, light blue theme, lead qualification methodology, candidate explorer, quality controls, and CSV/Google Sheets export.

The application is **read-only**. Opening the dashboard never runs Stagehand, Groq, OpenAI, or `pipeline.py`. There is no CSV upload control.

## Files to deploy

```text
app.py
pipeline.py                         # scorer imported by the app; no pipeline run
requirements.txt
.streamlit/config.toml
data/public/leads_public.csv        # public dashboard data, semicolon CSV
data/public/leads_public_google.csv # public Google Sheets CSV, comma separated
publish_public.py                  # regeneration tool; not executed by visitors
```

The public data currently contains **392 research candidates**, not 392 independently verified property managers. It excludes email addresses, telephone numbers, and personal contacts. Verify sources, accuracy, and publication rights before publishing.

## Run locally (Windows, PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Visit `http://localhost:8501` (or the port printed in your terminal).

## Deploy on Streamlit Community Cloud

1. Create a GitHub repository for the **dashboard** (separate from the Node.js scraper), such as `berlin-property-lead-dashboard`.
2. Push the files listed above. **Never push `.env`, private leads, `data/raw/`, `data/processed/`, `data/validation/`, API keys, or personal-contact exports.**
3. Open https://share.streamlit.io, create an app from your GitHub repository, select branch `main` and entry point `app.py`.
4. The dashboard uses `data/public/leads_public.csv` by default. No API key or secrets are required to display it.
5. Test all four pages in **English and German**, the exported CSV, and the Google Sheets section.

## Google Sheets — two supported paths

### A. First-time setup without a Google API key

From the dashboard's **Companies & Export** page:

1. Select **Create a Google Sheet** (opens `https://sheets.new`).
2. Either download the **Google Sheets-compatible CSV** (comma-delimited), then in Google Sheets use **File → Import → Upload**, or use the automatic link in step 3.
3. To link a publicly hosted CSV, make sure `data/public/leads_public_google.csv` exists on your **public GitHub repository**, then set this in Streamlit Cloud app settings → **Secrets**:

   ```toml
   PUBLIC_CSV_URL = "https://raw.githubusercontent.com/YOUR_USER/YOUR_REPO/main/data/public/leads_public_google.csv"
   ```

   After redeploying, the app shows a formula you can copy into cell A1 of a **new, empty** Google Sheet:

   ```gs
   =IMPORTDATA("https://raw.githubusercontent.com/YOUR_USER/YOUR_REPO/main/data/public/leads_public_google.csv")
   ```

   The CSV URL must be publicly reachable. This feature imports **only the public dataset**. Google may cache the imported contents; updates are not necessarily immediate.
4. Name the resulting Sheet and, if sharing with recruiters, configure the appropriate **Share → General access → Anyone with the link → Viewer** permission deliberately.

### B. One-click opening on subsequent visits

Set the URL of your prepared Google Sheet in Streamlit Cloud app settings → **Secrets**:

```toml
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"
```

The dashboard will then show **Open in Google Sheets / In Google Tabellen öffnen**, opening **that existing spreadsheet directly**.

**Not supported without Google OAuth:** silently creating a new spreadsheet inside each visitor's personal Google Drive. The app does not claim to do this. Google Sheets opening is separate from the download action and does not create a new sheet each click.

## Updating the research data

In your **private** analytics project (not on Streamlit Cloud), run:

```powershell
python pipeline.py
python publish_public.py --confirm
```

This generates **both** `leads_public.csv` and `leads_public_google.csv`. Carefully inspect them, then copy the sanitized files to this public dashboard repository and commit/push. Streamlit Cloud will update to the new Git commit. A formula using `IMPORTDATA` will eventually load updated public data when Google refreshes it.

## Privacy and verification

- `PUBLIC_MODE` defaults to `true`. Do not set `PUBLIC_MODE=false` in Streamlit Cloud.
- No individual email addresses or named contacts are included in this public export.
- The Google Sheets link and formula expose the **full public dataset**, not any temporary filtered selection in Streamlit. Download the filtered CSV if you need only the selected rows.
- `EVIDENCE_CHECKED` means text support was found; it is **not** a human verification.
- National portfolio totals must not be described as Berlin-only housing units.
