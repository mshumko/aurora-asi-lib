"""
The Imagers class handles multiple Imager objects and coordinates plotting and animating multiple
fisheye lens and mapped images. The mapped images are also called mosaics.
"""

from typing import Tuple
from collections import namedtuple
from datetime import datetime

import numpy as np
import matplotlib.pyplot as plt

from asilib.imager import Imager, _haversine


class Imagers:
    """
    Plot and animate multiple :py:meth:`~asilib.imager.Imager` objects.

    .. warning::

        This class is in development and not all methods are implemented/matured.

    Parameters
    ----------
    imagers: Tuple
        The Imager objects to plot and animate. 
    """
    def __init__(self, imagers:Tuple[Imager]) -> None:
        self.imagers = imagers
        return
    
    def plot_fisheye(self, ax:Tuple[plt.Axes], **kwargs):
        """
        Plots one fisheye image in each subplot, oriented with North on the top, and East on the 
        left of the image.

        Parameters
        ----------
        ax: Tuple[plt.Axes]
            Subplots corresponding to each fisheye lens image.
        kwargs: dict
            Keyword arguments directly passed into each :py:meth:`~asilib.imager.Imager.plot_fisheye()`
            method.

        Example
        -------
        >>> from datetime import datetime
        >>> 
        >>> import matplotlib.pyplot as plt
        >>> import asilib
        >>> import asilib.asi
        >>> 
        >>> time = datetime(2007, 3, 13, 5, 8, 45)
        >>> location_codes = ['FSIM', 'ATHA', 'TPAS', 'SNKQ']
        >>> 
        >>> fig, ax = plt.subplots(1, len(location_codes), figsize=(12, 3.5))
        >>> 
        >>> _imagers = []
        >>> 
        >>> for location_code in location_codes:
        >>>     _imagers.append(asilib.asi.themis(location_code, time=time))
        >>> 
        >>> for ax_i in ax:
        >>>     ax_i.axis('off')
        >>> 
        >>> asis = asilib.Imagers(_imagers)
        >>> asis.plot_fisheye(ax=ax)
        >>> 
        >>> plt.suptitle('Donovan et al. 2008 | First breakup of an auroral arc')
        >>> plt.tight_layout()
        >>> plt.show()
        """
        assert len(ax) == len(self.imagers), 'Number of subplots must equal the number of imagers.'

        for ax_i, imager_i in zip(ax, self.imagers):
            imager_i.plot_fisheye(ax=ax_i, **kwargs)
        return
    
    def plot_map(self, overlap=False, **kwargs):
        """
        Projects multiple ASI images onto a map at an altitude that is defined in the skymap 
        calibration file.

        Parameters
        ----------
        overlap: bool
            If False, allow no overlapping pixels: if any two pixels are co-located on
            the (lat, lon) grid point, only the pixel at the higher elevation pixel is plotted.
            If True, pixels that overlap between imager FOV's are overplotted such that only the 
            final imager's pixels are shown.
        kwargs: dict
            Keyword arguments directly passed into each :py:meth:`~asilib.imager.Imager.plot_map()`
            method.

        Example
        -------
        >>> from datetime import datetime
        >>> 
        >>> import matplotlib.pyplot as plt
        >>> 
        >>> import asilib
        >>> import asilib.map
        >>> import asilib.asi
        >>> 
        >>> time = datetime(2007, 3, 13, 5, 8, 45)
        >>> location_codes = ['FSIM', 'ATHA', 'TPAS', 'SNKQ']
        >>> map_alt = 110
        >>> min_elevation = 2
        >>> 
        >>> ax = asilib.map.create_map(lon_bounds=(-140, -60), lat_bounds=(40, 82))
        >>> 
        >>> _imagers = []
        >>> 
        >>> for location_code in location_codes:
        >>>     _imagers.append(asilib.asi.themis(location_code, time=time, alt=map_alt))
        >>> 
        >>> asis = asilib.Imagers(_imagers)
        >>> asis.plot_map(ax=ax, overlap=False, min_elevation=min_elevation)
        >>> 
        >>> ax.set_title('Donovan et al. 2008 | First breakup of an auroral arc')
        >>> plt.show()
        """
        if not overlap:
            self._calc_overlap_mask()

        for imager in self.imagers:
            imager.plot_map(**kwargs)
        return
    
    def animate_fisheye(self, ax:Tuple[plt.Axes], **kwargs):  # TODO: Explicitly define kwargs.
        """
        A wrapper for the ```animate_fisheye_gen()``` method that animates a series of
        fisheye images. Any kwargs are passed directly into ```animate_fisheye_gen()```.

        Parameters
        ----------
        ax: Tuple[plt.Axes]
            Subplots corresponding to each fisheye lens image.
        kwargs: dict
            Keyword arguments directly passed into each :py:meth:`~asilib.imager.Imagers.animate_fisheye_gen()`
            method.
        """
        movie_generator = self.animate_fisheye_gen(ax, **kwargs)

        for _ in movie_generator:
            pass
        return
    
    def animate_fisheye_gen(self, ax:Tuple[plt.Axes]):
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
        ax: Tuple[plt.Axes]
            Subplots corresponding to each fisheye lens image.
        TODO: Finish kwargs.
        """
    
        gen = self.parallel_image_loop(self, max_dt=None)
        for imager_id, image in gen:
            # Plot fisheye lens images. Call the methods or make our own?
            yield

        return
    
    def parallel_image_loop(self, max_dt=None):
        raise NotImplementedError

        gens = {img.meta['location_code']:iter(img) for img in self.imagers}
        imager_names = gens.keys()
        paused_gens = []

        for time_i in times:
            for _imager in self.imagers:
                try:
                    asi_time = _imager[time_i]
                except FileNotFoundError:
                    pass
                
        return
    
    # def animate_map(self):
        
    #     raise NotImplementedError
    
    # def animate_map_gen(self, overlap=False):
    #     if overlap:
    #         self._calc_overlap_mask()
    #     raise NotImplementedError

    def get_points(self, min_elevation:float=10, overlap:bool=False)->Tuple[np.ndarray, np.ndarray]:
        """
        Get pixel intensities in each (lat, lon) grid point.

        Parameters
        ----------
        min_elevation: float
            Only return pixel intensities above min_elevation.
        overlap: bool
            If False, allow no overlapping pixels: if any two pixels are co-located on
            the (lat, lon) grid point, only the pixel at the higher elevation is kept.
            If True, return all pixel intensities above min_elevation.

        Returns
        -------
        np.ndarray
            An (n, 2) array with each row corresponding to a (lat, lon) point.
        np.ndarray
            Pixel intensities with shape (n) for white-light images, and (n, 3) for RGB images.

        Examples
        --------
        >>> from datetime import datetime
        >>> 
        >>> import asilib
        >>> import asilib.asi
        >>> 
        >>> time = datetime(2007, 3, 13, 5, 8, 45)
        >>> location_codes = ['FSIM', 'ATHA', 'TPAS', 'SNKQ']
        >>> map_alt = 110
        >>> min_elevation = 2
        >>> 
        >>> _imagers = [asilib.asi.themis(location_code, time=time, alt=map_alt) 
        >>>             for location_code in location_codes]
        >>> asis = asilib.Imagers(_imagers)
        >>> lat_lon_points, intensities = asis.get_points(min_elevation=min_elevation)

        >>> # A comprehensive example showing how Imagers.get_points() can closely reproduce 
        >>> # Imagers.plot_map()
        >>> from datetime import datetime
        >>> 
        >>> import matplotlib.pyplot as plt
        >>> import matplotlib.colors
        >>> 
        >>> import asilib
        >>> import asilib.map
        >>> import asilib.asi
        >>> 
        >>> time = datetime(2007, 3, 13, 5, 8, 45)
        >>> location_codes = ['FSIM', 'ATHA', 'TPAS', 'SNKQ']
        >>> map_alt = 110
        >>> min_elevation = 2
        >>> 
        >>> _imagers = [asilib.asi.themis(location_code, time=time, alt=map_alt) 
        >>>             for location_code in location_codes]
        >>> asis = asilib.Imagers(_imagers)
        >>> lat_lon_points, intensities = asis.get_points(min_elevation=min_elevation)
        >>> 
        >>> fig = plt.figure(figsize=(12,5))
        >>> ax = asilib.map.create_simple_map(
        >>>     lon_bounds=(-140, -60), lat_bounds=(40, 82), fig_ax=(fig, 121)
        >>>     )
        >>> bx = asilib.map.create_simple_map(
        >>>     lon_bounds=(-140, -60), lat_bounds=(40, 82), fig_ax=(fig, 122)
        >>>     )
        >>> asis.plot_map(ax=ax, overlap=False, min_elevation=min_elevation)
        >>> bx.scatter(lat_lon_points[:, 1], lat_lon_points[:, 0], c=intensities, 
        >>>         norm=matplotlib.colors.LogNorm())
        >>> ax.text(0.01, 0.99, f'(A) Mosaic using Imagers.plot_map()', transform=ax.transAxes, 
        >>>         va='top', fontweight='bold', color='red')
        >>> bx.text(0.01, 0.99, f'(B) Mosaic from Imagers.get_points() scatter', transform=bx.transAxes,
        >>>         va='top', fontweight='bold', color='red')
        >>> fig.suptitle('Donovan et al. 2008 | First breakup of an auroral arc')
        >>> plt.tight_layout()
        >>> plt.show()
        """
        lat_lon_points = np.zeros((0, 2), dtype=float)
        if len(self.imagers[0].meta['resolution']) == 3: # RGB
            intensities  = np.zeros((0, self.imagers[0].meta['resolution'][-1]), dtype=float)
        else:  # single-color (or white light)
            intensities  = np.zeros(0, dtype=float)

        if not overlap:
            self._calc_overlap_mask()

        for _imager in self.imagers:
            assert 'time' in _imager.file_info.keys(), (
                f'Imagers.get_points() only works with single images.'
                )
            image = _imager.data.image
            _masked_lon_map, _masked_lat_map, _masked_image = _imager._mask_low_horizon(
                _imager.skymap['lon'], _imager.skymap['lat'], _imager.skymap['el'], min_elevation, 
                image=image
            )
            if _imager.skymap['lon'].shape[0] == image.shape[0] + 1:
                # Skymap defines vertices. We look for NaNs at either of the pixel edges.
                _valid_idx = np.where(
                    ~np.isnan(_masked_lon_map[1:, 1:]-_masked_lon_map[:-1, :-1])
                    )
            elif _imager.skymap['lon'].shape[0] == image.shape[0]:
                # Skymap defines pixel centers
                _valid_idx = np.where(~np.isnan(_masked_lon_map))
            else:
                raise ValueError(f'The skymap shape: {_imager.skymap["lon"].shape} and image '
                                 f'shape: {image.shape} are incompatible.')

            lat_grid = _masked_lat_map[_valid_idx[0], _valid_idx[1]]
            lon_grid = _masked_lon_map[_valid_idx[0], _valid_idx[1]]
            intensity = _masked_image[_valid_idx[0], _valid_idx[1], ...]

            # Concatenate joins arrays along an existing axis, while stack joins arrays
            # along a new axis. 
            intensities = np.concatenate((intensities, intensity))
            lat_lon_points = np.concatenate((
                lat_lon_points, 
                np.stack((lat_grid, lon_grid)).T
                ))
        return lat_lon_points, intensities
    
    def _calc_overlap_mask(self):
        """
        Calculate which pixels to plot for overlapping imagers by the criteria that the ith 
        imager's pixel must be closest to that imager (and not a neighboring one).

        Algorithm:
        1. Loop over ith imager
        2. Loop over jth imager within 500 km distance of the ith imager
        3. Mask low-elevations with np.nan
        4. Create a distance array with shape (resolution[0], resolution[1], j_total)
        5. For all pixels in ith imager, calculate the haversine distance to jth imager and 
        assign it to distance[..., j].
        6. For all pixels calculate the nearest imager out of all j's.
        7. If the minimum j is not the ith imager, mask the imager.skymap['lat'] and 
        imager.skymap['lon'] as np.nan.
        """
        if hasattr(self, '_masked'):
            return

        for i, imager in enumerate(self.imagers):
            _distances = np.nan*np.ones((*imager.skymap['lat'].shape, len(self.imagers)))
            for j, other_imager in enumerate(self.imagers):
                # Calculate the distance between all imager pixels and every other imager 
                # location (including itself).
                _distances[:, :, j] = _haversine(
                    imager.skymap['lat'], imager.skymap['lon'],
                    np.broadcast_to(other_imager.meta['lat'], imager.skymap['lat'].shape), 
                    np.broadcast_to(other_imager.meta['lon'], imager.skymap['lat'].shape)
                    )
            # Without this small reduction in the distance of pixels to its own imager,
            # there are gaps between the imager boundaries. In other words, this scaling
            # slightly biases to plotting pixels nearest to the imager. 
            _distances[:, :, i] *= 0.95
            # Need a masked array so that np.nanargmin correctly handles all NaN slices.
            _distances = np.ma.masked_array(_distances, np.isnan(_distances))
            # For each pixel, calculate the nearest imager. If the pixel is not closest to 
            # the imager that it's from, mask it as np.nan. Then the Imager._pcolormesh_nan() 
            # method then won't plot that pixel.
            min_distances = np.argmin(_distances, axis=2)
            far_pixels = np.where(min_distances != i)
            imager.skymap['lat'][far_pixels] = np.nan
            imager.skymap['lon'][far_pixels] = np.nan
        self._masked = True  # A flag to not run again.
        return
    
    
if __name__ == '__main__':
    from datetime import datetime
    
    import matplotlib.pyplot as plt
    import matplotlib.colors

    import asilib
    import asilib.map
    import asilib.asi
    
    time = datetime(2007, 3, 13, 5, 8, 45)
    location_codes = ['FSIM', 'ATHA', 'TPAS', 'SNKQ']
    map_alt = 110
    min_elevation = 2
    
    _imagers = []
    
    for location_code in location_codes:
        _imagers.append(asilib.asi.themis(location_code, time=time, alt=map_alt))
    
    asis = asilib.Imagers(_imagers)
    lat_lon_points, intensities = asis.get_points(min_elevation=min_elevation)

    fig = plt.figure(figsize=(12,5))
    ax = asilib.map.create_simple_map(
        lon_bounds=(-140, -60), lat_bounds=(40, 82), fig_ax=(fig, 121)
        )
    bx = asilib.map.create_simple_map(
        lon_bounds=(-140, -60), lat_bounds=(40, 82), fig_ax=(fig, 122)
        )
    asis.plot_map(ax=ax, overlap=False, min_elevation=min_elevation)
    bx.scatter(lat_lon_points[:, 1], lat_lon_points[:, 0], c=intensities, 
               norm=matplotlib.colors.LogNorm())
    ax.text(0.01, 0.99, f'(A) Mosaic using Imagers.plot_map()', transform=ax.transAxes, 
            va='top', fontweight='bold', color='red')
    bx.text(0.01, 0.99, f'(B) Mosaic from Imagers.get_points() scatter', transform=bx.transAxes,
            va='top', fontweight='bold', color='red')
    fig.suptitle('Donovan et al. 2008 | First breakup of an auroral arc')
    plt.tight_layout()
    plt.show()
    pass
