"""MultilevelUnzipper - unzip multiple levels of zip files at once."""

import os
import re
import shutil
import subprocess
import threading

try:
    import send2trash
except ImportError:  # pragma: no cover - fallback when dependency is missing
    send2trash = None

from last_level import check_if_is_last_level
from setting import Config
from log_msg import log_msg
from output_decode import is_not_archive, is_wrong_password

settings = Config.get_instance().settings


def build_extract_args(
    exe_path, archive_path, output_dir, password=None, use_bandizip=False
):
    """Build command-line arguments for extraction."""
    args = [exe_path, "x"]
    if password:
        if use_bandizip:
            args.append(f"-p:{password}")
        else:
            args.append(f"-p{password}")
    output_flag = f"-o:{output_dir}" if use_bandizip else f"-o{output_dir}"
    args.append(output_flag)
    args.append(archive_path)
    return args


def _output_dir_for(file_path, lv):
    return f"{file_path}lv{lv:d}"


def _slow_unzip_message(password=None):
    suffix = f" (password is {password})" if password else ""
    log_msg(f"Unzipping is taking time{suffix}, please wait...", log_level=3)


def _is_non_primary_multipart(file_path):
    """Return True if file_path is a non-primary part of a multi-part archive."""
    lower_path = file_path.lower()
    if re.search(r"\.part\d+\.rar$", lower_path):
        return not re.search(r"\.part0*1\.rar$", lower_path)
    if re.search(r"\.r\d{2}$", lower_path) or re.search(r"\.z\d{2}$", lower_path):
        return True
    match = re.search(r"\.(\d{3})$", lower_path)
    if match:
        return match.group(1) != "001"
    return False


def get_password_list(dir_path):
    """Get the password list from local and user password files."""
    password_list = [""]
    if os.path.isfile(dir_path):
        dir_path = os.path.dirname(dir_path)
    elif not os.path.isdir(dir_path):
        log_msg(f"{dir_path} is not a file or a directory", log_level=5)
        return password_list

    local_paths = [
        os.path.join(dir_path, "passwords.txt"),
        os.path.join(dir_path, ".passwords.txt"),
    ]
    for path in local_paths:
        if not os.path.exists(path):
            log_msg(f"{os.path.basename(path)} not found", log_level=5)
            continue
        with open(path, "r", encoding="utf8") as f:
            for line in f:
                password = line.strip()
                if password:
                    password_list.append(password)

    log_msg(f"Found {len(password_list):d} passwords in local files", log_level=3)

    global_passwords = os.path.join(os.path.expanduser("~"), ".passwords.txt")
    if os.path.exists(global_passwords):
        with open(global_passwords, "r", encoding="utf8") as f:
            for line in f:
                password = line.strip()
                if password:
                    password_list.append(password)

    log_msg(f"Found {len(password_list):d} passwords in total", log_level=4)
    return password_list


def get_passwords_from_filename(file_path, separator):
    """Get possible passwords from the file name using the configured separator."""
    if not separator:
        separator = "_"

    filename = os.path.basename(file_path)
    parts = filename.split(separator)
    if len(parts) <= 1:
        return []

    possible_passwords = []
    for i in range(1, len(parts)):
        pass_candidate = separator.join(parts[i:])
        if "." in pass_candidate:
            without_extension = pass_candidate.split(".", 1)[0]
            if without_extension:
                possible_passwords.append(without_extension)
            possible_passwords.append(pass_candidate)
        else:
            possible_passwords.append(pass_candidate)

    # De-duplicate while preserving order.
    seen = set()
    ordered = []
    for candidate in possible_passwords:
        if candidate and candidate not in seen:
            seen.add(candidate)
            ordered.append(candidate)
    return ordered


def remove_archive(file_path):
    """Remove archive files after unzipping, including all parts of multi-part archives."""
    dir_path = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)

    # Extract base name (strip extensions like .part01.rar, .r00, .001, etc.)
    base = re.split(
        r"\.part\d+\.rar|\.r\d+|\.z\d+|\.rar|\.7z|\.zip|\.001",
        file_name,
        flags=re.IGNORECASE,
    )[0]

    # List all files in the directory
    all_files = os.listdir(dir_path)

    # Compile regex to match all known multi-part formats related to the base name
    patterns = [
        re.escape(base) + r"\.part\d+\.rar$",  # part01.rar, part02.rar
        re.escape(base) + r"\.rar$",  # base.rar (often first file)
        re.escape(base) + r"\.r\d{2}$",  # r00, r01
        re.escape(base) + r"\.z\d{2}$",  # z01, z02
        re.escape(base) + r"\.\d{3}$",  # 001, 002
        re.escape(base) + r"\.7z\.\d{3}$",  # 7z.001, 7z.002
        re.escape(base) + r"\.zip$",  # base.zip
    ]

    # Match files to be deleted
    matched_files = []
    for pattern in patterns:
        regex = re.compile(pattern, re.IGNORECASE)
        matched_files += [f for f in all_files if regex.fullmatch(f)]

    # Remove duplicates and sort
    matched_files = sorted(set(matched_files))

    # Logging
    log_msg(f"Removing {len(matched_files)} archive part(s)", log_level=3)

    # Send all to recycle bin
    for f in matched_files:
        _send_to_trash(os.path.join(dir_path, f))


def _send_to_trash(path):
    if send2trash is not None:
        send2trash.send2trash(path)
        return
    os.remove(path)


# unzip a file
def unzipFileWith7z(
    file,
    z7path,
    passwords,
    autodelete=False,
    autodeleteexisting=False,
    lv=0,
    maximum_lv=None,
    use_bandizip=None,
    pass_in_file_separator=None,
):
    """Unzip a file with 7z.exe or Bandizip; return (success, level)."""
    has_archive = False
    password_protected = False
    output_dir = _output_dir_for(file, lv)
    if use_bandizip is None:
        use_bandizip = settings.get("use_bandizip", False)
    if maximum_lv is None:
        maximum_lv = settings.get("maximum_lv", 7)
    if pass_in_file_separator is None:
        pass_in_file_separator = settings.get("pass_in_file_separator", "_")

    # check if the file exists
    if not os.path.exists(file):
        log_msg(f"File {file} does not exist", log_level=5)
        return False, lv

    # check if is a .lib, .dll or .exe file, if yes skip
    # TODO: maybe a temporary solution, need to find a way to unzip .lib files
    if file.endswith(".lib") or file.endswith(".dll") or file.endswith(".exe"):
        log_msg(f"File {file} is a .lib, .dll or .exe file, skipping...", log_level=5)
        return False, lv

    # check if is a multi-archive sub archives, if yes skip
    if _is_non_primary_multipart(file):
        log_msg(
            f"File {file} is a multi-archive non-principle part, skipping...",
            log_level=5,
        )
        return False, lv

    # check if the output directory already exists
    if os.path.exists(output_dir):
        if autodeleteexisting:
            log_msg(
                f"Output directory {output_dir} already exists, deleting...",
                log_level=4,
            )
            shutil.rmtree(output_dir)
        else:
            log_msg(
                f"Output directory {output_dir} already exists, skipping...",
                log_level=4,
            )
            return False, lv

    # unzip without password
    # verify file is a a os.PathLike
    right_pass_found = False
    if not isinstance(file, os.PathLike) and not isinstance(file, str):
        raise TypeError(f"{file} must be a os.PathLike")

    log_msg(f"Unzipping {file} without password...", log_level=2)

    timer = threading.Timer(2, _slow_unzip_message)
    timer.start()
    args = build_extract_args(z7path, file, output_dir, use_bandizip=use_bandizip)
    result = subprocess.run(
        args,
        capture_output=True,
        stdin=subprocess.DEVNULL,
        check=False,
    )
    timer.cancel()

    # when using 7z, if the file is password protected, it will return 2 and the error message will contain "Wrong password"
    # when using bandizip, it will return 14 and the error message will contain "Wrong password"
    if is_wrong_password(result):
        log_msg(
            f"Archive {file} is password protected, start to unzip with passwords...",
            log_level=2,
        )
        shutil.rmtree(output_dir, ignore_errors=True)
        has_archive = True
        password_protected = True

    # when using 7z, if the file is not an archive, it will return 2 and the error message will contain "Cannot open the file as archive"
    # when using bandizip, it will return 17 and the error message will contain "Unknown archive"
    if is_not_archive(result):
        if lv == 0:
            log_msg(f'File "{file}" is not an archive', log_level=4)
        # remove the empty directory due to file is not an archive
        shutil.rmtree(output_dir, ignore_errors=True)
        return False, lv
    if result.returncode == 0:
        log_msg(
            f"Archive {file} is not password protected, unzipped to {file}lv{lv:d}",
            log_level=3,
        )
        right_pass_found = True
        has_archive = True
    elif password_protected is False:
        log_msg(f"Unknown error when unzipping {file}", log_level=5)
        log_msg(result.stderr.decode("utf-8", errors="replace"), log_level=5)
        return False, lv

    # try to unzip with password in file name
    if password_protected and not right_pass_found:
        passwords_in_file = get_passwords_from_filename(file, pass_in_file_separator)
        # add these passwords to be begining of the passwords list
        if passwords_in_file:
            passwords = passwords_in_file + passwords
            for password in passwords_in_file:
                timer = threading.Timer(
                    2,
                    _slow_unzip_message,
                    [password],
                )
                timer.start()
                result = subprocess.run(
                    build_extract_args(
                        z7path,
                        file,
                        output_dir,
                        password=password,
                        use_bandizip=use_bandizip,
                    ),
                    capture_output=True,
                    stdin=subprocess.DEVNULL,
                    check=False,
                )
                timer.cancel()
                if is_wrong_password(result):
                    # remove empty files created due to wrong password
                    shutil.rmtree(output_dir, ignore_errors=True)
                else:
                    log_msg(
                        f"Correct password for {file} is {password} (contained in file name), "
                        f"unzipped to {output_dir}",
                        log_level=3,
                    )
                    has_archive = True
                    right_pass_found = True
                    break

    # unzip with password
    if password_protected and not right_pass_found:
        for password in passwords:
            timer = threading.Timer(
                2,
                _slow_unzip_message,
                [password],
            )
            timer.start()
            result = subprocess.run(
                build_extract_args(
                    z7path,
                    file,
                    output_dir,
                    password=password,
                    use_bandizip=use_bandizip,
                ),
                capture_output=True,
                stdin=subprocess.DEVNULL,
                check=False,
            )
            timer.cancel()
            if is_wrong_password(result):
                # remove empty files created due to wrong password
                shutil.rmtree(output_dir, ignore_errors=True)
            else:
                log_msg(
                    f"Correct password for {file} is {password}, unzipped to {output_dir}",
                    log_level=3,
                )
                has_archive = True
                right_pass_found = True
                break

    # no password found for the file
    if not right_pass_found:
        log_msg(f"Cannot find the correct password for {file}", log_level=5)
        return False, lv

    if autodelete:
        remove_archive(file)

    # trying to unzip the files in the directory just created
    if has_archive:
        # check if is the last level
        if check_if_is_last_level(output_dir):
            # the file just unzipped is the final level
            return True, lv

        if lv >= maximum_lv:
            log_msg(
                f"Maximum depth {maximum_lv} reached at {output_dir}, stopping recursion.",
                log_level=4,
            )
            return True, lv

        log_msg(
            f"Archive {file} has been unzipped to {output_dir}, going to next level",
            log_level=3,
        )
        lv += 1
        # recursively unzip the files in the directory just created
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                unzipFileWith7z(
                    os.path.join(root, file),
                    z7path,
                    passwords,
                    autodelete,
                    autodeleteexisting,
                    lv,
                    maximum_lv=maximum_lv,
                    use_bandizip=use_bandizip,
                    pass_in_file_separator=pass_in_file_separator,
                )
        return True, lv
    return False, lv


def move_files_up(dir_path):
    """remove all redundant directories and move all files up to the first level"""
    if not os.path.isdir(dir_path):
        log_msg(f"{dir_path} is not a directory", log_level=5)
        return
    contents = os.listdir(dir_path)
    log_msg(f"Moving files up in {dir_path}", log_level=3)

    if len(contents) == 1 and os.path.isdir(os.path.join(dir_path, contents[0])):
        subdir_path = os.path.join(dir_path, contents[0])
        if os.path.isdir(subdir_path):
            subdir_contents = os.listdir(subdir_path)
            for item in subdir_contents:
                shutil.move(os.path.join(subdir_path, item), dir_path)
            os.rmdir(subdir_path)
            move_files_up(dir_path)


# Backward-compatible aliases.
getPasswordList = get_password_list


def getPassInFileName(file_path):
    return get_passwords_from_filename(
        file_path, settings.get("pass_in_file_separator", "_")
    )
