from pathlib import Path
from helpers.helper import ColourCliText

from holding_verification_core import HoldingVerificationCore, ResultSummary

colour_text = ColourCliText()
yellow = colour_text.yellow
red = colour_text.red
green = colour_text.green
magenta = colour_text.magenta
bright_cyan = colour_text.bright_cyan


class HoldingVerificationUi:
    def __init__(self, app: HoldingVerificationCore):
        self.app = app

    def prompt_use_gui(self, gui_or_cli_prompt=input) -> str:
        enter = yellow("Enter")
        return gui_or_cli_prompt(
            f"Press '{enter}' to use the GUI or type '{yellow("c")}' then '{enter}' for the CLI: "
        ).strip().lower()

    def run_verification(self, item_paths, selected_items):
        paths_as_string = ",\n  ".join(item_paths)
        paths_as_list = f"\n  {paths_as_string}" if len(paths_as_string) > 1 else paths_as_string
        print(f"""\n{yellow("You've selected")}: {paths_as_list}\n\t""")
        selected_items["paths"] = item_paths

        result_summary = self.app.start(selected_items)
        self.print_summary(result_summary)

    def open_select_window(self):
        from sys import platform
        import tkinter as tk  # Importing tkinter here because GitHub Actions can't import it & it's not needed for tests
        from tkinter.filedialog import askdirectory, askopenfilenames
        from tkinterdnd2 import DND_FILES, TkinterDnD
        select_window = TkinterDnD.Tk()  # notice - use this instead of tk.Tk()

        select_window.title("Holding Verification: Select Item")
        select_window.eval('tk::PlaceWindow . center')
        item_path = tuple()
        selected_items = {}
        windows_os = "win32"  # Windows 64-bit also falls under "win32"

        if platform == windows_os:
            window_dims = "565x490"
            button_text_colour = "white"
            file_button_x = 180
            folder_button_x = 300
            dnd_label_x = 130
            dnd_bg_colour = "white"
            dnd_confirm_button_x = 419
            dnd_confirm_button_y = 455

        else:
            window_dims = "500x450"
            button_text_colour = "black"
            file_button_x = 130
            folder_button_x = 250
            dnd_label_x = 80
            dnd_bg_colour = "grey"
            dnd_confirm_button_x = 319
            dnd_confirm_button_y = 405

        select_window.geometry(window_dims)
        file_and_folder_button_y = 50
        dnd_label_y = 100

        def clear_list_box():
            nonlocal confirmed_dropped_items
            confirmed_dropped_items = []
            list_box.delete(0, tk.END)
            confirm_dropped_items_button.config(bg='SystemButtonFace')
            confirm_dropped_items_button["state"] = "disabled"

        def file_callback() -> None:
            nonlocal item_path
            clear_list_box()

            item_path = askopenfilenames(parent=select_window, initialdir="", title='Select File(s)')
            if item_path != "":
                selected_items["are_directories"] = False
                self.run_verification(item_path, selected_items)

        def folder_callback() -> None:
            nonlocal item_path
            clear_list_box()

            folder_path = (askdirectory(parent=select_window, initialdir="", title='Select Folder'),)
            item_path = folder_path

            if item_path != ("",):
                selected_items["are_directories"] = True
                self.run_verification(item_path, selected_items)

        select_file_button = tk.Button(select_window, bg="blue", fg=button_text_colour, text="Select File(s)",
                                       command=file_callback)
        select_dir_button = tk.Button(select_window, bg="blue", fg=button_text_colour, text="Select Folder",
                                      command=folder_callback)
        select_file_button.place(x=file_button_x, y=file_and_folder_button_y)
        select_dir_button.place(x=folder_button_x, y=file_and_folder_button_y)

        dnd_label = tk.Label(select_window, text="...or drag and drop folders or files onto the box below")
        list_box = tk.Listbox(select_window, height=16, width=60, bg=dnd_bg_colour, activestyle="dotbox", font="Helvetica")
        # register the listbox as a drop target
        list_box.drop_target_register(DND_FILES)
        confirmed_dropped_items = []

        def get_items_and_run_verification_callback():
            nonlocal item_path
            item_path = tuple(confirmed_dropped_items)
            path = Path(confirmed_dropped_items[0])
            selected_items["are_directories"] = path.is_dir()

            if item_path != ("",):  # shouldn't be possible as button is disabled until an item is dropped
                self.run_verification(item_path, selected_items)

        def list_dropped_items_callback(drop_event: TkinterDnD.DnDEvent):
            nonlocal confirmed_dropped_items
            # remove all items that were there previously
            confirmed_dropped_items = []
            list_box.delete(0, tk.END)
            dropped_path_strings = drop_event.data.replace("{", "").replace("}", "")  # files with spaces get wrapped in {}

            if platform == windows_os:
                import re
                drive_and_path = re.split(r"([A-Z]:/)", dropped_path_strings)
                dropped_items = [drive_and_path[n] + drive_and_path[n + 1].rstrip()
                                 for n in range(1, len(drive_and_path), 2)]
            else:
                paths_with_safe_delimiter = dropped_path_strings.replace(" /", "<-DELIMITER->/")
                dropped_items = paths_with_safe_delimiter.split("<-DELIMITER->")

            item_types_dropped = set()  # user must drop either files or folders
            only_one_item_type_dropped = True

            for dropped_item_path in dropped_items:
                path = Path(dropped_item_path)
                is_directory = path.is_dir()
                item_types_dropped.add("folder") if is_directory else item_types_dropped.add("file")
                if len(item_types_dropped) > 1:
                    only_one_item_type_dropped = False
                    break

            if only_one_item_type_dropped:
                for dropped_item in dropped_items:
                    list_box.insert(tk.END, dropped_item)

            confirmed_dropped_items = dropped_items
            confirm_dropped_items_button["state"] = "active"

        list_box.dnd_bind('<<Drop>>', list_dropped_items_callback)
        dnd_label.place(x=dnd_label_x, y=dnd_label_y)
        list_box.place(x=10, y=140)

        confirm_dropped_items_button = tk.Button(
            select_window, text="Confirm dropped items", command=get_items_and_run_verification_callback
        )
        confirm_dropped_items_button["state"] = "disabled"
        confirm_dropped_items_button.place(x=dnd_confirm_button_x, y=dnd_confirm_button_y)

        select_window.wait_window()

        if len(item_path) == 0:
            self.app.connection.close()
            print(red("Application closed."))
            exit()  # User has closed the application window

        select_window.update_idletasks()  # Forces the window to close

    def cli_input(self):
        path_types = {"f": "file", "d": "directory"}
        selected_items = {}
        while True:
            file_or_dir = input("Would you like to look up a single file or directory? [f/d]: ").lower()
            if file_or_dir in path_types:
                path_type = path_types[file_or_dir]
                path_string = (input(f"Add the full {path_type} path here and press '{yellow("Enter")}': ")
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
                    selected_items["paths"] = (path_string,)
                    selected_items["are_directories"] = is_directory
                    break
            else:
                print(f"{file_or_dir} is not a valid option.")
                continue

        self.run_verification(selected_items["paths"], selected_items)

    def print_summary(self, summary: ResultSummary):
        print(f"\n{green("Completed.")}\n\n")
        file_or_files = "file was" if summary.files_processed == 1 else "files were"
        print(f"{bright_cyan(f"{summary.files_processed:,}")} {file_or_files} processed:")
        preserved = summary.tally.get(True)
        preserved_coloured = green(preserved) if preserved else magenta(preserved)
        print(f"""
        Files in Preservica/DRI: {preserved_coloured:}
        Files not in Preservica/DRI: {red(f"{summary.tally.get(False):}")}
        """)

        print(f"The full results can be found in a file called '{yellow(summary.output_csv_name)}'.\n")
        if summary.all_file_errors:
            print("These files encountered errors when trying to generate checksums:\n")
            for file_error in summary.all_file_errors:
                print(red(file_error))
