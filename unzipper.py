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

from archive_backends import resolve_available_backends
from last_level import check_if_is_last_level
from setting import Config
from log_msg import log_msg
from output_decode import classify_archive_result

settings = Config.get_instance().settings


def build_extract_args(
    exe_path, archive_path, output_dir, password=None, use_bandizip=False
):
    """Build command-line arguments for extraction."""
    args = [exe_path, "x", "-y"]
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


def resolve_archive_group(file_path):
    """Resolve a file to the exact archive members that belong together."""
    abs_path = os.path.abspath(file_path)
    dir_path = os.path.dirname(abs_path)
    file_name = os.path.basename(abs_path)
    lower_name = file_name.lower()

    def _existing_members(pattern):
        if not os.path.isdir(dir_path):
            return [abs_path]

        regex = re.compile(pattern, re.IGNORECASE)
        members = [
            os.path.join(dir_path, name)
            for name in os.listdir(dir_path)
            if regex.fullmatch(name)
        ]
        return sorted(set(members)) or [abs_path]

    part_rar = re.fullmatch(r"(?P<root>.+)\.part(?P<index>\d+)\.rar", lower_name)
    if part_rar:
        root = part_rar.group("root")
        index = int(part_rar.group("index"))
        return {
            "kind": "primary" if index == 1 else "non_primary",
            "primary_path": os.path.join(dir_path, f"{root}.part01.rar"),
            "members": _existing_members(re.escape(root) + r"\.part\d+\.rar$"),
        }

    seven_zip_split = re.fullmatch(r"(?P<root>.+\.7z)\.(?P<index>\d{3})", lower_name)
    if seven_zip_split:
        root = seven_zip_split.group("root")
        index = seven_zip_split.group("index")
        return {
            "kind": "primary" if index == "001" else "non_primary",
            "primary_path": os.path.join(dir_path, f"{root}.001"),
            "members": _existing_members(re.escape(root) + r"\.\d{3}$"),
        }

    old_rar_primary = re.fullmatch(r"(?P<root>.+)\.rar", lower_name)
    if old_rar_primary:
        root = old_rar_primary.group("root")
        members = _existing_members(re.escape(root) + r"\.(rar|r\d{2})$")
        if len(members) > 1:
            return {
                "kind": "primary",
                "primary_path": abs_path,
                "members": members,
            }

    old_rar_part = re.fullmatch(r"(?P<root>.+)\.r\d{2}", lower_name)
    if old_rar_part:
        root = old_rar_part.group("root")
        return {
            "kind": "non_primary",
            "primary_path": os.path.join(dir_path, f"{root}.rar"),
            "members": _existing_members(re.escape(root) + r"\.(rar|r\d{2})$"),
        }

    zip_primary = re.fullmatch(r"(?P<root>.+)\.zip", lower_name)
    if zip_primary:
        root = zip_primary.group("root")
        members = _existing_members(re.escape(root) + r"\.(zip|z\d{2})$")
        if len(members) > 1:
            return {
                "kind": "primary",
                "primary_path": abs_path,
                "members": members,
            }

    zip_part = re.fullmatch(r"(?P<root>.+)\.z\d{2}", lower_name)
    if zip_part:
        root = zip_part.group("root")
        return {
            "kind": "non_primary",
            "primary_path": os.path.join(dir_path, f"{root}.zip"),
            "members": _existing_members(re.escape(root) + r"\.(zip|z\d{2})$"),
        }

    generic_split = re.fullmatch(r"(?P<root>.+)\.(?P<index>\d{3})", lower_name)
    if generic_split:
        root = generic_split.group("root")
        index = generic_split.group("index")
        return {
            "kind": "primary" if index == "001" else "non_primary",
            "primary_path": os.path.join(dir_path, f"{root}.001"),
            "members": _existing_members(re.escape(root) + r"\.\d{3}$"),
        }

    return {
        "kind": "single",
        "primary_path": abs_path,
        "members": [abs_path],
    }


def _is_non_primary_multipart(file_path):
    """Return True if file_path is a non-primary part of a multi-part archive."""
    return resolve_archive_group(file_path)["kind"] == "non_primary"


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

    seen = set()
    ordered = []
    for candidate in possible_passwords:
        if candidate and candidate not in seen:
            seen.add(candidate)
            ordered.append(candidate)
    return ordered


def remove_archive(file_path, archive_group=None):
    """Remove the resolved archive members after a successful extraction."""
    if archive_group is None:
        archive_group = resolve_archive_group(file_path)

    matched_files = [
        member for member in archive_group["members"] if os.path.exists(member)
    ]

    log_msg(f"Removing {len(matched_files)} archive part(s)", log_level=3)

    for matched_file in matched_files:
        _send_to_trash(matched_file)


def _send_to_trash(path):
    if send2trash is not None:
        send2trash.send2trash(path)
        return
    os.remove(path)


def _run_extract_command(args, password=None):
    timer_args = [password] if password else []
    timer = threading.Timer(2, _slow_unzip_message, timer_args)
    timer.start()
    try:
        return subprocess.run(
            args,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            check=False,
        )
    finally:
        timer.cancel()


def _collect_password_candidates(file_path, passwords, pass_in_file_separator):
    candidates = get_passwords_from_filename(file_path, pass_in_file_separator)
    candidates.extend(passwords or [])

    ordered = []
    seen = set()
    for password in candidates:
        if not password or password in seen:
            continue
        seen.add(password)
        ordered.append(password)
    return ordered


def _attempt_extraction_with_backend(file_path, output_dir, backend, password=None):
    result = _run_extract_command(
        build_extract_args(
            backend["exe_path"],
            file_path,
            output_dir,
            password=password,
            use_bandizip=backend["use_bandizip"],
        ),
        password=password,
    )
    classification = classify_archive_result(result)
    if classification != "success":
        shutil.rmtree(output_dir, ignore_errors=True)
    return classification, result


def _log_backend_switch(file_path, backend, reason):
    log_msg(
        f"{backend['display_name']} did not finish extracting {file_path} ({reason}); "
        "trying the next backend.",
        log_level=3,
    )


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

    if not os.path.exists(file):
        log_msg(f"File {file} does not exist", log_level=5)
        return False, lv

    if file.endswith(".lib") or file.endswith(".dll") or file.endswith(".exe"):
        log_msg(f"File {file} is a .lib, .dll or .exe file, skipping...", log_level=5)
        return False, lv

    archive_group = resolve_archive_group(file)
    if archive_group["kind"] == "non_primary":
        log_msg(
            f"File {file} is a multi-archive non-primary part, skipping...",
            log_level=5,
        )
        return False, lv

    effective_settings = dict(settings)
    effective_settings["use_bandizip"] = use_bandizip
    if z7path:
        preferred_key = (
            "zip_executable_path_bandizip"
            if use_bandizip
            else "zip_executable_path_7z"
        )
        if not effective_settings.get(preferred_key):
            effective_settings[preferred_key] = z7path
    backends = resolve_available_backends(
        settings=effective_settings,
        preferred_path=z7path,
    )
    if not backends:
        log_msg("No available extraction backend is configured", log_level=5)
        return False, lv

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

    right_pass_found = False
    if not isinstance(file, os.PathLike) and not isinstance(file, str):
        raise TypeError(f"{file} must be a os.PathLike")

    log_msg(f"Unzipping {file} without password...", log_level=2)

    password_candidates = _collect_password_candidates(
        file,
        passwords,
        pass_in_file_separator,
    )
    filename_passwords = set(get_passwords_from_filename(file, pass_in_file_separator))
    saw_password_protected_archive = False
    last_error_result = None
    not_archive_count = 0

    for index, backend in enumerate(backends):
        status, result = _attempt_extraction_with_backend(
            file,
            output_dir,
            backend,
        )
        if status == "success":
            log_msg(
                f"Archive {file} is not password protected, unzipped with "
                f"{backend['display_name']} to {file}lv{lv:d}",
                log_level=3,
            )
            right_pass_found = True
            has_archive = True
            break

        if status == "wrong_password":
            if not saw_password_protected_archive:
                log_msg(
                    f"Archive {file} is password protected, start to unzip with passwords...",
                    log_level=2,
                )
            saw_password_protected_archive = True
            has_archive = True
            password_protected = True

            for password in password_candidates:
                status, result = _attempt_extraction_with_backend(
                    file,
                    output_dir,
                    backend,
                    password=password,
                )
                if status == "success":
                    if password in filename_passwords:
                        log_msg(
                            f"Correct password for {file} is {password} (contained in file name), "
                            f"unzipped with {backend['display_name']} to {output_dir}",
                            log_level=3,
                        )
                    else:
                        log_msg(
                            f"Correct password for {file} is {password}, "
                            f"unzipped with {backend['display_name']} to {output_dir}",
                            log_level=3,
                        )
                    has_archive = True
                    right_pass_found = True
                    break
                if status == "error":
                    last_error_result = result

            if right_pass_found:
                break

            if index < len(backends) - 1:
                _log_backend_switch(file, backend, "password attempts exhausted")
            continue

        if status == "not_archive":
            not_archive_count += 1
            if index < len(backends) - 1:
                _log_backend_switch(file, backend, "archive open failed")
            continue

        last_error_result = result
        if index < len(backends) - 1:
            _log_backend_switch(file, backend, "command failed")

    if not right_pass_found:
        if password_protected:
            log_msg(f"Cannot find the correct password for {file}", log_level=5)
            return False, lv
        if not_archive_count == len(backends):
            if lv == 0:
                log_msg(f'File "{file}" is not an archive', log_level=4)
            return False, lv
        if last_error_result is not None:
            log_msg(f"Unknown error when unzipping {file}", log_level=5)
            log_msg(last_error_result.stderr.decode("utf-8", errors="replace"), log_level=5)
            return False, lv
        return False, lv

    if autodelete:
        remove_archive(file, archive_group=archive_group)

    if has_archive:
        if check_if_is_last_level(output_dir):
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
        for root, dirs, files in os.walk(output_dir):
            for nested_file in files:
                unzipFileWith7z(
                    os.path.join(root, nested_file),
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
