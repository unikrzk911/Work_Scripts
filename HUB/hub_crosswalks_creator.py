from pathlib import Path

import pandas as pd
from utils import save_as_csv


# Files go to 'Generated Crosswalks/<GROUP_NAME>/' next to this script; both folders are created if missing.
SAVE_PATH = Path(__file__).parent / 'Generated Crosswalks'
FILE_PREFIX = 'hub_hbi_NeyraIndustries_anthem'

MATCH_FIELD = 'L13933'
GROUP_ID = '4629908'
GROUP_NAME = 'NEYRA INDUSTRIES'

# Division and plan lists come from an Excel file instead of being typed in here.
# Expected workbook layout:
#   'Divisions' sheet: division_id | division_name | employee_status
#   'Plans' sheet:     plan_id | plan_description | plan_type
DIVISION_PLAN_CONFIG_PATH = Path(__file__).parent / 'division_plan_config.xlsx'

HAS_SAME_PLAN_DIVISION_ID = False

START_DATE = '2015-01-01'
END_DATE = '2026-12-31'
CARRIER = 'Anthem'
RESERVED_FIELD_9 = 'ACCT_NBR`SUBGRP_NBR'

EMPLOYEE_TYPE_MAP = {
    'Active': 'Full Time',
    'Post-65 Retiree': 'Full Time',
    'Pre-65 Retiree': 'Full Time',
    'Retiree': 'Full Time',
    'Cobra': 'COBRA',
    'Unspecified': 'Unspecified',
}

LOA_COLUMNS = [
    'match_field', 'start_date', 'end_date', 'dw_record_id', 'dw_file_type', 'ins_carrier_id',
    'ins_carrier_name', 'ins_emp_group_id', 'ins_emp_group_name', 'ins_division_id', 'ins_division_name',
    'ins_plan_type_code', 'ins_plan_type_desc', 'ins_plan_id', 'ins_plan_desc', 'ins_plan_class',
    'ins_coverage_type_code', 'ins_coverage_type_desc', 'ins_coverage_class', 'employee_status_code',
    'employee_status_desc', 'division_type_code', 'division_type_desc', 'reserved_field_1',
    'reserved_field_2', 'reserved_field_3', 'reserved_field_4', 'reserved_field_5', 'reserved_field_6',
    'reserved_field_7', 'reserved_field_8', 'reserved_field_9', 'reserved_field_10', 'reserved_field_11',
    'reserved_field_12', 'reserved_field_13', 'reserved_field_14', 'reserved_field_15', 'reserved_field_16',
    'reserved_field_17', 'reserved_field_18', 'reserved_field_19', 'reserved_field_20',
    'destination_field_1', 'destination_field_2', 'destination_field_3', 'destination_field_4',
    'destination_field_5', 'destination_field_6', 'destination_field_7', 'destination_field_8',
    'destination_field_9', 'destination_field_10', 'destination_field_11', 'destination_field_12',
    'destination_field_13', 'destination_field_14', 'destination_field_15', 'destination_field_16',
    'destination_field_17', 'destination_field_18', 'destination_field_19', 'destination_field_20',
]


def load_division_plan_config(config_path):
    sheets = pd.read_excel(
        config_path, sheet_name=['Divisions', 'Plans'],
        dtype=str, keep_default_na=False, na_values=[''],
    )
    divisions_df = sheets['Divisions'].dropna(how='all').reset_index(drop=True)
    plans_df = sheets['Plans'].dropna(how='all').reset_index(drop=True)
    return divisions_df, plans_df


def build_plan_crosswalk(group_id, group_name, plans_df):
    return pd.DataFrame({
        'Key': group_id + '-' + plans_df['plan_id'],
        'Group ID': group_id,
        'Group Name': group_name,
        'Plan ID': plans_df['plan_id'],
        'Plan Description': plans_df['plan_description'],
        'Plan Type': plans_df['plan_type'],
    })


def build_division_crosswalk(group_id, group_name, divisions_df):
    return pd.DataFrame({
        'Key': group_id + '-' + divisions_df['division_id'],
        'Group ID': group_id,
        'Group Name': group_name,
        'Division ID': divisions_df['division_id'],
        'Division Name': divisions_df['division_name'],
        'Division Type': 'Unspecified',
    }).drop_duplicates()


def build_employee_status_crosswalk(group_id, group_name, divisions_df, plans_df,
                                    has_same_plan_division_id, employee_type_map):
    df_plan = plans_df[['plan_id']]
    df_division = divisions_df[['division_id', 'employee_status']]

    # When divisions and plans share the same ID space, pair each division with the plan
    # of matching ID; otherwise fall back to a full cross join (every division x every plan).
    if has_same_plan_division_id:
        df = pd.merge(df_division, df_plan, left_on='division_id', right_on='plan_id')
    else:
        df = pd.merge(df_division, df_plan, how='cross')

    return pd.DataFrame({
        'Key': group_id + '-' + df['division_id'] + '-' + df['plan_id'],
        'group_id': group_id,
        'group_name': group_name,
        'division_id': df['division_id'],
        'plan_id': df['plan_id'],
        'employee_status': df['employee_status'],
        'employee_type': df['employee_status'].map(employee_type_map),
    }).drop_duplicates()


def build_loa_crosswalk(employee_status_crosswalk, plan_crosswalk, division_crosswalk, match_field,
                         reserved_field_9, start_date, end_date, carrier, loa_columns):
    # Look up plan and division details for every employee status row.
    df = employee_status_crosswalk.merge(
        plan_crosswalk[['Plan ID', 'Plan Description', 'Plan Type']], left_on='plan_id', right_on='Plan ID', how='left'
    ).merge(
        division_crosswalk[['Division ID', 'Division Name']], left_on='division_id', right_on='Division ID', how='left'
    )

    loa_crosswalk = pd.DataFrame({
        'match_field': match_field + '`' + df['division_id'] + '`' + df['plan_id'],
        'start_date': start_date,
        'end_date': end_date,
        'dw_file_type': 'Account Structure',
        'ins_carrier_id': carrier,
        'ins_carrier_name': carrier,
        'ins_emp_group_id': df['group_id'],
        'ins_emp_group_name': df['group_name'],
        'ins_division_id': df['Division Name'],
        'ins_division_name': df['Division Name'],
        'ins_plan_type_code': df['Plan Type'],
        'ins_plan_type_desc': df['Plan Type'],
        'ins_plan_id': df['Plan Description'],
        'ins_plan_desc': df['Plan Description'],
        'employee_status_code': df['employee_status'],
        'employee_status_desc': df['employee_status'],
        'reserved_field_2': df['employee_type'],
        'reserved_field_3': df['employee_type'],
        'reserved_field_4': df['group_id'] + '-' + df['plan_id'],
        'reserved_field_5': df['group_id'] + '-' + df['division_id'],
        'reserved_field_6': df['Key'],
        'reserved_field_9': reserved_field_9,
    })
    # Add the remaining LOA columns (left blank) and put everything in file order.
    return loa_crosswalk.reindex(columns=loa_columns).drop_duplicates()


def main():
    save_path = SAVE_PATH / GROUP_NAME
    plan_filename = FILE_PREFIX + '_plancrosswalk_01012026.csv'
    division_filename = FILE_PREFIX + '_divisioncrosswalk_01012026.csv'
    employee_status_filename = FILE_PREFIX + '_employeestatuscrosswalk_01012026.csv'
    loa_filename = FILE_PREFIX + '_loacrosswalk_01012026.csv'

    divisions_df, plans_df = load_division_plan_config(DIVISION_PLAN_CONFIG_PATH)

    plan_crosswalk = build_plan_crosswalk(GROUP_ID, GROUP_NAME, plans_df)
    save_as_csv(plan_crosswalk, save_path, plan_filename, ';')

    division_crosswalk = build_division_crosswalk(GROUP_ID, GROUP_NAME, divisions_df)
    save_as_csv(division_crosswalk, save_path, division_filename, ';')

    employee_status_crosswalk = build_employee_status_crosswalk(
        group_id=GROUP_ID,
        group_name=GROUP_NAME,
        divisions_df=divisions_df,
        plans_df=plans_df,
        has_same_plan_division_id=HAS_SAME_PLAN_DIVISION_ID,
        employee_type_map=EMPLOYEE_TYPE_MAP,
    )
    save_as_csv(employee_status_crosswalk, save_path, employee_status_filename, ';')

    loa_crosswalk = build_loa_crosswalk(
        employee_status_crosswalk=employee_status_crosswalk,
        plan_crosswalk=plan_crosswalk,
        division_crosswalk=division_crosswalk,
        match_field=MATCH_FIELD,
        reserved_field_9=RESERVED_FIELD_9,
        start_date=START_DATE,
        end_date=END_DATE,
        carrier=CARRIER,
        loa_columns=LOA_COLUMNS,
    )
    save_as_csv(loa_crosswalk, save_path, loa_filename, '|')


if __name__ == "__main__":
    main()
