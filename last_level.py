"""Helpers for deciding whether an extracted directory is terminal output."""

import mimetypes
import os

from archive_backends import probe_archive_with_backends
from log_msg import log_msg


def check_if_is_program(dir_):
    """check if the directory is a program directory, return True if yes, otherwise return False"""
    if not os.path.isdir(dir_):
        return False

    contains_dll = False
    contains_exe = False
    for root, dirs, files in os.walk(dir_):
        for file_ in files:
            if file_.endswith(".dll"):
                contains_dll = True
            if file_.endswith(".exe"):
                contains_exe = True

    contains_folder = False
    if any(os.path.isdir(os.path.join(dir_, item)) for item in os.listdir(dir_)):
        contains_folder = True

    if contains_exe and (contains_folder or contains_dll):
        log_msg(
            f"Files unzipped to {dir_} is a program, will not go to next level",
            log_level=3,
        )
        return True
    return False


def check_if_is_image_collection(dir_):
    """check if the directory is a image collection directory, return True if yes, otherwise return False"""
    if not os.path.isdir(dir_):
        return False

    image_extensions = [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".tif"]
    image_count = 0
    for root, dirs, files in os.walk(dir_):
        for file_ in files:
            if os.path.splitext(file_)[1].lower() in image_extensions:
                image_count += 1
    if image_count > 4:
        log_msg(
            f"Files unzipped to {dir_} is a image collection, will not go to next level",
            log_level=3,
        )
        return True
    return False


def _is_video_like_file(file_name):
    mimetype, encoding = mimetypes.guess_type(file_name)
    return bool(mimetype and mimetype.startswith("video"))


def check_if_is_video_or_video_collection(dir_):
    """Return True when the directory only contains terminal video-like output."""
    has_video_file = False
    for root, dirs, files in os.walk(dir_):
        for file_ in files:
            if not _is_video_like_file(file_):
                continue

            has_video_file = True
            file_path = os.path.join(root, file_)
            if probe_archive_with_backends(file_path):
                log_msg(
                    f"Media-like file {file_path} can still be opened as an archive; "
                    "continuing recursion.",
                    log_level=3,
                )
                return False
    return has_video_file


def check_if_is_last_level(dir_):
    """check if the file just unzipped to dir_ is the last level, return True if yes, otherwise return False"""
    if not os.path.isdir(dir_):
        return False
    if check_if_is_program(dir_):
        return True
    if check_if_is_image_collection(dir_):
        return True
    if check_if_is_video_or_video_collection(dir_):
        return True
    return False
