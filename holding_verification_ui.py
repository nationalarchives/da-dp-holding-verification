import configparser
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
        self.app.csv_file_name_prefix = self.app.csv_file_name_prefix.strip().replace(" ", "_")
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
        config = configparser.ConfigParser()
        config.read("config.ini")
        default_config = config["DEFAULT"]

        select_window.title("CheckMate: Select Item")
        select_window.eval('tk::PlaceWindow . center')
        item_path = tuple()
        selected_items = {}
        windows_os = "win32"  # Windows 64-bit also falls under "win32"

        if platform == windows_os:
            content_width = 560
            window_dims = "565x510"
            box_bg_colour = "white"
            box_text_colour = "black"
            line_colour = "gray"
            button_text_colour = "white"
            file_button_x = 180
            folder_button_x = 300
            dnd_label_x = 130
            dnd_bg_colour = box_bg_colour
            dnd_confirm_button_x = 419
            dnd_confirm_button_y = 475
            version_label_x = 8
            version_label_y = 475

        else:
            content_width = 495
            window_dims = f"500x470"
            box_bg_colour = "grey"
            box_text_colour = "white"
            line_colour = "white"
            button_text_colour = "black"
            file_button_x = 130
            folder_button_x = 250
            dnd_label_x = 80
            dnd_bg_colour = box_bg_colour
            dnd_confirm_button_x = 319
            dnd_confirm_button_y = 425
            version_label_x = 8
            version_label_y = 425

        select_window.geometry(window_dims)
        file_and_folder_label_y = 70
        file_and_folder_button_y = file_and_folder_label_y + 25
        dnd_label_y = file_and_folder_button_y + 35

        def set_prepended_csv_title():
            self.app.csv_file_name_prefix = prepend_title_box.get("1.0", tk.END)

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
                set_prepended_csv_title()
                self.run_verification(item_path, selected_items)

        def folder_callback() -> None:
            nonlocal item_path
            clear_list_box()

            folder_path = (askdirectory(parent=select_window, initialdir="", title='Select Folder'),)
            item_path = folder_path

            if item_path != ("",):
                selected_items["are_directories"] = True
                set_prepended_csv_title()
                self.run_verification(item_path, selected_items)

        prepend_title_label = tk.Label(select_window, text="Title to be prepended to the CSV results' file name:")
        prepend_title_label.place(x=9, y=5)

        prepend_title_box = tk.Text(select_window, height=1.3, width=37, fg=box_text_colour, bg=box_bg_colour)
        prepend_title_box.place(x=13, y=30)
        csv_name_text = tk.Label(select_window, text="_INGESTED_FILES_in_{folder}.csv")
        csv_name_text.place(x=276, y=30)
        canvas = tk.Canvas(select_window, width=content_width, height=1)
        canvas.place(x=0, y=59)
        canvas.create_line(0, 0, content_width, 200, fill=line_colour, width=content_width, dash=5)

        file_and_folder_label = tk.Label(
            select_window,
            text="Select a file(s)/folder(s) in order to confirm that they are in database:"
        )
        file_and_folder_label.place(x=13, y=file_and_folder_label_y)

        select_file_button = tk.Button(select_window, bg="DodgerBlue", fg=button_text_colour, text="Select File(s)",
                                       command=file_callback)
        select_dir_button = tk.Button(select_window, bg="DodgerBlue", fg=button_text_colour, text="Select Folder",
                                      command=folder_callback)
        select_file_button.place(x=file_button_x, y=file_and_folder_button_y)
        select_dir_button.place(x=folder_button_x, y=file_and_folder_button_y)

        dnd_label = tk.Label(select_window, text="...or drag and drop folders or files onto the box below")
        list_box = tk.Listbox(select_window, height=16, width=60, bg=dnd_bg_colour, activestyle="dotbox", font="Helvetica")
        # register the listbox as a drop target
        list_box.drop_target_register(DND_FILES)
        version_label = tk.Label(select_window, text=f"v{default_config["APP_VERSION"]}")
        confirmed_dropped_items = []

        def get_items_and_run_verification_callback():
            nonlocal item_path
            item_path = tuple(confirmed_dropped_items)
            path = Path(confirmed_dropped_items[0])
            selected_items["are_directories"] = path.is_dir()

            if item_path != ("",):  # shouldn't be possible as button is disabled until an item is dropped
                set_prepended_csv_title()
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
        list_box.place(x=10, y=160)

        confirm_dropped_items_button = tk.Button(
            select_window, text="Confirm dropped items", command=get_items_and_run_verification_callback
        )
        confirm_dropped_items_button["state"] = "disabled"
        confirm_dropped_items_button.place(x=dnd_confirm_button_x, y=dnd_confirm_button_y)

        version_label.place(x=version_label_x, y=version_label_y)

        select_window.wait_window()

        if len(item_path) == 0:
            self.app.connection.close()
            print(red("Application closed."))
            exit()  # User has closed the application window

        select_window.update_idletasks()  # Forces the window to close

    def cli_input(self):
        enter = yellow("Enter")
        path_types = {"f": "file", "d": "directory"}
        selected_items = {}
        self.app.csv_file_name_prefix = input(
            f"Add a title to be prepended to the CSV result's file name then '{enter}' or just press '{enter}' to skip: "
        )
        while True:
            file_or_dir = input("\nWould you like to look up a single file or directory? [f/d]: ").lower()
            if file_or_dir in path_types:
                path_type = path_types[file_or_dir]
                path_string = (input(f"Add the full {path_type} path here and press '{enter}': ")
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
