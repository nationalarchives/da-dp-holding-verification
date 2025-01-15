# DA Holding Verification

This is a Pythpn app designed for finding out whether files on a drive have already been ingested.
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

   1. Allows you to select 1 or more files or a folder, via GUI or CLI
   2. Opens each file and generates a checksum hash (fixity value) on the content
   3. Looks for that checkum hash in the DB
      1. If not found, it will generate a checksum hash using another algorithm, if not found, it will generate a checksum hash using another algorithm 
         1. At most, it will generate 3 hashes: SHA256, SHA1 and MD5 and then give up
         2. If a file was found, the next file's checksum hash will be generated using the checksum hash algorithm 
            of the file that preceded it
      2. If found, it will return the file reference(s) associated with the checksum, fixity value, algorithm name 
         from the DB
   4. It will write the information obtained from the DB as well as the path, file size and `True` or `False` value 
      for whether the checksum was found

### Things you should know
1. Just because a checksum was matched doesn't necessarily mean the file that is ingested had the same name
2. Files that encountered errors are printed at the end but will look normal in the CSV
