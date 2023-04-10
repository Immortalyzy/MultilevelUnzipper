""" settings and global variables for MultiLevelUnzipper.py """
import json
import os
import shutil
from datetime import datetime

# for simplicity, use global variables to store write to file settings
settings = {
    "log_to_file": False,
    "log_file_name": "unzipper_log.txt",
    "zip_excutible_path": "C:\\Program Files\\7-Zip\\7z.exe",
    "autodelete": False,
    "autodeleteexisting": False,
    "automoveup": False,
    "unzipsubfolder": False,
    "log_level": 3,
    "pass_in_file_seperator": "_",
}

# the settings .json file will be stored in the users home directory
setting_file_name = ".MultiLevelUnzipperSettings.json"


# log function, its settings are controlled by global variables
def log_msg(message, log_level=3):
    """ log the message to the console and optionally to a file, automatically add time stamp """
    # log levels 1=tiny, 2=detailed, 3=normal, 4=important, 5=critical
    if log_level >= settings["log_level"]:
        time_message = datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " "
        for i in range(log_level):
            time_message += "-"
        time_message += " " + message

        if settings["log_to_file"]:
            with open(settings["log_file_name"], "a") as f:
                f.write(time_message + "\n")
        else:
            print(time_message)


def find7z():
    """ find the 7z.exe, return the path if found, otherwise return None """
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
            log_msg("7z.exe not found, please specify the path to 7z.exe")
            return None
    return path


def dict_compare(d1, d2):
    """ compare two dictionaries, return the added, removed, modified and same keys """
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


def read_settings():
    """Reads the settings file and returns a list of the lines"""
    global settings  # global is required only if you want to modify the global variable, super confusing (the word confusing is completed by Copilot)

    # generate the setting file path
    home = os.path.expanduser("~")
    settings_file = os.path.join(home, setting_file_name)
    is_valid_setting = True

    # if the file doesn't exist, create it and write the default settings
    if not os.path.exists(settings_file):
        # try to find the 7z.exe here
        zip_path = find7z()
        if zip_path is not None:
            settings["zip_excutible_path"] = zip_path
        else:
            log_msg(
                "7z.exe not found, please manually specify the path to 7z.exe in "
                + settings_file
                + ", remember to use double backslashes (\\\\) to escape the backslashes"
            )
            is_valid_setting = False

        with open(settings_file, "w") as f:
            json.dump(settings, f)

    # if the file exists, read the settings
    with open(settings_file, "r") as f:
        # check if the settings are from an older version
        settings_local = json.load(f)
        added, removed, modified, same = dict_compare(settings, settings_local)
        if len(added) > 0 or len(removed) > 0 or len(modified) > 0:
            # setting file from an older version
            new_settings = {**settings, **{k: v[1] for k, v in modified.items()}}
            settings = new_settings
            with open(settings_file, "w") as f:
                json.dump(settings, f)
            if len(added) > 0:
                log_msg("new settings added: " + str(added))

        # check if the 7z.exe path is valid
        if not os.path.exists(settings["zip_excutible_path"]):
            # try to find the 7z.exe
            zip_path = find7z()
            if zip_path is not None:
                settings["zip_excutible_path"] = zip_path
                # write the new settings to the file
                with open(settings_file, "w") as f:
                    json.dump(settings, f)
                log_msg("7z path updated")
            else:  # 7z.exe in setting file is not valid and cannot be found
                log_msg(
                    "7z.exe not found, please check the path to 7z.exe in "
                    + settings_file
                    + ", remember to use DOUBLE backslashes (\\\\) to escape the backslashes"
                )
                is_valid_setting = False

    # if the settings are not valid, return false, the program should not continue
    return is_valid_setting
