import os
import unittest
from unittest import mock

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
os.environ["MULTILEVEL_UNZIPPER_SETTINGS_FILE"] = os.path.join(
    REPO_ROOT, "mlunzipper_test_settings.json"
)
os.environ["MULTILEVEL_UNZIPPER_READONLY_SETTINGS"] = "1"

import unzipper


class TestUnzipperHelpers(unittest.TestCase):
    def test_build_extract_args_7zip(self):
        args = unzipper.build_extract_args(
            "7z.exe", "archive.zip", "outdir", use_bandizip=False
        )
        self.assertEqual(args, ["7z.exe", "x", "-ooutdir", "archive.zip"])

    def test_build_extract_args_bandizip_with_password(self):
        args = unzipper.build_extract_args(
            "bz.exe", "archive.zip", "outdir", password="pass", use_bandizip=True
        )
        self.assertEqual(
            args, ["bz.exe", "x", "-ppass", "-o:outdir", "archive.zip"]
        )

    def test_is_non_primary_multipart(self):
        self.assertTrue(unzipper._is_non_primary_multipart("file.part02.rar"))
        self.assertFalse(unzipper._is_non_primary_multipart("file.part01.rar"))
        self.assertTrue(unzipper._is_non_primary_multipart("file.r00"))
        self.assertTrue(unzipper._is_non_primary_multipart("file.z01"))
        self.assertFalse(unzipper._is_non_primary_multipart("file.001"))
        self.assertTrue(unzipper._is_non_primary_multipart("file.002"))
        self.assertFalse(unzipper._is_non_primary_multipart("file.7z.001"))
        self.assertTrue(unzipper._is_non_primary_multipart("file.7z.003"))

    def test_get_passwords_from_filename(self):
        passwords = unzipper.get_passwords_from_filename("file_pass123.zip", "_")
        self.assertEqual(passwords, ["pass123", "pass123.zip"])

    def test_get_passwords_from_filename_custom_separator(self):
        passwords = unzipper.get_passwords_from_filename("file-pass-word.zip", "-")
        self.assertEqual(
            passwords,
            ["pass-word", "pass-word.zip", "word", "word.zip"],
        )

    def test_remove_archive_deletes_all_parts(self):
        files = [
            "sample.part01.rar",
            "sample.part02.rar",
            "sample.rar",
            "sample.r00",
            "sample.z01",
            "sample.001",
            "sample.002",
            "sample.7z.001",
            "sample.7z.002",
            "sample.zip",
            "other.part02.rar",
        ]
        file_path = os.path.join("C:\\tmp", "sample.part01.rar")

        with mock.patch("unzipper.os.listdir", return_value=files), mock.patch(
            "unzipper._send_to_trash"
        ) as mock_trash:
            unzipper.remove_archive(file_path)
            trashed = {
                os.path.basename(call.args[0])
                for call in mock_trash.call_args_list
            }

            expected = {
                "sample.part01.rar",
                "sample.part02.rar",
                "sample.rar",
                "sample.r00",
                "sample.z01",
                "sample.001",
                "sample.002",
                "sample.7z.001",
                "sample.7z.002",
                "sample.zip",
            }
            self.assertEqual(trashed, expected)


if __name__ == "__main__":
    unittest.main()
