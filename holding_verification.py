import configparser
import os
import sqlite3
from pathlib import Path

from colorama import Fore, Style

from holding_verification_ui import HoldingVerificationUi
from holding_verification_core import HoldingVerificationCore, check_db_exists
from sys import platform


def main():
    # On Macs, the exe runs the script in the '_internal' dir so this changes it to the location of the executable
    if platform == "darwin":
        file_loc = Path(__file__) # this file's location
        os.chdir(file_loc.parent.parent if file_loc.parent.name.endswith("_internal") else file_loc.parent)

    config = configparser.ConfigParser()
    config.read("config.ini")
    default_config = config["DEFAULT"]
    db_file_name = default_config["CHECKSUM_DB_NAME"]
    check_db_exists(db_file_name)
    table_name = default_config["CHECKSUM_TABLE_NAME"]

    db_function = sqlite3.connect(db_file_name)
    csv_file_name_prefix = input(
        f"Add a title to be prepended to the CSV result's file name then '{Fore.YELLOW}Enter{Style.RESET_ALL}'"
        f" or just press '{Fore.YELLOW}Enter{Style.RESET_ALL}' to skip: "
    ).replace(" ", "_")
    app_core = HoldingVerificationCore(db_function, table_name, csv_file_name_prefix)
    ui = HoldingVerificationUi(app_core)
    cli_or_gui = ui.prompt_use_gui()

    if cli_or_gui == "c":
        ui.cli_input()
        while True:
            user_choice = input(
                f"Press '{Fore.YELLOW}q{Style.RESET_ALL}' and '{Fore.YELLOW}Enter{Style.RESET_ALL}' to "f"quit: "
            ).lower().strip()
            if user_choice == "q":
                app_core.connection.close()
                break
            else:
                continue
    else:
        ui.open_select_window()

if __name__ == "__main__":
    main()
