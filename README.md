# Work Scripts

A collection of personal helper scripts I use for office work — running SQL across Redshift databases, generating Redshift setup scripts (Spectrum raw imports, member-month counts), combining exported text files, and generating client crosswalk CSVs for data feeds.

## Structure

```
.
├── utils.py                     # Shared helpers: Redshift query fetch, CSV save/combine, prompts, SQL save
├── execute_on_all_dbs.py        # Runs a .sql script against every DB in a fixed list
├── combine_ctl_files.py         # Concatenates .TXT files in a folder into one combined file
├── requirements.txt
├── .env.example                 # Template for required environment variables
├── SQL Scripts/
│   ├── import_raw.py            # Interactive: generates Spectrum external table + view + grants SQL for a raw file
│   └── member_month_generate.py # Interactive: generates member-month count SQL for a client schema
└── HUB/
    ├── generate_group_file.py            # Builds a group-level crosswalk CSV from a source crosswalk
    ├── hub_crosswalks_creator.py         # Builds plan/division/employee-status/LOA crosswalk CSVs
    ├── hub_hub_smart_sheet_crosswalk.csv # Source data for generate_group_file.py (gitignored, client data)
    ├── division_plan_config.xlsx         # Division/plan input for hub_crosswalks_creator.py (gitignored, client-specific)
    └── division_plan_config_template.xlsx # Headers-only starting point for a new client's config (tracked)
```

## Setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate      # Windows
   source .venv/bin/activate   # macOS/Linux
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your Redshift credentials:
   ```bash
   copy .env.example .env       # Windows
   cp .env.example .env         # macOS/Linux
   ```
   `utils.py` and `execute_on_all_dbs.py` load these via `python-dotenv` — never commit the real `.env` file.

## Scripts

- **`utils.py`** — shared helpers: `get_data` (Redshift query → DataFrame), `save_as_csv`, `combine_csvs`, plus `ask` / `save_sql` / `run_interactive` for the interactive scripts.
- **`execute_on_all_dbs.py`** — runs a `.sql` file on every database in `DB_NAMES`.
- **`combine_ctl_files.py`** — merges every `*.TXT` in `INPUT_FOLDER` into `combined.txt`, with a header per file.
- **`SQL Scripts/import_raw.py`** — prompts for schema, delimiter, S3 location and a field file; writes the Spectrum external table, view and grants SQL. Field file: one `;`-separated line per field — `name` (delimited) or `name;datatype;length` (`FIXED`).
- **`SQL Scripts/member_month_generate.py`** — prompts for cycle end date, schema, optional group filter and dental/vision flags; writes SQL counting member months and subscribers over the last 60 months.
- **`HUB/generate_group_file.py`** — builds one client's group crosswalk CSV from `hub_hub_smart_sheet_crosswalk.csv`. Set the config block at the top first.
- **`HUB/hub_crosswalks_creator.py`** — builds plan/division/employee-status/LOA crosswalk CSVs from `division_plan_config.xlsx` (`Divisions` and `Plans` sheets). Set the config block first; `HAS_SAME_PLAN_DIVISION_ID` = `True` pairs divisions 1:1 with plans, `False` cross-joins them.

## Notes

- These scripts contain hardcoded local file paths (e.g. `C:/Users/...`) and per-client configuration that need to be updated before each run — they are not meant to be run as-is on a new machine.
- `HUB/hub_hub_smart_sheet_crosswalk.csv` and `HUB/division_plan_config.xlsx` are gitignored (client data) — they need to exist locally (next to the script) for `generate_group_file.py` / `hub_crosswalks_creator.py` to run. Start a new client's `division_plan_config.xlsx` from `HUB/division_plan_config_template.xlsx` (headers only, tracked in git).
- Database credentials are read from environment variables — see `.env.example`.
- The `SQL Scripts/` generators only write SQL (no DB connection). Run them by double-clicking or with `python "SQL Scripts/import_raw.py"` from anywhere — each adds the repo root to `sys.path` to find `utils.py`, and the `.sql` output is saved in `SQL Scripts/`. Since `utils.py` imports `pandas`/`redshift_connector`/`dotenv`, the full `requirements.txt` still needs to be installed. The file picker uses `tkinter` (ships with Python).
