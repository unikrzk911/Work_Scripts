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

- **`utils.py`** — `get_data(database, query)` fetches a query result from Redshift as a DataFrame; `save_as_csv(...)` writes a DataFrame to disk; `combine_csvs(...)` merges multiple CSVs into one. Also the shared bits for the interactive SQL generators: `ask(label, choices)` (prompt until a valid answer), `save_sql(sql, filename)` (print + save the SQL next to the script being run), `run_interactive(fn)` (runs a prompt-driven script and keeps the window open when double-clicked).
- **`execute_on_all_dbs.py`** — loads a SQL file and executes it across a hardcoded list of database names. Update `DB_NAMES` and `SQL_FILE_PATH` (env var, optional) for your use case.
- **`SQL Scripts/import_raw.py`** — run with no arguments and answer the prompts (date suffix, schema name, delimiter, header Y/N, S3 location, field file — paste a path or press Enter for a file picker). Generates the `create external table` in `<schema>_<date>_external`, a `create or replace view` in `<schema>_<date>` (adds `"$path" as sourcefilename`), and grants; saves it as `<schema>_<date>_<table>.sql`. The table name comes from the field file's name. Field file: optional `#` header line, then one `;`-separated line per field — `name` for delimited files, `name;datatype;length` for `FIXED` (fixed-length columns become `trim(substring(textline, start, length))`). Delimiter: `FIXED`, a single character (`tab` accepted), or 3 characters `<quote><separator><x>` (e.g. `"|"`) for quoted files via `OpenCSVSerde`. `numRows` is hardcoded to `170000`.
- **`SQL Scripts/member_month_generate.py`** — run with no arguments and answer the prompts (cycle end date, schema, optional `ins_emp_group_name` filter — full names, `|`-separated, Enter for all — and whether dental/vision data exist). Generates SQL that creates `perm_stage1_config`, builds `Ref_table_5year` (the cycle-end month plus the 59 before it, via a recursive CTE), counts member months and subscribers per `ins_emp_group_name, dw_vendor_name`/year/month from `perm_stage_eligibility` (medical, plus dental/vision coverage when flagged), and adds grants. Saved as `member_month_generate_<schema>.sql`.
- **`combine_ctl_files.py`** — `combine_txt_files(input_folder)` concatenates every `*.TXT` file (uppercase extension only) in a folder into `combined.txt` in that same folder, each section prefixed with a `====`/`FILE: name`/`====` header; the output file itself is excluded if the script is re-run. Edit `INPUT_FOLDER` before running.
- **`HUB/generate_group_file.py`** — builds a group-level crosswalk CSV for one client from `hub_hub_smart_sheet_crosswalk.csv`. Config block at the top: `PARENT_SAVE_PATH` (just the parent folder — the client subfolder is created automatically, named after `GROUP_NAME`), `OUTPUT_FILENAME`, `GROUP_NAME`, `SRC_GROUP_IDENTIFIER`. The CSV source has some malformed rows (unescaped commas from a Smartsheet export); the reader uses `engine='python', on_bad_lines='warn'` to skip those rows instead of crashing, printing a warning for each one skipped.
- **`HUB/hub_crosswalks_creator.py`** — builds plan/division/employee-status/LOA crosswalk CSVs for one client. Config block at the top: `PARENT_SAVE_PATH` (same auto-subfolder behavior as above, named after `GROUP_NAME`), `FILE_PREFIX`, `MATCH_FIELD`, `GROUP_ID`, `GROUP_NAME`, `HAS_SAME_PLAN_DIVISION_ID`, `START_DATE`/`END_DATE`, `CARRIER`, `RESERVED_FIELD_9`. Division/plan data is no longer typed in as lists — it's read from `division_plan_config.xlsx` (next to the script), which needs a `Divisions` sheet (`division_id | division_name | employee_status`) and a `Plans` sheet (`plan_id | plan_description | plan_type`). Swap that file's contents (or the config block) when switching clients.
  - `HAS_SAME_PLAN_DIVISION_ID` matters here: `True` pairs each division 1:1 with the plan of the same ID (e.g. RCD Sales); `False` cross-joins every division with every plan (e.g. Neyra Industries). Get this wrong and the LOA crosswalk will have the wrong row count.

## Notes

- These scripts contain hardcoded local file paths (e.g. `C:/Users/...`) and per-client configuration that need to be updated before each run — they are not meant to be run as-is on a new machine.
- `HUB/hub_hub_smart_sheet_crosswalk.csv` and `HUB/division_plan_config.xlsx` are gitignored (client data) — they need to exist locally (next to the script) for `generate_group_file.py` / `hub_crosswalks_creator.py` to run. Start a new client's `division_plan_config.xlsx` from `HUB/division_plan_config_template.xlsx` (headers only, tracked in git).
- Database credentials are read from environment variables — see `.env.example`.
- The `SQL Scripts/` generators only write SQL (no DB connection). Run them by double-clicking or with `python "SQL Scripts/import_raw.py"` from anywhere — each adds the repo root to `sys.path` to find `utils.py`, and the `.sql` output is saved in `SQL Scripts/`. Since `utils.py` imports `pandas`/`redshift_connector`/`dotenv`, the full `requirements.txt` still needs to be installed. The file picker uses `tkinter` (ships with Python).
