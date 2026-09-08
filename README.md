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
    ├── generate_group_file.py       # Builds a group-level crosswalk CSV from a source crosswalk
    └── hub_crosswalks_creator.py    # Builds plan/division/employee-status/LOA crosswalk CSVs
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
- **`TeamE/generate_group_file.py`** and **`TeamE/hub_crosswalks_creator.py`** — client-specific crosswalk generators. Each has a hardcoded config block at the top (client name, save path, IDs) that must be edited per client/run before executing.

## Notes

- These scripts contain hardcoded local file paths (e.g. `C:/Users/...`, `/Users/...`) and per-client configuration that need to be updated before each run — they are not meant to be run as-is on a new machine.
- `TeamE/` contains client data files (`Group info.txt`, `HUB_Crosswalk_20251001.xlsx`, `HUB_Crosswalks/`). Review whether these should be tracked in git or excluded (add rules to `.gitignore` if not).
- Database credentials are read from environment variables — see `.env.example`.
