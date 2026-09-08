from pathlib import Path

import pandas as pd
from utils import save_as_csv

# --- First Priority, Inc. ---
# Only the parent folder goes here; the client-specific subfolder is created automatically
# from GROUP_NAME below.
PARENT_SAVE_PATH = 'C:/Users/lenovo/OneDrive/Documents/CGT Files/Team E/'
OUTPUT_FILENAME = 'hub_hbi_rcdsales_anthem_grouplevel_crosswalk.csv'
GROUP_NAME = "RCD SALES"
SRC_GROUP_IDENTIFIER = 'L09058'
INPUT_FILE_PATH = Path(__file__).parent / 'hub_hub_smart_sheet_crosswalk.csv'

ID_COLUMNS = ['Benefit Point ID', 'Client Name', 'HUB Super Region', 'HUB Region', 'HUB Local', 'SIC Sub Industry']
VENDOR_COLUMNS = ['Medical Vendor', 'Eligibility Vendor', 'RX Vendor']

COLUMN_RENAMES = {
    'Benefit Point ID': 'ins_emp_group_id',
    'Client Name': 'ins_emp_group_name',
    'HUB Super Region': 'hub_super_region',
    'HUB Region': 'hub_region',
    'HUB Local': 'hub_local_region',
    'SIC Sub Industry': 'sic_industry_code',
    'Vendor': 'filler4',
    'Vendor Name': 'filler3',
}

OUTPUT_COLUMNS = [
    'src_group_identifier', 'ins_emp_group_id', 'ins_emp_group_name',
    'hub_super_region', 'hub_region', 'hub_local_region',
    'sic_industry_code', 'filler1', 'filler2', 'filler3', 'filler4',
]


def load_source_data(input_file_path):
    return pd.read_csv(input_file_path, delimiter=',', engine='python', on_bad_lines='warn')


def filter_client_data(src_data, group_name):
    return src_data[src_data['Client Name'].str.upper() == group_name.upper()].drop_duplicates()


def build_group_data(client_data, src_group_identifier):
    group_data = pd.melt(
        client_data,
        id_vars=ID_COLUMNS,
        value_vars=VENDOR_COLUMNS,
        var_name='Vendor',
        value_name='Vendor Name',
    ).rename(columns=COLUMN_RENAMES)

    group_data['ins_emp_group_name'] = group_data['ins_emp_group_name'].str.upper()
    group_data['ins_emp_group_id'] = group_data['ins_emp_group_id'].astype(int)
    group_data['filler4'] = group_data['filler4'].str.replace(' Vendor', '')

    group_data['src_group_identifier'] = src_group_identifier
    group_data['filler1'] = ''
    group_data['filler2'] = ''

    return group_data[OUTPUT_COLUMNS]


def main():
    save_path = f"{PARENT_SAVE_PATH}{GROUP_NAME}/"
    src_data = load_source_data(INPUT_FILE_PATH)
    client_data = filter_client_data(src_data, GROUP_NAME)
    group_data = build_group_data(client_data, SRC_GROUP_IDENTIFIER)
    save_as_csv(group_data, save_path, filename=OUTPUT_FILENAME, delimiter=';')


if __name__ == "__main__":
    main()
