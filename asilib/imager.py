"""
asilib.Imager provides methods to load ASI time stamps and images, as well as
basic plotting methods.

.. note::
    Most of the basic asilib operations are to download and load large amounts
    of images. Therefore, your performance is largely impacted by your internet speed
    and the type of hard drive/memory on your machine. 
"""
import datetime
import dateutil.parser
import pathlib
import inspect
import shutil
import copy
from collections import namedtuple
from typing import List, Tuple, Generator, Union
import warnings

import numpy as np
import numpy.linalg
import numpy.polynomial
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import ffmpeg
import aacgmv2

try:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    import cartopy.mpl.geoaxes

    cartopy_imported = True
except ImportError as err:
    # You can also get a ModuleNotFoundError if cartopy is not installed
    # (as compared to failed to import), but it is a subclass of ImportError.
    cartopy_imported = False

import asilib
import asilib.map
import asilib.utils as utils


class Imager:
    """
    The central asilib class to plot, animate, and analyze ASI data.

    Normally asilib.Imager() should not be directly called by users, but by the ASI wrapper functions.
    This interface is thoroughly documented in the :ref:`contribute_asi` documentation page.

    Parameters
    ----------
    file_info: dict
        Specifies image file paths, start end end times for each file, the loader function,
        and if the user needs one or multiple images.
    meta: dict
        Specifies ASI metadata that describes the ASI name, location, cadence, and pixel resolution.
    skymap: dict
        Specifies what each pixel maps to in (azimuth, elevation) coordinates as well as
        (latitude, longitude) coordinates at a prescribed auroral mission altitude.
    plot_settings: dict
        An optional dictionary customizing the plot colormap, color scale (logarithmic vs linear),
        and color bounds (vmin, vmax arguments in matplotlib.imshow()).
    """

    def __init__(
        self,
        file_info: dict,
        meta: dict,
        skymap: dict,
        plot_settings: dict = {},
    ) -> None:
        self.file_info = {k.lower(): v for k, v in file_info.items()}
        self.meta = {k.lower(): v for k, v in meta.items()}
        self.skymap = {k.lower(): v for k, v in skymap.items()}
        self.plot_settings = {k.lower(): v for k, v in plot_settings.items()}
        self._accumulate_n = 1
        return

    def plot_fisheye(
        self,
        ax: plt.Axes = None,
        label: bool = True,
        color_map: str = None,
        color_bounds: List[float] = None,
        color_norm: str = None,
        azel_contours: bool = False,
        azel_contour_color: str = 'yellow',
        cardinal_directions: str = 'NE',
        origin: tuple = (0.8, 0.1),
    ) -> Tuple[plt.Axes, matplotlib.collections.QuadMesh]:
        """
        Plots one fisheye image, oriented with North on the top, and East on the left of the image.

        Parameters
        ----------
        ax: plt.Axes
            The subplot to plot the image on. If None this method will create one.
        label: bool
            Flag to add the "asi_array_code/location_code/image_time" text to the plot.
        color_map: str
            The matplotlib colormap to use. By default will use a black-white colormap.
            For more information See `matplotlib colormaps <https://matplotlib.org/stable/tutorials/colors/colormaps.html>`_.
        color_bounds: List[float]
            The lower and upper values of the color scale. The default is: low=1st_quartile and
            high=min(3rd_quartile, 10*1st_quartile). This range works well for most cases.
        color_norm: str
            Set the 'lin' (linear) or 'log' (logarithmic) color normalization. If color_norm=None,
            the color normalization will be taken from the ASI array (if specified), and if not
            specified it will default to logarithmic.
        azel_contours: bool
            Superpose azimuth and elevation contours on or off.
        azel_contour_color: str
            The color of the azimuth and elevation contours.
        cardinal_directions: str
            Plot one or more cardinal directions specified with a string containing the first
            letter of one or more cardinal directions. Case insensitive. For example, to plot
            the North and East directions, set cardinal_directions='NE'.
        origin: tuple
            The origin of the cardinal direction arrows.

        Returns
        -------
        ax: plt.Axes
            The subplot object to modify the axis, labels, etc.
        im: matplotlib.collections.QuadMesh
            The plt.imshow image object. Common use for im is to add a colorbar.
            The image is oriented in the map orientation (north is up, south is down,
            west is right, and east is left). Set azel_contours=True to confirm.

        Raises
        ------
        NotImplementedError
            If the colormap is unspecified ('auto' by default) and the
            auto colormap is undefined for an ASI array.
        ValueError
            If the color_norm kwarg is not "log" or "lin".

        Example
        -------
        >>> # A bright auroral arc that was analyzed by Imajo et al., 2021 "Active
        >>> # auroral arc powered by accelerated electrons from very high altitudes"
        >>> from datetime import datetime
        >>> import matplotlib.pyplot as plt
        >>> import asilib.asi
        >>>
        >>> asi = asilib.asi.themis('RANK', time=datetime(2017, 9, 15, 2, 34, 0))
        >>> ax, im = asi.plot_fisheye(cardinal_directions='NE', origin=(0.95, 0.05))
        >>> plt.colorbar(im)
        >>> ax.axis('off')
        >>> plt.show()
        """
        if ax is None:
            _, ax = plt.subplots()

        self_copy = self.__getitem__(self.file_info['time'])
        time, image = self_copy.data

        color_map, color_norm = self._plot_params(image, color_bounds, color_map, color_norm)

        im = ax.imshow(image, cmap=color_map, norm=color_norm, origin="lower")
        if label:
            self._add_fisheye_label(time, ax)
        if azel_contours:
            self._add_azel_contours(ax, color=azel_contour_color)
        if cardinal_directions is not None:
            self._add_cardinal_directions(ax, cardinal_directions, origin=origin)
        return ax, im

    def animate_fisheye(self, **kwargs) -> None:
        """
        A wrapper for the ```animate_fisheye_gen()``` method that animates a series of
        fisheye images. Any kwargs are passed directly into ```animate_fisheye_gen()```.

        Parameters
        ----------
        ax: plt.Axes
            The optional subplot that will be drawn on.
        label: bool
            Flag to add the "asi_array_code/location_code/image_time" text to the plot.
        color_map: str
            The matplotlib colormap to use. By default will use a black-white colormap.
            For more information See `matplotlib colormaps <https://matplotlib.org/stable/tutorials/colors/colormaps.html>`_.
        color_bounds: List[float]
            The lower and upper values of the color scale. The default is: low=1st_quartile and
            high=min(3rd_quartile, 10*1st_quartile). This range works well for most cases.
        color_norm: str
            Set the 'lin' (linear) or 'log' (logarithmic) color normalization. If color_norm=None,
            the color normalization will be taken from the ASI array (if specified), and if not
            specified it will default to logarithmic.
        azel_contours: bool
            Superpose azimuth and elevation contours on or off.
        azel_contour_color: str
            The color of the azimuth and elevation contours.
        cardinal_directions: str
            Plot one or more cardinal directions specified with a string containing the first
            letter of one or more cardinal directions. Case insensitive. For example, to plot
            the North and East directions, set cardinal_directions='NE'.
        origin: tuple
            The origin of the cardinal direction arrows.
        movie_container: str
            The movie container: mp4 has better compression but avi was determined
            to be the official container for preserving digital video by the
            National Archives and Records Administration.
        ffmpeg_params: dict
            The additional/overwitten ffmpeg output parameters. The default parameters are:
            framerate=10, crf=25, vcodec=libx264, pix_fmt=yuv420p, preset=slower.
        overwrite: bool
            If true, the output will be overwritten automatically. If false it will
            prompt the user to answer y/n.

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

        Example
        -------
        >>> from datetime import datetime
        >>> import asilib.asi
        >>>
        >>> time_range = (datetime(2015, 3, 26, 6, 7), datetime(2015, 3, 26, 6, 12))
        >>> asi = asilib.asi.themis('FSMI', time_range=time_range)
        >>> asi.animate_fisheye(cardinal_directions='NE', origin=(0.95, 0.05), overwrite=True)
        >>> print(f'Animation saved in {asilib.config["ASI_DATA_DIR"] / "animations" / asi.animation_name}')
        """
        movie_generator = self.animate_fisheye_gen(**kwargs)

        for _ in movie_generator:
            pass
        return

    def animate_fisheye_gen(
        self,
        ax: plt.Axes = None,
        label: bool = True,
        color_map: str = None,
        color_bounds: List[float] = None,
        color_norm: str = None,
        azel_contours: bool = False,
        azel_contour_color: str = 'yellow',
        cardinal_directions: str = 'NE',
        origin: tuple = (0.8, 0.1),
        movie_container: str = 'mp4',
        ffmpeg_params={},
        overwrite: bool = False,
    ) -> Generator[
        Tuple[datetime.datetime, np.ndarray, plt.Axes, matplotlib.collections.QuadMesh], None, None
    ]:
        """
        Animate a series of fisheye images and superpose your data on each image.

        A generator behaves like an iterator in that it plots one fisheye image
        at a time and yields (similar to returns) the image. You can modify, or add
        content to the image (such as a spacecraft position). Then, once the iteration
        is complete, this method stitches the images into an animation. See the examples
        below and in the examples page for use cases. The ```animate_fisheye()``` method
        takes care of the iteration.

        Parameters
        ----------
        ax: plt.Axes
            The optional subplot that will be drawn on.
        label: bool
            Flag to add the "asi_array_code/location_code/image_time" text to the plot.
        color_map: str
            The matplotlib colormap to use. By default will use a black-white colormap.
            For more information See `matplotlib colormaps <https://matplotlib.org/stable/tutorials/colors/colormaps.html>`_.
        color_bounds: List[float]
            The lower and upper values of the color scale. The default is: low=1st_quartile and
            high=min(3rd_quartile, 10*1st_quartile). This range works well for most cases.
        color_norm: str
            Set the 'lin' (linear) or 'log' (logarithmic) color normalization. If color_norm=None,
            the color normalization will be taken from the ASI array (if specified), and if not
            specified it will default to logarithmic.
        azel_contours: bool
            Superpose azimuth and elevation contours on or off.
        azel_contour_color: str
            The color of the azimuth and elevation contours.
        cardinal_directions: str
            Plot one or more cardinal directions specified with a string containing the first
            letter of one or more cardinal directions. Case insensitive. For example, to plot
            the North and East directions, set cardinal_directions='NE'.
        origin: tuple
            The origin of the cardinal direction arrows.
        movie_container: str
            The movie container: mp4 has better compression but avi was determined
            to be the official container for preserving digital video by the
            National Archives and Records Administration.
        ffmpeg_params: dict
            The additional/overwitten ffmpeg output parameters. The default parameters are:
            framerate=10, crf=25, vcodec=libx264, pix_fmt=yuv420p, preset=slower.
        overwrite: bool
            Overwrite the animation. If False, ffmpeg will prompt you to answer y/n if the
            animation already exists.

        Yields
        ------
        image_time: datetime.datetime
            The time of the current image.
        image: np.ndarray
            A 2d image array of the image corresponding to image_time
        ax: plt.Axes
            The subplot object to modify the axis, labels, etc.
        im: matplotlib.collections.QuadMesh
            The plt.imshow image object. Common use for im is to add a colorbar.
            The image is oriented in the map orientation (north is up, south is down,
            west is right, and east is left). Set azel_contours=True to confirm.

        Raises
        ------
        NotImplementedError
            If the colormap is unspecified ('auto' by default) and the
            auto colormap is undefined for an ASI array.
        ValueError
            If the color_norm kwarg is not "log" or "lin".

        Example
        -------
        >>> from datetime import datetime
        >>> import asilib.asi
        >>> import asilib
        >>>
        >>> time_range = (datetime(2015, 3, 26, 6, 7), datetime(2015, 3, 26, 6, 12))
        >>> asi = asilib.asi.themis('FSMI', time_range=time_range)
        >>> gen = asi.animate_fisheye_gen(cardinal_directions='NE', origin=(0.95, 0.05), overwrite=True)
        >>> for image_time, image, ax, im in gen:
        ...         # Add your code that modifies each image here.
        ...         pass
        ...
        >>> print(f'Animation saved in {asilib.config["ASI_DATA_DIR"] / "animations" / asi.animation_name}')
        """
        if ax is None:
            _, ax = plt.subplots()

        # Create the animation directory inside asilib.config['ASI_DATA_DIR'] if it does
        # not exist.
        image_save_dir = pathlib.Path(
            asilib.config['ASI_DATA_DIR'],
            'animations',
            'images',
            f'{self.file_info["time_range"][0].strftime("%Y%m%d_%H%M%S")}_{self.meta["array"].lower()}_'
            f'{self.meta["location"].lower()}_fisheye',
        )
        self.animation_name = (
            f'{self.file_info["time_range"][0].strftime("%Y%m%d_%H%M%S")}_'
            f'{self.file_info["time_range"][-1].strftime("%H%M%S")}_'
            f'{self.meta["array"].lower()}_{self.meta["location"].lower()}_fisheye.{movie_container}'
        )
        movie_save_path = image_save_dir.parents[1] / self.animation_name
        # If the image directory exists we need to first remove all of the images to avoid
        # animating images from different method calls.
        if image_save_dir.is_dir():
            shutil.rmtree(image_save_dir)
        image_save_dir.mkdir(parents=True)

        image_paths = []
        _progressbar = utils.progressbar(
            enumerate(self.__iter__()),
            iter_length=self._estimate_n_times(),
            text=self.animation_name,
        )

        for i, (image_time, image) in _progressbar:
            # # If the image is all 0s we have a bad image and we need to skip it.
            # if np.all(image == 0):
            #     continue
            ax.clear()
            ax.axis('off')
            # Use an underscore so the original method parameters are not overwritten.
            _color_map, _color_norm = self._plot_params(image, color_bounds, color_map, color_norm)

            im = ax.imshow(image, cmap=_color_map, norm=_color_norm, origin='lower')
            if label:
                self._add_fisheye_label(image_time, ax)

            if azel_contours:
                self._add_azel_contours(ax, color=azel_contour_color)
            if cardinal_directions is not None:
                self._add_cardinal_directions(ax, cardinal_directions)

            # Give the user the control of the subplot, image object, and return the image time
            # so that they can manipulate the image to add, for example, the satellite track.
            yield image_time, image, ax, im

            # Save the plot before the next iteration.
            save_name = f'{str(i).zfill(6)}.png'
            plt.savefig(image_save_dir / save_name)
            image_paths.append(image_save_dir / save_name)

        self._create_animation(image_paths, movie_save_path, ffmpeg_params, overwrite)
        return

    def plot_map(
        self,
        lon_bounds: tuple = (-160, -50),
        lat_bounds: tuple = (40, 82),
        ax: Union[plt.Axes, tuple] = None,
        coast_color: str = 'k',
        land_color: str = 'g',
        ocean_color: str = 'w',
        color_map: str = None,
        color_bounds: List[float] = None,
        color_norm: str = None,
        min_elevation: float = 10,
        asi_label: bool = True,
        pcolormesh_kwargs: dict = {},
    ) -> Tuple[plt.Axes, matplotlib.collections.QuadMesh]:
        """
        Projects an ASI image onto a map at an altitude that is defined in the skymap calibration 
        file.

        Parameters
        ----------
        lon_bounds: tuple
            The map's longitude bounds.
        lat_bounds: tuple
            The map's latitude bounds.
        ax: plt.Axes, tuple
            The subplot to put the map on. If cartopy is installed, ```ax``` must be
            a two element tuple specifying the ``plt.Figure`` object and subplot position
            passed directly as ``args`` into
            `fig.add_subplot() <https://matplotlib.org/stable/api/figure_api.html#matplotlib.figure.Figure.add_subplot>`_.
        coast_color: str
            The coast color. If None will not draw it.
        land_color: str
            The land color. If None will not draw it.
        ocean_color: str
            The ocean color. If None will not draw it.
        color_map: str
            The matplotlib colormap to use. See `matplotlib colormaps <https://matplotlib.org/stable/tutorials/colors/colormaps.html>`_.
        min_elevation: float
            Masks the pixels below min_elevation degrees.
        asi_label: bool
            Annotates the map with the ASI code in the center of the mapped image.
        color_bounds: List[float] or None
            The lower and upper values of the color scale. If None, will
            automatically set it to low=1st_quartile and
            high=min(3rd_quartile, 10*1st_quartile)
        color_norm: str
            Set the 'lin' (linear) or 'log' (logarithmic) color normalization. If color_norm=None,
            the color normalization will be taken from the ASI array (if specified), and if not
            specified it will default to logarithmic.
        pcolormesh_kwargs: dict
            A dictionary of keyword arguments (kwargs) to pass directly into
            plt.pcolormesh.

        Returns
        -------
        plt.Axes
            The subplot object to modify the axis, labels, etc.
        matplotlib.collections.QuadMesh
            The plt.pcolormesh image object. Common use for p is to add a colorbar.

        Examples
        --------
        >>> # Project an image of STEVE onto a map.
        >>> from datetime import datetime
        >>> import matplotlib.pyplot as plt
        >>> import asilib.asi
        >>>
        >>> asi = asilib.asi.themis('ATHA', time=datetime(2010, 4, 5, 6, 7, 0))
        >>> asi.plot_map(lon_bounds=(-127, -100), lat_bounds=(45, 65))
        >>> plt.tight_layout()
        >>> plt.show()
        """
        assert 'time' in self.file_info.keys(), f'Need to specify an image time.'
        for _skymap_key in ['lat', 'lon', 'el']:
            assert _skymap_key in self.skymap.keys(), (
                f'The "{_skymap_key}" key not in ' f'Imager.skymap: got {self.skymap.keys()}'
            )

        if ax is None:
            ax = asilib.map.create_map(
                lon_bounds=lon_bounds,
                lat_bounds=lat_bounds,
                coast_color=coast_color,
                land_color=land_color,
                ocean_color=ocean_color,
            )

        self_copy = self.__getitem__(self.file_info['time'])
        _, image = self_copy.data
        color_map, color_norm = self._plot_params(image, color_bounds, color_map, color_norm)

        ax, p, _ = self._plot_mapped_image(
            ax, image, min_elevation, color_map, color_norm, asi_label, pcolormesh_kwargs
        )
        return ax, p

    def _plot_mapped_image(
        self, ax, image, min_elevation, color_map, color_norm, asi_label, pcolormesh_kwargs
    ):
        """
        Plot the image onto a geographic map using the modified version of plt.pcolormesh.
        """
        _masked_lon_map, _masked_lat_map, _masked_image = self._mask_low_horizon(
            self.skymap['lon'], self.skymap['lat'], self.skymap['el'], min_elevation, image=image
        )

        pcolormesh_kwargs_copy = pcolormesh_kwargs.copy()
        if cartopy_imported and isinstance(ax, cartopy.mpl.geoaxes.GeoAxes):
            assert 'transform' not in pcolormesh_kwargs.keys(), (
                f"The pcolormesh_kwargs in Imager.plot_map() can't contain "
                f"'transform' key because it is reserved for cartopy."
            )
            pcolormesh_kwargs_copy['transform'] = ccrs.PlateCarree()
        p = self._pcolormesh_nan(
            _masked_lon_map,
            _masked_lat_map,
            _masked_image,
            ax,
            cmap=color_map,
            norm=color_norm,
            pcolormesh_kwargs=pcolormesh_kwargs_copy,
        )

        if asi_label:
            if cartopy_imported and isinstance(ax, cartopy.mpl.geoaxes.GeoAxes):
                transform = ccrs.PlateCarree()
            else:
                transform = ax.transData
            label = ax.text(
                self.meta['lon'],
                self.meta['lat'],
                self.meta['location'].upper(),
                color='r',
                transform=transform,
                va='center',
                ha='center',
            )
        else:
            label = None
        return ax, p, label

    def animate_map(self, **kwargs) -> None:
        """
        A wrapper for the ```animate_map_gen()``` method that animates a series of
        mapped images. Any kwargs are passed directly into ```animate_map_gen()```.

        Parameters
        ----------
        ax: plt.Axes
            The optional subplot that will be drawn on.
        label: bool
            Flag to add the "asi_array_code/location_code/image_time" text to the plot.
        color_map: str
            The matplotlib colormap to use. By default will use a black-white colormap.
            For more information See `matplotlib colormaps <https://matplotlib.org/stable/tutorials/colors/colormaps.html>`_.
        color_bounds: List[float]
            The lower and upper values of the color scale. The default is: low=1st_quartile and
            high=min(3rd_quartile, 10*1st_quartile). This range works well for most cases.
        color_norm: str
            Set the 'lin' (linear) or 'log' (logarithmic) color normalization. If color_norm=None,
            the color normalization will be taken from the ASI array (if specified), and if not
            specified it will default to logarithmic.
        azel_contours: bool
            Superpose azimuth and elevation contours on or off.
        azel_contour_color: str
            The color of the azimuth and elevation contours.
        cardinal_directions: str
            Plot one or more cardinal directions specified with a string containing the first
            letter of one or more cardinal directions. Case insensitive. For example, to plot
            the North and East directions, set cardinal_directions='NE'.
        movie_container: str
            The movie container: mp4 has better compression but avi was determined
            to be the official container for preserving digital video by the
            National Archives and Records Administration.
        ffmpeg_params: dict
            The additional/overwitten ffmpeg output parameters. The default parameters are:
            framerate=10, crf=25, vcodec=libx264, pix_fmt=yuv420p, preset=slower.
        overwrite: bool
            If true, the output will be overwritten automatically. If false it will
            prompt the user to answer y/n.

        Example
        -------
        .. code-block:: python

            >>> from datetime import datetime
            >>> import asilib.asi
            >>> import asilib
            >>>
            >>> location = 'FSMI'
            >>> time_range = (datetime(2015, 3, 26, 6, 7), datetime(2015, 3, 26, 6, 12))
            >>> asi = asilib.asi.themis(location, time_range=time_range)
            >>> asi.animate_map(overwrite=True)
            >>> print(f'Animation saved in {asilib.config["ASI_DATA_DIR"] / "animations" / asi.animation_name}')

        """
        movie_generator = self.animate_map_gen(**kwargs)

        for _ in movie_generator:
            pass
        return

    def animate_map_gen(
        self,
        lon_bounds: tuple = (-160, -50),
        lat_bounds: tuple = (40, 82),
        ax: Union[plt.Axes, tuple] = None,
        coast_color: str = 'k',
        land_color: str = 'g',
        ocean_color: str = 'w',
        color_map: str = None,
        color_bounds: List[float] = None,
        color_norm: str = None,
        min_elevation: float = 10,
        pcolormesh_kwargs: dict = {},
        asi_label: bool = True,
        movie_container: str = 'mp4',
        ffmpeg_params={},
        overwrite: bool = False,
    ) -> Generator[
        Tuple[datetime.datetime, np.ndarray, plt.Axes, matplotlib.collections.QuadMesh], None, None
    ]:
        """
        Animate a series of mapped images and superpose your data on each image.

        A generator behaves like an iterator in that it plots one fisheye image
        at a time and yields (similar to returns) the image. You can modify, or add
        content to the image (such as a spacecraft position). Then, once the iteration
        is complete, this method stitches the images into an animation. See the examples
        below and in the examples page for use cases. The ```animate_fisheye()``` method
        takes care of the iteration.

        Parameters
        ----------
        lon_bounds: tuple
            The map's longitude bounds.
        lat_bounds: tuple
            The map's latitude bounds.
        ax: plt.Axes, tuple
            The subplot to put the map on. If cartopy is installed, ```ax``` must be
            a two element tuple specifying the ``plt.Figure`` object and subplot position
            passed directly as ``args`` into
            `fig.add_subplot() <https://matplotlib.org/stable/api/figure_api.html#matplotlib.figure.Figure.add_subplot>`_.
        coast_color: str
            The coast color. If None will not draw it.
        land_color: str
            The land color. If None will not draw it.
        ocean_color: str
            The ocean color. If None will not draw it.
        color_map: str
            The matplotlib colormap to use. See `matplotlib colormaps <https://matplotlib.org/stable/tutorials/colors/colormaps.html>`_
            for supported colormaps.
        color_bounds: List[float]
            The lower and upper values of the color scale. The default is: low=1st_quartile and
            high=min(3rd_quartile, 10*1st_quartile). This range works well for most cases.
        color_norm: str
            Set the 'lin' (linear) or 'log' (logarithmic) color normalization. If color_norm=None,
            the color normalization will be taken from the ASI array (if specified), and if not
            specified it will default to logarithmic.
        min_elevation: float
            Masks the pixels below min_elevation degrees.
        pcolormesh_kwargs: dict
            A dictionary of keyword arguments (kwargs) to pass directly into
            plt.pcolormesh.
        asi_label: bool
            Annotates the map with the ASI code in the center of the mapped image.
        movie_container: str
            The movie container: mp4 has better compression but avi was determined
            to be the official container for preserving digital video by the
            National Archives and Records Administration.
        ffmpeg_params: dict
            The additional/overwitten ffmpeg output parameters. The default parameters are:
            framerate=10, crf=25, vcodec=libx264, pix_fmt=yuv420p, preset=slower.
        overwrite: bool
            Overwrite the animation. If False, ffmpeg will prompt you to answer y/n if the
            animation already exists.

        Yields
        ------
        image_time: datetime.datetime
            The time of the current image.
        image: np.ndarray
            A 2d image array of the image corresponding to image_time
        ax: plt.Axes
            The subplot object to modify the axis, labels, etc.
        im: matplotlib.collections.QuadMesh
            The plt.imshow image object. Common use for im is to add a colorbar.
            The image is oriented in the map orientation (north is up, south is down,
            west is right, and east is left). Set azel_contours=True to confirm.

        Example
        -------
        .. code-block:: python

            >>> from datetime import datetime
            >>> import matplotlib.pyplot as plt
            >>> import asilib
            >>> import asilib.asi
            >>>
            >>> location = 'FSMI'
            >>> time_range = (datetime(2015, 3, 26, 6, 7), datetime(2015, 3, 26, 6, 12))
            >>> asi = asilib.asi.themis(location, time_range=time_range)
            >>> ax = asilib.map.create_map(lon_bounds=(-120, -100), lat_bounds=(55, 65))
            >>> plt.tight_layout()
            >>>
            >>> gen = asi.animate_map_gen(overwrite=True, ax=ax)
            >>>
            >>> for image_time, image, ax, im in gen:
            >>>     # Add your code that modifies each image here...
            >>>     # To demonstrate, lets annotate each frame with the timestamp.
            >>>     # We will need to delete the prior text object, otherwise the current one
            >>>     # will overplot on the prior one---clean up after yourself!
            >>>     if 'text_obj' in locals():
            >>>             ax.texts.remove(text_obj)
            >>>     text_obj = ax.text(0, 0.9, f'THEMIS-{location} at {image_time:%F %T}',
            >>>             transform=ax.transAxes, color='white', fontsize=15)
            >>>
            >>> print(f'Animation saved in {asilib.config["ASI_DATA_DIR"] / "animations" / asi.animation_name}')
        """
        if ax is None:
            ax = asilib.map.create_map(
                lon_bounds=lon_bounds,
                lat_bounds=lat_bounds,
                coast_color=coast_color,
                land_color=land_color,
                ocean_color=ocean_color,
            )
        # Create the animation directory inside asilib.config['ASI_DATA_DIR'] if it does
        # not exist.
        image_save_dir = pathlib.Path(
            asilib.config['ASI_DATA_DIR'],
            'animations',
            'images',
            f'{self.file_info["time_range"][0].strftime("%Y%m%d_%H%M%S")}_{self.meta["array"].lower()}_'
            f'{self.meta["location"].lower()}_map',
        )
        self.animation_name = (
            f'{self.file_info["time_range"][0].strftime("%Y%m%d_%H%M%S")}_'
            f'{self.file_info["time_range"][-1].strftime("%H%M%S")}_'
            f'{self.meta["array"].lower()}_{self.meta["location"].lower()}_map.{movie_container}'
        )
        movie_save_path = image_save_dir.parents[1] / self.animation_name
        # If the image directory exists we need to first remove all of the images to avoid
        # animating images produced by different method calls.
        if image_save_dir.is_dir():
            shutil.rmtree(image_save_dir)
        image_save_dir.mkdir(parents=True)

        image_paths = []
        _progressbar = utils.progressbar(
            enumerate(self.__iter__()),
            iter_length=self._estimate_n_times(),
            text=self.animation_name,
        )
        for i, (image_time, image) in _progressbar:
            # Use an underscore so the original method parameters are not overwritten.
            _color_map, _color_norm = self._plot_params(image, color_bounds, color_map, color_norm)

            ax, pcolormesh_obj, label_obj = self._plot_mapped_image(
                ax, image, min_elevation, _color_map, _color_norm, asi_label, pcolormesh_kwargs
            )

            # Give the user the control of the subplot, image object, and return the image time
            # so that they can manipulate the image to add, for example, the satellite track.
            yield image_time, image, ax, pcolormesh_obj

            # Save the plot before the next iteration.
            save_name = f'{str(i).zfill(6)}.png'
            plt.savefig(image_save_dir / save_name)
            image_paths.append(image_save_dir / save_name)

            # Clean up the objects that this method generated.
            if label_obj is not None:
                # ax.texts.remove(label_obj)
                label_obj.remove()
            # ax.collections.remove(pcolormesh_obj)
            pcolormesh_obj.remove()

        self._create_animation(image_paths, movie_save_path, ffmpeg_params, overwrite)
        return

    def keogram(
        self, path: np.array = None, aacgm=False, minimum_elevation: float = 0
    ) -> Tuple[np.array, np.array, np.array]:
        """
        Create a keogram along the meridian or a custom path.

        Parameters
        ----------
        path: array
            Make a keogram along a custom path. The path is a lat/lon array of shape (n, 2).
            Longitude must be between [-180, 180].
        aacgm: bool
            Map the keogram latitudes to Altitude Adjusted Corrected Geogmagnetic Coordinates
            (aacgmv2) derived by Shepherd, S. G. (2014), Altitude-adjusted corrected geomagnetic
            coordinates: Definition and functional approximations, Journal of Geophysical
            Research: Space Physics, 119, 7501-7521, doi:10.1002/2014JA020264.
        minimum_elevation: float
            The minimum elevation of pixels to use in the keogram.

        Returns
        -------
        np.array:
            Keogram timestamps
        np.array:
            Keogram latitudes: geographic if the aacgm kwarg is False and magnetic is
            aacgm if True.
        np.array:
            Keogram array with rows corresponding to times and columns with latitudes.

        Example
        -------
        >>> # A keogram in geographic and magnetic latitude coordinates. See
        >>> # Imager.plot_keogram() on how to plot a keogram.
        >>> # Event from https://doi.org/10.1029/2021GL094696
        >>> import numpy as np
        >>> import asilib.asi
        >>>
        >>> time_range=['2008-01-16T10', '2008-01-16T12']
        >>>
        >>> asi = asilib.asi.themis('GILL', time_range=time_range)
        >>> time, geo_lat, geo_keogram = asi.keogram()  # geographic latitude
        >>> time, mag_lat, mag_keogram = asi.keogram(aacgm=True)  # magnetic latitude
        >>> time
        array([datetime.datetime(2008, 1, 16, 10, 0, 0, 20162),
            datetime.datetime(2008, 1, 16, 10, 0, 3, 9658),
            datetime.datetime(2008, 1, 16, 10, 0, 6, 29345), ...,
            datetime.datetime(2008, 1, 16, 11, 59, 51, 50496),
            datetime.datetime(2008, 1, 16, 11, 59, 54, 10602),
            datetime.datetime(2008, 1, 16, 11, 59, 57, 60543)], dtype=object)
        >>> geo_lat[:10]
        array([47.900368, 48.506763, 49.057587, 49.556927, 50.009083, 50.418365,
            50.788963, 51.124836, 51.42965 , 51.706768], dtype=float32)
        >>> mag_lat[:10]
        array([57.97198543, 58.55886486, 59.09144098, 59.57379565, 60.01019679,
            60.40490277, 60.76203547, 61.0854798 , 61.37882613, 61.64536043])
        >>> np.all(mag_keogram == geo_keogram)  # aacgm=True only changes the latitudes.
        True
        """
        # Determine what pixels to slice (path or along the meridian).
        self._keogram_pixels(path, minimum_elevation)

        # Allocate the keogram time and image arrays. Currently the black and white (B&W)
        # and color (RGB) images are allocated separately. In the future we should try to
        # consolidate this into one self._keogram array allocation.
        self._keogram_time = np.nan * np.zeros(self._estimate_n_times(), dtype=object)
        if len(self.meta['resolution']) == 2:
            # B&W images.
            self._keogram = np.nan * np.zeros((self._estimate_n_times(), self._pixels.shape[0]))
        elif len(self.meta['resolution']) == 3:
            # RGB images.
            self._keogram = np.nan * np.zeros(
                (self._estimate_n_times(), self._pixels.shape[0], self.meta['resolution'][2])
            )

        self._geogram_lat = self._keogram_latitude(aacgm)

        if (hasattr(self, '_times')) and (hasattr(self, '_images')):
            # if self.data() was already called
            self._keogram[0 : self._images.shape[0], ...] = self._images[
                :, self._pixels[:, 0], self._pixels[:, 1], ...
            ]
            self._keogram_time = self._times
        else:
            # Otherwise load the data, one file at a time.
            start_time_index = 0
            _progressbar = utils.progressbar(
                self.iter_files(),
                iter_length=np.array(self.file_info['path']).shape[0],
                text=f'{self.meta["array"]} {self.meta["location"]} keogram',
            )
            for file_times, file_images in _progressbar:
                end_time_index = start_time_index + file_images.shape[0]

                self._keogram[start_time_index:end_time_index, ...] = file_images[
                    :, self._pixels[:, 0], self._pixels[:, 1], ...
                ]
                self._keogram_time[start_time_index:end_time_index] = file_times
                start_time_index += file_images.shape[0]

        # Remove NaN keogram rows (unfilled or the data is NaN.).
        i_valid = np.where(~np.isnan(self._keogram[:, 0, ...]))[0]
        self._keogram = self._keogram[i_valid, ...]
        self._keogram_time = self._keogram_time[i_valid]

        if self._keogram.shape[0] == 0:
            raise ValueError(
                f"The keogram is empty for {self.meta['array']}/{self.meta['location']} "
                f"during {self.file_info['time_range']}. The images likely don't exist "
                f"in this time interval."
            )
        return self._keogram_time, self._geogram_lat, self._keogram

    def plot_keogram(
        self,
        ax: plt.Axes = None,
        path: np.array = None,
        aacgm=False,
        title: bool = True,
        minimum_elevation: float = 0,
        color_map: str = None,
        color_bounds: List[float] = None,
        color_norm: str = None,
        pcolormesh_kwargs={},
    ) -> Tuple[plt.Axes, matplotlib.collections.QuadMesh]:
        """
        Plot a keogram along the meridian or a custom path.

        Parameters
        ----------
        ax: plt.Axes
            The subplot to plot the keogram on.
        path: np.array
            Make a keogram along a custom path. The path is a lat/lon array of shape (n, 2).
            Longitude must be between [-180, 180].
        aacgm: bool
            Map the keogram latitudes to Altitude Adjusted Corrected Geogmagnetic Coordinates
            (aacgmv2) derived by Shepherd, S. G. (2014), Altitude-adjusted corrected geomagnetic
            coordinates: Definition and functional approximations, Journal of Geophysical
            Research: Space Physics, 119, 7501-7521, doi:10.1002/2014JA020264.
        title: bool
            Add a plot title with the date, ASI array, and ASI location.
        minimum_elevation: float
            The minimum elevation of pixels to use in the keogram.
        color_map: str
            The matplotlib colormap to use. See `matplotlib colormaps <https://matplotlib.org/stable/tutorials/colors/colormaps.html>`_
            for supported colormaps.
        color_bounds: List[float]
            The lower and upper values of the color scale. The default is: low=1st_quartile and
            high=min(3rd_quartile, 10*1st_quartile). This range works well for most cases.
        color_norm: str
            Set the 'lin' (linear) or 'log' (logarithmic) color normalization. If color_norm=None,
            the color normalization will be taken from the ASI array (if specified), and if not
            specified it will default to logarithmic.
        pcolormesh_kwargs: dict
            A dictionary of keyword arguments (kwargs) to pass directly into
            plt.pcolormesh.

        Returns
        -------
        plt.Axes
            The subplot object to modify the axis, labels, etc.
        matplotlib.collections.QuadMesh
            The plt.pcolormesh image object, useful to add a colorbar, for example.

        Example
        -------
        >>> # Plot a keogram in geographic and magnetic latitude coordinates.
        >>> # Event from https://doi.org/10.1029/2021GL094696
        >>> import matplotlib.pyplot as plt
        >>> import asilib.asi
        >>>
        >>> time_range=['2008-01-16T10', '2008-01-16T12']
        >>> fig, ax = plt.subplots(2, sharex=True, figsize=(10, 6))
        >>>
        >>> asi = asilib.asi.themis('GILL', time_range=time_range)
        >>> _, p = asi.plot_keogram(ax=ax[0], color_map='turbo')
        >>> asi.plot_keogram(ax=ax[1], color_map='turbo', aacgm=True, title=False)
        >>>
        >>> ax[0].set_ylabel('Geographic Lat [deg]')
        >>> ax[1].set_ylabel('Magnetic Lat [deg]')
        >>> fig.subplots_adjust(right=0.8)
        >>> cbar_ax = fig.add_axes([0.85, 0.15, 0.05, 0.7])
        >>> fig.colorbar(p, cax=cbar_ax)
        >>> plt.show()
        """
        if ax is None:
            _, ax = plt.subplots()

        if ('cmap' in pcolormesh_kwargs.keys()) and (color_map is not None):
            raise ValueError(
                'The colormap is defined in both the color_map and pcolormesh_kwargs["cmap"].'
            )
        if ('norm' in pcolormesh_kwargs.keys()) and (color_norm is not None):
            raise ValueError(
                'The color norm is defined in both the color_norm and pcolormesh_kwargs["norm"].'
            )

        _keogram_time, _geogram_lat, _keogram = self.keogram(
            path=path, aacgm=aacgm, minimum_elevation=minimum_elevation
        )

        _color_map, _color_norm = self._plot_params(_keogram, color_bounds, color_map, color_norm)

        # Same as transpose, but correctly handles RGB keograms.
        _keogram = np.swapaxes(_keogram, 1, 0)
        if len(_keogram.shape) == 3:
            # To see anything, the channel intensities need to span 0-255
            # _keogram*=(255/_keogram.max())
            _keogram = _keogram.astype(np.uint8)

        pcolormesh_obj = ax.pcolormesh(
            _keogram_time,
            _geogram_lat,
            _keogram,
            norm=_color_norm,
            shading='auto',
            cmap=_color_map,
            **pcolormesh_kwargs,
        )

        if title:
            ax.set_title(
                f'{self.file_info["time_range"][0].date()} | {self.meta["array"]}-{self.meta["location"]} keogram'
            )
        return ax, pcolormesh_obj

    def _keogram_pixels(self, path, minimum_elevation=20):
        """
        Find what pixels to index and reshape the keogram.
        """
        # CASE 1: No path provided. Output self._pixels that slice the meridian.
        if path is None:
            self._pixels = -1*np.ones((self.meta['resolution'][0], 2), dtype=int)
            self._pixels[:, 0] = np.arange(self.meta['resolution'][0])
            self._pixels[:, 1] = int(self.meta['resolution'][1] // 2)

        # CASE 2: A path is provided so now we need to calculate the custom path
        # on the lat/lon skymap.
        else:
            self._pixels = self._path_to_pixels(path)

        above_elevation = np.where(
            (self.skymap['el'][self._pixels[:, 0], self._pixels[:, 1]] >= minimum_elevation)
            & (np.isfinite(self.skymap['lat'][self._pixels[:, 0], self._pixels[:, 1]]))
        )[0]
        self._pixels = self._pixels[above_elevation]
        return

    def _path_to_pixels(self, path: np.array, threshold: float = 1) -> np.array:
        """
        Map a lat/lon path to ASI x- and y-pixels.

        Parameters
        ----------
        path: np.array
            The lat/lon array of shape (n, 2). Longitude must be between [-180, 180]
        threshold: float
            The maximum distance threshold, in degrees, between the path (lat, lon)
            and the skymap (lat, lon)

        Returns
        -------
        np.array
            ASI x and y indices along the path.
        """
        if np.array(path).shape[0] == 0:
            raise ValueError('The path is empty.')
        if np.any(np.isnan(path)):
            raise ValueError("The lat/lon path can't contain NaNs.")
        if np.any(np.max(path) > 180) or np.any(np.min(path) < -180):
            raise ValueError("The lat/lon values must be in the range -180 to 180.")

        nearest_pixels = np.nan * np.zeros_like(path)

        for i, (lat, lon) in enumerate(path):
            distances = _haversine(
                self.skymap['lat'],
                self.skymap['lon'],
                lat * np.ones_like(self.skymap['lon']),
                lon * np.ones_like(self.skymap['lon']),
            )
            idx = np.where(distances == np.nanmin(distances))

            if distances[idx][0] > threshold:
                warnings.warn(
                    f'Some of the keogram path coordinates are outside of the '
                    f'maximum {threshold} degrees distance from the nearest '
                    f'skymap map coordinate.'
                )
                continue
            nearest_pixels[i, :] = [idx[0][0], idx[1][0]]

        valid_pixels = np.where(np.isfinite(nearest_pixels[:, 0]))[0]
        if valid_pixels.shape[0] == 0:
            raise ValueError('The keogram path is completely outside of the skymap.')
        return nearest_pixels[valid_pixels, :].astype(int)

    def _keogram_latitude(self, aacgm):
        """
        Keogram's vertical axis: geographic latitude, magnetic latitude, or pixel index.
        """
        _geo_lats = self.skymap['lat'][self._pixels[:, 0], self._pixels[:, 1]]
        assert np.all(np.isfinite(_geo_lats)), f'Some keogram lats are NaNs {_geo_lats=}.'
        if aacgm:
            _geo_lons = self.skymap['lon'][self._pixels[:, 0], self._pixels[:, 1]]
            _aacgm_lats = aacgmv2.convert_latlon_arr(
                _geo_lats,
                _geo_lons,
                self.skymap['alt'],
                self.file_info['time_range'][0],
                method_code="G2A",
            )[0]
            return _aacgm_lats
        else:
            return _geo_lats

    def __getitem__(self, _slice):
        """
        Slice an Imager object by time.

        Parameters
        ----------
        _slice: str, pd.Timestamp, datetime.datetime, or list.
            The time(s) to slice an Imager object. Can type of slice can be either
            1) [start_time:end_time], or 2) just time.

        Yields
        ------
        asilib.Imager:
            A sliced version of the Imager.
        """
        start_time, end_time = self._convert_slice(_slice)
        idx = np.where(
            (start_time <= np.array(self.file_info['end_time']))
            & (end_time >= np.array(self.file_info['start_time']))
        )[0]

        if len(idx) == 0:
            raise FileNotFoundError(f'Imager does not have any data contained in slice={_slice}')

        # Create the new variables.
        new_file_info = {}
        if start_time == end_time:
            # A single time stamp
            new_file_info['time'] = start_time
        else:
            new_file_info['time_range'] = [start_time, end_time]
        new_file_info['start_time'] = np.array(self.file_info['start_time'])[idx]
        new_file_info['end_time'] = np.array(self.file_info['end_time'])[idx]
        new_file_info['path'] = np.array(self.file_info['path'])[idx]
        new_file_info['loader'] = self.file_info['loader']

        new_meta = copy.copy(self.meta)
        new_skymap = copy.copy(self.skymap)
        new_plot_settings = copy.copy(self.plot_settings)

        cls = type(self)
        return cls(new_file_info, new_meta, new_skymap, plot_settings=new_plot_settings)

    def _convert_slice(self, _slice):
        """
        Validate and convert the slice into datetime objects.
        """
        # Convert the [start_time:end_time] slice to datetime objects.
        if isinstance(_slice, slice):
            # Check the start slice and if it is None assign time_range[0]
            if isinstance(_slice.start, str):
                start_time = dateutil.parser.parse(_slice.start)
            elif isinstance(_slice.start, (datetime.datetime, pd.Timestamp)):
                start_time = _slice.start
            elif _slice.start is None:
                start_time = self.file_info['time_range'][0]
            else:
                raise ValueError(
                    f'The start index can only be a time object, string, or None. '
                    f'{_slice.start} is unsupported'
                )

            # Check the end slice and if it is None assign time_range[1]
            if isinstance(_slice.stop, str):
                end_time = dateutil.parser.parse(_slice.stop)
            elif isinstance(_slice.stop, (datetime.datetime, pd.Timestamp)):
                end_time = _slice.stop
            elif _slice.stop is None:
                end_time = self.file_info['time_range'][1]
            else:
                raise ValueError(
                    f'The start index can only be a time object, string, or None. '
                    f'{_slice.stop} is unsupported'
                )

            if _slice.step is not None:
                raise NotImplementedError
            return start_time, end_time

        # Convert the [time] slice to datetime object.
        elif isinstance(_slice, (str, datetime.datetime, pd.Timestamp)):
            if isinstance(_slice, str):
                slice_time = dateutil.parser.parse(_slice)
            else:
                slice_time = _slice
            return slice_time, slice_time
        elif isinstance(_slice, tuple):
            raise NotImplementedError(
                'At this time asilib.Imager does not support multi-dimensional indexing.'
            )
        else:
            raise ValueError(f'The slice must be [time] or [start_time:end_time], not {_slice}.')

    def __iter__(self):
        """
        Iterate over individual timestamps and images using the
        ```for time, image in asilib.Imager(...)```.

        Parameters
        ----------
        None

        Yields
        ------
        datetime.datetime
            timestamp
        np.array
            image.
        """
        # TODO: Add a self._accumulate_n option.
        if hasattr(self, '_times') and hasattr(self, '_images'):
            for time_i, image_i in zip(self._times, self._images):
                yield time_i, image_i
        else:
            for file_times, file_images in self.iter_files():
                for time_i, image_i in zip(file_times, file_images):
                    yield time_i, image_i

    def iter_files(self) -> Union[np.array, np.array]:
        """
        Iterate one ASI file (or large chunks of a file) at a time.
        The output data is clipped by time_range.

        Yields
        ------
        np.array:
            ASI timestamps in datetine.datetime() or numpy.datetime64() format.
        np.array:
            ASI images.

        Example
        -------
        Loop over ~5 minutes of data, starting in the middle of one file.
            .. code-block:: python

                >>> import asilib.asi
                >>> time_range=['2008-01-16T10:00:30', '2008-01-16T10:05']
                >>> asi = asilib.asi.themis('GILL', time_range=time_range)
                >>> for file_times, file_images in asi.iter_files():
                ...     print(file_times[0], file_times[-1], file_images.shape)
                ...
                2008-01-16 10:00:30.019526 2008-01-16 10:00:57.049007 (10, 256, 256)
                2008-01-16 10:01:00.058996 2008-01-16 10:01:57.049620 (20, 256, 256)
                2008-01-16 10:02:00.059597 2008-01-16 10:02:57.029981 (20, 256, 256)
                2008-01-16 10:03:00.050822 2008-01-16 10:03:57.020254 (20, 256, 256)
                2008-01-16 10:04:00.030448 2008-01-16 10:04:57.046170 (20, 256, 256)
        """
        self._loader_is_gen = inspect.isgeneratorfunction(self.file_info['loader'])
        if 'time_range' not in self.file_info.keys():
            raise KeyError('Imager was not instantiated with a time_range.')

        for path in self.file_info['path']:
            # Check if the loader function is a generator. If not, asilib
            # will load one image file at a time and assume that opening one file
            # won't overwhelm the PC's memory. If loader is a generator,
            # on the other hand, we need to loop over every chunk of data
            # yielded by the generator and over the timestamps in each chunk.
            if not self._loader_is_gen:
                times, images = self.file_info['loader'](path)

                idt = np.where(
                    (times >= self.file_info['time_range'][0])
                    & (times <= self.file_info['time_range'][1])
                )[0]
                yield times[idt], images[idt]

            else:
                gen = self.file_info['loader'](path)

                for time_chunk, image_chunk in gen:
                    idt = np.where(
                        (time_chunk >= self.file_info['time_range'][0])
                        & (time_chunk <= self.file_info['time_range'][1])
                    )[0]
                    yield time_chunk[idt], image_chunk[idt]
        return

    # def iter_chunks(self, chunk_size: int) -> Union[np.array, np.array]:
    #     """
    #     Chunk and iterate over the ASI data. The output data is
    #     clipped by time_range.

    #     Parameters
    #     ----------
    #     chunk_size: int
    #         The number of time stamps and images to return.

    #     Yields
    #     ------
    #     np.array:
    #         ASI timestamps in datetine.datetime() or numpy.datetime64() format.
    #     np.array:
    #         ASI images.

    #     Example
    #     -------
    #     TODO: Add
    #     """
    #     raise NotImplementedError

    #     yield

    def _estimate_n_times(self):
        """
        Estimate the maximum number of time stamps for the Imager's time range.
        """
        n_sec = (self.file_info['time_range'][1] - self.file_info['time_range'][0]).total_seconds()
        # +2 is for when time_range includes the start and end time stamps.
        # This will be trimmed later.
        return int(n_sec / self.meta['cadence']) + 2

    @property
    def data(self):
        """
        Load ASI data.

        Returns
        -------
        namedtuple
            A named tuple containing (times, images). Members can be accessed using either
            index notation, or dot notation.
        """
        _img_data_type = namedtuple('data', ['time', 'image'])

        if 'time_range' in self.file_info.keys():
            # If already run.
            if hasattr(self, '_times') and hasattr(self, '_images'):
                return _img_data_type(self._times, self._images)

            self._times = np.nan * np.zeros(self._estimate_n_times(), dtype=object)
            self._images = np.nan * np.zeros((self._estimate_n_times(), *self.meta['resolution']))

            start_idt = 0
            for file_times, file_images in self.iter_files():
                self._times[start_idt : start_idt + file_times.shape[0]] = file_times
                self._images[start_idt : start_idt + file_times.shape[0]] = file_images
                start_idt += file_times.shape[0]
            # Cut any unfilled times and images
            valid_ind = np.where(~np.isnan(self._images[:, 0, 0]))[0]
            self._times = self._times[valid_ind]
            self._images = self._images[valid_ind]
            return _img_data_type(self._times, self._images)

        elif 'time' in self.file_info.keys():
            return _img_data_type(*self._load_image(self.file_info['time']))

        else:
            raise ValueError(
                f'This imager instance does not contain either the '
                f'"time" or "time_range" data variables. The data '
                f'variables are {self.file_info.keys()}.'
            )

    def _load_image(self, time):
        """
        Load a single image and time stamp nearest to time.

        Parameters
        ----------
        time: datetime.datetime
            The requested image time.

        Returns
        -------
        datetime.datetime
            Image timestamp
        np.array
            Image.

        Raises
        ------
        IndexError
            If the nearest image timestamp is more than self.meta['cadence'] away
            from time.
        """
        # Case where the loader is a function
        if not inspect.isgeneratorfunction(self.file_info['loader']):
            _times, _images = self.file_info['loader'](self.file_info['path'][0])
            image_index = np.argmin(np.abs([(time - t_i).total_seconds() for t_i in _times]))
            if np.abs((time - _times[image_index]).total_seconds()) > self.meta['cadence']:
                raise IndexError(
                    f'Cannot find a time stamp within {self.meta["cadence"]} seconds of '
                    f'{time}. Closest time stamp is {_times[image_index]}.'
                )
            return (
                _times[image_index],
                _images[image_index, ...],
            )  # Ellipses to load all other dimenstions.
        # Case where the loader is a generator function.
        else:
            gen = self.file_info['loader'](self.file_info['path'][0])
            for _times, _images in gen:
                image_index = np.argmin(np.abs([(time - t_i).total_seconds() for t_i in _times]))
                if np.abs((time - _times[image_index]).total_seconds()) < self.meta['cadence']:
                    return _times[image_index], _images[image_index, ...]

            raise IndexError(
                f'Cannot find a time stamp within {self.meta["cadence"]} seconds of ' f'{time}.'
            )

    def __str__(self) -> str:
        if ('time' in self.file_info.keys()) and (self.file_info['time'] is not None):
            s = (
                f'A {self.meta["array"]}-{self.meta["location"]} Imager. '
                f'time={self.file_info["time"]}'
            )
        elif ('time_range' in self.file_info.keys()) and (self.file_info['time_range'] is not None):
            s = (
                f'A {self.meta["array"]}-{self.meta["location"]} Imager. '
                f'time_range={self.file_info["time_range"]}'
            )
        return s

    def _plot_params(self, image, color_bounds, color_map, color_norm):
        """
        Sets the plot color bounds, map style, and normalization values. In order of precedence,
        these kwargs are checked first, and then self.plot_settings. If these values are
        unset in either place, defaults are returned.
        """
        # Check the plot_settings dict and fall back to a default if user did not specify
        # color_bounds in the method call.
        if color_bounds is None:
            # Is it part of the plot_settings generated by the ASI data loader?
            if 'color_bounds' in self.plot_settings.keys():
                # Is it a function?
                if callable(self.plot_settings['color_bounds']):
                    color_bounds = self.plot_settings['color_bounds'](image)
                else:
                    color_bounds = self.plot_settings['color_bounds']
            else:
                lower, upper = np.quantile(image, (0.25, 0.98))
                color_bounds = [lower, np.min([upper, lower * 10])]
        else:
            if callable(color_bounds):  # function that ouputs vmin, vmax
                color_bounds = color_bounds(image)
            else:
                color_bounds = color_bounds  # vmin, vmax

        if color_map is None:
            if 'color_map' in self.plot_settings.keys():
                color_map = self.plot_settings['color_map']
            else:
                color_map = 'Greys_r'
        else:
            color_map = color_map

        # If color_norm is specified by the method, it overrules the ASI array settings
        # or Imager setting. If the method's color_norm is not specified, check if the
        # ASI has it specified in self.plot_settings. Lastly, if the ASI does not have
        # it specified, default to a logarithmic color_norm.
        if color_norm is None:
            if 'color_norm' in self.plot_settings.keys():
                color_norm = self.plot_settings['color_norm']
            else:
                color_norm = 'log'
        if color_norm == 'log':
            color_norm = colors.LogNorm(vmin=color_bounds[0], vmax=color_bounds[1])
        elif color_norm == 'lin':
            color_norm = colors.Normalize(vmin=color_bounds[0], vmax=color_bounds[1])
        elif isinstance(color_norm, matplotlib.colors.Normalize):
            pass
        else:
            raise ValueError(f'color_norm must be either None, "log", or "lin", not {color_norm=}.')

        return color_map, color_norm

    def _add_azel_contours(self, ax: plt.Axes, color: str = 'yellow') -> None:
        """
        Adds contours of azimuth and elevation to the movie image.

        Parameters
        ----------
        ax: plt.Axes
            The subplot to draw on.
        color: str (optional)
            The contour color.
        """
        az_contours = ax.contour(
            self.skymap['az'],
            colors=color,
            linestyles='dotted',
            levels=np.arange(0, 361, 90),
            alpha=1,
        )
        el_contours = ax.contour(
            self.skymap['el'],
            colors=color,
            linestyles='dotted',
            levels=np.arange(1, 91, 30),
            alpha=1,
        )
        plt.clabel(az_contours, inline=True, fontsize=12)
        plt.clabel(el_contours, inline=True, fontsize=12, rightside_up=True)
        return

    def _add_fisheye_label(self, image_time, ax: plt.Axes):
        """
        Adds a ASI array-location-time label to the image
        """
        if self.meta['cadence'] > 1:
            time_label = image_time.strftime('%Y-%m-%d %T')
        else:
            time_label = image_time.strftime('%Y-%m-%d %T:%f')
        ax.text(
            0,
            0,
            (f"{self.meta['array'].upper()}/{self.meta['location'].upper()}\n" f"{time_label}"),
            va='bottom',
            transform=ax.transAxes,
            color='white',
        )
        return

    def _add_cardinal_directions(self, ax, directions, el_step=10, origin=(0.8, 0.1), length=0.1):
        """
        Plot cardinal direction arrows. See _calc_cardinal_direction() for the algorithm.

        Parameters
        ----------
        direction: str
            The cardinal direction. Must be a string containing 'N', 'S', 'E', or 'W', or a
            combination of them. Case insensitive.
        el_step: int
            The elevation steps used to fit the cardinal direction line.
        origin: tuple
            The origin of the direction arrows.
        length: float
            The arrow length.
        """
        assert isinstance(directions, str), 'Cardinal directions must be a string.'
        for direction in directions:
            direction = direction.upper()
            if direction not in ['N', 'S', 'E', 'W']:
                raise ValueError(f'Cardinality direction "{direction}" is invalid."')
            rise, run = self._calc_cardinal_direction(direction, el_step)
            norm = length / np.sqrt(rise**2 + run**2)

            ax.annotate(
                direction,
                xy=origin,
                xytext=(origin[0] + run * norm, origin[1] + rise * norm),  # trig
                arrowprops={'arrowstyle': "<-", 'color': 'w'},
                xycoords='axes fraction',
                color='w',
                ha='center',
                va='center',
            )
        return

    def _calc_cardinal_direction(self, direction, el_step, validate=False):
        """
        Calculate the cardinal direction arrows.

        Each direction is calculated by:
        1. Calculate the azimuths in each 5-degree elevation step.
        2. For each elevation step, find the azimuth corresponding to that cardinal direction.
        The result is a set of points going from 0 to 90 degree elevation along the cardinal
        direction.
        3. Calculate the rise and run between the two points that are nearest and furthest from
        zenith, located on the caridinal direction.

        Parameters
        ----------
        direction: str
            The cardinal direction. Must be one of 'N', 'S', 'E', or 'W' (case sensitive).
        el_step: int
            The elevation steps used to fit the cardinal direction line.

        Returns
        -------
        float
            The rise of the difference in the two pixels that are closest and furthest
            from zenith
        float
            The run of the difference in the two pixels that are closest and furthest
            from zenith
        """
        _azimuths = {'N': 0, 'E': 90, 'S': 180, 'W': 270}

        # Don't recalculate the rise and run if they've already been calculated.
        if not hasattr(self, '_cardinal_direction'):
            self._cardinal_direction = {}
        else:
            if direction in self._cardinal_direction.keys():
                return self._cardinal_direction[direction]

        elevation_steps = np.arange(0, 91, el_step)
        _direction_pixels = np.nan * np.zeros((elevation_steps.shape[0], 2), dtype=int)

        for i, (el_low, el_high) in enumerate(zip(elevation_steps[:-1], elevation_steps[1:])):
            id_el = np.where(~((self.skymap['el'] > el_low) & (self.skymap['el'] <= el_high)))
            _az = self.skymap['az'].copy()
            _az[id_el] = np.nan

            try:
                min_az_flat_array = np.nanargmin(np.abs(_az - _azimuths[direction]))
            except ValueError as err:
                if 'All-NaN slice encountered' == str(err):
                    continue
                raise
            _direction_pixels[i, :] = np.unravel_index(min_az_flat_array, self.skymap['az'].shape)

        _direction_pixels = _direction_pixels[~np.isnan(_direction_pixels[:, 0]), :]
        _direction_pixels = _direction_pixels.astype(int)

        # Calculate the pixels nerest and furthest away from zenith. This will define the rise
        # and run.
        center_pixel = np.array([self.skymap['az'].shape[0] // 2, self.skymap['az'].shape[1] // 2])
        dx = _direction_pixels - np.tile(center_pixel, (_direction_pixels.shape[0], 1))
        distances = numpy.linalg.norm(dx, axis=1)
        nearest_pixel = _direction_pixels[np.argmin(distances), :]
        furthest_pixel = _direction_pixels[np.argmax(distances), :]
        rise = furthest_pixel[0] - nearest_pixel[0]
        run = furthest_pixel[1] - nearest_pixel[1]
        self._cardinal_direction[direction] = [rise, run]

        if validate:
            fig, ax = plt.subplots()
            p = ax.pcolormesh(self.skymap['az'])
            plt.colorbar(p, ax=ax)
            ax.scatter(_direction_pixels[:, 1], _direction_pixels[:, 0])
            ax.set_title(f'{direction} | {rise=}, {run=}')
            plt.show()

        return rise, run

    def _mask_low_horizon(self, lon_map, lat_map, el_map, min_elevation, image=None):
        """
        Mask the image, skymap['lon'], skymap['lat'] arrays with np.nans
        where the skymap['el'] < min_elevation or is nan.
        """
        idh = np.where(np.isnan(el_map) | (el_map < min_elevation))
        # Copy variables to not modify original np.arrays.
        lon_map_copy = lon_map.copy()
        lat_map_copy = lat_map.copy()
        lon_map_copy[idh] = np.nan
        lat_map_copy[idh] = np.nan

        # if image is not None:
        #     image_copy = image.copy()
        #     original_dtype = image.dtype
        #     image_copy = image_copy.astype(float)  # Can't mask image unless it is a float array.
        #     image_copy[idh] = np.nan
        # else:
        #     image_copy = None

        if (lon_map.shape[0] == el_map.shape[0] + 1) and (lon_map.shape[1] == el_map.shape[1] + 1):
            # TODO: This is REGO/THEMIS specific. Remove here and add this to the themis() function?
            # For some reason the THEMIS & REGO lat/lon_map arrays are one size larger than el_map, so
            # here we mask the boundary indices in el_map by adding 1 to both the rows
            # and columns.
            idh_boundary_bottom = (
                idh[0] + 1,
                idh[1],
            )  # idh is a tuple so we have to create a new one.
            idh_boundary_right = (idh[0], idh[1] + 1)
            lon_map_copy[idh_boundary_bottom] = np.nan
            lat_map_copy[idh_boundary_bottom] = np.nan
            lon_map_copy[idh_boundary_right] = np.nan
            lat_map_copy[idh_boundary_right] = np.nan
        return lon_map_copy, lat_map_copy, image

    def _create_animation(
        self,
        image_paths: List[pathlib.Path],
        movie_save_path: pathlib.Path,
        ffmpeg_params: dict,
        overwrite: bool,
    ):
        """
        Helper function to stich together images into an animation using ffmpeg.

        Parameters
        ----------
        image_save_dir: pathlib.Path
            The directory where the individual images are saved.
        ffmpeg_params: dict
            The additional/overwitten ffmpeg output parameters. The default parameters are:
            framerate=10, crf=25, vcodec=libx264, pix_fmt=yuv420p, preset=slower.
        movie_file_name: str
            The movie file name.
        overwrite: bool
            Overwrite the movie.
        """
        _ffmpeg_params = {
            'framerate': 10,
            'crf': 25,
            'vcodec': 'libx264',
            'pix_fmt': 'yuv420p',
            'preset': 'slower',
        }
        # Add or change the ffmpeg_params's key:values with ffmpeg_params
        _ffmpeg_params.update(ffmpeg_params)

        try:
            movie_obj = ffmpeg.input(
                str(image_paths[0].parent / "%06d.png"),
                pattern_type='sequence',
                # Pop so it won't be passed into movie_obj.output().
                framerate=_ffmpeg_params.pop('framerate'),
            )
            movie_obj.output(str(movie_save_path), **_ffmpeg_params).run(overwrite_output=overwrite)
            print(f'Animation saved to {movie_save_path}')
        except FileNotFoundError as err:
            if '[WinError 2] The system cannot find the file specified' in str(err):
                raise FileNotFoundError("Windows doesn't have ffmpeg installed.") from err
        return

    def __repr__(self):
        """
        A machine-readable representation of Imager.
        """
        params = (
            f'file_info={self.file_info}, skymap={self.skymap}, '
            f'meta={self.meta}, plot_settings={self.plot_settings}'
        )
        return f'{self.__class__.__qualname__}(' + params + ')'

    def _pcolormesh_nan(
        self,
        x: np.ndarray,
        y: np.ndarray,
        c: np.ndarray,
        ax,
        cmap=None,
        norm=None,
        pcolormesh_kwargs={},
    ):
        """
        Since pcolormesh cant handle nan lat/lon grid values, we will compress them to the
        nearest valid lat/lon grid. There are two main steps:

        1) All nan values to the left of the first valid value are
        reassigned to the first valid value. Likewise, all nan values to the
        right of the last valid value are reassigned to it.

        2) All nan-filled rows above the first valid row are assigned to the
        maximum value in the first row, likewise for the bottom rows.

        Essentially this is a reassignment (or a compression) of all nan values in the periphery
        to the valid grid values in the center.

        Function taken from `Michael, scivision @ GitHub <https://github.com/scivision/python-matlab-examples/blob/0dd8129bda8f0ec2c46dae734d8e43628346388c/PlotPcolor/pcolormesh_NaN.py>`_.
        """
        # mask is True when lat and lon grid values are not nan.
        mask = np.isfinite(x) & np.isfinite(y)
        top = None
        bottom = None

        for i, m in enumerate(mask):
            # A common use for nonzero is to find the indices of
            # an array, where a condition is True (not nan or inf)
            good = m.nonzero()[0]

            if good.size == 0:  # Skip row is all columns are nans.
                continue
            # First row that has at least 1 valid value.
            elif top is None:
                top = i
            # Bottom row that has at least 1 value value. All indices in between top and bottom
            else:
                bottom = i

            # Reassign all lat/lon columns after good[-1] (all nans) to good[-1].
            x[i, good[-1] :] = x[i, good[-1]]
            y[i, good[-1] :] = y[i, good[-1]]
            # Reassign all lat/lon columns before good[0] (all nans) to good[0].
            x[i, : good[0]] = x[i, good[0]]
            y[i, : good[0]] = y[i, good[0]]

        # Reassign all of the fully invalid lat/lon rows above top to the the max lat/lon value.
        x[:top, :] = np.nanmax(x[top, :])
        y[:top, :] = np.nanmax(y[top, :])
        # Same, but for the rows below bottom.
        x[bottom:, :] = np.nanmax(x[bottom, :])
        y[bottom:, :] = np.nanmax(y[bottom, :])

        # old masked c code: np.ma.masked_where(~mask[:-1, :-1], c)[::-1, ::-1]
        p = ax.pcolormesh(
            x,
            y,
            c,
            cmap=cmap,
            shading='auto',
            norm=norm,
            **pcolormesh_kwargs,
        )
        return p


def _haversine(
    lat1: np.array, lon1: np.array, lat2: np.array, lon2: np.array, r: float = 1
) -> np.array:
    """
    _haversine distance equation.

    Parameters
    ----------
    lat1, lat2: np.array
        The latitude of points 1 and 2 in units of degrees. Can be n-dimensional.
    lon1, lon2: np.array
        The longitude of points 1 and 2 in units of degrees. Can be n-dimensional.
    r: float
        The sphere radius.
    """
    assert (
        lat1.shape == lon1.shape == lat2.shape == lon2.shape
    ), 'All input arrays must have the same shape.'
    lat1_rad = np.deg2rad(lat1)
    lat2_rad = np.deg2rad(lat2)
    lon1_rad = np.deg2rad(lon1)
    lon2_rad = np.deg2rad(lon2)

    d = (
        2
        * r
        * np.arcsin(
            np.sqrt(
                np.sin((lat1_rad - lat2_rad) / 2) ** 2
                + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin((lon2_rad - lon1_rad) / 2) ** 2
            )
        )
    )
    return d
