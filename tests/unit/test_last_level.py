import os
import tempfile
import unittest
from unittest import mock

import last_level


class TestLastLevel(unittest.TestCase):
    def test_genuine_video_directory_stays_terminal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "clip.mp4")
            with open(path, "wb") as handle:
                handle.write(b"not-a-real-video")

            with mock.patch(
                "last_level.probe_archive_with_backends",
                return_value=False,
            ):
                self.assertTrue(last_level.check_if_is_last_level(temp_dir))

    def test_disguised_video_directory_keeps_recursing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "clip.mp4")
            with open(path, "wb") as handle:
                handle.write(b"not-a-real-video")

            with mock.patch(
                "last_level.probe_archive_with_backends",
                return_value=True,
            ):
                self.assertFalse(last_level.check_if_is_last_level(temp_dir))


if __name__ == "__main__":
    unittest.main()
