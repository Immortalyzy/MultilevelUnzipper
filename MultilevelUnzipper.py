""" main function of the program """

import os
import sys
import time
import importlib
from datetime import datetime

from tqdm import tqdm

from setting import Config
from log_msg import log_msg
from unzipper import getPasswordList, move_files_up, unzipFileWith7z

settings = Config.get_instance().settings


################### MAIN FUNCTION ################################################################
def main(target):
    """main function, can take both a file or a directory as argument"""
    # load settings

    # print the settings
    print("Settings:")
    for key, value in settings.items():
        print(f"\t{key} : {value}")

    # get the password list
    passwords = getPasswordList(target)

    #################################### prepare for unzipping #####################################
    # start timer
    start_time = time.time()
    total_files = 0
    finished_files = 0
    total_file_size = 0
    finished_files_size = 0
    successed = 0
    failed = 0

    # if target is a folder, get the total size of the files
    if os.path.isdir(target):
        for root, dirs, files in os.walk(target):
            for file in files:
                total_files += 1
                total_file_size += os.path.getsize(os.path.join(root, file))
    # convert to MB
    total_file_size = total_file_size / 1024 / 1024

    # display info
    print(f"Total files: {total_files}, total size: {total_file_size:.2f} MB")

    ##################################### start unzipping ##########################################
    # if target is a directory
    if os.path.isdir(target):
        if settings["unzipsubfolder"]:
            # unzip all files including files under subfolders
            for root, dirs, files in os.walk(target):
                for file in tqdm(files):
                    finished_files_size += (
                        os.path.getsize(os.path.join(root, file)) / 1024 / 1024
                    )
                    success, lv = unzipFileWith7z(
                        os.path.join(root, file),
                        settings["zip_excutible_path"],
                        passwords=passwords,
                        autodelete=settings["autodelete"],
                        autodeleteexisting=settings["autodeleteexisting"],
                    )
                    finished_files += 1
                    if success:
                        log_msg(
                            f"vv Archive {file} has been unzipped to {file}lv{0:d}",
                            log_level=5,
                        )
                        successed += 1
                    else:
                        log_msg(f"-- {file} cannot be unzipped.", log_level=5)
                        failed += 1

            if settings["automoveup"]:
                dirs = os.listdir(target)
                for dir_ in dirs:
                    # if dir is a directory, it could just unzipped from a file
                    #! it can also be a directory existing before the program runs
                    if os.path.isdir(os.path.join(target, dir_)):
                        move_files_up(os.path.join(target, dir_))
        else:
            # unzip all files in the target directory, but not including files under subfolders
            # get all items in the target directory
            list_of_files = os.listdir(target)
            # create a list of files (not directories)
            list_of_files = [
                file
                for file in list_of_files
                if os.path.isfile(os.path.join(target, file))
            ]

            for file in tqdm(list_of_files):
                finished_files_size += (
                    os.path.getsize(os.path.join(target, file)) / 1024 / 1024
                )
                success, lv = unzipFileWith7z(
                    os.path.join(target, file),
                    settings["zip_excutible_path"],
                    passwords=passwords,
                    autodelete=settings["autodelete"],
                    autodeleteexisting=settings["autodeleteexisting"],
                )
                finished_files += 1
                if success:
                    log_msg(
                        f"vv Archive {file} has been unzipped to {file}lv{0:d}",
                        log_level=5,
                    )
                    successed += 1
                else:
                    log_msg(f"-- {file} cannot be unzipped.", log_level=5)
                    failed += 1

            if settings["automoveup"]:
                for file in list_of_files:
                    dir_ = os.path.join(target, file + "lv0")
                    # move up only the list of files just unzipped
                    if os.path.isdir(dir_):
                        move_files_up(dir_)

    # if target is a file
    if os.path.isfile(target):
        unzipFileWith7z(
            target,
            settings["zip_excutible_path"],
            passwords=passwords,
            autodelete=settings["autodelete"],
            autodeleteexisting=settings["autodeleteexisting"],
        )
        if settings["automoveup"]:
            move_files_up(target + "lv0")


################### MAIN FUNCTION ################################################################

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # run the main function
        if os.path.exists(sys.argv[1]):
            main(
                sys.argv[1],
            )

    input("Press Enter to exit...")
