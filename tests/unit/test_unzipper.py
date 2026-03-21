import os
import subprocess
import unittest
from unittest import mock

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
os.environ["MULTILEVEL_UNZIPPER_SETTINGS_FILE"] = os.path.join(
    REPO_ROOT, "mlunzipper_test_settings.json"
)
os.environ["MULTILEVEL_UNZIPPER_READONLY_SETTINGS"] = "1"

import unzipper


def _completed_process(returncode, stdout="", stderr=""):
    return subprocess.CompletedProcess(
        args=[],
        returncode=returncode,
        stdout=stdout.encode("utf-8"),
        stderr=stderr.encode("utf-8"),
    )


class TestUnzipperHelpers(unittest.TestCase):
    def test_build_extract_args_7zip(self):
        args = unzipper.build_extract_args(
            "7z.exe", "archive.zip", "outdir", use_bandizip=False
        )
        self.assertEqual(args, ["7z.exe", "x", "-y", "-ooutdir", "archive.zip"])

    def test_build_extract_args_bandizip_with_password(self):
        args = unzipper.build_extract_args(
            "bz.exe", "archive.zip", "outdir", password="pass", use_bandizip=True
        )
        self.assertEqual(
            args, ["bz.exe", "x", "-y", "-p:pass", "-o:outdir", "archive.zip"]
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

    def test_resolve_archive_group_for_split_rar(self):
        files = [
            "sample.part01.rar",
            "sample.part02.rar",
            "sample.part03.rar",
            "other.part02.rar",
        ]
        with mock.patch("unzipper.os.path.isdir", return_value=True), mock.patch(
            "unzipper.os.listdir", return_value=files
        ):
            group = unzipper.resolve_archive_group("C:\\tmp\\sample.part02.rar")

        self.assertEqual(group["kind"], "non_primary")
        self.assertTrue(group["primary_path"].endswith("sample.part01.rar"))
        self.assertEqual(
            {os.path.basename(path) for path in group["members"]},
            {"sample.part01.rar", "sample.part02.rar", "sample.part03.rar"},
        )

    def test_get_passwords_from_filename(self):
        passwords = unzipper.get_passwords_from_filename("file_pass123.zip", "_")
        self.assertEqual(passwords, ["pass123", "pass123.zip"])

    def test_get_passwords_from_filename_custom_separator(self):
        passwords = unzipper.get_passwords_from_filename("file-pass-word.zip", "-")
        self.assertEqual(
            passwords,
            ["pass-word", "pass-word.zip", "word", "word.zip"],
        )

    def test_remove_archive_deletes_only_resolved_members(self):
        files = [
            "sample.part01.rar",
            "sample.part02.rar",
            "sample.part03.rar",
            "sample-copy.part02.rar",
            "other.part02.rar",
        ]
        file_path = os.path.join("C:\\tmp", "sample.part01.rar")

        with mock.patch("unzipper.os.path.isdir", return_value=True), mock.patch(
            "unzipper.os.listdir", return_value=files
        ), mock.patch("unzipper.os.path.exists", return_value=True), mock.patch(
            "unzipper._send_to_trash"
        ) as mock_trash:
            unzipper.remove_archive(file_path)
            trashed = {os.path.basename(call.args[0]) for call in mock_trash.call_args_list}

        self.assertEqual(
            trashed,
            {
                "sample.part01.rar",
                "sample.part02.rar",
                "sample.part03.rar",
            },
        )

    def test_unzip_retries_alternate_backend_before_failing(self):
        file_path = "archive.zip"
        backends = [
            {
                "display_name": "7-Zip",
                "exe_path": "7z.exe",
                "use_bandizip": False,
            },
            {
                "display_name": "Bandizip",
                "exe_path": "bz.exe",
                "use_bandizip": True,
            },
        ]

        with mock.patch(
            "unzipper.resolve_archive_group",
            return_value={"kind": "single", "primary_path": file_path, "members": [file_path]},
        ), mock.patch(
            "unzipper.resolve_available_backends",
            return_value=backends,
        ), mock.patch(
            "unzipper.os.path.exists",
            side_effect=lambda path: path == file_path,
        ), mock.patch(
            "unzipper.check_if_is_last_level",
            return_value=True,
        ), mock.patch(
            "unzipper._run_extract_command",
            side_effect=[
                _completed_process(2, stderr="Cannot open the file as archive"),
                _completed_process(0),
            ],
        ) as mock_run:
            success, _ = unzipper.unzipFileWith7z(
                file_path,
                "ignored.exe",
                passwords=[""],
                maximum_lv=0,
                use_bandizip=False,
            )

        self.assertTrue(success)
        commands = [call.args[0] for call in mock_run.call_args_list]
        self.assertEqual([command[0] for command in commands], ["7z.exe", "bz.exe"])

    def test_password_attempts_exhaust_one_backend_before_switching(self):
        file_path = "archive.zip"
        backends = [
            {
                "display_name": "7-Zip",
                "exe_path": "7z.exe",
                "use_bandizip": False,
            },
            {
                "display_name": "Bandizip",
                "exe_path": "bz.exe",
                "use_bandizip": True,
            },
        ]

        with mock.patch(
            "unzipper.resolve_archive_group",
            return_value={"kind": "single", "primary_path": file_path, "members": [file_path]},
        ), mock.patch(
            "unzipper.resolve_available_backends",
            return_value=backends,
        ), mock.patch(
            "unzipper.os.path.exists",
            side_effect=lambda path: path == file_path,
        ), mock.patch(
            "unzipper.check_if_is_last_level",
            return_value=True,
        ), mock.patch(
            "unzipper._run_extract_command",
            side_effect=[
                _completed_process(2, stderr="Wrong password"),
                _completed_process(2, stderr="Wrong password"),
                _completed_process(2, stderr="Wrong password"),
                _completed_process(14, stdout="Invalid password"),
                _completed_process(14, stdout="Invalid password"),
                _completed_process(0),
            ],
        ) as mock_run:
            success, _ = unzipper.unzipFileWith7z(
                file_path,
                "ignored.exe",
                passwords=["", "secret", "later"],
                maximum_lv=0,
                use_bandizip=False,
            )

        self.assertTrue(success)
        commands = [call.args[0] for call in mock_run.call_args_list]
        self.assertEqual(
            [command[0] for command in commands],
            ["7z.exe", "7z.exe", "7z.exe", "bz.exe", "bz.exe", "bz.exe"],
        )
        self.assertEqual(commands[1][3], "-psecret")
        self.assertEqual(commands[2][3], "-plater")
        self.assertEqual(commands[4][3], "-p:secret")
        self.assertEqual(commands[5][3], "-p:later")

    def test_missing_alternate_backend_does_not_trigger_second_attempt(self):
        file_path = "archive.zip"
        backends = [
            {
                "display_name": "7-Zip",
                "exe_path": "7z.exe",
                "use_bandizip": False,
            }
        ]

        with mock.patch(
            "unzipper.resolve_archive_group",
            return_value={"kind": "single", "primary_path": file_path, "members": [file_path]},
        ), mock.patch(
            "unzipper.resolve_available_backends",
            return_value=backends,
        ), mock.patch(
            "unzipper.os.path.exists",
            side_effect=lambda path: path == file_path,
        ), mock.patch(
            "unzipper._run_extract_command",
            return_value=_completed_process(2, stderr="Cannot open the file as archive"),
        ) as mock_run:
            success, _ = unzipper.unzipFileWith7z(
                file_path,
                "ignored.exe",
                passwords=[""],
                maximum_lv=0,
                use_bandizip=False,
            )

        self.assertFalse(success)
        self.assertEqual(mock_run.call_count, 1)

    def test_failed_extraction_preserves_archive_group(self):
        file_path = "sample.part01.rar"
        backends = [
            {
                "display_name": "7-Zip",
                "exe_path": "7z.exe",
                "use_bandizip": False,
            }
        ]
        group = {
            "kind": "primary",
            "primary_path": file_path,
            "members": ["sample.part01.rar", "sample.part02.rar"],
        }

        with mock.patch("unzipper.resolve_archive_group", return_value=group), mock.patch(
            "unzipper.resolve_available_backends",
            return_value=backends,
        ), mock.patch(
            "unzipper.os.path.exists",
            side_effect=lambda path: path == file_path,
        ), mock.patch(
            "unzipper._run_extract_command",
            return_value=_completed_process(2, stderr="Cannot open the file as archive"),
        ), mock.patch("unzipper.remove_archive") as mock_remove:
            success, _ = unzipper.unzipFileWith7z(
                file_path,
                "ignored.exe",
                passwords=[""],
                autodelete=True,
                maximum_lv=0,
                use_bandizip=False,
            )

        self.assertFalse(success)
        mock_remove.assert_not_called()

    def test_non_primary_part_is_skipped_without_extraction(self):
        file_path = "sample.part02.rar"
        backends = [
            {
                "display_name": "7-Zip",
                "exe_path": "7z.exe",
                "use_bandizip": False,
            }
        ]
        group = {
            "kind": "non_primary",
            "primary_path": "sample.part01.rar",
            "members": ["sample.part01.rar", "sample.part02.rar"],
        }

        with mock.patch("unzipper.resolve_archive_group", return_value=group), mock.patch(
            "unzipper.resolve_available_backends",
            return_value=backends,
        ), mock.patch(
            "unzipper.os.path.exists",
            side_effect=lambda path: path == file_path,
        ), mock.patch("unzipper._run_extract_command") as mock_run:
            success, _ = unzipper.unzipFileWith7z(
                file_path,
                "ignored.exe",
                passwords=[""],
                maximum_lv=0,
                use_bandizip=False,
            )

        self.assertFalse(success)
        mock_run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
