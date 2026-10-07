import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # utils.py lives one folder up
from utils import ask, run_interactive, save_sql
from import_raw import create_schemas_sql

STAGE_FIELDS = ("ins_emp_group_name", "dw_vendor_name")
FILTER_FIELD = "ins_emp_group_name"
REF_MONTHS = 60


def member_month_generate(cycle_end_date, source_schema, dental_exists, vision_exists, ins_emp_group_name=""):
    """Reads <source_schema>.perm_stage_eligibility; every table it creates goes in <source_schema>_MM,
    which (with <source_schema>_MM_external) is dropped (cascade) and recreated on each run."""
    schema = f"{source_schema}_MM"
    dental_exists, vision_exists = dental_exists.upper(), vision_exists.upper()
    group_filter = ""
    if ins_emp_group_name:
        group_filter = f"{FILTER_FIELD} IN ('" + ins_emp_group_name.replace("|", "', '") + "')"
    return (
        f"DROP SCHEMA IF EXISTS {schema} CASCADE;\n"
        f"DROP SCHEMA IF EXISTS {schema}_external CASCADE;\n\n"
        + create_schemas_sql(schema)
        + config_table_sql(schema, cycle_end_date, dental_exists, vision_exists)
        + ref_table_sql(schema)
        + member_months_sql(source_schema, schema, group_filter, dental_exists == "TRUE", vision_exists == "TRUE")
        + grants_sql(schema)
    )


def grants_sql(schema):
    """Grants on <schema> and <schema>_external to group public."""
    return f"""
GRANT ALL ON SCHEMA {schema} TO GROUP public;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {schema} TO GROUP public;
GRANT ALL ON SCHEMA {schema}_external TO GROUP public;
"""


def config_table_sql(schema, cycle_end_date, dental_exists, vision_exists):
    return f"""
DROP TABLE IF EXISTS {schema}.perm_stage1_config;
CREATE TABLE {schema}.perm_stage1_config (name VARCHAR(200), value VARCHAR(200));
INSERT INTO {schema}.perm_stage1_config VALUES ('cycleEndDate', '{cycle_end_date}');
INSERT INTO {schema}.perm_stage1_config VALUES ('dentalExists', '{dental_exists}');
INSERT INTO {schema}.perm_stage1_config VALUES ('visionExists', '{vision_exists}');
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
        where += f"\n    OR CASE WHEN UPPER(c.value) = 'TRUE' THEN {coverage_sql('den', group_filter)} END"
    if include_vision:
        where += f"\n    OR CASE WHEN UPPER(d.value) = 'TRUE' THEN {coverage_sql('vis', group_filter)} END"

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
LEFT JOIN (SELECT value FROM {schema}.perm_stage1_config WHERE name = 'cycleEndDate') b ON 1 = 1
LEFT JOIN (SELECT value FROM {schema}.perm_stage1_config WHERE name = 'dentalExists') c ON 1 = 1
LEFT JOIN (SELECT value FROM {schema}.perm_stage1_config WHERE name = 'visionExists') d ON 1 = 1
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
    schema = ask("Schema name (e.g. raw_clientname_202609)")
    ins_emp_group_name = input(f"Name(s) for {FILTER_FIELD} (full names; separate several with |; Enter for all): ").strip()
    dental_exists = ask_true_false("Dental data exists?")
    vision_exists = ask_true_false("Vision data exists?")

    sql = member_month_generate(cycle_end_date, schema, dental_exists, vision_exists, ins_emp_group_name)

    save_sql(sql, f"member_month_generate_{schema}.sql")


def ask_true_false(question):
    return "TRUE" if ask(question + " Y/N", choices=("Y", "N")).upper() == "Y" else "FALSE"


if __name__ == "__main__":
    run_interactive(interactive)
