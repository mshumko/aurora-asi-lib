import unittest
from datetime import datetime

import asilib


class TestAnimateMap(unittest.TestCase):
    def test_animate_map_generator(self):
        """Checks that the example in animate_map_generator() works."""
        time_range = (datetime(2015, 3, 26, 6, 7), datetime(2015, 3, 26, 6, 12))
        movie_generator = asilib.animate_map_generator(
            'THEMIS', 'FSMI', time_range, 110, overwrite=True
        )

        for image_time, image, im, ax in movie_generator:
            # The code that modifies each image here.
            pass
        return

    def test_animate_map(self):
        """Checks that animate_map() works."""
        time_range = (datetime(2015, 3, 26, 6, 7), datetime(2015, 3, 26, 6, 12))
        asilib.animate_map('THEMIS', 'FSMI', time_range, 110, overwrite=True)
        return

    def test_animate_map_generator_send(self):
        """Check that the generator function and the .send() method works"""
        time_range = (datetime(2015, 3, 26, 6, 7), datetime(2015, 3, 26, 6, 12))
        gen = asilib.animate_map_generator('THEMIS', 'FSMI', time_range, 110, overwrite=True)
        tup = gen.send("get_image_data")
        self.assertEqual(tup.time.shape, (100,))
        self.assertEqual(tup.images.shape, (100, 256, 256))


if __name__ == '__main__':
    unittest.main()
