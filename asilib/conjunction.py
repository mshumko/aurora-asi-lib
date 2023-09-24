import importlib
from typing import Tuple, Union, Callable
import warnings
import functools

import numpy as np
import pandas as pd
from matplotlib.dates import date2num
import matplotlib.pyplot as plt  # TODO: Remove when done testing.
import pymap3d
import scipy

try:
    import IRBEM
except ImportError:
    pass  # make sure that asilb.__init__ fully loads and crashes if the user calls asilib.lla2footprint()

import asilib
from asilib.imager import _haversine

earth_radius_km = 6371


class Conjunction:
    """
    Calculates conjunctions between an imager and a satellite.

    Parameters
    ----------
    imager: asilib.Imager
        An instance of the imager class.
    satellite: tuple or pd.Dataframe
        Satellite time stamps and position in the latitude, longitude, altitude (LLA) coordinates.

        If a tuple, the first element must be a np.array of shape (n) filled with
        datetime.datetime() timestamps. The second tuple element must be a np.array
        of shape (n, 3) with the satellite positions with the columns mapping to
        (latitude, longitude, altitude), in that order. This tuple is converted to a
        pd.Dataframe described below.

        If a pd.Dataframe, the index must be pd.Timestamp() and the columns correspond to
        (latitude, longitude, altitude). The columns do not need to be in that order, but are
        automatically distinguished by searching for columns that match "lat", "lon", and "alt"
        (case insensitive).
    """
    def __init__(self, imager: asilib.Imager, satellite: Union[tuple, pd.DataFrame]) -> None:
        self.imager = imager
        assert hasattr(imager, 'skymap'), 'imager does not contain a skymap.'

        assert isinstance(
            satellite, (tuple, pd.DataFrame)  # TODO: Add support for pyaurorax ephemeris.
        ), 'satellite must be a tuple or pd.Dataframe.'
        if isinstance(satellite, tuple):
            assert len(satellite) == 2, 'Satellite tuple must have length of 2'
            assert isinstance(
                satellite[0], np.ndarray
            ), 'satellite tuple must contain two np.arrays'
            assert isinstance(
                satellite[1], np.ndarray
            ), 'satellite tuple must contain two np.arrays'
            assert (
                satellite[1].shape[1] == 3
            ), '2nd element in the satellite tuple must have 3 columns.'
            self.sat = pd.DataFrame(
                index=satellite[0],
                data={
                    'lat': satellite[1][:, 0],
                    'lon': satellite[1][:, 1],
                    'alt': satellite[1][:, 2],
                },
            )
        else:  # the pd.Dataframe case.
            self.sat = self._rename_satellite_df_columns(satellite)
        if np.nanmax(self.sat['lon']) > 180:
            raise ValueError('Satellite longitude must be in the range -180 to 180 degrees.')
        return

    def _rename_satellite_df_columns(self, df: pd.DataFrame):
        """
        Detect and rename the satellite df columns to lat, lon, and alt.
        """
        lon_keys = [key for key in df.columns if 'lon' in key.lower()]
        lat_keys = [key for key in df.columns if 'lat' in key.lower()]
        alt_keys = [key for key in df.columns if 'alt' in key.lower()]
        assert len(lon_keys) == 1, f'{len(lon_keys)} longitude columns found from {df.columns}.'
        assert len(lat_keys) == 1, f'{len(lat_keys)} latitude columns found from {df.columns}.'
        assert len(alt_keys) == 1, f'{len(alt_keys)} altitude columns found from {df.columns}.'
        df = df.rename(columns={lon_keys[0]: 'lon', lat_keys[0]: 'lat', alt_keys[0]: 'alt'})
        return df

    def find(self, min_el=20, time_gap_s=60):
        """
        Finds the start and end times of conjunctions defined by a minimum elevation.

        Parameters
        ----------
        min_el: float
            The minimum elevation of the conjunction.
        """
        assert 0 < min_el < 90, "The minimum elevation must be between 0 and 90 degrees."

        # # Filter the elevation map to values > min_el
        self._lon_map, self._lat_map, _ = self.imager._mask_low_horizon(
            self.imager.skymap['lon'],
            self.imager.skymap['lat'],
            self.imager.skymap['el'],
            min_elevation=min_el,
        )

        # Search LLA for times when it was inside the map box
        conjunction_idx = np.where(
            (self.sat['lat'] > np.nanmin(self._lat_map))
            & (self.sat['lat'] < np.nanmax(self._lat_map))
            & (self.sat['lon'] > np.nanmin(self._lon_map))
            & (self.sat['lon'] < np.nanmax(self._lon_map))
        )[0]
        if conjunction_idx.shape[0] == 0:
            return pd.DataFrame(columns=['start_time', 'end_time', 'start_index', 'end_index'])

        start, end = self._conjunction_intervals(self.sat.index[conjunction_idx], min_dt=time_gap_s)

        df = pd.DataFrame(
            data={
                'start_time': self.sat.index[conjunction_idx][start],
                'end_time': self.sat.index[conjunction_idx][end],
                'start_index': conjunction_idx[start],
                'end_index': conjunction_idx[end],
            }
        )
        return df

    def intensity(
        self, box: Tuple[float, float] = None, box_op: Callable = None
    ) -> np.ndarray:
        """
        Calculate the auroral intensity near the satellite's footprint at the ASI time stamps.

        Parameters
        ----------
        box: Tuple[float, float]
            A tuple of two floats that specifies the rectangular area, at the auroral emission
            altitude, in which to calculate the auroral intensity. The intensities in the box
            are averaged by default, and can be changed using the ``box_op`` kwarg. If ``box_size=None``,
            the auroral intensity will come from the pixel nearest to the footprint. In this case the
            box_op kwarg is irrelevant.
        box_op: Callable
            The function to apply to the auroral intensity in the box surrounding the footprint. Since
            it must operate on the mask array that :py:meth:`~asilib.Conjunction.equal_area()` produces,
            the ``box_op`` function must work with (i.e., ignore) ``np.nan`` values. If None, the function
            is np.nanmean() summed over the x-y pixels.

        Returns
        -------
        np.ndarray
            The auroral intensity near the footprint, calculated either from the nearest pixel
            (if ``box_size=None``) or the mean intensity in a rectangular area defined by
            ``box_size``.

        .. note::
            If box_size=None the nearest pixel is calculated using :py:meth:`~asilib.Conjunction.map_azel`, otherwise
            if ``box_size=(10, 10)`` and ``box_op`` is the default, :py:meth:`~asilib.Conjunction.equal_area()` is
            used to calculate the mean intensity in a 10x10 km box. The two different implementations should yield
            similar results, but discrepancies may arise if the skymap (az, el) and (lat, lon) mapping arrays are
            mismatched. This is the case for some of the THEMIS ASIs right after they were deployed.
        """
        self.interp_sat()  # Need the sat time stamps and coordinates to match the Imager's.
        
        if len(self.imager.meta['resolution']) == 2: # white-light intensity
            _intensity = np.nan * np.zeros(self.sat.shape[0], dtype=float)
        elif len(self.imager.meta['resolution']) == 3: # RGB intensity
            _intensity = np.nan * np.zeros(
                (self.sat.shape[0], self.imager.meta['resolution'][-1]), dtype=float
                )
        else:
            raise ValueError(
                f'Imager resolution must be 2d or 3d, not {len(self.imager.meta["resolution"])}d.'
                )

            
        if box is None:  # Nearest pixel to footprint
            _, azel_pixels = self.map_azel()
            for i, ((_, image), pixels) in enumerate(zip(self.imager, azel_pixels)):
                if np.any(np.isnan(pixels)):
                    continue
                # The ::-1 b/c pixels are in plotting (not indexing) order.
                _intensity[i] = image[int(pixels[1]), int(pixels[0])]
        else:  # Area around footprint
            box_op = functools.partial(np.nanmean, axis=(0,1))  # Sum only the x-y pixels.
            # equal_area_gen() is slower than using equal_area(), but this plays nice with memory.
            gen = self.equal_area_gen(box=box)
            for i, ((_, image), mask) in enumerate(zip(self.imager, gen)):
                _intensity[i] = box_op(image * mask)
        return _intensity

    def interp_sat(self):
        """
        Interpolate the satellite timestamps and LLA to imager timestamps.
        """
        imager_times, _ = self.imager.data
        numeric_imager_times = date2num(imager_times)
        numeric_sat_times = date2num(self.sat.index)
        if len(imager_times) == 0:
            raise ValueError('No imager time stamps to interpolate over.')

        assert np.all(
            np.diff(numeric_imager_times) > 0
        ), 'Imager times are not strictly increasing.'
        assert np.all(
            np.diff(numeric_sat_times) > 0
        ), 'satellite times are not strictly increasing.'

        interpolated_lla = {}

        # TODO: Detect when longitudes cross the 180-meridian and
        # correctly interpolate. Use the FIREBIRD data_processing code.
        for key in ['lat', 'lon', 'alt']:
            interpolated_lla[key] = np.interp(
                numeric_imager_times,
                numeric_sat_times,
                self.sat.loc[:, key],
                left=np.nan,
                right=np.nan,
            )
        if np.nanmax(np.abs(np.diff(self.sat.loc[:, 'lon']))) > 200:
            warnings.warn(
                'The asilib.Conjunction.interp_sat() does not yet correctly interpolate'
                'longitudes across the 180-meridian.',
                UserWarning,
            )
        self.sat = pd.DataFrame(index=imager_times, data=interpolated_lla)
        return self.sat

    def lla_footprint(
        self,
        alt: float,
        b_model: str = 'OPQ77',
        maginput: dict = None,
        hemisphere: int = 0,
    ) -> np.ndarray:
        """
        Map the spacecraft's position to ``alt`` along the magnetic field line.
        The mapping is implemented in ``IRBEM`` and by default it maps to the same
        hemisphere.

        Parameters
        ----------
        map_alt: float
            The altitude to map to, in km, in the same hemisphere.
        b_model: str
            The magnetic field model to use, by default the model is Olson-Pfitzer
            1974. This parameter is passed directly into IRBEM.MagFields as the
            'kext' parameter.
        maginput: dict
            If you use a different b_model that requires time-dependent parameters,
            supply the appropriate values to the maginput dictionary. It is directly
            passed into IRBEM.MagFields so refer to IRBEM on the proper format.
        hemisphere: int
            The hemisphere to map to. This kwarg is passed to IRBEM and can be one of
            these four values:
            0    = same magnetic hemisphere as starting point
            +1   = northern magnetic hemisphere
            -1   = southern magnetic hemisphere
            +2   = opposite magnetic hemisphere as starting point

        Returns
        -------
        magnetic_footprint: np.ndarray
            A numpy.array with size (n_times, 3) with lat, lon, alt
            columns representing the magnetic footprint coordinates.

        Raises
        ------
        ImportError
            If IRBEM can't be imported.
        """
        if importlib.util.find_spec('IRBEM') is None:
            raise ImportError(
                "IRBEM can't be imported. This is a required dependency for asilib.lla2footprint()"
                " that must be installed separately. See https://github.com/PRBEM/IRBEM"
                " and https://aurora-asi-lib.readthedocs.io/en/latest/installation.html."
            )

        magnetic_footprint = np.nan * np.zeros((self.sat.shape[0], 3))

        # TODO: Do a trade study with geopack (https://pypi.org/project/geopack/)
        m = IRBEM.MagFields(kext=b_model)  # Initialize the IRBEM model.

        # Loop over every set of satellite coordinates.
        for i, (_time, (_lat, _lon, _alt)) in enumerate(self.sat.iterrows()):
            X = {'datetime': _time, 'x1': _alt, 'x2': _lat, 'x3': _lon}
            m_output = m.find_foot_point(X, maginput, alt, hemisphere)
            magnetic_footprint[i, :] = m_output['XFOOT']
        # Map from IRBEM's (alt, lat, lon) -> (lat, lon, alt)
        # magnetic_footprint[:, [2, 0, 1]] = magnetic_footprint[:, [0, 1, 2]]
        self.sat.loc[:, ['alt', 'lat', 'lon']] = magnetic_footprint
        self.sat[self.sat['lat'] == -1E31] = np.nan
        return self.sat

    def map_azel(self, min_el=0) -> Tuple[np.ndarray, np.ndarray]:
        """
        Maps a satellite's location to the ASI's azimuth and elevation (azel)
        coordinates and image pixel index.

        Parameters
        ----------
        min_el: float
            The minimum elevation in degrees for which return valid values for.
            The satellite's azel values and pixel indices are NaN below min_el.

        Returns
        -------
        np.ndarray
            An array with shape (nPosition, 2) of the satellite's azimuth and
            elevation coordinates.
        np.ndarray
            An array with shape (nPosition, 2) of the x- and y-axis pixel
            indices for the ASI image.

        .. note::
            The azel pixel columns are ordered for plotting with an image:
            plt.plot(azel_pixels[:, 0], azel_pixels[:, 1]). However, the
            column order must be flipped for indexing. For example:
            image[azel_pixels[:, 1], azel_pixels[:, 0]]
        """
        azel = np.nan * np.zeros((self.sat.shape[0], 2))

        for i, (_, (lat_i, lon_i, alt_km_i)) in enumerate(self.sat.iterrows()):
            any_nan = np.any(np.isnan([lat_i, lon_i, alt_km_i]))
            any_neg = np.any([lat_i, lon_i, alt_km_i] == -1e31)  # IRBEM error value.
            if any_nan or any_neg:
                continue

            az, el, _ = pymap3d.geodetic2aer(
                lat_i,
                lon_i,
                1e3 * alt_km_i,  # Meters
                self.imager.meta['lat'],
                self.imager.meta['lon'],
                1e3 * self.imager.meta['alt'],  # Meters
            )
            azel[i, :] = [az, el]

        # Now find the corresponding x- and y-axis pixel indices.
        azel_pixels = self._nearest_pixel(azel)

        # Mask elevations below min_el as NaN. This is necessary because
        # _nearest_pixel will find the nearest pixel even if the delta
        # az and delta el is large.
        invalid_el = np.where(azel[:, 1] < min_el)[0]
        azel[invalid_el, :] = np.nan
        azel_pixels[invalid_el, :] = np.nan
        return azel, azel_pixels

    def equal_area(self, box: Tuple[float, float] = (5, 5)) -> np.ndarray:
        """
        Find all pixels around the footprint within a rectangular area
        defined by box.

        Parameters
        ----------
        box: Tuple[float, float]
            Bounds the emission area box dimensions in longitude and latitude.
            Units are kilometers.

        Returns
        -------
        np.ndarray
            An array with dimensions (n_time, n_x_pixels, n_y_pixels) with
            dimensions n_x_pixels and n_y_pixels dimensions the size of each
            image. Values inside the area are 1 and outside are np.nan.

        See Also
        --------
        Conjunction.equal_area_gen : A memory-friendly way to calculate equal areas.

        """
        assert len(box) == 2, 'The box_km parameter must have a length of 2.'

        self.area_mask = np.nan * np.zeros((self.sat.shape[0], *self.imager.meta['resolution']))

        gen = self.equal_area_gen(box=box)

        for i, mask in enumerate(gen):
            # Check that the lat/lon values are inside the skymap coordinates.
            self.area_mask[i, :, :] = mask
        return self.area_mask

    def equal_area_gen(self, box: Tuple[float, float] = (5, 5)) -> np.ndarray:
        """
        Generator to find all pixels around the footprint within a rectangular area
        defined by box.

        Parameters
        ----------
        box: Tuple[float, float]
            Bounds the emission box dimensions in longitude and latitude.
            Units are kilometers.

        Returns
        -------
        np.ndarray
            An array with (n_time, n_x_pixels, n_y_pixels) dimensions with
            dimensions n_x_pixels and n_y_pixels dimensions the size of each
            image. Values inside the area are 1 and outside are np.nan.
        """
        assert len(box) == 2, 'The box_km parameter must have a length of 2.'

        lat_map = self.imager.skymap['lat']
        lon_map = self.imager.skymap['lon']

        for lat, lon, alt in self.sat.to_numpy():
            mask = np.nan * np.zeros(self.imager.meta['resolution'])
            dlat = self._dlat(box[1], alt)
            dlon = self._dlon(box[0], alt, lat)
            # Check that the lat/lon values are inside the skymap coordinates.
            if (
                (lat > np.nanmax(lat_map))
                or (lat < np.nanmin(lat_map))
                or (lon > np.nanmax(lon_map))
                or (lon < np.nanmin(lon_map))
                or np.isnan(lat)
                or np.isnan(lon)
                or np.isnan(alt)
            ):
                warnings.warn(
                    'Some latitude or longitude values are outside of the skymap '
                    'lat/lon arrays or are invalid. The equal area mask will be '
                    'all NaNs.'
                )
                yield mask
                continue

            # Find the indices of the box. If none were found (pixel smaller than
            # the box_size_km) then increase the box size until one pixel is found.
            masked_box_len = 0
            multiplier = 1
            step = 0.1

            while masked_box_len == 0:
                idx_box = np.where(
                    (lat_map >= lat - multiplier * dlat / 2)
                    & (lat_map <= lat + multiplier * dlat / 2)
                    & (lon_map >= lon - multiplier * dlon / 2)
                    & (lon_map <= lon + multiplier * dlon / 2)
                )

                masked_box_len = len(idx_box[0])
                if masked_box_len:
                    mask[idx_box[0], idx_box[1]] = 1
                else:
                    multiplier += step
            yield mask

    def _dlat(self, d, alt):
        """
        Calculate the change in latitude that correpsponds to arc length distance d at
        alt altitude. Units are kilometers. Both d and alt must be the same length.

        Parameters
        ----------
        d: float or np.ndarray
            A float, 1d list, or 1d np.array of arc length.
        alt: float or np.ndarray
            A float, 1d list, or 1d np.array of satellite altitudes.

        Returns
        -------
        dlat: float or np.ndarray
            A float or an array of the corresponding latitude differences in degrees.
        """
        if isinstance(alt, list):  # Don't need to cast d since it is in np.divide().
            alt = np.array(alt)
        return np.rad2deg(np.divide(d, (earth_radius_km + alt)))

    def _dlon(self, d, alt, lat):
        """
        Calculate the change in longitude that corresponds to arc length distance d at
        a lat latitude, and alt altitude.

        Parameters
        ----------
        d: float or np.ndarray
            A float or an array of arc length in kilometers.
        alt: float or np.ndarray
            A float or an array of satellite altitudes in kilometers.
        lat: float
            The latitude to evaluate the change in longitude in degrees.

        Returns
        -------
        dlon: float or np.ndarray
            A float or an array of the corresponding longitude differences in degrees.
        """
        if isinstance(alt, list):  # Don't need to cast other variables.
            alt = np.array(alt)

        numerator = np.sin(d / (2 * (earth_radius_km + alt)))
        denominator = np.cos(np.deg2rad(lat))
        dlon_rads = 2 * np.arcsin(numerator / denominator)
        return np.rad2deg(dlon_rads)

    def _nearest_pixel(self, azel, n_max_vectorize=1_000) -> np.ndarray:
        """
        Locate the nearest ASI skymap (x, y) pixel indices.

        Parameters
        ----------
        azel: array
            A 1d or 2d array of satellite azimuth and elevation points.
            If 2d, the rows corresponds to time.
        n_max_vectorize: int
            The maximum number of azel values before switching from the vectorized
            mode to the for-loop mode.

        Returns
        -------
        np.ndarray
            An array with the same shape as azel, but representing the
            x- and y-axis pixel indices in the ASI image.
        """
        pixel_index = np.nan * np.ones_like(azel)

        if azel.shape[0] < n_max_vectorize:
            skymap_shape = self.imager.skymap['el'].shape
            # Broadcast the skymaps such that the skymaps are copies along dim 0.
            # I need to read up on how broadcasting works in numpy, but it should
            # be very memory efficient.
            asi_el = np.broadcast_to(
                self.imager.skymap['el'][np.newaxis, :, :],
                (azel.shape[0], skymap_shape[0], skymap_shape[1]),
            )
            asi_az = np.broadcast_to(
                self.imager.skymap['az'][np.newaxis, :, :],
                (azel.shape[0], skymap_shape[0], skymap_shape[1]),
            )
            sat_az = azel[:, 0]
            sat_az = np.broadcast_to(sat_az[:, np.newaxis, np.newaxis], asi_el.shape)
            sat_el = azel[:, 1]
            sat_el = np.broadcast_to(sat_el[:, np.newaxis, np.newaxis], asi_el.shape)
            distances = _haversine(asi_el, asi_az, sat_el, sat_az)
            # This should be vectorized too, but np.nanargmin() can't find a minimum
            # along the 1st and 2nd dims.
            for i, distance in enumerate(distances):
                if np.all(np.isnan(distance)):
                    continue
                pixel_index[i, :] = np.unravel_index(np.nanargmin(distance), distance.shape)
                pass
        else:
            # Calculate one at a time to save memory.
            for i, (az, el) in enumerate(azel):
                el = el * np.ones_like(self.imager.skymap['el'])
                az = el * np.ones_like(self.imager.skymap['az'])
                distances = _haversine(self.imager.skymap['el'], self.imager.skymap['az'], el, az)
                pixel_index[i, :] = np.unravel_index(np.nanargmin(distances), distances.shape)
        # Before, pixel_index columns corresponded to (row, column) = (y-pixel, x-pixel), but for plotting
        # we need to flip them to be (column, row) = (x-pixel, y-pixel).
        pixel_index[:, [1, 0]] = pixel_index[:, [0, 1]]
        return pixel_index

    def _conjunction_intervals(self, times: np.array, min_dt: float):
        """
        Given an array of times that contain continuously incrementing spans of
        time with gaps between them, calculate the start and end indices of each
        time span.

        Parameters
        ----------
        times: np.array
            The array of continuos times with gaps.
        min_dt: float
            The minimum time gap threshold.

        Returns
        -------
        np.array
            An array of start indices for times
        np.array
            An array of end indices for times
        """
        dt = (times[1:] - times[:-1]).total_seconds()
        dIntervals = dt / min_dt
        # Calculate the start and end indices excluding the first and last index
        # dIntervals > 1 means tha a time gap exceeded the threshold.
        break_indices = np.where(dIntervals > 1)[0]

        # Add in the first and last index.
        start = np.insert(break_indices + 1, 0, 0)
        end = np.append(break_indices, len(dIntervals))
        return start, end
