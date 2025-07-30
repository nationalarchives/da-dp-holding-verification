import csv, sqlite3
import configparser


def get_csv_rows(csv_name: str, file_ref_col: str, fixity_value_col: str, algo_name_col: str):
    with open(csv_name, "r") as checksum_file:
        dr = csv.DictReader(checksum_file)
        print(f"Getting rows from CSV: '{csv_name}'")
        rows_to_write = tuple((row[file_ref_col], row[fixity_value_col], row[algo_name_col]) for row in dr)
    return rows_to_write


def populate_table(cursor: sqlite3.Cursor, table_name: str, rows_to_write: tuple[tuple[str, str, str]]):
    print(f"Adding rows into table: '{table_name}'")
    cursor.executemany(f"INSERT INTO {table_name} (file_ref, fixity_value, algorithm_name) VALUES (?, ?, ?);",
                       rows_to_write)
    cursor.execute(f"CREATE INDEX index_fixity_value ON {table_name} (fixity_value ASC)")


def main():
    config = configparser.ConfigParser()
    config.read("config.ini")
    checksum_db_name = config["DEFAULT"]["CHECKSUM_DB_NAME"]
    table_name = config["DEFAULT"]["CHECKSUM_TABLE_NAME"]
    csv_name = input("Paste the full path of the CSV file with the checksums here and press ENTER: ")

    connection = sqlite3.connect(checksum_db_name)
    cursor = connection.cursor()

    cursor.execute(f"CREATE TABLE {table_name} (file_ref, fixity_value, algorithm_name);")

    file_ref_col = config["DEFAULT"]["CSV_FILEREF_COLUMN"]
    fixity_value_col = config["DEFAULT"]["CSV_FIXITYVALUE_COLUMN"]
    algo_name_col = config["DEFAULT"]["CSV_ALGORITHMNAME_COLUMN"]

    rows_to_write = get_csv_rows(csv_name, file_ref_col, fixity_value_col, algo_name_col)
    populate_table(cursor, table_name, rows_to_write)

    connection.commit()
    connection.close()
    print("Completed.")


if __name__ == "__main__":
    main()
