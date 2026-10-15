"""Functions shared by the ALN crosswalk creator scripts."""
import pandas as pd
from openpyxl.styles import Font


def load_division_plan_config(config_path):
    sheets = pd.read_excel(
        config_path, sheet_name=['Divisions', 'Plans', 'Updated Standard Values'],
        dtype=str, keep_default_na=False, na_values=[''],
    )
    divisions_df = sheets['Divisions'].dropna(how='all')
    plans_df = sheets['Plans'].dropna(how='all')
    updated_standard_values = sheets['Updated Standard Values']
    return divisions_df, plans_df, updated_standard_values


def style_table(worksheet):
    # Bold header row, hide Excel's gridlines, and size each column to its longest value.
    for cell in worksheet[1]:
        cell.font = Font(bold=True)
    worksheet.sheet_view.showGridLines = False
    for column in worksheet.columns:
        longest = max(len(str(cell.value)) for cell in column if cell.value is not None)
        worksheet.column_dimensions[column[0].column_letter].width = longest + 2
