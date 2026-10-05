import os
from contextlib import closing
from pathlib import Path

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


def execute_on_all_dbs(sql, db_names):
    credentials = {
        "user": os.environ['REDSHIFT_USER'],
        "password": os.environ['REDSHIFT_PASSWORD'],
        "host": os.environ['REDSHIFT_HOST'],
        "port": os.environ.get('REDSHIFT_PORT', '5439'),
    }
    for db_name in db_names:
        try:
            print(f"Connecting to {db_name}...")
            with closing(psycopg2.connect(dbname=db_name, **credentials)) as conn, conn.cursor() as cur:
                cur.execute(sql)
                conn.commit()
            print(f"✅ Executed on {db_name}")
        except Exception as e:
            print(f"❌ Failed on {db_name}: {e}")


def main():
    sql = Path(os.environ['SQL_FILE_PATH']).read_text()
    execute_on_all_dbs(sql, DB_NAMES)


if __name__ == "__main__":
    main()
