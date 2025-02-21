from pathlib import Path
from colorama import Fore
from colorama import Style

class GetPathFromUser:
    def open_select_window(self) -> dict[str, tuple[str] | bool]:
        import tkinter as tk # Importing tkinter here because GitHub Actions can't import it & it's not needed for tests
        from tkinter.filedialog import askdirectory, askopenfilenames
        select_window = tk.Tk()
        select_window.title("Holding Verification: Select Item")
        select_window.geometry("500x200")
        select_window.eval('tk::PlaceWindow . center')
        item_path = tuple()
        result = {}

        def file_callback() -> None:
            nonlocal item_path

            item_path = askopenfilenames(parent=select_window, initialdir="", title='Select File(s)')
            if item_path != "":
                result["is_directory"] = False
                select_window.destroy()

        def folder_callback() -> None:
            nonlocal item_path
            folder_path = (askdirectory(parent=select_window, initialdir="", title='Select Folder'),)
            item_path = folder_path

            if item_path != ("",):
                result["is_directory"] = True
                select_window.destroy()

        select_file_button = tk.Button(select_window, text="Select File(s)", command=file_callback)
        select_dir_button = tk.Button(select_window, text="Select Folder", command=folder_callback)
        select_file_button.place(x=130, y=50)
        select_dir_button.place(x=250, y=50)

        select_window.wait_window()
        select_window.update_idletasks()  # Forces the window to close

        if len(item_path) == 0:
            print(f"{Fore.RED}Application closed.{Style.RESET_ALL}")
            exit()  # User has closed the application window

        paths_as_string = ",\n  ".join(item_path)
        paths_as_list = f"\n  {paths_as_string}" if len(paths_as_string) > 1 else paths_as_string
        print(f"""\n{Fore.YELLOW}You've selected{Style.RESET_ALL}: {paths_as_list}\n\t""")
        result["path"] = item_path
        return result


    def cli_input(self) -> dict[str, tuple[str] | bool]:
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
            else:
                print(f"{file_or_dir} is not a valid option.")
                continue
        return result