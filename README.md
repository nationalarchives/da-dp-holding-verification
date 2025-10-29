# DA DP Holding Verification (AKA Checkmate)

This is a Python app designed for finding out whether files on a drive have already been ingested.

## For Users - How to run and use the app:
1. Go to the [Releases page](https://github.com/nationalarchives/da-dp-holding-verification/releases)
2. Under the latest release, click on the `da-holding-verification-windows-64.zip` link to download the app
3. It should open up a "Save" prompt; save it to your computer
4. Locate the `.zip` file in your file explorer and extract the contents from it
5. You should now see a folder named `holding_verification`
6. Copy the `checksums_of_files_in_dri.db` database file to the folder
7. Go inside the `holding_verification` folder and double-click the `holding_verification.exe` file to start the app
8. Click [here](#3-get_path_from_userpy) for guidance on how to use the app

## For Devs - The project:

This app consists of 3 files:

### 1. convert_checksum_csv_to_sqlite.py

A "config.ini" file can be found at the root of this project that contains the environment variables that this script
needs:

1. CHECKSUM_DB_NAME
2. CHECKSUM_TABLE_NAME
3. CSV_FILEREF_COLUMN
4. CSV_FIXITYVALUE_COLUMN
5. CSV_ALGORITHMNAME_COLUMN

These all have defaults that can be modified as needed.

#### Running the script

   1. In order to run the script, run `python convert_checksum_csv_to_sqlite.py` or `python3 
   convert_checksum_csv_to_sqlite.py`
   2. It will request the full path to the CSV file that is to be converted to a DB
      - the CSV must contain the headings defined in the config.ini file
   3. Creates an SQLite table
   4. Converts each CSV row into an SQLite row
   5. Creates an index with the fixity value
   6. Outputs the `.db` file to the root of this project

#### Things you should know
This script is only necessary if you only have the CSV version of the DB, otherwise, skip to the 
holding_verification.py with the DB or generate a new DB with the headings mentioned in step 1

### 2. holding_verification_core.py

Which, with the env variables: CHECKSUM_DB_NAME, CHECKSUM_TABLE_NAME and CSV_FILE_WITH_CHECKSUMS:

   1. Allows you to select 1 or more files or a folder, via GUI or CLI
   2. Opens each file and generates a checksum hash (fixity value) on the content
   3. Looks for that checksum hash in the DB
      1. If not found, it will generate a checksum hash using another algorithm, if not found, it will generate a checksum hash using another algorithm 
         1. At most, it will generate 3 hashes: SHA256, SHA1 and MD5 and then give up
         2. If a file was found, the next file's checksum hash will be generated using the checksum hash algorithm 
            of the file that preceded it
      2. If found, it will return the file reference(s) associated with the checksum, fixity value, algorithm name 
         from the DB
   4. It will write the information obtained from the DB as well as the path, file size and `True` or `False` value 
      for whether the checksum was found

### 3. holding_verification_ui.py

(called by 'holding_verification_core.py') Allows you to select 1 or more files or a folder, via GUI or (Command Line
Interface) CLI.

1. It will ask the user if they would like to use the GUI or CLI to select the file(s)/folder
2. If the user:
   1. Presses the "Enter" button, they will choose the GUI, a GUI appears with an option to:
      1. Select file(s) - button
         1. Clicking the button will open a dialog box where you can select 1 or more files
         2. Once selected, the window will close
      2. Select folder - button
         1. Clicking the button will open a dialog box where you can select a folder
         2. Once selected, the window will close
      3. Drag and Drop either file(s) or a folder (but not both types) - empty box
          1. Drag and drop 1 or more files or a single folder from your file explorer onto the box area
          2. What you've dropped should be displayed on the box
          3. Note: There is no ability to remove particular items; if you would like to remove the items dropped, you'd
             have to drop new items or close the app
          4. Once you're happy with your selection, press the "confirm" button to confirm that these files/folder should be
             validated
   2. Types `c` and then presses "Enter", the CLI option will be selected, which will then give an option to:
      1. Type `f` for a single file (only one file supported at the moment) or `d` for a single directory
      2. Once the user types either `f` or `d` and presses "Enter", they will be asked to add the full path to the
         file/folder
3. What you've selected will appear in the command line window and the processing of the file(s) will start
4. The GUI will remain open until you close it and the CLI will remain open until you enter "q" and press "Enter"
5. Whilst processing, "IN_PROGRESS" will be appended to the output CSV's name and then removed at the end; this is
   so that if the app stops running, for whatever reason, the user will know whether it completed or not

### Running holding_verification_core.py tests

The tests are located here `test/test_holding_verification_core.py`. In order to run the tests, run `python3 -m unittest` or
`python -m unittest` from the root folder. If running from PyCharm, you might have to change the "Working Directory" to the root folder,
as it might default to the `test` folder.

### Things you should know
1. You'd need to run this project with Python 3.12 or higher
2. Just because a checksum was matched, doesn't necessarily mean the file that is ingested had the same name
3. Files that encountered errors are printed at the end but will look normal in the CSV
4. The holding_verification.py is transformed into a .exe via GitHub Actions (check build.yml file) and added to the
 releases page so that there is no need to install Python on Windows
