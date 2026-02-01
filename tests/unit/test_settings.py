import unittest
from unittest import mock

from setting import select_zip_executable_path


class TestSettings(unittest.TestCase):
    def test_select_zip_executable_prefers_bandizip(self):
        bz_path = "C:\\fake\\bz.exe"
        z7_path = "C:\\fake\\7z.exe"
        settings = {
            "use_bandizip": True,
            "zip_executable_path_bandizip": bz_path,
            "zip_executable_path_7z": z7_path,
        }
        with mock.patch("setting.os.path.exists") as mock_exists:
            mock_exists.side_effect = lambda path: path in {bz_path, z7_path}
            select_zip_executable_path(settings)
        self.assertEqual(settings["zip_executable_path"], bz_path)
        self.assertTrue(settings["use_bandizip"])

    def test_select_zip_executable_falls_back_to_7zip(self):
        bz_path = "C:\\fake\\missing.exe"
        z7_path = "C:\\fake\\7z.exe"
        settings = {
            "use_bandizip": True,
            "zip_executable_path_bandizip": bz_path,
            "zip_executable_path_7z": z7_path,
        }
        with mock.patch("setting.os.path.exists") as mock_exists:
            mock_exists.side_effect = lambda path: path == z7_path
            select_zip_executable_path(settings)
        self.assertEqual(settings["zip_executable_path"], z7_path)
        self.assertFalse(settings["use_bandizip"])


if __name__ == "__main__":
    unittest.main()
