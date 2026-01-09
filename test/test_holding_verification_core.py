import configparser
from collections import defaultdict
from datetime import datetime
import os
from pathlib import Path
import unittest
from unittest.mock import Mock

from holding_verification_core import HoldingVerificationCore, check_db_exists


class TestHoldingVerification(unittest.TestCase):
    def setUp(self):
        self.test_file = os.path.normpath("test/test_files/testFile.txt")
        self.empty_test_file = os.path.normpath("test/test_files/emptyTestFile.txt")
        self.empty_test_db = os.path.normpath("test/test_files/test_checksums_of_files_in_dri.testdb")
        self.test_files_folder = os.path.normpath("test/test_files")

    config = configparser.ConfigParser()
    config.read("config.ini")
    table_name = config["DEFAULT"]["CHECKSUM_TABLE_NAME"]

    class HVWithMockedChecksumMethods(HoldingVerificationCore):
        def __init__(self, table_name,
                     checksum_in_db_return_vals: tuple[list[list[str]]] = (),
                     checksum_for_file_return_errors: tuple[dict[str, str]] = ({}, {}, {})):
            super().__init__(Mock(), table_name)

            self.checksum_for_file = {"sha256": "sha256Checksum123", "md5": "md5Checksum234", "sha1": "sha1Checksum345"}
            self.errors_when_getting_checksum_for_file = iter(checksum_for_file_return_errors)
            self.checksum_in_db = iter(checksum_in_db_return_vals)
            self.checksum_for_file_calls = 0
            self.checksum_in_db_calls = 0
            self.options = iter(["c", "f"])

        def get_checksum_for_file(self, file_path: str, hash_func) -> tuple[str, dict[str, str]]:
            self.checksum_for_file_calls += 1
            return self.checksum_for_file[hash_func.name], next(self.errors_when_getting_checksum_for_file)

        def find_checksum_in_db(self, file_hash: str) -> list[list[str]]:
            self.checksum_in_db_calls += 1
            return next(self.checksum_in_db)

    class HVWithMockedRowsWithHash(HoldingVerificationCore):
        def __init__(self, table_name, sha256_hash, rows_with_hash: list[list[str]], checksum_found: bool,
                     errors_generating_checksum: dict[str, str],
                     next_hash_name: str):
            super().__init__(Mock(), table_name)
            self.sha256_hash = sha256_hash
            self.rows_with_hash = rows_with_hash
            self.checksum_found = checksum_found
            self.errors_generating_checksum = errors_generating_checksum
            self.next_hash_name = next_hash_name

        def get_rows_with_hash(self, file_path: str, hash_name: str):
            return (self.sha256_hash, self.rows_with_hash, self.checksum_found, self.errors_generating_checksum,
                    self.next_hash_name)

    class HVWithMockedUserPromptCsvAndRunMethods(HoldingVerificationCore):
        def __init__(self, table_name, file_or_dir: dict[str, tuple[str] | bool], db_connection):
            super().__init__(db_connection, table_name)
            self.file_or_dir = file_or_dir
            self.csv_file = Mock()
            self.csv_file.close = Mock()
            self.csv_writer = Mock(object_type="csv_writer")
            self.output_csv_name = "INGESTED_FILES_in_testpath_19-01-2038-03_14_08_IN_PROGRESS.csv"
            self.final_output_csv_name = self.output_csv_name.replace("_IN_PROGRESS", "")
            self.get_csv_output_writer_and_file_name_args = Mock()
            self.run_args = Mock()
            self.print = Mock()

        def get_csv_output_writer_and_file_name(self, dir_path: Path,
                                                date: str = datetime.fromtimestamp(2147483648).strftime(
                                                    "%d-%m-%Y-%H_%M_%S")):
            self.get_csv_output_writer_and_file_name_args(dir_path, date)
            if self.output_csv_name == "non-existent_file.csv":
                pass
            elif Path(self.final_output_csv_name).exists():
                os.rename(self.final_output_csv_name, self.output_csv_name)
            else:
                with open(self.output_csv_name, "w") as csv_file:
                    csv_file.write("content")

            return self.csv_file, self.csv_writer, self.output_csv_name

        def run(self, path, file_hash_name, all_file_errors: list[dict[str, str]], csv_writer, tally):
            self.run_args(path, file_hash_name, all_file_errors, csv_writer, tally)
            return "sha256", [], {True: 1}

    def test_get_csv_output_writer_and_file_name_should_append_csv_prefix_to_csv_name(self):
        path = Path("test_files")
        mock_db_connection = Mock()
        csv_file, csv_writer, output_csv_name = HoldingVerificationCore(
            mock_db_connection, self.table_name, "csv_prefix").get_csv_output_writer_and_file_name(
            path, datetime.fromtimestamp(2147483648).strftime("%d-%m-%Y-%H_%M_%S")
        )
        csv_name = csv_file.name
        csv_file.close()

        expected_csv_file_name = "csv_prefix_INGESTED_FILES_in_test_files_19-01-2038-03_14_08_IN_PROGRESS.csv"
        os.remove(expected_csv_file_name)

    def test_get_csv_output_writer_and_file_name_should_return_expected_file_object_and_writer_and_name(self):
        path = Path("test_files")
        mock_db_connection = Mock()
        csv_file, csv_writer, output_csv_name = HoldingVerificationCore(
            mock_db_connection, self.table_name).get_csv_output_writer_and_file_name(
            path, datetime.fromtimestamp(2147483648).strftime("%d-%m-%Y-%H_%M_%S")
        )
        csv_name = csv_file.name
        csv_file.close()

        expected_csv_file_name = "INGESTED_FILES_in_test_files_19-01-2038-03_14_08_IN_PROGRESS.csv"
        self.assertEqual(expected_csv_file_name, csv_name)
        self.assertEqual(True, csv_writer.__str__().startswith("<_csv.writer object"))
        self.assertEqual(expected_csv_file_name, output_csv_name)
        self.assertEqual(os.path.exists(expected_csv_file_name), True)

    def test_get_checksum_for_file_should_not_call_update_if_file_has_no_bytes_to_read(self):
        mock_db_connection = Mock()
        hash_function = Mock()
        hash_function.update = Mock()
        hash_function.hexdigest = Mock(return_value="checksum")

        (file_hex, errors) = HoldingVerificationCore(mock_db_connection, self.table_name).get_checksum_for_file(
            self.empty_test_file, hash_function
        )

        hash_function.update.assert_not_called()
        self.assertEqual("checksum", file_hex)
        self.assertEqual({}, errors)

    def test_get_checksum_for_file_should_call_update_if_file_has_bytes_to_read(self):
        mock_db_connection = Mock()
        hash_function = Mock()
        hash_function.update = Mock()
        hash_function.hexdigest = Mock(return_value="checksum")

        (file_hex, errors) = HoldingVerificationCore(mock_db_connection, self.table_name).get_checksum_for_file(
            self.test_file, hash_function
        )

        self.assertEqual(1, hash_function.update.call_count)
        self.assertEqual("checksum", file_hex)
        self.assertEqual({}, errors)

    def test_get_checksum_for_file_should_return_an_os_error_if_thrown(self):
        mock_db_connection = Mock()
        hash_function = Mock()
        hash_function.update = Mock(side_effect=OSError("OS Error thrown"))
        hash_function.hexdigest = Mock(return_value="checksum")

        (file_hex, errors) = HoldingVerificationCore(mock_db_connection, self.table_name).get_checksum_for_file(
            self.test_file, hash_function
        )

        self.assertEqual(1, hash_function.update.call_count)
        self.assertEqual(0, hash_function.hexdigest.call_count)
        self.assertEqual("", file_hex)
        self.assertEqual({self.test_file: "OS Error thrown"}, errors)

    def test_find_checksum_in_db_should_use_correct_sql_query_and_return_list_of_results(self):
        cursor = Mock()
        cursor.execute = Mock()
        cursor.fetchall = Mock(return_value=["result1", "result2"])
        mock_db_connection = Mock()
        mock_db_connection.cursor = Mock(return_value=cursor)

        response = HoldingVerificationCore(mock_db_connection, self.table_name).find_checksum_in_db("mock_hash")
        cursor.execute.assert_called_with(
            """SELECT file_ref, fixity_value, algorithm_name FROM files_in_dri WHERE "fixity_value" = "mock_hash";""")
        self.assertEqual(["result1", "result2"], response)

    def test_get_rows_with_hash_should_call_other_methods_1X_if_it_starts_with_sha256_and_sha256_checksum_found(self):
        mock_holding_verification = self.HVWithMockedChecksumMethods(
            self.table_name, ([["1", "sha256Checksum123", "sha256"]],)
        )
        (sha256_hash, rows_with_hash, checksum_found, errors, next_hash_name) = mock_holding_verification.get_rows_with_hash(
            self.test_file, "sha256"
        )

        self.assertEqual("sha256Checksum123", sha256_hash)
        self.assertEqual([["1", "sha256Checksum123", "sha256"]], rows_with_hash)
        self.assertEqual(True, checksum_found)
        self.assertEqual({}, errors)
        self.assertEqual("sha256", next_hash_name)

        self.assertEqual(1, mock_holding_verification.checksum_for_file_calls)
        self.assertEqual(1, mock_holding_verification.checksum_in_db_calls)

    def test_get_rows_with_hash_should_call_other_methods_2X_if_it_starts_with_sha256_but_md5_checksum_found(self):

        mock_holding_verification = self.HVWithMockedChecksumMethods(
            self.table_name, ([], [["2", "md5Checksum234", "md5"]], [])
        )
        (sha256_hash, rows_with_hash, checksum_found, errors, next_hash_name) = mock_holding_verification.get_rows_with_hash(
            self.test_file, "sha256"
        )

        self.assertEqual("sha256Checksum123", sha256_hash)
        self.assertEqual([["2", "md5Checksum234", "md5"]], rows_with_hash)
        self.assertEqual(True, checksum_found)
        self.assertEqual({}, errors)
        self.assertEqual("md5", next_hash_name)

        self.assertEqual(2, mock_holding_verification.checksum_for_file_calls)
        self.assertEqual(2, mock_holding_verification.checksum_in_db_calls)

    def test_get_rows_with_hash_should_call_other_methods_3X_if_it_starts_with_sha256_but_sha1_checksum_found(self):

        mock_holding_verification = self.HVWithMockedChecksumMethods(
            self.table_name, ([], [], [["3", "sha1Checksum345", "sha1"]])
        )
        (sha256_hash, rows_with_hash, checksum_found, errors, next_hash_name) = mock_holding_verification.get_rows_with_hash(
            self.test_file, "sha256"
        )

        self.assertEqual("sha256Checksum123", sha256_hash)
        self.assertEqual([["3", "sha1Checksum345", "sha1"]], rows_with_hash)
        self.assertEqual(True, checksum_found)
        self.assertEqual({}, errors)
        self.assertEqual("sha1", next_hash_name)

        self.assertEqual(3, mock_holding_verification.checksum_for_file_calls)
        self.assertEqual(3, mock_holding_verification.checksum_in_db_calls)

    def test_get_rows_with_hash_should_call_other_methods_3X_if_it_starts_with_sha256_but_no_checksum_found(self):
        mock_holding_verification = self.HVWithMockedChecksumMethods(
            self.table_name, ([], [], [])
        )
        (sha256_hash, rows_with_hash, checksum_found, errors, next_hash_name) = mock_holding_verification.get_rows_with_hash(
            self.test_file, "sha256"
        )

        self.assertEqual("sha256Checksum123", sha256_hash)
        self.assertEqual([], rows_with_hash)
        self.assertEqual(False, checksum_found)
        self.assertEqual({}, errors)
        self.assertEqual("", next_hash_name)

        self.assertEqual(3, mock_holding_verification.checksum_for_file_calls)
        self.assertEqual(3, mock_holding_verification.checksum_in_db_calls)

    def test_get_rows_with_hash_should_call_other_methods_1X_if_it_starts_with_md5_and_md5_checksum_found(self):
        mock_holding_verification = self.HVWithMockedChecksumMethods(
            self.table_name, ([["2", "md5Checksum234", "md5"]],)
        )
        (sha256_hash, rows_with_hash, checksum_found, errors, next_hash_name) = mock_holding_verification.get_rows_with_hash(
            self.test_file, "md5"
        )

        self.assertEqual("sha256Checksum123", sha256_hash)
        self.assertEqual([["2", "md5Checksum234", "md5"]], rows_with_hash)
        self.assertEqual(True, checksum_found)
        self.assertEqual({}, errors)
        self.assertEqual("md5", next_hash_name)

        self.assertEqual(2, mock_holding_verification.checksum_for_file_calls)
        self.assertEqual(1, mock_holding_verification.checksum_in_db_calls)

    def test_get_rows_with_hash_should_call_other_methods_2X_if_it_starts_with_md5_but_sha256_checksum_found(self):
        mock_holding_verification = self.HVWithMockedChecksumMethods(
            self.table_name, ([], [["1", "sha256Checksum123", "sha256"]])
        )
        (sha256_hash, rows_with_hash, checksum_found, errors, next_hash_name) = mock_holding_verification.get_rows_with_hash(
            self.test_file, "md5"
        )

        self.assertEqual("sha256Checksum123", sha256_hash)
        self.assertEqual([["1", "sha256Checksum123", "sha256"]], rows_with_hash)
        self.assertEqual(True, checksum_found)
        self.assertEqual({}, errors)
        self.assertEqual("sha256", next_hash_name)

        self.assertEqual(2, mock_holding_verification.checksum_for_file_calls)
        self.assertEqual(2, mock_holding_verification.checksum_in_db_calls)

    def test_get_rows_with_hash_should_call_other_methods_3X_if_it_starts_with_md5_but_sha1_checksum_found(self):
        mock_holding_verification = self.HVWithMockedChecksumMethods(
            self.table_name, ([], [], [["3", "sha1Checksum345", "sha1"]])
        )
        (sha256_hash, rows_with_hash, checksum_found, errors, next_hash_name) =  mock_holding_verification.get_rows_with_hash(
            self.test_file, "md5"
        )

        self.assertEqual("sha256Checksum123", sha256_hash)
        self.assertEqual([["3", "sha1Checksum345", "sha1"]], rows_with_hash)
        self.assertEqual(True, checksum_found)
        self.assertEqual({}, errors)
        self.assertEqual("sha1", next_hash_name)

        self.assertEqual(3, mock_holding_verification.checksum_for_file_calls)
        self.assertEqual(3, mock_holding_verification.checksum_in_db_calls)

    def test_get_rows_with_hash_should_call_other_methods_3X_if_it_starts_with_md5_but_no_checksum_found(self):
        mock_holding_verification = self.HVWithMockedChecksumMethods(
            self.table_name, ([], [], [])
        )
        (sha256_hash, rows_with_hash, checksum_found, errors, next_hash_name) = mock_holding_verification.get_rows_with_hash(
            self.test_file, "md5"
        )

        self.assertEqual("sha256Checksum123", sha256_hash)
        self.assertEqual([], rows_with_hash)
        self.assertEqual(False, checksum_found)
        self.assertEqual({}, errors)
        self.assertEqual("", next_hash_name)

        self.assertEqual(3, mock_holding_verification.checksum_for_file_calls)
        self.assertEqual(3, mock_holding_verification.checksum_in_db_calls)

    def test_get_rows_with_hash_should_call_other_methods_1X_if_it_starts_with_sha1_and_sha1_checksum_found(self):
        mock_holding_verification = self.HVWithMockedChecksumMethods(
            self.table_name, ([["3", "sha1Checksum345", "sha1"]],)
        )
        (sha256_hash, rows_with_hash, checksum_found, errors, next_hash_name) = mock_holding_verification.get_rows_with_hash(
            self.test_file, "sha1"
        )

        self.assertEqual("sha256Checksum123", sha256_hash)
        self.assertEqual([["3", "sha1Checksum345", "sha1"]], rows_with_hash)
        self.assertEqual(True, checksum_found)
        self.assertEqual({}, errors)
        self.assertEqual("sha1", next_hash_name)

        self.assertEqual(2, mock_holding_verification.checksum_for_file_calls)
        self.assertEqual(1, mock_holding_verification.checksum_in_db_calls)

    def test_get_rows_with_hash_should_call_other_methods_2X_if_it_starts_with_sha1_but_sha256_checksum_found(self):
        mock_holding_verification = self.HVWithMockedChecksumMethods(
            self.table_name, ([], [["1", "sha256Checksum123", "sha256"]])
        )
        (sha256_hash, rows_with_hash, checksum_found, errors, next_hash_name) = mock_holding_verification.get_rows_with_hash(
            self.test_file, "sha1"
        )

        self.assertEqual("sha256Checksum123", sha256_hash)
        self.assertEqual([["1", "sha256Checksum123", "sha256"]], rows_with_hash)
        self.assertEqual(True, checksum_found)
        self.assertEqual({}, errors)
        self.assertEqual("sha256", next_hash_name)

        self.assertEqual(2, mock_holding_verification.checksum_for_file_calls)
        self.assertEqual(2, mock_holding_verification.checksum_in_db_calls)

    def test_get_rows_with_hash_should_call_other_methods_3X_if_it_starts_with_sha1_but_md5_checksum_found(self):
        mock_holding_verification = self.HVWithMockedChecksumMethods(
            self.table_name, ([], [], [["2", "md5Checksum234", "md5"]])
        )
        (sha256_hash, rows_with_hash, checksum_found, errors, next_hash_name) = mock_holding_verification.get_rows_with_hash(
            self.test_file, "sha1"
        )

        self.assertEqual("sha256Checksum123", sha256_hash)
        self.assertEqual([["2", "md5Checksum234", "md5"]], rows_with_hash)
        self.assertEqual(True, checksum_found)
        self.assertEqual({}, errors)
        self.assertEqual("md5", next_hash_name)

        self.assertEqual(3, mock_holding_verification.checksum_for_file_calls)
        self.assertEqual(3, mock_holding_verification.checksum_in_db_calls)

    def test_get_rows_with_hash_should_call_other_methods_3X_if_it_starts_with_sha1_but_no_checksum_found(self):
        mock_holding_verification = self.HVWithMockedChecksumMethods(
            self.table_name, ([], [], [])
        )
        (sha256_hash, rows_with_hash, checksum_found, errors, next_hash_name) = mock_holding_verification.get_rows_with_hash(
            self.test_file, "sha1"
        )

        self.assertEqual("sha256Checksum123", sha256_hash)
        self.assertEqual([], rows_with_hash)
        self.assertEqual(False, checksum_found)
        self.assertEqual({}, errors)
        self.assertEqual("", next_hash_name)

        self.assertEqual(3, mock_holding_verification.checksum_for_file_calls)
        self.assertEqual(3, mock_holding_verification.checksum_in_db_calls)

    def test_run_should_write_the_correct_info_to_the_csv_if_checksum_found_and_return_a_tally(self):
        csv_writer = Mock()
        csv_writer.writerow = Mock()
        mock_holding_verification = self.HVWithMockedRowsWithHash(self.table_name, "sha256Checksum123",
            [["1", "sha256Checksum123", "sha256"], ["10", "sha256Checksum123", "sha256"]],
            True, dict(), "sha256"
        )
        (starting_hash_name_for_next_file, all_file_errors, tally) = mock_holding_verification.run(
            self.test_file, "sha256", [], csv_writer, defaultdict(int)
        )
        self.assertEqual("sha256", starting_hash_name_for_next_file)
        self.assertEqual([], all_file_errors)
        self.assertEqual({True: 1}, tally)
        (args, _) = csv_writer.writerow.call_args
        self.assertEqual(((self.test_file, 19, True, "sha256Checksum123", "1, 10", "sha256", "sha256Checksum123"),), args)

    def test_run_should_write_the_correct_info_to_the_csv_if_checksum_not_found_and_return_a_tally(self):
        csv_writer = Mock()
        csv_writer.writerow = Mock()
        mock_holding_verification = self.HVWithMockedRowsWithHash(self.table_name, "sha256Checksum123",
            [], False, dict(), ""
        )
        (starting_hash_name_for_next_file, all_file_errors, tally) = mock_holding_verification.run(
            self.test_file, "sha256", [], csv_writer, defaultdict(int)
        )
        self.assertEqual("sha256", starting_hash_name_for_next_file)
        self.assertEqual([], all_file_errors)
        self.assertEqual({False: 1}, tally)
        (args, _) = csv_writer.writerow.call_args
        self.assertEqual(((self.test_file, 19, False, "sha256Checksum123", "", "", ""),), args)

    def test_run_should_write_the_correct_info_to_the_csv_if_error_was_thrown_when_getting_checksum_and_return_a_tally(
        self):
        csv_writer = Mock()
        csv_writer.writerow = Mock()
        mock_holding_verification = self.HVWithMockedRowsWithHash(self.table_name, "sha256Checksum123",
            [], False, {self.test_file: "OS Error thrown"}, ""
        )
        (starting_hash_name_for_next_file, all_file_errors, tally) = mock_holding_verification.run(
            self.test_file, "sha256", [], csv_writer, defaultdict(int)
        )
        self.assertEqual("sha256", starting_hash_name_for_next_file)
        self.assertEqual([{self.test_file: "OS Error thrown"}], all_file_errors)
        self.assertEqual({False: 1}, tally)
        (args, _) = csv_writer.writerow.call_args
        self.assertEqual(((self.test_file, 19, False, "sha256Checksum123", "", "", ""),), args)

    def test_check_db_exists_should_prompt_the_user_if_db_does_not_exist(self):
        db_file_name = "non_existent_db_file_name"
        confirm_prompt = Mock()
        confirm_prompt.side_effect = ["", "", False]
        check_db_exists(db_file_name, confirm_prompt)

        confirm_prompt_input_args = confirm_prompt.call_args_list
        self.assertEqual(3, confirm_prompt.call_count)
        self.assertEqual(
            True,
            all("'non_existent_db_file_name' is missing from the directory '" in input_arg[0][0] for input_arg in
                confirm_prompt_input_args
                )
        )

    def test_start_should_call_run_method_2x_and_other_methods_once_with_correct_args_if_2_files_have_been_passed_in(
        self):
        db_connection = Mock()
        db_connection.commit = Mock()
        db_connection.close = Mock()
        mock_holding_verification = self.HVWithMockedUserPromptCsvAndRunMethods(self.table_name,
            {"path": (self.test_file, self.empty_test_file), "is_directory": False},
            db_connection
        )

        mock_holding_verification.start(mock_holding_verification.file_or_dir)

        self.assertEqual(1, mock_holding_verification.get_csv_output_writer_and_file_name_args.call_count)
        ((path_arg, date_arg), _) = mock_holding_verification.get_csv_output_writer_and_file_name_args.call_args
        self.assertEqual(True, path_arg.match(self.test_files_folder))
        self.assertEqual("19-01-2038-03_14_08", date_arg)

        self.assertEqual(2, mock_holding_verification.run_args.call_count)
        actual_and_expected_args = zip(
            mock_holding_verification.run_args.call_args_list,
            ((self.test_file, {}), (self.empty_test_file, {True: 1}))
        )
        for (run_args, _), (expected_file_path, expected_tally) in actual_and_expected_args:
            first_3_run_args = run_args[0: 3]
            csv_writer_run_args = run_args[3]
            tally = run_args[4]

            self.assertEqual((expected_file_path, "sha256", []), first_3_run_args)
            self.assertEqual("csv_writer", csv_writer_run_args.object_type)
            self.assertEqual(expected_tally, tally)

        self.assertEqual(1, mock_holding_verification.csv_file.close.call_count)
        self.assertEqual(1, db_connection.cursor.call_count)

        files_in_current_dir = os.listdir()
        self.assertEqual(False, mock_holding_verification.output_csv_name in files_in_current_dir)
        self.assertEqual(True, "INGESTED_FILES_in_testpath_19-01-2038-03_14_08.csv" in files_in_current_dir)

    def test_start_should_call_run_method_3x_and_other_methods_once_with_correct_args_if_a_folder_with_3_files_have_been_passed_in(
        self):
        db_connection = Mock()
        db_connection.commit = Mock()
        db_connection.close = Mock()
        mock_holding_verification = self.HVWithMockedUserPromptCsvAndRunMethods(self.table_name,
            {"path": (self.test_files_folder,), "is_directory": True}, db_connection
        )

        mock_holding_verification.start(mock_holding_verification.file_or_dir)

        self.assertEqual(1, mock_holding_verification.get_csv_output_writer_and_file_name_args.call_count)
        ((path_arg, date_arg), _) = mock_holding_verification.get_csv_output_writer_and_file_name_args.call_args
        self.assertEqual(True, Path(path_arg).match(self.test_files_folder))
        self.assertEqual("19-01-2038-03_14_08", date_arg)

        self.assertEqual(3, mock_holding_verification.run_args.call_count)
        actual_and_expected_args = zip(
            sorted(mock_holding_verification.run_args.call_args_list),
            ((self.empty_test_file, {}), (self.test_file, {True: 1}), (self.empty_test_db, {True: 1}))
        )
        for (run_args, _), (expected_file_path, expected_tally) in actual_and_expected_args:
            path_arg = run_args[0]
            hash_name_and_all_errors = run_args[1: 3]
            csv_writer_run_args = run_args[3]
            tally = run_args[4]
            self.assertEqual(True, Path(path_arg).match(f"*{expected_file_path}"))
            self.assertEqual(("sha256", []), hash_name_and_all_errors)
            self.assertEqual("csv_writer", csv_writer_run_args.object_type)
            self.assertEqual(expected_tally, tally)

        self.assertEqual(1, mock_holding_verification.csv_file.close.call_count)
        self.assertEqual(1, db_connection.cursor.call_count)

        files_in_current_dir = os.listdir()
        self.assertEqual(False, mock_holding_verification.output_csv_name in files_in_current_dir)
        self.assertEqual(True, "INGESTED_FILES_in_testpath_19-01-2038-03_14_08.csv" in files_in_current_dir)


    def test_start_should_print_a_message_letting_users_know_that_processing_is_completed_but_file_not_renamed(self):
        db_connection = Mock()
        db_connection.commit = Mock()
        db_connection.close = Mock()
        mock_holding_verification = self.HVWithMockedUserPromptCsvAndRunMethods(self.table_name, {"path": (
            self.test_file, self.empty_test_file), "is_directory": False}, db_connection)
        mock_holding_verification.output_csv_name = "non-existent_file.csv"
        mock_holding_verification.start(mock_holding_verification.file_or_dir)
        self.assertIn(
            "WARNING: Processing completed but was unable to remove '_IN_PROGRESS' from the CSV file name, due to this error:",
            mock_holding_verification.print.call_args_list[0].args[0]
        )

if __name__ == "__main__":
    unittest.main()
