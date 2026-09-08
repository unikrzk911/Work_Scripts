# Work Scripts

A collection of one-off Python utilities for working with Redshift/PostgreSQL databases and building crosswalk/reference files for client data feeds.

## Structure

```
.
├── main.py                    # Sample/entry stub (PyCharm default)
├── utils.py                   # Shared helpers: Redshift query fetch, CSV save, CSV combine
├── execute_on_all_dbs.py      # Runs a .sql script against every DB in a fixed list
├── combine_ctl_files.py       # Concatenates .TXT files in a folder into one combined file
├── requirements.txt
├── .env.example                # Template for required environment variables
└── TeamE/
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

- **`utils.py`** — `get_data(database, query)` fetches a query result from Redshift as a DataFrame; `save_as_csv(...)` writes a DataFrame to disk; `combine_csvs(...)` merges multiple CSVs into one.
- **`execute_on_all_dbs.py`** — loads a SQL file and executes it across a hardcoded list of database names. Update `db_names` and `SQL_FILE_PATH` (env var, optional) for your use case.
- **`combine_ctl_files.py`** — merges all `.TXT` files in a source folder into a single combined file. Edit `input_folder` before running.
- **`TeamE/generate_group_file.py`** — builds a group-level crosswalk CSV for one client from `hub_hub_smart_sheet_crosswalk.csv`. Config block at the top: `parent_save_path` (just the parent folder — the client subfolder is created automatically, named after `group_name`), `cw_name`, `group_name`, `src_group_identifier`. The CSV source has some malformed rows (unescaped commas from a Smartsheet export); the reader uses `engine='python', on_bad_lines='warn'` to skip those rows instead of crashing, printing a warning for each one skipped.
- **`TeamE/hub_crosswalks_creator.py`** — builds plan/division/employee-status/LOA crosswalk CSVs for one client. Config block at the top: `parent_save_path` (same auto-subfolder behavior as above, named after `group_name`), `file_prefix`, `match_field`, `group_id`, `group_name`, `has_same_plan_division_id`, `start_date`/`end_date`, `carrier`, `reserved_field_9`. `division_ids`/`division_names`/`employee_status` and `plan_ids`/`plan_descriptions`/`plan_types` are no longer typed in as lists — they're read from `division_plan_config.xlsx` (next to the script), which needs a `Divisions` sheet (`division_id | division_name | employee_status`) and a `Plans` sheet (`plan_id | plan_description | plan_type`). Swap that file's contents (or the config block) when switching clients.
  - `has_same_plan_division_id` matters here: `True` pairs each division 1:1 with the plan of the same ID (e.g. RCD Sales); `False` cross-joins every division with every plan (e.g. Neyra Industries). Get this wrong and the LOA crosswalk will have the wrong row count.

## Notes

- These scripts contain hardcoded local file paths (e.g. `C:/Users/...`) and per-client configuration that need to be updated before each run — they are not meant to be run as-is on a new machine.
- `TeamE/hub_hub_smart_sheet_crosswalk.csv` and `TeamE/division_plan_config.xlsx` are gitignored (client data) — they need to exist locally (next to the script) for `generate_group_file.py` / `hub_crosswalks_creator.py` to run. Start a new client's `division_plan_config.xlsx` from `TeamE/division_plan_config_template.xlsx` (headers only, tracked in git).
- Database credentials are read from environment variables — see `.env.example`.
