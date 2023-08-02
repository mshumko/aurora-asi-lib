import unittest
import pathlib
from datetime import date, datetime

import numpy as np

from asilib.analysis.map import lla2azel

"""
Tests that the LLA to AzEl projecting (mapping) returns correct outputs
for the Athabasca (ATHA) THEMIS and REGO imagers. The LLA is assumed 
overhead and at 500 km altitude.
"""


class TestProjectLLAtoSkyfield(unittest.TestCase):
    def setUp(self):
        self.location_code = 'LUCK'
        self.time = datetime(2020, 1, 1)
        return

    def test_themis_lla_to_azel(self):
        """
        Tests that the input LLA corresponds to right overhead of the THEMIS ATHA
        imager (elevation ~ 90 degrees) and (az_index, el_index) ~= (127, 127).
        """
        lla = np.array([54.60, -113.644, 500])
        azel, pixel_index = lla2azel('THEMIS', 'ATHA', self.time, lla)

        # Test the El values
        self.assertEqual(round(azel[1]), 90)

        # Test that the AzEl indices are witin 3 pixels of zenith.
        self.assertTrue(abs(pixel_index[0] - 133) < 3)
        return

    def test_rego_lla_to_azel(self):
        """
        Tests that the input LLA corresponds to right overhead of the ATHA REGO imager
        (elevation ~ 90 degrees) and (az_index, el_index) ~= (127, 127).
        """
        lla = np.array([54.60, -113.64, 500])
        azel, pixel_index = lla2azel('REGO', 'ATHA', self.time, lla)

        # Test the AzEl values
        self.assertEqual(round(azel[0]), 137)
        self.assertEqual(round(azel[1]), 90)

        # Test that the AzEl indices are within 15 pixels of zenith.
        self.assertTrue(abs(pixel_index[0] - 256) < 15)
        self.assertTrue(abs(pixel_index[0] - 256) < 15)
        return

    def test_rego_lla_to_azel_track(self):
        """
        Tests that the input LLA track corresponds to a north-south
        path other REGO/ATHA.

        ATHA is at lon=-113, and the satellite track is lon=-112
        (the pass is to the east). The azimuth values should go
        0 -> 90 -> 180 degrees and not 0 -> 270 -> 180 degrees
        """
        n = 10
        lats = np.linspace(70, 40, n)
        lons = -112.64 * np.ones(n)
        alts = 500 * np.ones(n)
        lla = np.array([lats, lons, alts]).T

        sat_azel, asi_pixels = lla2azel('REGO', 'ATHA', self.time, lla)

        reference_sat_azel = np.array(
            [
                [1.29535674, 7.86276448],
                [1.9053143, 13.57476298],
                [2.97096799, 21.86606296],
                [5.32950314, 35.80304471],
                [14.9730986, 62.57537388],
                [154.58750264, 71.34691226],
                [171.98265159, 40.62183087],
                [175.0067123, 24.4947799],
                [176.25685658, 15.2649472],
                [176.94287565, 9.09964082],
            ]
        )

        reference_asi_pixels = np.array(
            [
                [268.0, 469.0],
                [270.0, 454.0],
                [272.0, 432.0],
                [276.0, 395.0],
                [282.0, 323.0],
                [286.0, 211.0],
                [286.0, 126.0],
                [284.0, 84.0],
                [283.0, 59.0],
                [282.0, 43.0],
            ]
        )
        np.testing.assert_array_almost_equal(sat_azel, reference_sat_azel)
        np.testing.assert_array_almost_equal(asi_pixels, reference_asi_pixels)
        return


if __name__ == '__main__':
    unittest.main()
