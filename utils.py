import csv
import os
import pandas as pd
import redshift_connector
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()


def get_data(database, query):
    # Establish the connection to the Redshift database
    conn = redshift_connector.connect(
        user=os.environ['REDSHIFT_USER'],
        password=os.environ['REDSHIFT_PASSWORD'],
        host=os.environ['REDSHIFT_HOST'],
        port=int(os.environ.get('REDSHIFT_PORT', 5439)),
        database=database
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

    df = pd.DataFrame(result, columns=column_names)
    print("All data fetched")
    # save_as_csv(df, '', 'query_data.csv', '|', get_data=True)
    return df



def save_as_csv(df, path, filename, delimiter, quotchar=False, get_data=False):
    output_dir = Path(path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = path + filename
    if quotchar:
        df.to_csv(path, sep=delimiter, index=False, quotechar='"', quoting=csv.QUOTE_ALL)
    else:
        df.to_csv(path, sep=delimiter, index=False)
    if get_data:
        print(f'File temporarily saved to location: {path}')
    else:
        print(f'{filename} saved to location: {path}')


def combine_csvs(csv_files, out_path=None, read_sep=",", write_sep="|", add_source_cols=False):
    if not csv_files:
        return pd.DataFrame()

    df_list = []
    for file in csv_files:
        df = pd.read_csv(file, sep=read_sep, dtype=str)
        if add_source_cols:
            df["__source_file"] = os.path.basename(file)  # just the filename
            df["__source_path"] = file  # full path
        df_list.append(df)

    combined_df = pd.concat(df_list, ignore_index=True)

    if out_path:
        combined_df.to_csv(out_path, sep=write_sep, index=False)
    return combined_df
