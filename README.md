# DA DP Holding Verification

This is a Python app designed for finding out whether files on a drive have already been ingested.
It consists of two files:

## 1. convert_checksum_csv_to_sqlite.py

Which, with the env variables: CHECKSUM_DB_NAME, CHECKSUM_TABLE_NAME and CSV_FILE_WITH_CHECKSUMS:

   1. Takes a CSV with the headings:
       1. FILEREF
       2. FIXITYVALUE
       3. ALGORITHMNAME
   2. Creates an SQLite Table
   3. Converts each CSV row into an SQLite row
   4. Creates an index with the fixity value

### Things you should know
This script is only necessary if you only have the CSV version of the DB, otherwise, skip to the 
holding_verification.py with the DB or generate a new DB with the headings mentioned in step 1

## 2. holding_verification.py

Which, with the env variables: CHECKSUM_DB_NAME, CHECKSUM_TABLE_NAME and CSV_FILE_WITH_CHECKSUMS:

   1. Fetches the file(s) that it's been pointed to
   2. For each file, generates a checksum hash (fixity value) on the content
   3. Looks for that checksum hash in the DB
      1. If not found, it will generate a checksum hash using another algorithm, if not found, it will generate a checksum hash using another algorithm 
         1. At most, it will generate 3 hashes: SHA256, SHA1 and MD5 and then give up
         2. If a file was found, the next file's checksum hash will be generated using the checksum hash algorithm 
            of the file that preceded it
      2. If found, it will return the file reference(s) associated with the checksum, fixity value, algorithm name 
         from the DB
   4. It will write the information obtained from the DB as well as the path, file size and `True` or `False` value 
      for whether the checksum was found

## 3. get_path_from_user.py

(called by 'holding_verification.py') Allows you to select 1 or more files or a folder, via GUI or (Command Line
Interface) CLI.

1. It will ask the use if they would like to use the GUI or CLI to select the file(s)/folder
2. If the user:
   1. Presses the "Enter" button, they will choose the GUI, a GUI appears with an option to:
      1. Select file(s) - button
         1. Clicking the button will open a dialog box where you can select 1 or more files
         2. Once selected, the window will close
      2. Select folder - button
         1. Clicking the button will open a dialog box where you can select a folder
         2. Once selected, the window will close
   2. Types `c` and the presses "Enter", they will choose the CLI, which will then give an option to:
      1. Type `f` for a single file (only one file supported at the moment) or `d` for a single directory?
      2. Once the user types either `f` or `d` and presses "Enter", they will be asked to add the full path to the
         file/folder
3. What you've selected will appear in the command line window and the processing of the file(s) will start

## Running holding_verification.py tests

The tests are located here `test/test_holding_verification.py`. In order to run the tests, run `python3 -m unittest` or
`python -m unittest` from the root folder. If running from PyCharm, you might have to change the "Working Directory" to the root folder,
as it might default to the `test` folder.

### Things you should know
1. Just because a checksum was matched, doesn't necessarily mean the file that is ingested had the same name
2. Files that encountered errors are printed at the end but will look normal in the CSV
