"""Generate the Redshift Spectrum script (external table, view, grants) for a raw file.

Run with no arguments and answer the prompts; the SQL is printed and saved next to this script.
Field file: optional '#' header line, then one ';'-separated line per field:
  delimited  -> name[;...]
  FIXED      -> name;datatype;length
"""
import os
import re

NUM_ROWS = "170000"  # hard-coded 'numRows' table property, same as the original


def import_raw(date_suffix, schema_name, table_name, delimiter, has_header, location, field_file):
    """
    delimiter  'FIXED' for fixed-length files, else the field delimiter.
               3 characters = <quote><separator><x> (OpenCSVSerde), e.g. '"|"'.
    has_header 'Y' adds 'skip.header.line.count'='1'
    table_name '' -> use the field file's name
    """
    table_name = table_name or table_name_from_file(field_file)
    lines = read_field_lines(field_file)
    if not lines:
        raise ValueError(f"No field definitions found in {field_file}")

    schema = f"{schema_name}_{date_suffix}"
    ext_schema = f"{schema}_external"
    header = ", 'skip.header.line.count'='1'" if has_header.upper() == "Y" else ""
    table_props = f"table properties ('numRows'='{NUM_ROWS}'{header}); \n"
    from_clause = f'"$path" as sourcefilename from {ext_schema}.{table_name} WITH NO SCHEMA BINDING;'

    if delimiter.upper() == "FIXED":
        sql = (
            f"create external table {ext_schema}.{table_name} (\n\ttextline varchar(max))\n"
            "ROW FORMAT DELIMITED LINES TERMINATED BY '\\n' \n"
            "STORED AS TEXTFILE \n"
            f"location '{location}' \n{table_props}\n"
            f"create or replace view {schema}.{table_name} as select \n"
            + ",\n".join(substring_columns(lines)) + "," + from_clause
        )
    else:
        names = [line.split(";")[0] for line in lines]
        sql = (
            f"create external table {ext_schema}.{table_name} (\n"
            + " varchar(max),\n".join(names) + " varchar(max))\n"
            + row_format(delimiter) + f" location '{location}' \n{table_props}"
            f" create or replace view {schema}.{table_name} as select *," + from_clause
        )
    return sql + grants(schema, ext_schema)


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
        columns.append(f"\ttrim(substring(textline,{start},{length})) as {name}")
        start += length
    return columns


def row_format(delimiter):
    """ROW FORMAT clause for a delimited file; 3 chars = quoted CSV via OpenCSVSerde."""
    if len(delimiter) == 3:
        quote, separator = delimiter[0], delimiter[1]
        return (
            "ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'\n"
            "WITH SERDEPROPERTIES (\n"
            f"\t'separatorChar' = '{separator}',\n"
            f"\t'quoteChar' = '{quote}'\n"
            " ) STORED AS TEXTFILE \n"
        )
    return f"ROW FORMAT DELIMITED FIELDS TERMINATED BY '{delimiter}' LINES TERMINATED BY '\\n' \n STORED AS TEXTFILE \n"


def grants(schema, ext_schema):
    return (
        f"\n\ngrant all on schema {schema} to group public;\n"
        f"grant select,insert,update,delete on all tables in schema {schema}  to group public;\n"
        f"grant all on schema {ext_schema}  to group public;"
    )


def interactive():
    print("=== import_raw : Redshift Spectrum script generator ===\n")
    date_suffix = ask("Date suffix (e.g. 202609)")
    schema_name = ask("Schema name (e.g. raw_clientname)")
    delimiter = ask('Delimiter (FIXED for fixed-length; otherwise e.g. |  ,  tab  or 3 chars like "|" for quoted)')
    if delimiter.lower() in ("tab", "\\t"):
        delimiter = "\t"
    has_header = ask("Has header row? Y/N", choices=("Y", "N"))
    location = ask("S3 location (e.g. s3://bucket/folder/)")
    field_file = ask_field_file()
    table_name = table_name_from_file(field_file)
    print("  Table name (from file name): " + table_name)

    try:
        sql = import_raw(date_suffix, schema_name, table_name, delimiter, has_header, location, field_file)
    except ValueError as exc:
        print("\nERROR: " + str(exc))
        return

    print("\n" + "-" * 70 + "\n" + sql + "\n" + "-" * 70)
    # always save next to this script, e.g. cigna_202609_eligibility.sql
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{schema_name}_{date_suffix}_{table_name}.sql")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(sql + "\n")
    print("\nSaved to: " + out)


def ask(label, choices=None):
    """Prompt until a non-empty answer (one of `choices`, if given) is entered."""
    while True:
        answer = input(label + ": ").strip()
        if answer and (not choices or answer.upper() in choices):
            return answer
        print("  Enter one of: " + "/".join(choices) if choices else "  A value is required.")


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
    try:
        interactive()
        input("\nPress Enter to exit...")
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
