from pathlib import Path

import pandas as pd
from utils import save_as_csv


# Only the parent folder goes here; the client-specific subfolder is created automatically from GROUP_NAME below.
PARENT_SAVE_PATH = 'C:/Users/lenovo/OneDrive/Documents/CGT Files/Team E/'
FILE_PREFIX = 'hub_hbi_rcdsales_anthem'

MATCH_FIELD = 'L09058'
GROUP_ID = '4064345'
GROUP_NAME = 'RCD SALES'

# Division and plan lists come from an Excel file instead of being typed in here.
# Expected workbook layout:
#   'Divisions' sheet: division_id | division_name | employee_status
#   'Plans' sheet:     plan_id | plan_description | plan_type
DIVISION_PLAN_CONFIG_PATH = Path(__file__).parent / 'division_plan_config.xlsx'

HAS_SAME_PLAN_DIVISION_ID = True

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
    divisions_df = pd.read_excel(config_path, sheet_name='Divisions')
    plans_df = pd.read_excel(config_path, sheet_name='Plans')
    return divisions_df, plans_df


def build_plan_crosswalk(group_id, group_name, plans_df):
    plan_ids = plans_df['plan_id'].tolist()
    return pd.DataFrame({
        'Key': [f"{group_id}-{plan_id}" for plan_id in plan_ids],
        'Group ID': group_id,
        'Group Name': group_name,
        'Plan ID': plan_ids,
        'Plan Description': plans_df['plan_description'].tolist(),
        'Plan Type': plans_df['plan_type'].tolist(),
    })


def build_division_crosswalk(group_id, group_name, divisions_df):
    division_ids = divisions_df['division_id'].tolist()
    division_crosswalk = pd.DataFrame({
        'Key': [f"{group_id}-{division_id}" for division_id in division_ids],
        'Group ID': group_id,
        'Group Name': group_name,
        'Division ID': division_ids,
        'Division Name': divisions_df['division_name'].tolist(),
        'Division Type': 'Unspecified',
    })
    division_crosswalk.drop_duplicates(inplace=True)
    return division_crosswalk


def build_employee_status_crosswalk(group_id, group_name, divisions_df, plan_crosswalk, division_crosswalk,
                                     has_same_plan_division_id, employee_type_map):
    df_plan = pd.DataFrame({'plan_id': plan_crosswalk['Plan ID'].tolist()})
    df_division = pd.DataFrame({
        'division_id': divisions_df['division_id'].tolist(),
        'employee_status': divisions_df['employee_status'].tolist(),
    })

    # When divisions and plans share the same ID space, pair each division with the plan
    # of matching ID; otherwise fall back to a full cross join (every division x every plan).
    if has_same_plan_division_id:
        df_plan['Key'] = plan_crosswalk['Plan ID']
        df_division['Key'] = division_crosswalk['Division ID']
    else:
        df_plan['Key'] = 1
        df_division['Key'] = 1

    employee_status_crosswalk = pd.merge(df_division, df_plan, on='Key')
    employee_status_crosswalk['group_id'] = group_id
    employee_status_crosswalk['group_name'] = group_name
    employee_status_crosswalk['Key'] = (
        group_id + '-' + employee_status_crosswalk['division_id'] + '-' + employee_status_crosswalk['plan_id']
    )
    employee_status_crosswalk['employee_type'] = employee_status_crosswalk['employee_status'].map(employee_type_map)

    employee_status_crosswalk = employee_status_crosswalk[
        ['Key', 'group_id', 'group_name', 'division_id', 'plan_id', 'employee_status', 'employee_type']
    ]
    employee_status_crosswalk.drop_duplicates(inplace=True)
    return employee_status_crosswalk


def build_loa_crosswalk(employee_status_crosswalk, plan_crosswalk, division_crosswalk, match_field,
                         reserved_field_9, start_date, end_date, carrier, loa_columns):
    loa_crosswalk = pd.DataFrame({
        'reserved_field_6': employee_status_crosswalk['Key'],
        'employee_status_code': employee_status_crosswalk['employee_status'],
        'reserved_field_2': employee_status_crosswalk['employee_type'],
    })

    loa_crosswalk[['ins_emp_group_id', 'division_id', 'plan_id']] = (
        loa_crosswalk['reserved_field_6'].str.split('-', expand=True)
    )
    loa_crosswalk['reserved_field_4'] = loa_crosswalk['ins_emp_group_id'] + '-' + loa_crosswalk['plan_id']
    loa_crosswalk['reserved_field_5'] = loa_crosswalk['ins_emp_group_id'] + '-' + loa_crosswalk['division_id']
    loa_crosswalk['match_field'] = match_field + '`' + loa_crosswalk['division_id'] + '`' + loa_crosswalk['plan_id']
    loa_crosswalk.drop(['division_id', 'plan_id'], axis=1, inplace=True)

    plan_info = plan_crosswalk[['Key', 'Plan Description', 'Plan Type']]
    division_info = division_crosswalk[['Key', 'Group Name', 'Division Name']]

    loa_crosswalk = pd.merge(
        loa_crosswalk, plan_info, left_on=['reserved_field_4'], right_on=['Key'], how='left'
    ).drop(['Key'], axis=1)
    loa_crosswalk = pd.merge(
        loa_crosswalk, division_info, left_on=['reserved_field_5'], right_on=['Key'], how='left'
    ).drop(['Key'], axis=1)

    loa_crosswalk.rename(columns={
        'Group Name': 'ins_emp_group_name',
        'Plan Description': 'ins_plan_desc',
        'Plan Type': 'ins_plan_type_desc',
        'Division Name': 'ins_division_name',
    }, inplace=True)

    loa_crosswalk['reserved_field_9'] = reserved_field_9
    loa_crosswalk['ins_division_id'] = loa_crosswalk['ins_division_name']
    loa_crosswalk['ins_plan_type_code'] = loa_crosswalk['ins_plan_type_desc']
    loa_crosswalk['ins_plan_id'] = loa_crosswalk['ins_plan_desc']
    loa_crosswalk['employee_status_desc'] = loa_crosswalk['employee_status_code']
    loa_crosswalk['reserved_field_3'] = loa_crosswalk['reserved_field_2']
    loa_crosswalk['start_date'] = start_date
    loa_crosswalk['end_date'] = end_date
    loa_crosswalk['dw_file_type'] = 'Account Structure'
    loa_crosswalk['ins_carrier_id'] = carrier
    loa_crosswalk['ins_carrier_name'] = carrier

    dummy_loa = pd.DataFrame(columns=loa_columns)
    loa_crosswalk = pd.concat([dummy_loa, loa_crosswalk])
    loa_crosswalk.drop_duplicates(inplace=True)
    return loa_crosswalk


def main():
    save_path = f'{PARENT_SAVE_PATH}{GROUP_NAME}/'
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
        plan_crosswalk=plan_crosswalk,
        division_crosswalk=division_crosswalk,
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
