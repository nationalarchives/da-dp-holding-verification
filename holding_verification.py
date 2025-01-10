import csv
import hashlib
import sqlite3
import tkinter as tk
from collections import defaultdict
from datetime import datetime
import os
from pathlib import Path
from tkinter.filedialog import askdirectory, askopenfilenames

BUFFER_SIZE = 1_000_000
connection = sqlite3.connect(os.environ["CHECKSUM_DB_NAME"])
cursor = connection.cursor()
table_name = os.environ["CHECKSUM_TABLE_NAME"]
select_statement = f"""SELECT file_ref, fixity_value, algorithm_name FROM {table_name} WHERE "fixity_value" """


def open_select_window() -> dict[str, tuple[str]]:
    select_window = tk.Tk()
    select_window.title("Holding Verification: Select Item")
    select_window.geometry("500x200")
    select_window.eval('tk::PlaceWindow . center')
    item_path = tuple()
    result = {}

    def fileCallback() -> None:
        nonlocal item_path

        item_path = askopenfilenames(parent=select_window, initialdir="", title='Select File(s)')
        if item_path != "":
            result["is_directory"] = False
            select_window.destroy()

    def folderCallback() -> None:
        nonlocal item_path
        folder_path = (askdirectory(parent=select_window, initialdir="", title='Select Folder'),)
        item_path = folder_path

        if item_path != ("",):
            result["is_directory"] = True
            select_window.destroy()

    select_file_button = tk.Button(select_window, text="Select File(s)", command=fileCallback)
    select_dir_button = tk.Button(select_window, text="Select Folder", command=folderCallback)
    select_file_button.place(x=130, y=50)
    select_dir_button.place(x=250, y=50)

    select_window.wait_window()
    select_window.update_idletasks()  # Forces the window to close
    if item_path == "":
        print("Application closed.")
        quit()  # User has closed the application window
    print(f"\nYou've selected: {",\n".join(item_path)}\n")
    result["path"] = item_path
    return result


def what_to_look_up() -> dict[str, tuple[str]]:
    path_types = {"f": "file", "d": "directory"}
    result = {}
    while True:
        file_or_dir = input("Would you like to look up a single file or directory? [f/d]: ").lower()
        if file_or_dir in path_types:
            path_type = path_types[file_or_dir]
            path_string = (input(f"Add the full {path_type} path here and press 'Enter': ")
                           .strip()
                           .removeprefix('"')
                           .removesuffix('"')
                           )
            path = Path(path_string)
            path_exists = path.exists() and path_string != ""
            is_directory = path.is_dir()
            wrong_item_type = (is_directory and file_or_dir != "d") or (not is_directory and file_or_dir != "f")

            if not path_exists:
                print(f"\nA path for this {path_type} does not exist. Starting again...")
            if wrong_item_type:
                print(
                    f"\nYou want to look up a {path_type} but did not provide a path for a {path_type}. Starting again...")
            else:
                result["path"] = (path_string,)
                result["is_directory"] = is_directory
                break
            what_to_look_up()
        else:
            print(f"{file_or_dir} is not a valid option.")
            continue
    return result


def get_checksum_for_file(file_path: str, hash_func) -> tuple[str, dict[str, str]]:
    errors = dict()
    try:
        with open(file_path, "rb") as file:
            while True:
                contents = file.read(BUFFER_SIZE)
                if not contents:
                    break
                hash_func.update(contents)

            return hash_func.hexdigest(), errors
    except OSError as e:
        errors[file_path] = str(e)
        return "", errors


def find_checksum_in_db(file_hash: str) -> list:
    cursor.execute(f"""{select_statement}= "{file_hash}";""")
    results_with_hash = cursor.fetchall()
    return results_with_hash


def run(path, file_hash_name, all_file_errors, csv_writer, tally):
    file_size = Path(path).stat().st_size
    if file_size > 500_000_000:
        print(f"Currently processing a file that is {file_size:,} bytes; might take a while...")

    #  MD5 is 2nd as really old files (which we have a lot of) are MD5 so looking for them first is optimal
    hashes_to_lookup = {"sha256": hashlib.sha256, "md5": hashlib.md5, "sha1": hashlib.sha1}
    errors = dict()
    next_hash_name = file_hash_name
    checksum_found = False
    rows_with_hash = 0

    while not checksum_found and len(hashes_to_lookup) > 0:
        next_hash_name = file_hash_name if file_hash_name in hashes_to_lookup else list(hashes_to_lookup.keys())[0]
        hash_function = hashes_to_lookup.pop(next_hash_name)

        (checksum, errors) = get_checksum_for_file(path, hash_function())
        rows_with_hash = find_checksum_in_db(checksum)
        checksum_found = len(rows_with_hash) > 0
        if checksum_found:
            hashes_to_lookup = dict()

    file_refs = ", ".join((row[0] for row in rows_with_hash))
    checksum_value = "".join({row[1] for row in rows_with_hash})
    checksum_algo_name = "".join({row[2] for row in rows_with_hash})

    csv_writer.writerow((path, file_size, checksum_found, file_refs, checksum_algo_name, checksum_value))
    tally[checksum_found] += 1
    print(f"File ingested = {checksum_found}: {path}")

    if errors:
        all_file_errors.append(errors)

    starting_hash_name_for_next_file = next_hash_name if checksum_found else file_hash_name

    return starting_hash_name_for_next_file, all_file_errors, tally


def main():
    use_gui = input("Press 'Enter' to use the GUI or type 'c' then 'Enter' for the CLI: ").lower()

    file_or_dir: dict[str, tuple[str]] = what_to_look_up() if use_gui == "c" else open_select_window()
    paths = file_or_dir["path"]

    is_directory = file_or_dir["is_directory"]

    output_csv_name = f"""files_that_have_been_ingested_{datetime.now().strftime("%d-%m-%Y-%H_%M_%S")}.csv"""
    assumed_hash_algo = "sha256"  # SHA256 because newer files have SHA256 hashes
    all_file_errors: list[dict[str, str]] = []
    tally = defaultdict(int)

    with open(output_csv_name, "w", newline="", encoding="utf-8") as csvFile:
        csv_writer = csv.writer(csvFile)
        csv_writer.writerow(("Local File Path", "File Size (Bytes)", "In Preservica/DRI", "Matching File Refs",
                             "Algorithm Name", "Algorithm Hash"))
        files_processed = 0

        if is_directory:
            path = paths[0]
            # if we move to Python 3.12+ on TNA Desktops, please replace the '.rglob("*")' for-loop with this
            # commented out '.walk()' version as the .walk() version seems to pick up more file types:
            # for direct_dir, _, files_in_dir in Path(path).walk():
            #     if files_in_dir:  # for each directory, there could be just directories inside
            #         for file_name in files_in_dir:
            #             item_path = f"{direct_dir / file_name}"
            #             ... keep the rest of the old for-loop the same

            for item_path in Path(path).rglob("*"):
                if item_path.is_file():
                    files_processed += 1
                    (hash_name, all_file_errors, tally) = run(
                        str(item_path), assumed_hash_algo, all_file_errors, csv_writer, tally
                    )
                    assumed_hash_algo = hash_name  # Assume next file uses same algo in order to reduce file hashing

                    if files_processed % 100 == 0:
                        print(f"\n{files_processed:,} files processed\n")

        else:
            for path in paths:
                files_processed += 1
                (hash_name, all_file_errors, tally) = run(path, assumed_hash_algo, all_file_errors, csv_writer, tally)
                assumed_hash_algo = hash_name  # Assume next file uses same algo in order to reduce file hashing

    connection.commit()
    connection.close()

    print(f"\nCompleted.\n\n")
    print(f"{files_processed:,} files were processed:")
    print(f"""
    Files in Preservica/DRI: {tally.get(True):}
    Files not in Preservica/DRI: {tally.get(False):}
    """)

    print(f"The full results can be found in a file called '{output_csv_name}'.\n")
    if all_file_errors:
        print("These files encountered errors when trying to generate checksums:\n")
        for file_error in all_file_errors:
            print(file_error)

    while True:
        user_choice = input("Press 'q' and 'Enter' to quit: ").lower()
        if user_choice == "q":
            break
        else:
            continue


if __name__ == "__main__":
    main()
