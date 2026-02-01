import importlib
import os
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TEST_DIR = os.path.join(REPO_ROOT, "test")
SETTINGS_PATH = os.path.join(TEST_DIR, "mlunzipper_test_settings.json")
FILE_TARGET = os.path.join(TEST_DIR, "火影2016p.EP195_1.rar")
FOLDER_TARGET = os.path.join(TEST_DIR, "test_folder")


def _reload_modules():
    os.environ["MULTILEVEL_UNZIPPER_SETTINGS_FILE"] = SETTINGS_PATH
    os.environ["MULTILEVEL_UNZIPPER_READONLY_SETTINGS"] = "1"

    import setting

    setting.Config._instance = None
    importlib.reload(setting)

    import log_msg
    import last_level
    import unzipper
    import MultilevelUnzipper

    importlib.reload(log_msg)
    importlib.reload(last_level)
    importlib.reload(unzipper)
    importlib.reload(MultilevelUnzipper)

    return setting, unzipper, MultilevelUnzipper


class TestFullUnzip(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        setting, unzipper, multilevel = _reload_modules()
        cls.settings = setting.Config.get_instance().settings
        cls.settings["autodelete"] = False
        cls.settings["autodeleteexisting"] = True
        cls.unzipper = unzipper
        cls.multilevel = multilevel

    def _ensure_executable_available(self):
        exe_path = self.settings.get("zip_executable_path", "")
        if not exe_path or not os.path.exists(exe_path):
            self.skipTest(f"zip executable not found: {exe_path}")
        return exe_path

    def test_unzip_single_archive(self):
        exe_path = self._ensure_executable_available()
        if not os.path.exists(FILE_TARGET):
            self.skipTest(f"archive not found: {FILE_TARGET}")

        passwords = self.unzipper.get_password_list(FILE_TARGET)
        success, _ = self.unzipper.unzipFileWith7z(
            FILE_TARGET,
            exe_path,
            passwords=passwords,
            autodelete=self.settings["autodelete"],
            autodeleteexisting=self.settings["autodeleteexisting"],
            maximum_lv=self.settings["maximum_lv"],
            use_bandizip=self.settings["use_bandizip"],
            pass_in_file_separator=self.settings["pass_in_file_separator"],
        )

        self.assertTrue(success, "archive failed to unzip")
        self.assertTrue(os.path.isdir(FILE_TARGET + "lv0"))

    def test_unzip_folder(self):
        self._ensure_executable_available()
        if not os.path.isdir(FOLDER_TARGET):
            self.skipTest(f"folder not found: {FOLDER_TARGET}")

        self.multilevel.main(FOLDER_TARGET)

        for entry in os.listdir(FOLDER_TARGET):
            path = os.path.join(FOLDER_TARGET, entry)
            if os.path.isfile(path) and entry.lower().endswith(".mp4"):
                self.assertFalse(os.path.exists(path + "lv0"))


if __name__ == "__main__":
    unittest.main()
