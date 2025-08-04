import configparser
import os
import sqlite3
from pathlib import Path

from colorama import Fore, Style

import holding_verification
from get_path_from_user import GetPathFromUser
from holding_verification import HoldingVerification

config = configparser.ConfigParser()
config.read("config.ini")
default_config = config["DEFAULT"]

def main():
    if __name__ == "__main__":
        from sys import platform
        # On Macs, the exe runs the script in the '_internal' dir so this changes it to the location of the executable
        if platform == "darwin":
            os.chdir(Path(__file__).parent.parent)

        db_file_name = default_config["CHECKSUM_DB_NAME"]
        holding_verification.check_db_exists(db_file_name)

        db_function = sqlite3.connect(db_file_name)
        app = HoldingVerification(db_function)

        use_gui = input(
            f"Press '{Fore.YELLOW}Enter{Style.RESET_ALL}' to use the GUI or type '{Fore.YELLOW}c{Style.RESET_ALL}'"
            f" then 'Enter' for the CLI: "
        ).strip().lower()
        prompt = GetPathFromUser(app)
        prompt.cli_input() if use_gui == "c" else prompt.open_select_window()


        while True:
            user_choice = input(f"Press '{Fore.YELLOW}q{Style.RESET_ALL}' and '{Fore.YELLOW}Enter{Style.RESET_ALL}' to "
                                f"quit: ").lower()
            if user_choice == "q":
                app.connection.close()
                break
            else:
                continue

if __name__ == "__main__":
    main()
