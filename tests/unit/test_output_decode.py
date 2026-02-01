import unittest
from subprocess import CompletedProcess

from output_decode import is_not_archive, is_wrong_password


class TestOutputDecode(unittest.TestCase):
    def test_is_not_archive_7zip(self):
        result = CompletedProcess(
            args=["7z.exe"],
            returncode=2,
            stdout=b"",
            stderr=b"Cannot open the file as archive",
        )
        self.assertTrue(is_not_archive(result))

    def test_is_not_archive_bandizip(self):
        result = CompletedProcess(
            args=["bz.exe"],
            returncode=17,
            stdout=b"Unknown archive",
            stderr=b"",
        )
        self.assertTrue(is_not_archive(result))

    def test_is_wrong_password_7zip(self):
        result = CompletedProcess(
            args=["7z.exe"],
            returncode=2,
            stdout=b"",
            stderr=b"Wrong password",
        )
        self.assertTrue(is_wrong_password(result))

    def test_is_wrong_password_bandizip(self):
        result = CompletedProcess(
            args=["bz.exe"],
            returncode=14,
            stdout=b"Invalid password",
            stderr=b"",
        )
        self.assertTrue(is_wrong_password(result))


if __name__ == "__main__":
    unittest.main()
