"""
Tests asilib/analysis.equal_area.py
"""

from datetime import datetime
import unittest
import pathlib

import pytest
import numpy as np

import asilib
from asilib.io.load import load_skymap
from asilib.analysis.equal_area import _dlon, _dlat

# Number of km in a degree of latitude. Also a degree of longitude at the equator
deg_distance_km = 111.321


class Test_equal_area(unittest.TestCase):
    def test_dlat(self):
        """
        Tests the _dlat() helper function. Given one altitude, these should be the same.
        https://www.thoughtco.com/degree-of-latitude-and-longitude-distance-4070616
        """
        # Check that one degree of latitude is ~111 km at sea-level
        assert np.isclose(
            _dlat(deg_distance_km, 0), 1, rtol=0.005
        )  # rtol=0.005 -> 0.5 km accuracy.
        # Same, but for array inputs
        assert np.all(np.isclose(_dlat(3 * [deg_distance_km], [0, 0, 0]), [1, 1, 1], rtol=0.005))
        assert np.all(
            np.isclose(
                _dlat(deg_distance_km * np.ones(3), np.array([0, 0, 0])), [1, 1, 1], rtol=0.005
            )
        )
        return

    def test_dlon(self):
        """
        Tests the _dlon() helper function
        https://www.thoughtco.com/degree-of-latitude-and-longitude-distance-4070616
        """
        # A degree of longitude at the equator is 111.321 km.
        assert np.isclose(_dlon(deg_distance_km, 0, 0), 1, rtol=0.005)
        assert np.all(
            np.isclose(_dlon(3 * [deg_distance_km], 3 * [0], 3 * [0]), np.ones(1), rtol=0.005)
        )
        assert np.all(
            np.isclose(
                _dlon(deg_distance_km * np.ones(3), np.zeros(3), np.zeros(3)),
                np.ones(1),
                rtol=0.005,
            )
        )

        # Test at lat = +/-40 degrees
        assert np.isclose(_dlon(85, 0, 40), 1, rtol=0.005)
        assert np.isclose(_dlon(85, 0, -40), 1, rtol=0.005)
        return

    def test_equal_area(self, create_reference=False):
        asi_array_code = 'THEMIS'
        location_code = 'RANK'
        time = datetime(2020, 1, 1)
        skymap_dict = load_skymap(asi_array_code, location_code, time, redownload=True)

        # Set up a north-south satellite track oriented to the east of the THEMIS/RANK
        # imager.
        n = 10
        lats = np.linspace(
            skymap_dict["SITE_MAP_LATITUDE"] + 5, skymap_dict["SITE_MAP_LATITUDE"] - 5, n
        )
        lons = (skymap_dict["SITE_MAP_LONGITUDE"] - 0.5) * np.ones(n)
        alts = 110 * np.ones(n)
        lla = np.array([lats, lons, alts]).T

        area_box_mask = asilib.equal_area(asi_array_code, location_code, time, lla, box_km=(20, 20))

        reference_path = pathlib.Path(
            asilib.config['ASILIB_DIR'], 'tests', 'data', 'area_box_mask.npy'
        )
        if create_reference:
            np.save(reference_path, area_box_mask)
        else:
            area_box_mask_reference = np.load(reference_path)
            assert np.array_equal(area_box_mask, area_box_mask_reference, equal_nan=True)
        return

    def test_equal_area_below_horizon(self):
        asi_array_code = 'THEMIS'
        location_code = 'RANK'
        time = datetime(2020, 1, 1)
        skymap_dict = load_skymap(asi_array_code, location_code, time)

        # Set up a north-south satellite track oriented to the east of the THEMIS/RANK
        # imager.
        n = 10
        lats = np.linspace(0, 5, n)  # Just above the equator, way below the horizon.
        lons = (skymap_dict["SITE_MAP_LONGITUDE"] - 0.5) * np.ones(n)
        alts = 110 * np.ones(n)
        lla = np.array([lats, lons, alts]).T
        with pytest.warns(UserWarning):
            area_box_mask = asilib.equal_area(
                asi_array_code, location_code, time, lla, box_km=(20, 20)
            )
        assert np.all(np.isnan(area_box_mask))
        return


if __name__ == '__main__':
    unittest.main()
