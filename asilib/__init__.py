import pathlib
import configparser

__version__ = '0.11.0'

# Load the configuration settings.
HERE = pathlib.Path(__file__).parent.resolve()
settings = configparser.ConfigParser()
settings.read(HERE / 'config.ini')

try:
    ASI_DATA_DIR = settings['Paths'].get('ASI_DATA_DIR', pathlib.Path.home() / 'asilib-data')
    ASI_DATA_DIR = pathlib.Path(ASI_DATA_DIR)
except KeyError:  # Raised if config.ini does not have Paths.
    ASI_DATA_DIR = pathlib.Path.home() / 'asilib-data'

config = {'ASILIB_DIR': HERE, 'ASI_DATA_DIR': ASI_DATA_DIR}

# Import download programs.
from asilib.io.download import download_image
from asilib.io.download import download_skymap

# Import the loading functions.
from asilib.io.load import load_skymap
from asilib.io.load import load_image
from asilib.io.load import load_image_generator
from asilib.io.load import get_frame  # Deprecated
from asilib.io.load import get_frames  # Deprecated

# Import the plotting and animating functions.
from asilib.plot.plot_fisheye import plot_fisheye
from asilib.plot.plot_fisheye import plot_frame  # Deprecated
from asilib.plot.plot_fisheye import plot_image  # Deprecated
from asilib.plot.plot_map import plot_map
from asilib.plot.plot_map import make_map
from asilib.plot.plot_keogram import plot_keogram
from asilib.plot.animate_fisheye import plot_movie  # Deprecated
from asilib.plot.animate_fisheye import plot_movie_generator  # Deprecated
from asilib.plot.animate_fisheye import animate_fisheye
from asilib.plot.animate_fisheye import animate_fisheye_generator
from asilib.plot.animate_map import animate_map
from asilib.plot.animate_map import animate_map_generator

# Import the analysis functions.
from asilib.analysis.map import lla2azel
from asilib.analysis.map import lla2footprint
from asilib.analysis.keogram import keogram
from asilib.analysis.equal_area import equal_area
