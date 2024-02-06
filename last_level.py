""" This module contains functions used to check if a directory is the last level of a zip file """
import mimetypes
import os
from setting import Config
from log_msg import log_msg

settings = Config.get_instance().settings


def check_if_is_program(dir_):
    """check if the directory is a program directory, return True if yes, otherwise return False"""
    if not os.path.isdir(dir_):
        return False

    # criteria 1 : files just extracted contains at the same time .dll and .exe files
    contains_dll = False
    contains_exe = False
    for root, dirs, files in os.walk(dir_):
        for file_ in files:
            if file_.endswith(".dll"):
                contains_dll = True
            if file_.endswith(".exe"):
                contains_exe = True

    # criteria 2 : files just extracted contains at the same time .exe files and folders
    contains_folder = False
    if any(os.path.isdir(os.path.join(dir_, item)) for item in os.listdir(dir_)):
        contains_folder = True

    if contains_exe and (contains_folder or contains_dll):
        log_msg(
            f"Files unzipped to {dir_} is a program, will not go to next level",
            log_level=3,
        )
        return True
    else:
        return False


def check_if_is_image_collection(dir_):
    """check if the directory is a image collection directory, return True if yes, otherwise return False"""
    # if a directory contains more than 2 image files return true
    if not os.path.isdir(dir_):
        return False
    image_extensions = [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".tif"]
    image_count = 0
    for root, dirs, files in os.walk(dir_):
        for file_ in files:
            if os.path.splitext(file_)[1].lower() in image_extensions:
                image_count += 1
    if image_count > 2:
        log_msg(
            f"Files unzipped to {dir_} is a image collection, will not go to next level",
            log_level=3,
        )
        return True
    return False


def check_if_is_video_or_video_collection(dir_):
    """check if the directory is a video or video collection directory, return True if yes, otherwise return False"""
    # sometimes there is only one video
    # checking of the file can only be done with the file extension
    has_video_file = False
    for root, dirs, files in os.walk(dir_):
        for file_ in files:
            mimetype, encoding = mimetypes.guess_type(file_)
            if mimetype and mimetype.startswith("video"):
                has_video_file = True
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
