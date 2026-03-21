"""Main function of the program."""

import os
import shutil
import sys

from tqdm import tqdm

from archive_backends import clear_archive_probe_cache
from last_level import check_if_is_last_level
from setting import Config
from log_msg import log_msg
from unzipper import get_password_list, move_files_up, unzipFileWith7z

settings = Config.get_instance().settings


def _list_files(dir_path, recursive):
    if recursive:
        files = []
        for root, _, filenames in os.walk(dir_path):
            for filename in filenames:
                files.append(os.path.join(root, filename))
        return files
    return [
        os.path.join(dir_path, filename)
        for filename in os.listdir(dir_path)
        if os.path.isfile(os.path.join(dir_path, filename))
    ]


def _move_single_file_to_root(output_dir, root_dir):
    entries = os.listdir(output_dir)
    files = [name for name in entries if os.path.isfile(os.path.join(output_dir, name))]
    dirs = [name for name in entries if os.path.isdir(os.path.join(output_dir, name))]

    if len(files) != 1 or dirs:
        return None

    src = os.path.join(output_dir, files[0])
    dest = os.path.join(root_dir, files[0])
    if os.path.exists(dest):
        log_msg(
            f"Destination {dest} already exists; keeping {src} in {output_dir}",
            log_level=4,
        )
        return None

    shutil.move(src, dest)
    os.rmdir(output_dir)
    log_msg(f"Moved single extracted file {src} to {dest}", log_level=3)
    return dest


################### MAIN FUNCTION ################################################################
def main(target):
    """main function, can take both a file or a directory as argument"""
    # load settings
    clear_archive_probe_cache()

    # print the settings
    print("Settings:")
    for key, value in settings.items():
        print(f"\t{key} : {value}")

    # get the password list
    passwords = get_password_list(target)

    #################################### prepare for unzipping #####################################
    # start timer
    total_files = 0
    finished_files = 0
    total_file_size = 0
    finished_files_size = 0
    succeeded = 0
    failed = 0
    zip_executable_path = settings.get("zip_executable_path", "")

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
        level = 0
        processed = set()
        files_to_process = _list_files(target, settings["unzipsubfolder"])

        while files_to_process:
            if level > settings["maximum_lv"]:
                break

            next_files = []
            seen = set()
            level_files = []
            for file_path in files_to_process:
                if file_path not in seen:
                    seen.add(file_path)
                    level_files.append(file_path)

            for file_path in tqdm(level_files):
                # it is possible that a part of the multi-part archive is deleted and no longer exists
                # in this case, the file will be skipped
                if not os.path.exists(file_path):
                    log_msg(
                        f"-- {os.path.basename(file_path)} does not exist "
                        "(deleted after unzipping the main part).",
                        log_level=5,
                    )
                    continue

                if file_path in processed:
                    continue

                finished_files_size += os.path.getsize(file_path) / 1024 / 1024
                success, _ = unzipFileWith7z(
                    file_path,
                    zip_executable_path,
                    passwords=passwords,
                    autodelete=settings["autodelete"],
                    autodeleteexisting=settings["autodeleteexisting"],
                    lv=level,
                    maximum_lv=level,
                    use_bandizip=settings["use_bandizip"],
                    pass_in_file_separator=settings["pass_in_file_separator"],
                )
                processed.add(file_path)
                finished_files += 1
                if success:
                    log_msg(
                        f"vv Archive {os.path.basename(file_path)} has been unzipped "
                        f"to {file_path}lv{level:d}",
                        log_level=5,
                    )
                    succeeded += 1
                else:
                    log_msg(
                        f"-- {os.path.basename(file_path)} cannot be unzipped.",
                        log_level=5,
                    )
                    failed += 1
                    continue

                output_dir = f"{file_path}lv{level:d}"
                if not os.path.isdir(output_dir):
                    continue

                if check_if_is_last_level(output_dir):
                    continue

                moved_file = _move_single_file_to_root(
                    output_dir, os.path.dirname(file_path)
                )
                if moved_file:
                    next_files.append(moved_file)
                    continue

                next_files.extend(_list_files(output_dir, True))

            level += 1
            if level > settings["maximum_lv"]:
                break
            files_to_process = next_files

        if settings["automoveup"]:
            for dir_ in os.listdir(target):
                if os.path.isdir(os.path.join(target, dir_)):
                    move_files_up(os.path.join(target, dir_))

    # if target is a file
    if os.path.isfile(target):
        unzipFileWith7z(
            target,
            zip_executable_path,
            passwords=passwords,
            autodelete=settings["autodelete"],
            autodeleteexisting=settings["autodeleteexisting"],
            maximum_lv=settings["maximum_lv"],
            use_bandizip=settings["use_bandizip"],
            pass_in_file_separator=settings["pass_in_file_separator"],
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
