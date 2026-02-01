"""Helpers to analyze unzipper output for different tools."""

# 7-Zip output messages are directed to stderr, while Bandizip outputs messages to stdout.

import subprocess


def is_not_archive(result: subprocess.CompletedProcess) -> bool:
    """Check if the file is not an archive based on the result of the unip operation."""
    # when using 7z, if the file is not an archive, it will return 2 and the error message will contain "Cannot open the file as archive"
    if (
        result.returncode == 2
        and "Cannot open the file as archive"
        in result.stderr.decode("utf-8", errors="replace")
    ):
        return True

    # when using bandizip, it will return 17 and the error message will contain "Unknown archive"
    if result.returncode == 17 and "Unknown archive" in result.stdout.decode(
        "utf-8", errors="replace"
    ):
        return True

    return False


def is_wrong_password(result: subprocess.CompletedProcess) -> bool:
    """Check if the archive is password protected based on the result of the unzip operation."""
    # when using 7z, if the file is password protected, it will return 2 and the error message will contain "Wrong password"
    # this is for 7zip
    if result.returncode == 2 and "Wrong password" in result.stderr.decode(
        "utf-8", errors="replace"
    ):
        return True
    # this is for bandizip
    if "Invalid password" in result.stdout.decode("utf-8", errors="replace"):
        return True

    # when using bandizip, it will return 14 and the error message will contain "Invalid password"
    if result.returncode == 14 or "Invalid password" in result.stdout.decode(
        "utf-8", errors="replace"
    ):
        return True

    return False
