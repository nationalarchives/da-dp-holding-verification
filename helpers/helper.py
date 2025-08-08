from colorama import Fore
from colorama import Style
from colorama import init as colorama_init

class ColourCliText:
    def __init__(self):
        colorama_init()

    def yellow(self, text) -> str:
        return f"{Fore.YELLOW}{text}{Style.RESET_ALL}"

    def green(self, text) -> str:
        return f"{Fore.GREEN}{text}{Style.RESET_ALL}"

    def red(self, text) -> str:
        return f"{Fore.RED}{text}{Style.RESET_ALL}"

    def l_red(self, text) -> str:
        return f"{Fore.LIGHTRED_EX}{text}{Style.RESET_ALL}"

    def cyan(self, text) -> str:
        return f"{Fore.CYAN}{Style.BRIGHT}{text}{Style.RESET_ALL}"

    def magenta(self, text) -> str:
        return f"{Fore.MAGENTA}{text}{Style.RESET_ALL}"