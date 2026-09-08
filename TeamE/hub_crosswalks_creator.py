from pathlib import Path
import pandas as pd
from utils import save_as_csv

#################################################### Hansen Fruit######################################################

# Only the parent folder goes here; the client-specific subfolder is created automatically from group_name below.
parent_save_path = 'C:/Users/lenovo/OneDrive/Documents/CGT Files/Team E/'
file_prefix = 'hub_hbi_rcdsales_anthem'

match_field = 'L09058'
group_id = '4064345'
group_name = 'RCD SALES'

# Client-specific subfolder, named after the group, under the given parent folder
save_path = f'{parent_save_path}{group_name}/'

# Division and plan lists come from an Excel file instead of being typed in here.
# Expected workbook layout:
#   'Divisions' sheet: division_id | division_name | employee_status
#   'Plans' sheet:     plan_id | plan_description | plan_type
division_plan_config_path = Path(__file__).parent / 'division_plan_config.xlsx'

divisions_df = pd.read_excel(division_plan_config_path, sheet_name='Divisions')
division_ids = divisions_df['division_id'].tolist()
division_names = divisions_df['division_name'].tolist()
employee_status = divisions_df['employee_status'].tolist()

plans_df = pd.read_excel(division_plan_config_path, sheet_name='Plans')
plan_ids = plans_df['plan_id'].tolist()
plan_descriptions = plans_df['plan_description'].tolist()
plan_types = plans_df['plan_type'].tolist()

has_same_plan_division_id = True

start_date = '2015-01-01'
end_date = '2026-12-31'
carrier = 'Anthem'
reserved_field_9 = 'ACCT_NBR`SUBGRP_NBR'
######################################################################################################################

employee_type = {
    'Active': 'Full Time',
    'Post-65 Retiree': 'Full Time',
    'Pre-65 Retiree': 'Full Time',
    'Retiree': 'Full Time',
    'Cobra': 'COBRA',
    'Unspecified': 'Unspecified'
}

plan_filename = file_prefix + '_plancrosswalk_01012026.csv'
division_filename = file_prefix + '_divisioncrosswalk_01012026.csv'
employee_status_filename = file_prefix + '_employeestatuscrosswalk_01012026.csv'
loa_filename = file_prefix + '_loacrosswalk_01012026.csv'

################################################### Plan Crosswalk ####################################################
plan_crosswalk = pd.DataFrame({
    'Key': [f"{group_id}-{plan_id}" for plan_id in plan_ids],
    'Group ID': group_id,
    'Group Name': group_name,
    'Plan ID': plan_ids,
    'Plan Description': plan_descriptions,
    'Plan Type': plan_types
})
save_as_csv(plan_crosswalk, save_path, plan_filename, ';')
######################################################################################################################

############################################### Division Crosswalk ####################################################
division_crosswalk = pd.DataFrame({
    'Key': [f"{group_id}-{division_id}" for division_id in division_ids],
    'Group ID': group_id,
    'Group Name': group_name,
    'Division ID': division_ids,
    'Division Name': division_names,
    'Division Type': 'Unspecified'
})
division_crosswalk.drop_duplicates(inplace=True)
save_as_csv(division_crosswalk, save_path, division_filename, ';')
######################################################################################################################

############################################### Employee Status Crosswalk #############################################
df_plan = pd.DataFrame({'plan_id': plan_ids})
df_division = pd.DataFrame({
    'division_id': division_ids,
    'employee_status': employee_status
})

# Perform the cross join
if has_same_plan_division_id:
    df_plan['Key'] = plan_crosswalk['Plan ID']
    df_division['Key'] = division_crosswalk['Division ID']
else:
    df_plan['Key'] = 1
    df_division['Key'] = 1

employee_status_crosswalk = pd.merge(df_division, df_plan, on='Key')
employee_status_crosswalk['group_id'] = group_id
employee_status_crosswalk['group_name'] = group_name
employee_status_crosswalk['Key'] = group_id + '-' + employee_status_crosswalk['division_id'] + '-' + \
                                   employee_status_crosswalk['plan_id']
employee_status_crosswalk['employee_type'] = employee_status_crosswalk['employee_status'].map(employee_type)

employee_status_crosswalk = employee_status_crosswalk[
    ['Key', 'group_id', 'group_name', 'division_id', 'plan_id', 'employee_status', 'employee_type']]
employee_status_crosswalk.drop_duplicates(inplace=True)
save_as_csv(employee_status_crosswalk, save_path, employee_status_filename, ';')
######################################################################################################################

#################################################### LOA Crosswalk ###################################################
loa_crosswalk = pd.DataFrame({
    'reserved_field_6': employee_status_crosswalk['Key'],
    'employee_status_code': employee_status_crosswalk['employee_status'],
    'reserved_field_2': employee_status_crosswalk['employee_type'],
})

loa_crosswalk[['ins_emp_group_id', 'division_id', 'plan_id']] = loa_crosswalk['reserved_field_6'].str.split('-', expand=True)
loa_crosswalk['reserved_field_4'] = loa_crosswalk['ins_emp_group_id'] + '-' + loa_crosswalk['plan_id']
loa_crosswalk['reserved_field_5'] = loa_crosswalk['ins_emp_group_id'] + '-' + loa_crosswalk['division_id']
loa_crosswalk['match_field'] = match_field + '`' + loa_crosswalk['division_id'] + '`' + loa_crosswalk['plan_id']
loa_crosswalk.drop(['division_id', 'plan_id'], axis=1, inplace=True)

plan_info = plan_crosswalk[['Key', 'Plan Description', 'Plan Type']]
division_info = division_crosswalk[['Key', 'Group Name', 'Division Name']]

loa_crosswalk = pd.merge(loa_crosswalk, plan_info, left_on=['reserved_field_4'], right_on=['Key'], how='left').drop(
    ['Key'], axis=1)
loa_crosswalk = pd.merge(loa_crosswalk, division_info, left_on=['reserved_field_5'], right_on=['Key'], how='left').drop(
    ['Key'], axis=1)

loa_crosswalk.rename(columns={
    'Group Name': 'ins_emp_group_name',
    'Plan Description': 'ins_plan_desc',
    'Plan Type': 'ins_plan_type_desc',
    'Division Name': 'ins_division_name'
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
# loa_crosswalk['match_field'] = ''


loa_columns = ['match_field', 'start_date', 'end_date', 'dw_record_id', 'dw_file_type', 'ins_carrier_id',
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
               'destination_field_17', 'destination_field_18', 'destination_field_19', 'destination_field_20']
dummy_loa = pd.DataFrame(columns=loa_columns)
loa_crosswalk = pd.concat([dummy_loa, loa_crosswalk])
loa_crosswalk.drop_duplicates(inplace=True)

save_as_csv(loa_crosswalk, save_path, loa_filename, '|')
######################################################################################################################
