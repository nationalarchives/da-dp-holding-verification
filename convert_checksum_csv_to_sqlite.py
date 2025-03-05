import csv, sqlite3
import os

def get_csv_rows(csv_name: str):
    with open(csv_name, "r") as checksum_file:
        dr = csv.DictReader(checksum_file)
        print(f"Getting rows from CSV: '{csv_name}'")
        rows_to_write = tuple((row["FILEREF"], row["FIXITYVALUE"], row["ALGORITHMNAME"]) for row in dr)
    return rows_to_write

def populate_table(cursor: sqlite3.Cursor, table_name: str, rows_to_write: tuple[tuple[str, str, str]]):
    print(f"Adding rows into table: '{table_name}'")
    cursor.executemany(f"INSERT INTO {table_name} (file_ref, fixity_value, algorithm_name) VALUES (?, ?, ?);",
                       rows_to_write)
    cursor.execute(f"CREATE INDEX index_fixity_value ON {table_name} (fixity_value ASC)")

def main():
    connection = sqlite3.connect(os.environ["CHECKSUM_DB_NAME"])
    cursor = connection.cursor()

    table_name = os.environ["CHECKSUM_TABLE_NAME"]
    cursor.execute(f"CREATE TABLE {table_name} (file_ref, fixity_value, algorithm_name);")
    csv_name = os.environ["CSV_FILE_WITH_CHECKSUMS"]

    rows_to_write = get_csv_rows(csv_name)
    populate_table(cursor, table_name, rows_to_write)

    connection.commit()
    connection.close()
    print("Completed.")

if __name__ == "__main__":
    main()