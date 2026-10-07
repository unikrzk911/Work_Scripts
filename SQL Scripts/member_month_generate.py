import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # utils.py lives one folder up
from utils import ask, run_interactive, save_sql
from import_raw import create_schemas_sql, grants_sql

STAGE_FIELDS = ("ins_emp_group_name", "dw_vendor_name")
FILTER_FIELD = "ins_emp_group_name"
REF_MONTHS = 60


def member_month_generate(cycle_end_date, source_schema, include_dental, include_vision, group_names=""):
    """Reads <source_schema>.perm_stage_eligibility; every table it creates goes in <source_schema>_MM,
    which (with <source_schema>_MM_external) is dropped (cascade) and recreated on each run.
    group_names: '|'-separated FILTER_FIELD values to keep; '' = all."""
    mm_schema = f"{source_schema}_MM"
    group_filter = group_filter_sql(group_names)
    return (
        drop_schemas_sql(mm_schema)
        + create_schemas_sql(mm_schema)
        + config_table_sql(mm_schema, cycle_end_date, include_dental, include_vision)
        + ref_table_sql(mm_schema)
        + member_months_sql(source_schema, mm_schema, group_filter, include_dental, include_vision)
        + grants_sql(mm_schema)
    )


def group_filter_sql(group_names):
    """'A|B' -> "<FILTER_FIELD> IN ('A', 'B')"; '' -> ''."""
    if not group_names:
        return ""
    return f"{FILTER_FIELD} IN ('" + group_names.replace("|", "', '") + "')"


def drop_schemas_sql(schema):
    return f"DROP SCHEMA IF EXISTS {schema} CASCADE;\nDROP SCHEMA IF EXISTS {schema}_external CASCADE;\n\n"


def config_table_sql(schema, cycle_end_date, include_dental, include_vision):
    return f"""
DROP TABLE IF EXISTS {schema}.perm_stage1_config;
CREATE TABLE {schema}.perm_stage1_config (name VARCHAR(200), value VARCHAR(200));
INSERT INTO {schema}.perm_stage1_config VALUES ('cycleEndDate', '{cycle_end_date}');
INSERT INTO {schema}.perm_stage1_config VALUES ('dentalExists', '{str(include_dental).upper()}');
INSERT INTO {schema}.perm_stage1_config VALUES ('visionExists', '{str(include_vision).upper()}');
"""


def ref_table_sql(schema):
    """Cycle-end month and the REF_MONTHS - 1 months before it, via a recursive CTE (replaces the old 60 x UNION)."""
    return f"""
DROP TABLE IF EXISTS {schema}.Ref_table_5year;
CREATE TABLE {schema}.Ref_table_5year (SN INT IDENTITY(1, 1), Ref_Date DATE);
INSERT INTO {schema}.Ref_table_5year (Ref_Date)
WITH RECURSIVE months (n, ref_date) AS (
    SELECT 0, DATE_TRUNC('month', CAST(value AS DATE))::DATE
    FROM {schema}.perm_stage1_config
    WHERE name = 'cycleEndDate'
    UNION ALL
    SELECT n + 1, DATEADD(MONTH, -1, ref_date)::DATE
    FROM months
    WHERE n < {REF_MONTHS - 1}
)
SELECT ref_date FROM months ORDER BY 1;
"""


def member_months_sql(source_schema, schema, group_filter, include_dental, include_vision):
    where = "    " + coverage_sql("med", group_filter)
    if include_dental:
        where += "\n    OR " + coverage_sql("den", group_filter)
    if include_vision:
        where += "\n    OR " + coverage_sql("vis", group_filter)

    select_fields = "".join(f"    {field},\n" for field in STAGE_FIELDS)
    group_fields = ", ".join(STAGE_FIELDS)
    return f"""
SELECT DISTINCT
{select_fields}    EXTRACT(YEAR FROM Ref_Date) AS year,
    EXTRACT(MONTH FROM Ref_Date) AS month,
    COUNT(DISTINCT dw_member_id) AS MM,
    COUNT(DISTINCT CASE WHEN mbr_relationship_class = 'Employee' THEN dw_member_id END) AS subscriber
FROM {source_schema}.perm_stage_eligibility a
INNER JOIN {schema}.Ref_table_5year ref ON 1 = 1
WHERE
{where}
GROUP BY {group_fields}, year, month
ORDER BY {group_fields}, year, month, MM;
"""


def coverage_sql(kind, group_filter):
    """Member's <kind> (med/den/vis) coverage spans Ref_Date, plus `group_filter` ('' = none)."""
    eff = f"NULLIF(NULLIF(a.ins_{kind}_eff_date, ''), '2099-12-31')"
    term = f"COALESCE(NULLIF(NULLIF(a.ins_{kind}_term_date, ''), '2099-12-31'), '2099-12-31')"
    conditions = [
        f"{eff} < {term}",
        f"(LEFT({eff}, 7) || '-01')::DATE <= CAST(ref.Ref_Date AS DATE)",
        f"{term} >= CAST(ref.Ref_Date AS DATE)",
    ]
    if group_filter:
        conditions.append(group_filter)
    return "(\n        " + "\n        AND ".join(conditions) + "\n    )"


def interactive():
    print("=== member_month_generate : Redshift member-month script generator ===\n")
    cycle_end_date = ask("Cycle end date (e.g. 2026-08-31)")
    source_schema = ask("Schema name (e.g. raw_clientname_202609)")
    group_names = input(f"Name(s) for {FILTER_FIELD} (full names; separate several with |; Enter for all): ").strip()
    include_dental = ask_yes_no("Dental data exists?")
    include_vision = ask_yes_no("Vision data exists?")

    sql = member_month_generate(cycle_end_date, source_schema, include_dental, include_vision, group_names)
    save_sql(sql, f"member_month_generate_{source_schema}.sql")


def ask_yes_no(question):
    return ask(question + " Y/N", choices=("Y", "N")).upper() == "Y"


if __name__ == "__main__":
    run_interactive(interactive)
