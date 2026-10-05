import csv
import os
import sys
from pathlib import Path

import pandas as pd
import redshift_connector
from dotenv import load_dotenv

load_dotenv()


def get_data(database, query):
    conn = redshift_connector.connect(
        user=os.environ['REDSHIFT_USER'],
        password=os.environ['REDSHIFT_PASSWORD'],
        host=os.environ['REDSHIFT_HOST'],
        port=int(os.environ.get('REDSHIFT_PORT', 5439)),
        database=database,
    )
    cursor = conn.cursor()
    print("Connection established")
    try:
        print("Fetching data")
        cursor.execute(query)
        result = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
    finally:
        cursor.close()
        conn.close()

    print("All data fetched")
    return pd.DataFrame(result, columns=column_names)


def save_as_csv(df, path, filename, delimiter, quote_all=False, is_temp_file=False):
    output_dir = Path(path)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename

    if quote_all:
        df.to_csv(output_path, sep=delimiter, index=False, quotechar='"', quoting=csv.QUOTE_ALL)
    else:
        df.to_csv(output_path, sep=delimiter, index=False)

    if is_temp_file:
        print(f'File temporarily saved to location: {output_path}')
    else:
        print(f'{filename} saved to location: {output_path}')


def combine_csvs(csv_files, out_path=None, read_sep=",", write_sep="|", add_source_cols=False):
    if not csv_files:
        return pd.DataFrame()

    df_list = []
    for file in csv_files:
        df = pd.read_csv(file, sep=read_sep, dtype=str)
        if add_source_cols:
            df["__source_file"] = os.path.basename(file)
            df["__source_path"] = file
        df_list.append(df)

    combined_df = pd.concat(df_list, ignore_index=True)

    if out_path:
        combined_df.to_csv(out_path, sep=write_sep, index=False)
    return combined_df


def combine_txt_files(input_folder):
    """Merge every *.TXT in `input_folder` into combined.txt, with a header per file."""
    input_folder = Path(input_folder)
    output_file = input_folder / "combined.txt"
    txt_files = sorted(
        f for f in input_folder.glob("*.TXT")
        if f.resolve() != output_file.resolve()
    )
    separator = "=" * 80

    with output_file.open("w", encoding="utf-8") as outfile:
        for txt_file in txt_files:
            print(f"Processing: {txt_file.name}")
            outfile.write(f"{separator}\nFILE: {txt_file.name}\n{separator}\n")
            outfile.write(txt_file.read_text(encoding="utf-8") + "\n\n")

    print(f"Combined {len(txt_files)} files into {output_file}")
    return output_file


def ask(label, choices=None):
    """Prompt until a non-empty answer (one of `choices`, if given) is entered."""
    while True:
        answer = input(label + ": ").strip()
        if answer and (not choices or answer.upper() in choices):
            return answer
        print("  Enter one of: " + "/".join(choices) if choices else "  A value is required.")


def save_sql(sql, filename):
    """Print the SQL and save it as `filename` next to the script being run."""
    print("\n" + "-" * 70 + "\n" + sql + "\n" + "-" * 70)
    out = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), filename)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(sql + "\n")
    print("\nSaved to: " + out)


def run_interactive(interactive):
    """Run a prompt-driven script; keep the window open when double-clicked."""
    try:
        interactive()
        input("\nPress Enter to exit...")
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
