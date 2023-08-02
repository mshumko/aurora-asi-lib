import unittest
import pathlib
from datetime import datetime

import asilib

"""
Unit tests to check that the functions in download_rego.py are working correctly.
Run with "python3 test_download_rego.py -v" for the verbose output.
"""


class TestDownloadRego(unittest.TestCase):
    def setUp(self):
        """Set up a few variables."""
        self.day = datetime(2020, 8, 1, 4)
        self.location_code = 'Luck'
        self.asi_array_code = 'rEGO'
        return

    def test_download_img(self):
        """
        Test the REGO data downloader to download an hour file
        clg_l1_rgf_luck_2020080104_v01.cdf to ./rego/.
        """
        image_dir = pathlib.Path(asilib.config['ASI_DATA_DIR'], 'rego')
        image_path = image_dir / 'clg_l1_rgf_luck_2020080104_v01.cdf'

        save_path = asilib.download_image(
            self.asi_array_code, self.location_code, time=self.day, redownload=True
        )

        assert image_path == save_path[0]
        assert image_path.is_file()
        return


if __name__ == '__main__':
    unittest.main()
