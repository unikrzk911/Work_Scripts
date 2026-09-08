import csv
import os
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
