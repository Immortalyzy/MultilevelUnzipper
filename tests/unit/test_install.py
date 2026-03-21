"""Tests for installer validation, payload resolution, and install behavior."""

import os
import unittest
import uuid
from unittest.mock import patch

import install
from setting import DEFAULT_SETTINGS


def make_test_dir():
    root = os.path.join(os.getcwd(), "test_tmp_local")
    os.makedirs(root, exist_ok=True)
    path = os.path.join(root, uuid.uuid4().hex)
    os.makedirs(path, exist_ok=True)
    return path


def make_executable(root, name):
    path = os.path.join(root, name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("echo test")
    return path


def build_valid_settings(root, prefer_bandizip=True, include_alternate=True):
    settings = dict(DEFAULT_SETTINGS)
    settings["use_bandizip"] = prefer_bandizip
    settings["zip_executable_path_bandizip"] = (
        make_executable(root, "bz.exe")
        if prefer_bandizip or include_alternate
        else ""
    )
    settings["zip_executable_path_7z"] = (
        make_executable(root, "7z.exe")
        if (not prefer_bandizip) or include_alternate
        else ""
    )
    return settings


class InstallTests(unittest.TestCase):
    def test_validate_install_settings_requires_preferred_backend_path(self):
        temp_root = make_test_dir()
        settings = dict(DEFAULT_SETTINGS)
        settings["use_bandizip"] = True
        settings["zip_executable_path_bandizip"] = os.path.join(temp_root, "missing-bz.exe")
        settings["zip_executable_path_7z"] = ""

        with self.assertRaises(ValueError) as exc:
            install.validate_install_settings(settings)

        self.assertIn("Bandizip executable was not found", str(exc.exception))

    def test_validate_install_settings_allows_single_backend_with_warning(self):
        temp_root = make_test_dir()
        settings = build_valid_settings(
            temp_root,
            prefer_bandizip=False,
            include_alternate=False,
        )

        validated, warnings = install.validate_install_settings(settings)

        self.assertEqual(validated["zip_executable_path_7z"], settings["zip_executable_path_7z"])
        self.assertEqual(len(warnings), 1)
        self.assertIn("fallback will stay disabled", warnings[0])

    def test_get_payload_source_folder_prefers_side_by_side(self):
        temp_root = make_test_dir()
        side_by_side = os.path.join(temp_root, "MultilevelUnzipper")
        os.makedirs(side_by_side, exist_ok=True)

        with patch.object(install, "get_runtime_root", return_value=temp_root):
            src, checked = install.get_payload_source_folder()

        self.assertEqual(src, side_by_side)
        self.assertEqual(checked[0], side_by_side)

    def test_get_payload_source_folder_falls_back_to_meipass(self):
        temp_root = make_test_dir()
        temp_meipass = make_test_dir()
        bundled_payload = os.path.join(temp_meipass, "MultilevelUnzipper")
        os.makedirs(bundled_payload, exist_ok=True)

        with (
            patch.object(install, "get_runtime_root", return_value=temp_root),
            patch.object(install.sys, "frozen", True, create=True),
            patch.object(install.sys, "_MEIPASS", temp_meipass, create=True),
        ):
            src, checked = install.get_payload_source_folder()

        self.assertEqual(src, bundled_payload)
        self.assertEqual(len(checked), 2)

    def test_install_application_raises_clear_error_when_payload_missing(self):
        temp_root = make_test_dir()
        settings = build_valid_settings(temp_root, prefer_bandizip=True, include_alternate=True)
        with (
            patch.object(install, "save_settings", return_value="C:\\settings.json"),
            patch.object(
                install,
                "get_payload_source_folder",
                return_value=(None, ["C:\\missing\\MultilevelUnzipper"]),
            ),
            patch.dict(os.environ, {"APPDATA": temp_root}, clear=False),
        ):
            with self.assertRaises(FileNotFoundError) as exc:
                install.install_application(settings)

        self.assertIn("Please unzip the full release package", str(exc.exception))

    def test_install_application_copies_payload_and_registers_menu_entries(self):
        temp_root = make_test_dir()
        settings = build_valid_settings(temp_root, prefer_bandizip=True, include_alternate=True)

        source_payload = os.path.join(temp_root, "MultilevelUnzipper")
        os.makedirs(source_payload, exist_ok=True)
        with open(os.path.join(source_payload, "sample.txt"), "w", encoding="utf-8") as fh:
            fh.write("ok")

        calls = []
        saved_settings = {}
        appdata = os.path.join(temp_root, "appdata")
        os.makedirs(appdata, exist_ok=True)
        with (
            patch.object(
                install,
                "save_settings",
                side_effect=lambda settings_to_save: saved_settings.setdefault(
                    "settings", dict(settings_to_save)
                )
                or "C:\\settings.json",
            ),
            patch.object(
                install,
                "get_payload_source_folder",
                return_value=(source_payload, [source_payload]),
            ),
            patch.object(
                install,
                "add_context_menu_option",
                side_effect=lambda name, exe_path, reg_class: calls.append(
                    (name, exe_path, reg_class)
                ),
            ),
            patch.dict(os.environ, {"APPDATA": appdata}, clear=False),
        ):
            result = install.install_application(settings)

        copied_file = os.path.join(result["destination_folder"], "sample.txt")
        self.assertTrue(os.path.isfile(copied_file))
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0], "Unzip all files under this directory")
        self.assertEqual(calls[1][0], "Unzip this file")
        self.assertEqual(saved_settings["settings"]["zip_executable_path"], settings["zip_executable_path_bandizip"])
        self.assertEqual(result["warnings"], [])


if __name__ == "__main__":
    unittest.main()
