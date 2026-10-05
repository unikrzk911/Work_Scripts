"""
Plain-Python replacement for the deprecated Redshift plpythonu function
public.member_month_generate(...). Returns the same SQL script (config table,
5-year reference table, member-month query and grants) the old UDF returned.

Changes from the old UDF signature: `start` removed (no 'cycleStartDate' config
row); `stage_fields` and `field1` hard-coded below.

Run with no arguments and answer the prompts; the SQL is printed and saved next
to this script.
"""
import os

from import_raw import ask

STAGE_FIELDS = "ins_emp_group_name, dw_vendor_name"
FILTER_FIELD = "ins_emp_group_name"
REF_MONTHS = 60  # months in Ref_table_5year (cycle-end month + 59 before it)


def member_month_generate(cycle_end_date, schema, ins_emp_group_name, dental_exists, vision_exists):
    """
    cycle_end_date  e.g. '2026-08-31'
    schema          target schema, e.g. 'raw_client_202609'
    ins_emp_group_name  full FILTER_FIELD value(s), '|'-separated, e.g. 'ABC Corp|XYZ Inc'
    dental_exists   'TRUE' / 'FALSE'
    vision_exists   'TRUE' / 'FALSE'
    """
    dental_exists, vision_exists = dental_exists.upper(), vision_exists.upper()
    condition = f"{FILTER_FIELD} in ('" + ins_emp_group_name.replace("|", "','") + "')"
    return (
        config_table_sql(schema, cycle_end_date, dental_exists, vision_exists)
        + ref_table_sql(schema)
        + member_months_sql(schema, condition, dental_exists == "TRUE", vision_exists == "TRUE")
        + grants_sql(schema)
    )


def config_table_sql(schema, cycle_end_date, dental_exists, vision_exists):
    return f"""create schema if not exists {schema};
drop table if exists {schema}.perm_stage1_config;

create table {schema}.perm_stage1_config (name varchar(200), value varchar(200));
insert into {schema}.perm_stage1_config values ('cycleEndDate','{cycle_end_date}');
insert into {schema}.perm_stage1_config values ('dentalExists','{dental_exists}');
insert into {schema}.perm_stage1_config values ('visionExists','{vision_exists}');
"""


def ref_table_sql(schema):
    """Cycle-end month and the REF_MONTHS - 1 months before it, via a recursive CTE (replaces the old 60 x UNION)."""
    return f"""
drop table if exists {schema}.Ref_table_5year;
create table {schema}.Ref_table_5year (SN INT IDENTITY(1,1), Ref_Date DATE);
insert into {schema}.Ref_table_5year(Ref_Date)
with recursive months(n, ref_date) as (
  select 0, date_trunc('month', cast(value as date))::date
  from {schema}.perm_stage1_config where name='cycleEndDate'
  union all
  select n + 1, dateadd(month,-1,ref_date)::date from months where n < {REF_MONTHS - 1}
)
select ref_date from months order by 1;
"""


def member_months_sql(schema, condition, include_dental, include_vision):
    where = coverage_sql("med", condition)
    if include_dental:
        where += f"\nOR case when upper(c.value)='TRUE' then {coverage_sql('den', condition)} END"
    if include_vision:
        where += f"\nOR case when upper(d.value)='TRUE' then {coverage_sql('vis', condition)} END"

    fields = STAGE_FIELDS + ","
    return f"""
SELECT distinct {fields}extract(year from Ref_Date) as year,extract(month from Ref_Date) as month,count(distinct dw_member_id) as MM,count(distinct case when mbr_relationship_class='Employee' then dw_member_id end) as subscriber
FROM {schema}.perm_stage_eligibility a
inner join {schema}.Ref_table_5year ref on (1=1)
left join (select value from {schema}.perm_stage1_config where name ='cycleEndDate') b ON (1=1)
left join (select value from {schema}.perm_stage1_config where name ='dentalExists') c ON (1=1)
left join (select value from {schema}.perm_stage1_config where name ='visionExists') d ON (1=1)
WHERE
{where}
group by {fields} year,month
order by {fields} year,month,MM;
"""


def coverage_sql(kind, condition):
    """Member's <kind> (med/den/vis) coverage spans Ref_Date and matches `condition`."""
    eff = f"nullif(nullif(a.ins_{kind}_eff_date,''),'2099-12-31')"
    term = f"coalesce(nullif(nullif(a.ins_{kind}_term_date,''),'2099-12-31'),'2099-12-31')"
    return (
        f"(\n  {eff} < {term}\n"
        f"  and (left({eff},7)||'-'||'01')::date <= cast(ref.Ref_Date as date)\n"
        f"  and {term} >= cast(ref.Ref_Date as date)\n"
        f"  and {condition}\n)"
    )


def grants_sql(schema):
    return f"""
grant all on schema {schema} to group public;
grant select,insert,update,delete on all tables in schema {schema} to group public;
grant all on schema {schema}_external to group public;"""


def interactive():
    print("=== member_month_generate : Redshift member-month script generator ===\n")
    cycle_end_date = ask("Cycle end date (e.g. 2026-08-31)")
    schema = ask("Schema name (e.g. raw_clientname_202609)")
    ins_emp_group_name = ask(f"Name(s) for {FILTER_FIELD} (full names; separate several with |)")
    dental_exists = ask_true_false("Dental data exists?")
    vision_exists = ask_true_false("Vision data exists?")

    sql = member_month_generate(cycle_end_date, schema, ins_emp_group_name, dental_exists, vision_exists)

    print("\n" + "-" * 70 + "\n" + sql + "\n" + "-" * 70)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"member_month_generate_{schema}.sql")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(sql + "\n")
    print("\nSaved to: " + out)


def ask_true_false(question):
    return "TRUE" if ask(question + " Y/N", choices=("Y", "N")).upper() == "Y" else "FALSE"


if __name__ == "__main__":
    try:
        interactive()
        input("\nPress Enter to exit...")
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
