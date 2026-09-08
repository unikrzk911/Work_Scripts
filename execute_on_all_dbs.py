import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_NAMES = [
    "a", "actuarial", "actuary", "b", "c", "cbh", "d", "da", "dba", "dev", "devims",
    "e", "f", "fm", "fme_db", "g", "h", "hikmat_test", "i", "ima_ima_pa_01_20_b2_rs_20200122",
    "j", "k", "l", "m", "ml_ed_clustering", "n", "near_real_time_prod", "near_real_time_qc",
    "o", "p", "padb_harvest", "q", "quicksight", "r", "raw_apostophe", "raw_eba",
    "s", "sys:internal", "t", "test_pae_dev", "test_ps_dev", "test_ps_dev_2",
    "test_qa", "test_qa1", "test_so_dev", "test_so_extract", "u", "v", "w", "z",
]


def load_sql_file(file_path):
    with open(file_path, 'r') as file:
        return file.read()


def build_db_connections(db_names):
    return [
        {
            "dbname": dbname,
            "user": os.environ['REDSHIFT_USER'],
            "password": os.environ['REDSHIFT_PASSWORD'],
            "host": os.environ['REDSHIFT_HOST'],
            "port": os.environ.get('REDSHIFT_PORT', '5439'),
        }
        for dbname in db_names
    ]


def execute_on_all_dbs(sql_script, db_list):
    for db in db_list:
        conn = None
        cur = None
        try:
            print(f"Connecting to {db['dbname']}...")
            conn = psycopg2.connect(**db)
            cur = conn.cursor()
            cur.execute(sql_script)
            conn.commit()
            print(f"✅ Function created in {db['dbname']}")
        except Exception as e:
            print(f"❌ Failed on {db['dbname']}: {e}")
        finally:
            if cur is not None:
                cur.close()
            if conn is not None:
                conn.close()


def main():
    sql_file_path = os.environ.get('SQL_FILE_PATH', '')
    create_function_sql = load_sql_file(sql_file_path)
    databases = build_db_connections(DB_NAMES)
    execute_on_all_dbs(create_function_sql, databases)


if __name__ == "__main__":
    main()
