import configparser
import os
import sqlite3
from pathlib import Path

from colorama import Fore, Style

from holding_verification_ui import HoldingVerificationUi
from holding_verification_core import HoldingVerificationCore, check_db_exists
from sys import platform

config = configparser.ConfigParser()
config.read("config.ini")
default_config = config["DEFAULT"]

def start():
    # On Macs, the exe runs the script in the '_internal' dir so this changes it to the location of the executable
    if platform == "darwin":
        os.chdir(Path(__file__).parent.parent)

    db_file_name = default_config["CHECKSUM_DB_NAME"]
    check_db_exists(db_file_name)

    db_function = sqlite3.connect(db_file_name)
    app_core = HoldingVerificationCore(db_function)
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
    start()
