from pathlib import Path

import pandas as pd
from utils import save_as_csv


############################### First Priority, Inc. ##############################################
save_path = 'C:/Users/u1218516/Documents/CGT Files/Other teams/'
cw_name = 'hub_hbi_rcdsales_anthem_grouplevel_crosswalk.csv'
group_name = "RCD SALES"
src_group_identifier = 'L09058'
##########################################################################################



# Read data
input_file_path = 'C:/Users/u1218516/Documents/CGT Files/Other teams/HUB/MasterCW/hub_hub_smart_sheet_crosswalk.csv'
src_data = pd.read_csv(input_file_path, delimiter=',', skiprows=0)

# Filter data for the specific client name
client_data = src_data[src_data['Client Name'].str.upper() == group_name.upper()].drop_duplicates()

# Melt columns
melted_data = pd.melt(
    client_data,
    id_vars=['Benefit Point ID', 'Client Name', 'HUB Super Region', 'HUB Region', 'HUB Local', 'SIC Sub Industry'],
    value_vars=['Medical Vendor', 'Eligibility Vendor', 'RX Vendor'],
    var_name='Vendor',
    value_name='Vendor Name'
)

melted_data.rename(columns={
    'Benefit Point ID': 'ins_emp_group_id',
    'Client Name': 'ins_emp_group_name',
    'HUB Super Region': 'hub_super_region',
    'HUB Region': 'hub_region',
    'HUB Local': 'hub_local_region',
    'SIC Sub Industry': 'sic_industry_code',
    'Vendor': 'filler4',
    'Vendor Name': 'filler3'
}, inplace=True)

# Update specific columns
melted_data['ins_emp_group_name'] = melted_data['ins_emp_group_name'].str.upper()
melted_data['ins_emp_group_id'] = melted_data['ins_emp_group_id'].astype(int)
melted_data['filler4'] = melted_data['filler4'].str.replace(' Vendor', '')

# Add filler columns
melted_data['src_group_identifier'] = src_group_identifier
melted_data['filler1'] = ''
melted_data['filler2'] = ''

# Select and reorder columns
final_columns = ['src_group_identifier', 'ins_emp_group_id', 'ins_emp_group_name',
                 'hub_super_region', 'hub_region', 'hub_local_region',
                 'sic_industry_code', 'filler1', 'filler2', 'filler3', 'filler4']

group_data = melted_data[final_columns]

save_as_csv(group_data, save_path, filename=cw_name, delimiter=';')

