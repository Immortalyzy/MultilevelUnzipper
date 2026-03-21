import os
import subprocess
import unittest
from unittest import mock

import archive_backends


def _completed_process(returncode, stdout="", stderr=""):
    return subprocess.CompletedProcess(
        args=[],
        returncode=returncode,
        stdout=stdout.encode("utf-8"),
        stderr=stderr.encode("utf-8"),
    )


class TestArchiveBackends(unittest.TestCase):
    def tearDown(self):
        archive_backends.clear_archive_probe_cache()

    def test_resolve_available_backends_prefers_selected_backend(self):
        settings = {
            "use_bandizip": True,
            "zip_executable_path_bandizip": "C:\\tools\\bz.exe",
            "zip_executable_path_7z": "C:\\tools\\7z.exe",
        }
        with mock.patch("archive_backends.os.path.exists", return_value=True):
            backends = archive_backends.resolve_available_backends(settings=settings)

        self.assertEqual(
            [backend["name"] for backend in backends],
            [archive_backends.BACKEND_BANDIZIP, archive_backends.BACKEND_7Z],
        )

    def test_resolve_available_backends_filters_missing_alternate(self):
        settings = {
            "use_bandizip": False,
            "zip_executable_path_bandizip": "C:\\tools\\missing-bz.exe",
            "zip_executable_path_7z": "C:\\tools\\7z.exe",
        }
        with mock.patch(
            "archive_backends.os.path.exists",
            side_effect=lambda path: path.endswith("7z.exe"),
        ):
            backends = archive_backends.resolve_available_backends(settings=settings)

        self.assertEqual(len(backends), 1)
        self.assertEqual(backends[0]["name"], archive_backends.BACKEND_7Z)

    def test_probe_archive_uses_cache_with_same_backend_set(self):
        file_path = os.path.abspath("archive.mp4")
        backends = [
            {
                "name": archive_backends.BACKEND_BANDIZIP,
                "display_name": "Bandizip",
                "exe_path": "bz.exe",
                "use_bandizip": True,
            }
        ]

        with mock.patch("archive_backends.os.path.isfile", return_value=True), mock.patch(
            "archive_backends.subprocess.run",
            return_value=_completed_process(0),
        ) as mock_run:
            self.assertTrue(
                archive_backends.probe_archive_with_backends(
                    file_path,
                    backends=backends,
                )
            )
            self.assertTrue(
                archive_backends.probe_archive_with_backends(
                    file_path,
                    backends=backends,
                )
            )

        self.assertEqual(mock_run.call_count, 1)


if __name__ == "__main__":
    unittest.main()
