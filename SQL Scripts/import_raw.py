"""Generate the Redshift Spectrum script (external table, view, grants) for a raw file.

Run with no arguments and answer the prompts; the SQL is printed and saved to 'Generated scripts' next to this script.
Field file: optional '#' header line, then one ';'-separated line per field:
  delimited  -> name[;...]
  FIXED      -> name;datatype;length
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # utils.py lives one folder up
from utils import ask, run_interactive, save_sql

NUM_ROWS = "170000"  # 'numRows' table property; a fixed estimate, not the real row count
SPECTRUM_IAM_ROLE = "arn:aws:iam::985867512284:role/rol_data_infra_spectrum01"


def import_raw(date_suffix, schema_name, table_name, delimiter, has_header, location, field_file):
    """
    delimiter  'FIXED' for fixed-length files, else the field delimiter.
               3 characters = <quote><separator><x> (OpenCSVSerde), e.g. '"|"'.
    has_header True adds 'skip.header.line.count'='1'
    table_name '' -> use the field file's name
    """
    table_name = table_name or table_name_from_file(field_file)
    lines = read_field_lines(field_file)
    if not lines:
        raise ValueError(f"No field definitions found in {field_file}")

    if delimiter.upper() == "FIXED":
        table_columns = ["textline VARCHAR(MAX)"]
        view_columns = substring_columns(lines)
    else:
        table_columns = [line.split(";")[0] + " VARCHAR(MAX)" for line in lines]
        view_columns = ["*"]
    view_columns.append('"$path" AS sourcefilename')

    schema = f"{schema_name}_{date_suffix}"
    ext_table = f"{schema}_external.{table_name}"
    skip_header = ", 'skip.header.line.count' = '1'" if has_header else ""
    sql = (
        f"CREATE EXTERNAL TABLE {ext_table} (\n{indented_list(table_columns)}\n)\n"
        + row_format(delimiter)
        + f"LOCATION '{location}'\n"
        f"TABLE PROPERTIES ('numRows' = '{NUM_ROWS}'{skip_header});\n\n"
        f"CREATE OR REPLACE VIEW {schema}.{table_name} AS\n"
        f"SELECT\n{indented_list(view_columns)}\n"
        f"FROM {ext_table}\n"
        "WITH NO SCHEMA BINDING;\n"
    )
    return create_schemas_sql(schema) + "\n" + sql + grants_sql(schema)


def indented_list(items):
    """One item per line, indented, comma-separated."""
    return ",\n".join("    " + item for item in items)


def create_schemas_sql(schema):
    """External schema (and its data-catalog database) plus the Redshift schema for the views."""
    return (
        f"CREATE EXTERNAL SCHEMA IF NOT EXISTS {schema}_external\n"
        "FROM DATA CATALOG\n"
        f"DATABASE '{schema}'\n"
        f"IAM_ROLE '{SPECTRUM_IAM_ROLE}'\n"
        "CREATE EXTERNAL DATABASE IF NOT EXISTS;\n\n"
        f"CREATE SCHEMA IF NOT EXISTS {schema};\n"
    )


def grants_sql(schema):
    """Grants on <schema> and <schema>_external to group public."""
    return f"""
GRANT ALL ON SCHEMA {schema} TO GROUP public;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {schema} TO GROUP public;
GRANT ALL ON SCHEMA {schema}_external TO GROUP public;"""


def read_field_lines(path):
    """Upper-cased, non-blank lines of the field file, without the '#' header."""
    # utf-8-sig so a BOM (Excel "CSV UTF-8" exports) doesn't hide the '#'
    with open(path, encoding="utf-8-sig") as fh:
        lines = [line.strip() for line in fh.read().upper().splitlines()]
    if lines and lines[0].startswith("#"):
        lines = lines[1:]
    return [line for line in lines if line]


def table_name_from_file(path):
    """Table name = field file name (no folder, no extension)."""
    stem = os.path.splitext(os.path.basename(path))[0]
    return re.sub(r"\W+", "_", stem).strip("_")


def substring_columns(lines):
    """Fixed-length 'name;datatype;length' lines -> trim(substring(textline, start, length)) columns."""
    columns, start = [], 1
    for line in lines:
        parts = line.split(";")
        if len(parts) < 3 or not parts[2].strip().isdigit():
            raise ValueError(f"Fixed-length field file needs 'name;datatype;length' on every line, got: {line!r}")
        name, length = parts[0], int(parts[2])
        columns.append(f"TRIM(SUBSTRING(textline, {start}, {length})) AS {name}")
        start += length
    return columns


def row_format(delimiter):
    """ROW FORMAT clause: FIXED = one text line per row; 3 chars = quoted CSV via OpenCSVSerde."""
    if delimiter.upper() == "FIXED":
        return "ROW FORMAT DELIMITED\n    LINES TERMINATED BY '\\n'\nSTORED AS TEXTFILE\n"
    if len(delimiter) == 3:
        quote, separator = delimiter[0], delimiter[1]
        return (
            "ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'\n"
            "WITH SERDEPROPERTIES (\n"
            f"    'separatorChar' = '{separator}',\n"
            f"    'quoteChar' = '{quote}'\n"
            ")\n"
            "STORED AS TEXTFILE\n"
        )
    return (
        "ROW FORMAT DELIMITED\n"
        f"    FIELDS TERMINATED BY '{delimiter}'\n"
        "    LINES TERMINATED BY '\\n'\n"
        "STORED AS TEXTFILE\n"
    )


def interactive():
    print("=== import_raw : Redshift Spectrum script generator ===\n")
    date_suffix = ask("Date suffix (e.g. 202609)")
    schema_name = ask("Schema name (e.g. raw_clientname)")
    delimiter = ask('Delimiter (FIXED for fixed-length; otherwise e.g. |  ,  tab  or 3 chars like "|" for quoted)')
    if delimiter.lower() in ("tab", "\\t"):
        delimiter = "\t"
    has_header = ask("Has header row? Y/N", choices=("Y", "N")).upper() == "Y"
    location = ask("S3 location (e.g. s3://bucket/folder/)")
    field_file = ask_field_file()
    table_name = table_name_from_file(field_file)
    print("  Table name (from file name): " + table_name)

    try:
        sql = import_raw(date_suffix, schema_name, table_name, delimiter, has_header, location, field_file)
    except ValueError as exc:
        print("\nERROR: " + str(exc))
        return

    save_sql(sql, f"{schema_name}_{date_suffix}_{table_name}.sql")


def ask_field_file():
    while True:
        path = input("Field file - paste its path, or press Enter to browse: ").strip().strip("\"'")
        path = path or pick_file_dialog()
        if os.path.isfile(path):
            print("  Selected: " + path)
            return path
        print("  File not found: " + path if path else "  No file selected.")


def pick_file_dialog():
    """File-picker window; '' if cancelled or no display."""
    try:
        import tkinter
        from tkinter import filedialog

        root = tkinter.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askopenfilename(
            title="Select the field-definition file",
            filetypes=[("Field files", "*.csv *.txt"), ("All files", "*.*")],
        )
        root.destroy()
        return path
    except Exception:
        return ""


if __name__ == "__main__":
    run_interactive(interactive)
