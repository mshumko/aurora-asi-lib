import importlib
import pathlib
from datetime import datetime
from typing import List, Union, Generator, Tuple

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

try:
    import cartopy.crs as ccrs
except ImportError:
    pass  # make sure that asilb.__init__ fully loads and crashes if the user calls asilib.plot_map()

import asilib
import asilib.plot.utils
from asilib.io.load import load_image
from asilib.io.load import load_skymap
from asilib.plot.plot_map import create_cartopy_map
from asilib.plot.plot_map import _pcolormesh_nan
from asilib.analysis.start_generator import start_generator
from asilib.plot.animate_fisheye import _write_movie
from asilib.plot.animate_fisheye import _add_azel_contours
from asilib.plot.animate_fisheye import Images

def animate_map(
    asi_array_code: str, 
    location_code: str, 
    time_range: asilib.io.utils._time_range_type, 
    map_alt: float,
    **kwargs):
    """
    Animate a series of THEMIS or REGO images projected onto a map.

    This function basically runs animate_map_generator() in a for loop. The two function's
    arguments and keyword arguments are identical, so see animate_map_generator() docs for
    the full argument list.

    Note: To make movies, you'll need to install ffmpeg in your operating system.

    Parameters
    ----------
    asi_array_code: str
        The imager array name, i.e. ``THEMIS`` or ``REGO``.
    location_code: str
        The ASI station code, i.e. ``ATHA``
    time_range: list of datetime.datetimes or stings
        Defined the duration of data to download. Must be of length 2.

    Returns
    -------
    None

    Raises
    ------
    NotImplementedError
        If the colormap is unspecified ('auto' by default) and the
        auto colormap is undefined for an ASI array.
    ValueError
        If the color_norm kwarg is not "log" or "lin".
    ImportError
        If the cartopy library can't be imported.
    AssertionError
        If the ASI data exists for that time period, but without time stamps
        inside time_range.

    Example
    -------
    | from datetime import datetime
    |
    | import asilib
    |
    | time_range = (datetime(2015, 3, 26, 6, 7), datetime(2015, 3, 26, 6, 12))
    | asilib.animate_map('THEMIS', 'FSMI', time_range)
    | print(f'Movie saved in {asilib.config["ASI_DATA_DIR"] / "movies"}')
    """
    map_generator = animate_map_generator(asi_array_code, asi_location_code, time_range, map_alt, 
        **kwargs)

    for _ in map_generator:
        pass
    return


@start_generator
def animate_map_generator(
    asi_array_code: str,
    location_code: str,
    time_range: asilib.io.utils._time_range_type,
    map_alt: float,
    min_elevation: float = 10,
    lon_bounds: tuple = (-160, -50), 
    lat_bounds: tuple = (40, 82),
    force_download: bool = False,
    color_map: str = 'auto',
    color_bounds: Union[List[float], None] = None,
    color_norm: str = 'log',
    azel_contours: bool = False,
    ax: plt.Axes = None,
    map_style: str = 'green',
    label: bool = True,
    movie_container: str = 'mp4',
    ffmpeg_output_params={},
    overwrite: bool = False,
    pcolormesh_kwargs : dict = {}
) -> Generator[Tuple[datetime, np.ndarray, plt.Axes, matplotlib.image.AxesImage], None, None]:
    """
    TODO: Update the doc string.
    TODO: Add lat_range and lon_range kwargs and defaults.
    Projects the fisheye images into the ionosphere at map_alt (altitude in kilometers) and 
    animates them using ffmpeg. 

    Once this generator is initiated with the name `gen`, for example, but **before** 
    the for loop, you can get the ASI images and times by calling `gen.send('data')`. 
    This will yield a collections.namedtuple with `time` and `images` attributes.

    Parameters
    ----------
    asi_array_code: str
        The imager array name, i.e. ``THEMIS`` or ``REGO``.
    location_code: str
        The ASI station code, i.e. ``ATHA``
    time_range: list of datetime.datetimes or stings
        Defined the duration of data to download. Must be of length 2.
    map_alt: float
        The altitude in kilometers to project to. Must be an altitude value
        in the skymap calibration.
    min_elevation: floatasilib.plot.utils
        Masks the pixels below min_elevation degrees.
    lon_bounds: tuple
        The map's longitude bounds. If unspecified, the default parameters make a map of Canada.
    lat_bounds: tuple
        The map's latitude bounds. If unspecified, the default parameters make a map of Canada.
    force_download: bool
        If True, download the file even if it already exists. Useful if a prior
        data download was incomplete.
    color_map: str
        The matplotlib colormap to use. If 'auto', will default to a
        black-red colormap for REGO and black-white colormap for THEMIS.
        For more information See
        https://matplotlib.org/3.3.3/tutorials/colors/colormaps.html
    color_bounds: List[float] or None
        The lower and upper values of the color scale. If None, will
        automatically set it to low=1st_quartile and
        high=min(3rd_quartile, 10*1st_quartile)
    ax: plt.Axes
        The optional subplot that will be drawn on.
    map_style: str
        If ax is None, this kwarg toggles between two predefined map styles:
        'green' map has blue oceans and green land, while the `white` map
        has white oceans and land with black coastlines.
    label: bool
        Annotates the map with the ASI code in the center of the image.
    movie_container: str
        The movie container: mp4 has better compression but avi was determined
        to be the official container for preserving digital video by the
        National Archives and Records Administration.
    ffmpeg_output_params: dict
        The additional/overwitten ffmpeg output parameters. The default parameters are:
        framerate=10, crf=25, vcodec=libx264, pix_fmt=yuv420p, preset=slower.
    color_norm: str
        Sets the 'lin' linear or 'log' logarithmic color normalization.
    azel_contours: bool
        Switch azimuth and elevation contours on or off.
    overwrite: bool
        If true, the output will be overwritten automatically. If false it will
        prompt the user to answer y/n.
    pcolormesh_kwargs: dict
        A dictionary of keyword arguments (kwargs) to pass directly into
        plt.pcolormesh. One use of this parameter is to change the colormap. For example,
        pcolormesh_kwargs = {'cmap':'tu}

    Yields
    ------
    image_time: datetime.datetime
        The time of the current image.
    image: np.ndarray
        A 2d image array of the image corresponding to image_time
    ax: plt.Axes
        The subplot object to modify the axis, labels, etc.
    im: plt.AxesImage
        The plt.pcolormesh object.

    Raises
    ------
    NotImplementedError
        If the colormap is unspecified ('auto' by default) and the
        auto colormap is undefined for an ASI array.
    ValueError
        If the color_norm kwarg is not "log" or "lin".
    ImportError
        If the cartopy library can't be imported.
    AssertionError
        If the ASI data exists for that time period, but without time stamps
        inside time_range.

    Example
    -------
    | from datetime import datetime
    |
    | import asilib
    |
    | time_range = (datetime(2015, 3, 26, 6, 7), datetime(2015, 3, 26, 6, 12))
    | map_generator = asilib.animate_map_generator('THEMIS', 'FSMI', time_range)
    |
    | for image_time, image, im, ax in map_generator:
    |       # The code that modifies each image here.
    |       pass
    |
    | print(f'Movie saved in {asilib.config["ASI_DATA_DIR"] / "movies"}')
    """
    # Halt here if cartopy is not installed.
    if importlib.util.find_spec("cartopy") is None:
        raise ImportError(
            "cartopy can't be imported. This is a required dependency for asilib.plot_map()"
            " that must be installed separately. See https://scitools.org.uk/cartopy/docs/latest/installing.html"
            " and https://aurora-asi-lib.readthedocs.io/en/latest/installation.html."
        )

    try:
        image_times, images = load_image(
            asi_array_code, location_code, time_range=time_range, force_download=force_download
        )
    except AssertionError as err:
        if '0 number of time stamps were found in time_range' in str(err):
            print(
                f'The file exists for {asi_array_code}/{location_code}, but no data '
                f'between {time_range}.'
            )
            raise
        else:
            raise
    skymap = load_skymap(asi_array_code, location_code, time_range[0])

    # Create the movie directory inside asilib.config['ASI_DATA_DIR'] if it does
    # not exist.
    image_save_dir = pathlib.Path(
        asilib.config['ASI_DATA_DIR'],
        'movies',
        'images',
        f'{image_times[0].strftime("%Y%m%d_%H%M%S")}_{asi_array_code.lower()}_'
        f'{location_code.lower()}_map',
    )
    if not image_save_dir.is_dir():
        image_save_dir.mkdir(parents=True)
        print(f'Created a {image_save_dir} directory')

    # Check that the map_alt is in the skymap calibration data.
    assert (
        map_alt in skymap['FULL_MAP_ALTITUDE'] / 1000
    ), f'{map_alt} km is not in skymap calibration altitudes: {skymap["FULL_MAP_ALTITUDE"]/1000} km'
    alt_index = np.where(skymap['FULL_MAP_ALTITUDE'] / 1000 == map_alt)[0][0]
    image, lon_map, lat_map = _mask_low_horizon(
        images,
        skymap['FULL_MAP_LONGITUDE'][alt_index, :, :],
        skymap['FULL_MAP_LATITUDE'][alt_index, :, :],
        skymap['FULL_ELEVATION'],
        min_elevation,
    )

    if ax is None:
        ax = create_cartopy_map(map_style=map_style, lon_bounds=lon_bounds, lat_bounds=lat_bounds)

    color_map = asilib.plot.utils.get_color_map(asi_array_code, color_map)

    # With the @start_generator decorator, when this generator first gets called, it
    # will halt here. This way the errors due to missing data will be raised up front.
    # user_input can be used to get the image_times and images out of the generator.
    user_input = yield
    if isinstance(user_input, str) and 'data' in user_input.lower():
        yield Images(image_times, images)

    for image_time, image in zip(image_times, images):
        if 'p' in locals():
            p.remove()

        # if-else statement is to recalculate color_bounds for every image
        # and set it to _color_bounds. If _color_bounds did not exist,
        # color_bounds will be overwritten after the first iteration which will
        # disable the dynamic color bounds for each image.
        if color_bounds is None:
            _color_bounds = asilib.plot.utils.get_color_bounds(image)
        else:
            _color_bounds = color_bounds

        norm = asilib.plot.utils.get_color_norm(color_norm, _color_bounds)

        p = _pcolormesh_nan(
            lon_map, lat_map, image, ax, cmap=color_map, norm=norm, pcolormesh_kwargs=pcolormesh_kwargs
        )

        if azel_contours:
            _add_azel_contours(asi_array_code, location_code, image_time, ax, force_download)

        # Give the user the control of the subplot, image object, and return the image time
        # so that the user can manipulate the image to add, for example, the satellite track.
        yield image_time, image, ax, p

        # Save the plot before the next iteration.
        save_name = (
            f'{image_time.strftime("%Y%m%d_%H%M%S")}_{asi_array_code.lower()}_'
            f'{location_code.lower()}.png'
        )
        plt.savefig(image_save_dir / save_name)

    if label:
        ax.text(
            skymap['SITE_MAP_LONGITUDE'],
            skymap['SITE_MAP_LATITUDE'],
            location_code.upper(),
            color='r',
            transform=ccrs.PlateCarree(),
            va='center',
            ha='center',
        )
    # Make the movie
    movie_file_name = (
        f'{image_times[0].strftime("%Y%m%d_%H%M%S")}_'
        f'{image_times[-1].strftime("%H%M%S")}_'
        f'{asi_array_code.lower()}_{location_code.lower()}_map.{movie_container}'
    )
    _write_movie(image_save_dir, ffmpeg_output_params, movie_file_name, overwrite)
    return


def _mask_low_horizon(images, lon_map, lat_map, el_map, min_elevation):
    """
    Mask the image, skymap['FULL_MAP_LONGITUDE'], skymap['FULL_MAP_LONGITUDE'] arrays
    with np.nans where the skymap['FULL_ELEVATION'] is nan or
    skymap['FULL_ELEVATION'] < min_elevation.
    """
    idh = np.where(np.isnan(el_map) | (el_map < min_elevation))
    # Copy variables to not modify original np.arrays.
    images_copy = images.copy()
    lon_map_copy = lon_map.copy()
    lat_map_copy = lat_map.copy()
    # Can't mask image unless it is a float array.
    image_copy = images_copy.astype(float)
    image_copy[:, idh] = np.nan
    lon_map_copy[idh] = np.nan
    lat_map_copy[idh] = np.nan

    # For some reason the lat/lon_map arrays are one size larger than el_map, so
    # here we mask the boundary indices in el_map by adding 1 to both the rows
    # and columns.
    idh_boundary_bottom = (idh[0] + 1, idh[1])  # idh is a tuple so we have to create a new one.
    idh_boundary_right = (idh[0], idh[1] + 1)
    lon_map_copy[idh_boundary_bottom] = np.nan
    lat_map_copy[idh_boundary_bottom] = np.nan
    lon_map_copy[idh_boundary_right] = np.nan
    lat_map_copy[idh_boundary_right] = np.nan
    return images_copy, lon_map_copy, lat_map_copy

if __name__ == '__main__':
    time_range = (datetime(2015, 3, 26, 6, 7), datetime(2015, 3, 26, 6, 12))
    asi_array_code = 'THEMIS'
    asi_location_code = 'FSMI'
    map_generator = animate_map_generator(asi_array_code, asi_location_code, time_range, 110, overwrite=True)

    for image_time, image, im, ax in map_generator:
        # The code that modifies each image here.
        pass

    print(f'Movie saved in {asilib.config["ASI_DATA_DIR"] / "movies"}')