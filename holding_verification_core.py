import csv
import hashlib
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from helpers.helper import ColourCliText

colour_text = ColourCliText()
yellow = colour_text.yellow
light_red = colour_text.light_red
red = colour_text.red
green = colour_text.green
bright_cyan = colour_text.bright_cyan


def check_db_exists(db_file_name, confirm_db_added_prompt=input):
    db_file_does_not_exist = True
    while db_file_does_not_exist:
        if Path(db_file_name).exists():
            break
        else:
            response = confirm_db_added_prompt(
                f"'{db_file_name}' is missing from the directory '{os.getcwd()}'; add it a press 'Enter' to continue"
            )
            if isinstance(response, bool):  # In tests, confirm_db_added_prompt returns Boolean in order to break loop
                db_file_does_not_exist = response


@dataclass(frozen=True)
class ResultSummary:
    files_processed: int
    tally: dict[bool, int]
    all_file_errors: list[dict[str, str]]
    output_csv_name: str


class HoldingVerificationCore:
    def __init__(self, connection, table_name, csv_file_name_prefix=""):
        self.connection = connection
        self.cursor = self.connection.cursor()
        self.select_statement = f"""SELECT file_ref, fixity_value, algorithm_name FROM {table_name} WHERE "fixity_value" """
        self.IN_PROGRESS_SUFFIX = "_IN_PROGRESS"
        self.csv_file_name_prefix = f"{csv_file_name_prefix}_" if csv_file_name_prefix else csv_file_name_prefix
        self.print = print

    BUFFER_SIZE = 1_000_000

    def get_checksum_for_file(self, file_path: str, hash_func) -> tuple[str, dict[str, str]]:
        errors = dict()
        try:
            with open(file_path, "rb") as file:
                while True:
                    contents = file.read(self.BUFFER_SIZE)
                    if not contents:
                        break
                    hash_func.update(contents)

                return hash_func.hexdigest(), errors
        except OSError as e:
            errors[file_path] = str(e)
            return "", errors

    def find_checksum_in_db(self, file_hash: str) -> list[list[str]]:
        self.cursor.execute(f"""{self.select_statement}= "{file_hash}";""")
        results_with_hash = self.cursor.fetchall()
        return results_with_hash

    def get_rows_with_hash(self, path: str, presumed_hash_name: str):
        sha256_name = "sha256"
        #  MD5 is 2nd since really old files (which we have a lot of) are MD5 so looking for them first is optimal
        hashes_to_lookup = {sha256_name: hashlib.sha256, "md5": hashlib.md5, "sha1": hashlib.sha1}
        errors = dict()
        actual_hash_name = ""
        checksum_found = False
        rows_with_hash = []
        sha256_hash = "" # We need to get this, regardless of whether the file has matched with another hash

        presumed_hash = {presumed_hash_name: hashes_to_lookup[presumed_hash_name]} if presumed_hash_name in hashes_to_lookup else {}
        hashes_to_lookup =  presumed_hash | hashes_to_lookup

        for hash_name, hash_function in hashes_to_lookup.items():
            (checksum, errors) = self.get_checksum_for_file(path, hash_function())
            if hash_name == sha256_name:
                sha256_hash = checksum
                if checksum_found: # An md5 or sha1 may have matched previously so don't need to look in DB again
                    break
            rows_with_hash = self.find_checksum_in_db(checksum)
            checksum_found = len(rows_with_hash) > 0

            if checksum_found:
                actual_hash_name = hash_name
                if sha256_hash:
                    break
        else:
            actual_hash_name = ""

        return sha256_hash, rows_with_hash, checksum_found, errors, actual_hash_name

    def run(self, path, file_hash_name, all_file_errors: list[dict[str, str]], csv_writer, tally):
        file_size = Path(path).stat().st_size
        if file_size > 500_000_000:
            print(f"Currently processing a file that is {file_size:,} bytes; might take a while...")

        (sha256_hash, rows_with_hash, checksum_found, errors_generating_checksum, next_hash_name) = \
            self.get_rows_with_hash(path, file_hash_name)

        checksum_found_colour = green(checksum_found) if checksum_found else light_red(checksum_found)
        print(f"{yellow("File ingested")} = {checksum_found_colour}: {path}")
        tally[checksum_found] += 1

        file_refs = ", ".join((row[0] for row in rows_with_hash))
        checksum_value = "".join({row[1] for row in rows_with_hash})
        checksum_algo_name = next_hash_name

        row = (path, file_size, checksum_found, sha256_hash, file_refs, checksum_algo_name, checksum_value)
        csv_writer.writerow(row)

        if errors_generating_checksum:
            all_file_errors.append(errors_generating_checksum)

        starting_hash_name_for_next_file = checksum_algo_name if checksum_found else file_hash_name
        return starting_hash_name_for_next_file, all_file_errors, tally

    def get_csv_output_writer_and_file_name(self, path: Path, date: str = datetime.now().strftime("%d-%m-%Y-%H_%M_%S")):
        output_csv_name = (f"{self.csv_file_name_prefix}INGESTED_FILES_in_{path.name}_{date}"
                           f"{self.IN_PROGRESS_SUFFIX}.csv")
        csv_file = open(output_csv_name, "w", newline="", encoding="utf-8")
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(("Local File Path", "File Size (Bytes)", "In Preservica/DRI", "SHA256 Hash",
                             "Matching File Refs", "Matching Algorithm Name", "Matching Algorithm Hash"))
        return csv_file, csv_writer, output_csv_name


    def start(self, file_or_dir) -> ResultSummary:
        is_directory = file_or_dir["is_directory"]
        paths = file_or_dir["path"]
        path_of_an_item_path = Path(paths[0])  # assuming that files are in the same folder for now
        dir_path: Path = path_of_an_item_path.parent if path_of_an_item_path.is_file() else path_of_an_item_path

        assumed_hash_algo = "sha256"  # SHA256 because newer files have SHA256 hashes
        all_file_errors: list[dict[str, str]] = []
        tally: dict[bool, int] = defaultdict(int)
        files_processed = 0

        csv_file, csv_writer, output_csv_name = self.get_csv_output_writer_and_file_name(dir_path)

        if is_directory:
            for direct_dir, _, files_in_dir in Path(dir_path).walk():
                if files_in_dir:  # for each directory, there could be just directories inside
                    for file_name in files_in_dir:
                        item_path = f"{direct_dir / file_name}"
                        files_processed += 1
                        (hash_name, all_file_errors, tally) = self.run(
                            str(item_path), assumed_hash_algo, all_file_errors, csv_writer, tally
                        )
                        assumed_hash_algo = hash_name  # Assume next file uses same algo in order to reduce file hashing

                    if files_processed % 100 == 0:
                        print(f"\n{bright_cyan(f"{files_processed:,} files processed")}\n")

        else:
            for path in paths:
                files_processed += 1
                (hash_name, all_file_errors, tally) = self.run(path, assumed_hash_algo, all_file_errors, csv_writer, tally)
                assumed_hash_algo = hash_name  # Assume next file uses same algo in order to reduce file hashing

        csv_file.close()
        self.connection.commit()
        try:
            os.rename(output_csv_name, output_csv_name.replace(self.IN_PROGRESS_SUFFIX, ""))
        except Exception as e:
            self.print(red("\n\nWARNING: Processing completed but was unable to remove '_IN_PROGRESS' from the " +
                      f"CSV file name, due to this error: {e}")
            )

        return ResultSummary(files_processed, tally, all_file_errors, output_csv_name)
