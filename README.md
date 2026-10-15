# Work Scripts

A collection of personal helper scripts I use for office work — running SQL across Redshift databases, generating Redshift setup scripts (Spectrum raw imports, member-month counts), combining exported text files, and generating client crosswalk files (HUB CSVs, ALN Excel review workbook) for data feeds.

## Structure

```
.
├── utils.py                     # Shared helpers: Redshift query fetch, CSV/TXT combine, prompts, SQL save
├── execute_on_all_dbs.py        # Runs a .sql script against every DB in a fixed list
├── requirements.txt
├── .env.example                 # Template for required environment variables
├── SQL Scripts/
│   ├── import_raw.py            # Interactive: generates Spectrum schemas + external table + view + grants SQL for a raw file
│   ├── member_month_generate.py # Interactive: generates member-month count SQL for a client schema
│   └── Generated scripts/       # .sql output of the two generators (created on first run, gitignored)
├── HUB/
│   ├── generate_group_file.py            # Builds a group-level crosswalk CSV from a source crosswalk
│   ├── hub_crosswalks_creator.py         # Builds plan/division/employee-status/LOA crosswalk CSVs
│   ├── hub_hub_smart_sheet_crosswalk.csv # Source data for generate_group_file.py (gitignored, client data)
│   ├── division_plan_config.xlsx         # Division/plan input for hub_crosswalks_creator.py (gitignored, client-specific)
│   ├── division_plan_config_template.xlsx # Headers-only starting point for a new client's config (tracked)
│   └── Generated Crosswalks/<GROUP_NAME>/ # CSV output of hub_crosswalks_creator.py (created on run, gitignored)
└── ALN/
    ├── aln_client_review_timesensitive_crosswalk_creator.py # Builds the client review crosswalk workbook (.xlsx)
    ├── aln_client_review_crosswalk_creator.py               # Builds the client review workbook with separate division/employee status/location tabs
    ├── aln_utils.py                                         # Functions shared by the two ALN scripts (config loader, sheet styling)
    ├── division_plan_config.xlsx                            # Division/plan input + static 'Updated Standard Values' tab (gitignored, client-specific)
    ├── division_plan_config_template.xlsx                   # Headers-only starting point for a new client's config + 'Updated Standard Values' tab (tracked)
    └── Generated Crosswalks/                                # .xlsx output of aln_client_review_timesensitive_crosswalk_creator.py (created on run, gitignored)
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

- **`utils.py`** — shared helpers: `get_data` (Redshift query → DataFrame), `save_as_csv`, `combine_csvs`, `combine_txt_files` (merges every `*.TXT` in a folder into `combined.txt`, with a header per file), plus `ask` / `save_sql` / `run_interactive` for the interactive scripts.
- **`execute_on_all_dbs.py`** — runs a `.sql` file on every database in `DB_NAMES`.
- **`SQL Scripts/import_raw.py`** — prompts for date suffix, schema, delimiter, header row, S3 location and a field file; writes SQL that creates `<schema>_<date>` and `<schema>_<date>_external` (if missing), the external table, the view and the grants. Field file: one `;`-separated line per field — `name` (delimited) or `name;datatype;length` (`FIXED`). A 3-character delimiter like `"|"` means quoted CSV (OpenCSVSerde). Also provides `create_schemas_sql` / `grants_sql`, which `member_month_generate.py` reuses.
- **`SQL Scripts/member_month_generate.py`** — prompts for cycle end date, schema, optional group filter and dental/vision flags; writes SQL counting member months and subscribers over the last 60 months. Only `<schema>.perm_stage_eligibility` is read from the given schema; the config and reference tables go in a separate `<schema>_MM` schema. **The generated SQL drops `<schema>_MM` and `<schema>_MM_external` with `CASCADE` before recreating them**, so anything else saved there is lost on each run.
- **`HUB/generate_group_file.py`** — builds one client's group crosswalk CSV from `hub_hub_smart_sheet_crosswalk.csv`. Set the config block at the top first.
- **`HUB/hub_crosswalks_creator.py`** — builds plan/division/employee-status/LOA crosswalk CSVs from `division_plan_config.xlsx` (`Divisions` and `Plans` sheets). Set the config block first; `HAS_SAME_PLAN_DIVISION_ID` = `True` pairs divisions 1:1 with plans, `False` cross-joins them. Output goes to `HUB/Generated Crosswalks/<GROUP_NAME>/`.
- **`ALN/aln_client_review_timesensitive_crosswalk_creator.py`** — builds one Excel workbook, `ALN/Generated Crosswalks/<alliant_client>_<GROUP_NAME>_client_review_crosswalk.xlsx`, with five tabs: `plan cw` and `division_emp_status_location cw` (from the `Plans` / `Divisions` sheets of `ALN/division_plan_config.xlsx`), `time sensitive cw` (every plan × every entry in `TIME_PERIODS`), `group level cw` (from the group variables), and `Updated Standard Values` (copied as is from the config file). EmployeeType comes from `EMPLOYEE_TYPE_MAP` (a status missing from the map leaves EmployeeType blank). Set the config block at the top first (group/office values, `LOCATION`, `SALARY_FREQUENCY`, `PAY_CLASSIFICATION`, `TIME_PERIODS`). Headers are bold, gridlines hidden, columns sized to their longest value.
- **`ALN/aln_client_review_crosswalk_creator.py`** — same config file, but builds `ALN/Generated Crosswalks/<FILE_PREFIX>_<GROUP_NAME>_client_review_crosswalk.xlsx` with `plan cw`, `division cw`, `employee_status cw`, `location cw` (`LOCATION` for every division) and `Updated Standard Values` — no time sensitive or group level tabs. `employee_status cw` follows `hub_crosswalks_creator.py`: the division's `employee_status` mapped through `EMPLOYEE_TYPE_MAP`; `HAS_SAME_PLAN_DIVISION_ID` = `True` pairs divisions 1:1 with plans of the same ID, `False` cross-joins them.
- **`ALN/aln_utils.py`** — `load_division_plan_config` and `style_table`, used by both ALN scripts. Keep it in `ALN/` next to them.

## Notes

- These scripts contain hardcoded local file paths (e.g. `C:/Users/...`) and per-client configuration that need to be updated before each run — they are not meant to be run as-is on a new machine.
- `HUB/hub_hub_smart_sheet_crosswalk.csv` and `HUB/division_plan_config.xlsx` are gitignored (client data) — they need to exist locally (next to the script) for `generate_group_file.py` / `hub_crosswalks_creator.py` to run. Start a new client's `division_plan_config.xlsx` from `HUB/division_plan_config_template.xlsx` (headers only, tracked in git). Run `hub_crosswalks_creator.py` from the repo root (`python HUB/hub_crosswalks_creator.py`) so `from utils import ...` resolves.
- Both ALN scripts read `ALN/division_plan_config.xlsx` (gitignored, client data) — start it from `ALN/division_plan_config_template.xlsx` and fill in the client's divisions and plans before running. Config cells are read as text (IDs like `0001` keep their zeros, `N/A` stays `N/A`). Close the output workbook in Excel before re-running, or the save fails with `PermissionError`.
- Both `Generated Crosswalks/` folders are gitignored (client data).
- Database credentials are read from environment variables — see `.env.example`.
- The `SQL Scripts/` generators only write SQL (no DB connection). Run them with `python "SQL Scripts/import_raw.py"` from anywhere (or by double-clicking, though the window closes as soon as the file is saved) — each adds the repo root to `sys.path` to find `utils.py`. The SQL is printed and saved to `SQL Scripts/Generated scripts/`, which is created if it doesn't exist and is gitignored. Since `utils.py` imports `pandas`/`redshift_connector`/`dotenv`, the full `requirements.txt` still needs to be installed. The file picker uses `tkinter` (ships with Python).
