from pathlib import Path

import pandas as pd

from aln_utils import load_division_plan_config, style_table


SAVE_PATH = Path(__file__).parent / 'Generated Crosswalks'
ALLIANT_CLIENT = 'ALN_BBS'
FILE_PREFIX = ALLIANT_CLIENT.lower()

GROUP_ID = '123456'
GROUP_NAME = 'Test Group'
REGION = 'South'
OFFICE_CODE = 'HS'
OFFICE_DESCRIPTION = 'Houston'
INDUSTRY = 'Professional Services'

# Expected workbook layout:
#   'Divisions' sheet: division_id | division_name | employee_status
#   'Plans' sheet:     plan_id | plan_description | plan_type
#   'Updated Standard Values' sheet: copy standard values sheet
DIVISION_PLAN_CONFIG_PATH = Path(__file__).parent / 'division_plan_config.xlsx'

# Same value for every division row.
LOCATION = 'N/A'
SALARY_FREQUENCY = 'Bi-Weekly'
PAY_CLASSIFICATION = 'N/A'

# One entry per date period; every plan gets a row for every period.
TIME_PERIODS = [
    {
        'Start Date': '2023-01-01',
        'End Date': '2025-12-31',
        'Stop Loss Vendor': 'BCBSIL',
        'Stop Loss Coalition': 'BUCA',
        'RX Vendor': 'ESI',
        'RX Coalition': 'No',
        'No Financials Flag': 'N/A',
        'Tribal Nontribal': 'Non Tribal',
    },
    {
        'Start Date': '2026-01-01',
        'End Date': '2099-12-31',
        'Stop Loss Vendor': 'BCBSIL',
        'Stop Loss Coalition': 'BUCA',
        'RX Vendor': 'BCBSIL',
        'RX Coalition': 'No',
        'No Financials Flag': 'N/A',
        'Tribal Nontribal': 'Non Tribal',
    },
]

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


def build_division_crosswalk(group_id, group_name, divisions_df, employee_type_map):
    division_crosswalk = pd.DataFrame({
        'Group ID': group_id,
        'Group Name': group_name,
        'DivisionID': divisions_df['division_id'],
        'Division Name': divisions_df['division_name'],
        'Location': LOCATION,
        'EmployeeStatus': divisions_df['employee_status'],
        'EmployeeType': divisions_df['employee_status'].map(employee_type_map),
        'Salary Frequency': SALARY_FREQUENCY,
        'Pay Classification': PAY_CLASSIFICATION,
    })
    return division_crosswalk.drop_duplicates()


def build_time_sensitive_crosswalk(plan_crosswalk, time_periods):
    # Cross join, ordered period by period: all plans for the first period, then all plans for the next.
    periods_df = pd.DataFrame(time_periods)
    time_sensitive_crosswalk = pd.merge(periods_df, plan_crosswalk, how='cross')
    return time_sensitive_crosswalk[list(plan_crosswalk.columns) + list(periods_df.columns)]


def build_group_crosswalk():
    return pd.DataFrame([{
        'Alliant Clients': ALLIANT_CLIENT,
        'Group ID': GROUP_ID,
        'Group Name': GROUP_NAME,
        'Region': REGION,
        'Office Code': OFFICE_CODE,
        'Office Description': OFFICE_DESCRIPTION,
        'Industry': INDUSTRY,
    }])


def main():
    SAVE_PATH.mkdir(exist_ok=True)
    save_file = SAVE_PATH / f'{FILE_PREFIX}_{GROUP_NAME}_client_review_crosswalk.xlsx'

    divisions_df, plans_df, standard_values_df = load_division_plan_config(DIVISION_PLAN_CONFIG_PATH)

    plan_crosswalk = build_plan_crosswalk(GROUP_ID, GROUP_NAME, plans_df)
    division_crosswalk = build_division_crosswalk(GROUP_ID, GROUP_NAME, divisions_df, EMPLOYEE_TYPE_MAP)
    time_sensitive_crosswalk = build_time_sensitive_crosswalk(plan_crosswalk, TIME_PERIODS)

    with pd.ExcelWriter(save_file) as writer:
        plan_crosswalk.to_excel(writer, sheet_name='plan cw', index=False)
        division_crosswalk.to_excel(writer, sheet_name='division_emp_status_location cw', index=False)
        time_sensitive_crosswalk.to_excel(writer, sheet_name='time sensitive cw', index=False)
        build_group_crosswalk().to_excel(writer, sheet_name='group level cw', index=False)
        standard_values_df.to_excel(writer, sheet_name='Updated Standard Values', index=False)
        for worksheet in writer.sheets.values():
            style_table(worksheet)
    print(f'Saved {save_file}')


if __name__ == "__main__":
    main()
