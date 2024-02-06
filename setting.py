""" settings and global variables for MultiLevelUnzipper.py """
import json
import os
import shutil
from datetime import datetime

# the settings .json file will be stored in the users home directory
setting_file_name = ".MultiLevelUnzipperSettings.json"


class Config:
    """Config Singleton class"""

    _instance = None

    @staticmethod
    def get_instance():
        """Get the instance of the singleton class"""
        if Config._instance is None:
            Config()
        return Config._instance

    def __init__(self):
        if Config._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            Config._instance = self
            self.settings = self.load_config()

    def load_config(self, settings_file=setting_file_name):
        """load config from local file, if not exist, create one"""
        # generate the setting file path
        home = os.path.expanduser("~")
        settings_file = os.path.join(home, setting_file_name)

        # default settings
        temp_settings = {
            "log_to_file": False,
            "log_file_name": "unzipper_log.txt",
            "zip_excutible_path": "C:\\Program Files\\7-Zip\\7z.exe",
            "autodelete": True,
            "autodeleteexisting": False,
            "automoveup": True,
            "unzipsubfolder": True,
            "log_level": 3,
            "pass_in_file_seperator": "_",
        }

        # if the file doesn't exist, create it and write the default settings
        if not os.path.exists(settings_file):
            # try to find the 7z.exe here
            zip_path = find7z()
            if zip_path is not None:
                temp_settings["zip_excutible_path"] = zip_path
            else:
                print(
                    "7z.exe not found, please manually specify the path to 7z.exe in "
                    + settings_file
                    + ", remember to use double backslashes (\\\\) to escape the backslashes"
                )

            with open(settings_file, "w") as f:
                json.dump(temp_settings, f)

        # if the file exists, read the settings
        with open(settings_file, "r") as f:
            # check if the settings are from an older version
            settings_local = json.load(f)
            added, removed, modified, same = dict_compare(temp_settings, settings_local)
            if len(added) > 0 or len(removed) > 0 or len(modified) > 0:
                # setting file from an older version
                new_settings = {
                    **temp_settings,
                    **{k: v[1] for k, v in modified.items()},
                }
                temp_settings = new_settings
                with open(settings_file, "w") as f:
                    json.dump(temp_settings, f)
                if len(added) > 0:
                    print("new settings added: " + str(added))

            # check if the 7z.exe path is valid
            if not os.path.exists(temp_settings["zip_excutible_path"]):
                # try to find the 7z.exe
                zip_path = find7z()
                if zip_path is not None:
                    temp_settings["zip_excutible_path"] = zip_path
                    # write the new settings to the file
                    with open(settings_file, "w") as f:
                        json.dump(temp_settings, f)
                    print("7z path updated")
                else:  # 7z.exe in setting file is not valid and cannot be found
                    print(
                        "7z.exe not found, please check the path to 7z.exe in "
                        + settings_file
                        + ", remember to use DOUBLE backslashes (\\\\) to escape the backslashes"
                    )
        return temp_settings


def find7z():
    """find the 7z.exe, return the path if found, otherwise return None"""
    path = shutil.which("7z.exe")
    if path is None:
        # check if 7z.exe is in the default installation directory
        if os.path.exists("C:\\Program Files\\7-Zip\\7z.exe"):
            path = "C:\\Program Files\\7-Zip\\7z.exe"
            return path
        elif os.path.exists("C:\\Program Files (x86)\\7-Zip\\7z.exe"):
            path = "C:\\Program Files (x86)\\7-Zip\\7z.exe"
            return path
        else:
            print("7z.exe not found, please specify the path to 7z.exe")
            return None
    return path


def dict_compare(d1, d2):
    """compare two dictionaries, return the added, removed, modified and same keys"""
    # this function is from https://stackoverflow.com/questions/4527942/comparing-two-dictionaries-and-checking-how-many-key-value-pairs-are-equal
    # this function is use to check if the local setting file is from an older version
    d1_keys = set(d1.keys())
    d2_keys = set(d2.keys())
    shared_keys = d1_keys.intersection(d2_keys)
    added = d1_keys - d2_keys
    removed = d2_keys - d1_keys
    modified = {o: (d1[o], d2[o]) for o in shared_keys if d1[o] != d2[o]}
    same = set(o for o in shared_keys if d1[o] == d2[o])
    return added, removed, modified, same
