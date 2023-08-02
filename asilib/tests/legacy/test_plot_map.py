""" 
Tests for plot_map.py.
"""
import unittest
from datetime import datetime

import asilib
from asilib.plot.plot_map import plot_map


class Test_plot_map(unittest.TestCase):
    def test_steve_map(self):
        """
        Tests that plot_map() doesn't crash when making this plot:
        http://themis.igpp.ucla.edu/nuggets/nuggets_2018/Gallardo-Lacourt/fig2.jpg.
        """
        plot_map('THEMIS', 'ATHA', datetime(2010, 4, 5, 6, 7, 0), 110)
        return

    def test_plot_map_altitude_error(self):
        """
        Checks that plto_map() raises an AssertionError if map_alt is not
        in the list of skymap calibration altitudes.
        """
        with self.assertRaises(AssertionError):
            plot_map('THEMIS', 'ATHA', datetime(2010, 4, 5, 6, 7, 0), 500)
        return

    def test_donovan_et_al_2008_plot(self):
        """
        Checks that Figure 2b from Donovan et al. 2008 successfully plots.

        https://agupubs.onlinelibrary.wiley.com/doi/pdf/10.1029/2008GL033794
        """
        time = datetime(2007, 3, 13, 5, 8, 45)
        asi_array_code = 'THEMIS'
        location_codes = ['FSIM', 'ATHA', 'TPAS', 'SNKQ']
        map_alt = 110
        min_elevation = 2

        ax = asilib.make_map(lon_bounds=(-160, -52), lat_bounds=(40, 82))

        for location_code in location_codes:
            plot_map(
                asi_array_code, location_code, time, map_alt, ax=ax, min_elevation=min_elevation
            )

        ax.set_title('Donovan et al. 2008 | First breakup of an auroral arc')


if __name__ == '__main__':
    unittest.main()
