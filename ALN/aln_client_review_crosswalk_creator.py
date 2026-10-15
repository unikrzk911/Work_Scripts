from pathlib import Path

import pandas as pd

from aln_utils import load_division_plan_config, style_table


SAVE_PATH = Path(__file__).parent / 'Generated Crosswalks'
ALLIANT_CLIENT = 'ALN_CIG'
FILE_PREFIX = ALLIANT_CLIENT.lower()

GROUP_ID = '123456'
GROUP_NAME = 'Test Group'

# Expected workbook layout:
#   'Divisions' sheet: division_id | division_name | employee_status
#   'Plans' sheet:     plan_id | plan_description | plan_type
#   'Updated Standard Values' sheet: copy standard values sheet
DIVISION_PLAN_CONFIG_PATH = Path(__file__).parent / 'division_plan_config.xlsx'

# True: pair each division with the plan of the same ID. False: every division x every plan.
HAS_SAME_PLAN_DIVISION_ID = False

# Same value for every division row.
LOCATION = 'San Francisco, CA'

EMPLOYEE_TYPE_MAP = {
    'Active': 'Full Time',
    'Post-65 Retiree': 'Full Time',
    'Pre-65 Retiree': 'Full Time',
    'Retiree': 'Full Time',
    'COBRA': 'COBRA',
    'Unspecified': 'Unspecified',
}


def build_plan_crosswalk(group_id, group_name, plans_df):
    return pd.DataFrame({
        'Group ID': group_id,
        'Group Name': group_name,
        'Plan ID': plans_df['plan_id'],
        'Plan Description': plans_df['plan_description'],
        'Plan Type': plans_df['plan_type'],
    })


def build_division_crosswalk(group_id, group_name, divisions_df):
    return pd.DataFrame({
        'Group ID': group_id,
        'Group Name': group_name,
        'Division ID': divisions_df['division_id'],
        'DivisionName': divisions_df['division_name'],
    }).drop_duplicates()


def build_employee_status_crosswalk(group_id, group_name, divisions_df, plans_df,
                                    has_same_plan_division_id, employee_type_map):
    df_plan = pd.DataFrame({'plan_id': plans_df['plan_id']})
    df_division = divisions_df[['division_id', 'employee_status']]

    # When divisions and plans share the same ID space, pair each division with the plan
    # of matching ID; otherwise fall back to a full cross join (every division x every plan).
    if has_same_plan_division_id:
        rows = pd.merge(df_division, df_plan, left_on='division_id', right_on='plan_id')
    else:
        rows = pd.merge(df_division, df_plan, how='cross')

    return pd.DataFrame({
        'GroupID': group_id,
        'GroupName': group_name,
        'DivisionID': rows['division_id'],
        'PlanID': rows['plan_id'],
        'EmployeeStatus': rows['employee_status'],
        'EmployeeType': rows['employee_status'].map(employee_type_map),
    }).drop_duplicates()


def build_location_crosswalk(group_id, group_name, divisions_df):
    return pd.DataFrame({
        'Group ID': group_id,
        'Group Name': group_name,
        'Division ID': divisions_df['division_id'],
        'Location': LOCATION,
    }).drop_duplicates()


def main():
    SAVE_PATH.mkdir(exist_ok=True)
    save_file = SAVE_PATH / f'{FILE_PREFIX}_{GROUP_NAME}_client_review_crosswalk.xlsx'

    divisions_df, plans_df, standard_values_df = load_division_plan_config(DIVISION_PLAN_CONFIG_PATH)

    plan_crosswalk = build_plan_crosswalk(GROUP_ID, GROUP_NAME, plans_df)
    division_crosswalk = build_division_crosswalk(GROUP_ID, GROUP_NAME, divisions_df)
    employee_status_crosswalk = build_employee_status_crosswalk(
        GROUP_ID, GROUP_NAME, divisions_df, plans_df, HAS_SAME_PLAN_DIVISION_ID, EMPLOYEE_TYPE_MAP
    )
    location_crosswalk = build_location_crosswalk(GROUP_ID, GROUP_NAME, divisions_df)

    with pd.ExcelWriter(save_file) as writer:
        plan_crosswalk.to_excel(writer, sheet_name='plan cw', index=False)
        division_crosswalk.to_excel(writer, sheet_name='division cw', index=False)
        employee_status_crosswalk.to_excel(writer, sheet_name='employee_status cw', index=False)
        location_crosswalk.to_excel(writer, sheet_name='location cw', index=False)
        standard_values_df.to_excel(writer, sheet_name='Updated Standard Values', index=False)
        for worksheet in writer.sheets.values():
            style_table(worksheet)
    print(f'Saved {save_file}')


if __name__ == "__main__":
    main()
