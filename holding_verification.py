import csv
import hashlib
import sqlite3

from collections import defaultdict
from datetime import datetime
from pathlib import Path

from colorama import init as colorama_init
from colorama import Fore
from colorama import Style

from get_path_from_user import GetPathFromUser

colorama_init()


class HoldingVerification:
    def __init__(self, connection):
        self.connection = connection
        self.cursor = self.connection.cursor()

    BUFFER_SIZE = 1_000_000
    table_name = "files_in_dri"
    select_statement = f"""SELECT file_ref, fixity_value, algorithm_name FROM {table_name} WHERE "fixity_value" """


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


    def get_rows_with_hash(self, path: str, file_hash_name: str):
        #  MD5 is 2nd since really old files (which we have a lot of) are MD5 so looking for them first is optimal
        hashes_to_lookup = {"sha256": hashlib.sha256, "md5": hashlib.md5, "sha1": hashlib.sha1}
        errors = dict()
        next_hash_name = file_hash_name
        checksum_found = False
        rows_with_hash = []

        while not checksum_found and len(hashes_to_lookup) > 0:
            next_hash_name = file_hash_name if file_hash_name in hashes_to_lookup else list(hashes_to_lookup.keys())[0]
            hash_function = hashes_to_lookup.pop(next_hash_name)

            (checksum, errors) = self.get_checksum_for_file(path, hash_function())
            rows_with_hash = self.find_checksum_in_db(checksum)
            checksum_found = len(rows_with_hash) > 0
            if checksum_found:
                hashes_to_lookup = dict()

        return rows_with_hash, checksum_found, errors, next_hash_name

    def run(self, path, file_hash_name, all_file_errors: list[dict[str, str]], csv_writer, tally):
        file_size = Path(path).stat().st_size
        if file_size > 500_000_000:
            print(f"Currently processing a file that is {file_size:,} bytes; might take a while...")

        (rows_with_hash, checksum_found, errors_generating_checksum, next_hash_name) =\
            self.get_rows_with_hash(path, file_hash_name)

        checksum_found_colour = f"{Fore.GREEN}{checksum_found}{Style.RESET_ALL}" if checksum_found else (
            f"{Fore.LIGHTRED_EX}{checksum_found}{Style.RESET_ALL}"
        )
        print(f"{Fore.YELLOW}File ingested{Style.RESET_ALL} = {checksum_found_colour}: {path}")
        tally[checksum_found] += 1

        file_refs = ", ".join((row[0] for row in rows_with_hash))
        checksum_value = "".join({row[1] for row in rows_with_hash})
        checksum_algo_name = next_hash_name if checksum_found else ""

        csv_writer.writerow((path, file_size, checksum_found, file_refs, checksum_algo_name, checksum_value))

        if errors_generating_checksum:
            all_file_errors.append(errors_generating_checksum)

        starting_hash_name_for_next_file = checksum_algo_name if checksum_found else file_hash_name
        return starting_hash_name_for_next_file, all_file_errors, tally

    def get_csv_output_writer_and_file_name(self, path: Path, date: str=datetime.now().strftime("%d-%m-%Y-%H_%M_%S")):
        output_csv_name =  f"INGESTED_FILES_in_{path.name}_{date}.csv"
        csv_file = open(output_csv_name, "w", newline="", encoding="utf-8")
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(("Local File Path", "File Size (Bytes)", "In Preservica/DRI", "Matching File Refs",
                             "Algorithm Name", "Algorithm Hash"))
        return csv_file, csv_writer, output_csv_name

    def get_file_or_dir_from_user(self, gui_or_cli_prompt=input, file_prompt=GetPathFromUser) -> dict[str, tuple[str] | bool]:
        use_gui = gui_or_cli_prompt(
            f"Press '{Fore.YELLOW}Enter{Style.RESET_ALL}' to use the GUI or type '{Fore.YELLOW}c{Style.RESET_ALL}'"
            f" then 'Enter' for the CLI: "
        ).strip().lower()
        prompt = file_prompt()
        return prompt.cli_input() if use_gui == "c" else (prompt.open_select_window())


def main(app: HoldingVerification):
    file_or_dir: dict[str, tuple[str] | bool] = app.get_file_or_dir_from_user()
    is_directory = file_or_dir["is_directory"]
    paths = file_or_dir["path"]
    path_of_an_item_path = Path(paths[0]) # assuming that files are in the same folder for now
    dir_path: Path = path_of_an_item_path.parent if path_of_an_item_path.is_file() else path_of_an_item_path

    assumed_hash_algo = "sha256"  # SHA256 because newer files have SHA256 hashes
    all_file_errors: list[dict[str, str]] = []
    tally = defaultdict(int)
    files_processed = 0

    csv_file, csv_writer, output_csv_name = app.get_csv_output_writer_and_file_name(dir_path)

    if is_directory:
        for direct_dir, _, files_in_dir in Path(dir_path).walk():
            if files_in_dir:  # for each directory, there could be just directories inside
                for file_name in files_in_dir:
                    item_path = f"{direct_dir / file_name}"
                    files_processed += 1
                    (hash_name, all_file_errors, tally) = app.run(
                        str(item_path), assumed_hash_algo, all_file_errors, csv_writer, tally
                    )
                    assumed_hash_algo = hash_name  # Assume next file uses same algo in order to reduce file hashing

                if files_processed % 100 == 0:
                    print(f"\n{Fore.CYAN}{Style.BRIGHT}{files_processed:,} files processed{Style.RESET_ALL}\n")

    else:
        for path in paths:
            files_processed += 1
            (hash_name, all_file_errors, tally) = app.run(path, assumed_hash_algo, all_file_errors, csv_writer, tally)
            assumed_hash_algo = hash_name  # Assume next file uses same algo in order to reduce file hashing

    csv_file.close()
    app.connection.commit()
    app.connection.close()

    print(f"\n{Fore.GREEN}Completed.{Style.RESET_ALL}\n\n")
    print(f"{Fore.CYAN}{Style.BRIGHT}{files_processed:,}{Style.RESET_ALL} files were processed:")
    preserved =  tally.get(True)
    preserved_colour = f"{Fore.GREEN}{preserved}{Style.RESET_ALL}" if preserved else f"{Fore.MAGENTA}{preserved}{Style.RESET_ALL}"
    print(f"""
    Files in Preservica/DRI: {preserved_colour:}
    Files not in Preservica/DRI: {Fore.RED}{tally.get(False):}{Style.RESET_ALL}
    """)

    print(f"The full results can be found in a file called '{Fore.YELLOW}{output_csv_name}{Style.RESET_ALL}'.\n")
    if all_file_errors:
        print("These files encountered errors when trying to generate checksums:\n")
        for file_error in all_file_errors:
            print(f"{Fore.RED}{file_error}{Style.RESET_ALL}")


if __name__ == "__main__":
    from sys import platform
# Macs run the script from root dir, so this changes it to the location of theexecutable
    if platform == "darwin":
        import os
        os.chdir(Path(__file__).parent.parent)
    db_function = sqlite3.connect("checksums_of_files_in_dri.db")
    app = HoldingVerification(db_function)
    main(app)

    while True:
        user_choice = input("Press 'q' and 'Enter' to quit: ").lower()
        if user_choice == "q":
            break
        else:
            continue
