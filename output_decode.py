"""Helpers to analyze unzipper output for different tools."""

# 7-Zip output messages are directed to stderr, while Bandizip outputs messages to stdout.

import subprocess


def _decoded_output(result: subprocess.CompletedProcess) -> tuple[str, str]:
    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")
    return stdout, stderr


def is_not_archive(result: subprocess.CompletedProcess) -> bool:
    """Check if the file is not an archive based on the result of the unip operation."""
    stdout, stderr = _decoded_output(result)

    # when using 7z, if the file is not an archive, it will return 2 and the error message will contain "Cannot open the file as archive"
    if result.returncode == 2 and "Cannot open the file as archive" in stderr:
        return True

    # when using bandizip, it will return 17 and the error message will contain "Unknown archive"
    if result.returncode == 17 and "Unknown archive" in stdout:
        return True

    return False


def is_wrong_password(result: subprocess.CompletedProcess) -> bool:
    """Check if the archive is password protected based on the result of the unzip operation."""
    stdout, stderr = _decoded_output(result)

    # when using 7z, if the file is password protected, it will return 2 and the error message will contain "Wrong password"
    if result.returncode == 2 and "Wrong password" in stderr:
        return True

    # When 7-Zip prompts for a password with stdin closed, it exits after printing the prompt.
    if result.returncode == 255 and "Enter password" in stdout:
        return True

    # Bandizip reports both wrong-password and password-required cases through stdout.
    if "Invalid password" in stdout:
        return True

    if "Password is needed" in stdout:
        return True

    # when using bandizip, it will return 14 and the error message will contain "Invalid password"
    if result.returncode == 14:
        return True

    return False


def classify_archive_result(result: subprocess.CompletedProcess) -> str:
    """Classify archive command output into a small set of states."""
    if result.returncode == 0:
        return "success"
    if is_wrong_password(result):
        return "wrong_password"
    if is_not_archive(result):
        return "not_archive"
    return "error"
