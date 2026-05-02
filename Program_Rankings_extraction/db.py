import os
import pyodbc
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


def get_readonly_connection():
    db_string = os.getenv('DB_STRING')
    if not db_string:
        raise ValueError("DB_STRING environment variable is not set")
    conn = pyodbc.connect(db_string + "ApplicationIntent=ReadOnly;")
    conn.autocommit = False
    return conn


def fetch_data_from_db(query: str) -> pd.DataFrame:
    conn = get_readonly_connection()
    try:
        return pd.read_sql(query, conn)
    finally:
        conn.close()


def fetch_program_rankings() -> pd.DataFrame:
    query = """
        SELECT
            cp.Id          AS ProgramId,
            cp.CollegeId,
            cp.ProgramName,
            c.CollegeName,
            c.city         AS City,
            cp.Level,
            cp.QsWorldRanking,
            cp.UsNewsRanking
        FROM CollegePrograms cp
        INNER JOIN Colleges c ON cp.CollegeId = c.Id
    """
    return fetch_data_from_db(query)


if __name__ == "__main__":
    df = fetch_program_rankings()
    batch_size = 10_000
    total = len(df)
    num_batches = (total + batch_size - 1) // batch_size
    for i in range(num_batches):
        chunk = df.iloc[i * batch_size : (i + 1) * batch_size]
        chunk.to_csv(f"program_qs_rankings_part{i + 1}.csv", index=False)
        print(f"Part {i + 1}/{num_batches}: {len(chunk):,} rows → program_qs_rankings_part{i + 1}.csv")
    print(f"\nTotal: {total:,} rows across {num_batches} files.")
