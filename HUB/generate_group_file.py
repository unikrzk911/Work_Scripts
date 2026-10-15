from pathlib import Path

import pandas as pd
from utils import save_as_csv

# Files go to 'Generated Crosswalks/<GROUP_NAME>/' next to this script; both folders are created if missing.
SAVE_PATH = Path(__file__).parent / 'Generated Crosswalks'
OUTPUT_FILENAME = 'hub_hbi_NeyraIndustries_anthem_grouplevel_crosswalk.csv'
GROUP_NAME = "NEYRA INDUSTRIES"
SRC_GROUP_IDENTIFIER = 'L13933'
INPUT_FILE_PATH = Path(__file__).parent / 'hub_hub_smart_sheet_crosswalk.csv'

# Source column -> output column, kept on every row.
ID_COLUMNS = {
    'Benefit Point ID': 'ins_emp_group_id',
    'Client Name': 'ins_emp_group_name',
    'HUB Super Region': 'hub_super_region',
    'HUB Region': 'hub_region',
    'HUB Local': 'hub_local_region',
    'SIC Sub Industry': 'sic_industry_code',
}
# One output row per vendor column: filler4 = vendor type ('Medical', ...), filler3 = vendor name.
VENDOR_COLUMNS = ['Medical Vendor', 'Eligibility Vendor', 'RX Vendor']

OUTPUT_COLUMNS = [
    'src_group_identifier', 'ins_emp_group_id', 'ins_emp_group_name',
    'hub_super_region', 'hub_region', 'hub_local_region',
    'sic_industry_code', 'filler1', 'filler2', 'filler3', 'filler4',
]


def build_group_data(src_data, group_name, src_group_identifier):
    client_data = src_data[src_data['Client Name'].str.upper() == group_name.upper()].drop_duplicates()
    group_data = client_data.melt(
        id_vars=list(ID_COLUMNS), value_vars=VENDOR_COLUMNS, var_name='filler4', value_name='filler3',
    ).rename(columns=ID_COLUMNS)

    return group_data.assign(
        src_group_identifier=src_group_identifier,
        ins_emp_group_id=group_data['ins_emp_group_id'].astype(int),
        ins_emp_group_name=group_data['ins_emp_group_name'].str.upper(),
        filler1='',
        filler2='',
        filler4=group_data['filler4'].str.replace(' Vendor', ''),
    )[OUTPUT_COLUMNS]


def main():
    # The source export has malformed lines; skip them with a warning instead of failing.
    src_data = pd.read_csv(INPUT_FILE_PATH, delimiter=',', engine='python', on_bad_lines='warn')
    group_data = build_group_data(src_data, GROUP_NAME, SRC_GROUP_IDENTIFIER)
    save_as_csv(group_data, SAVE_PATH / GROUP_NAME, filename=OUTPUT_FILENAME, delimiter=';')


if __name__ == "__main__":
    main()
