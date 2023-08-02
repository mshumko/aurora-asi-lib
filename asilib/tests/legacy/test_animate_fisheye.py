import unittest
from datetime import datetime

import asilib


class TestAnimateFisheye(unittest.TestCase):
    def test_animate_fisheye_generator(self):
        """Checks that the example in animate_fisheye_generator() works."""
        time_range = (datetime(2015, 3, 26, 6, 7), datetime(2015, 3, 26, 6, 12))
        movie_generator = asilib.animate_fisheye_generator(
            'THEMIS', 'FSMI', time_range, azel_contours=True, overwrite=True
        )

        for image_time, image, im, ax in movie_generator:
            # The code that modifies each image here.
            pass
        return

    def test_animate_fisheye(self):
        """Checks that animate_fisheye() works."""
        time_range = (datetime(2015, 3, 26, 6, 7), datetime(2015, 3, 26, 6, 12))
        asilib.animate_fisheye('THEMIS', 'FSMI', time_range, azel_contours=True, overwrite=True)
        return

    def test_animate_fisheye_generator_send(self):
        """Check that the generator function and the .send() method works"""
        time_range = (datetime(2015, 3, 26, 6, 7), datetime(2015, 3, 26, 6, 12))
        gen = asilib.animate_fisheye_generator(
            'THEMIS', 'FSMI', time_range, azel_contours=True, overwrite=True
        )
        tup = gen.send("get_image_data")
        self.assertEqual(tup.time.shape, (100,))
        self.assertEqual(tup.images.shape, (100, 256, 256))


if __name__ == '__main__':
    unittest.main()
