import dateutil.parser

import matplotlib.pyplot as plt
import matplotlib.colors as colors
import numpy as np

from asilib.io.load import get_frames, load_cal_file


def keogram(time_range, mission, station, map_alt=None, ax=None, color_bounds=None, 
            color_norm='lin', title=True):
    """
    Makes a keogram along the central meridian.

    Parameters
    ----------
    time_range: List[Union[datetime, str]]
        A list with len(2) == 2 of the start and end time to get the
        frames. If either start or end time is a string,
        dateutil.parser.parse will attempt to parse it into a datetime
        object. The user must specify the UT hour and the first argument
        is assumed to be the start_time and is not checked.
    mission: str
        The mission id, can be either THEMIS or REGO.
    station: str
        The station id to download the data from.
    map_alt: int, optional
        The mapping altitude, in kilometers, used to index the mapped latitude in the 
        calibration data. If None, will plot pixel index for the y-axis.
    ax: plt.subplot
        The subplot to plot the frame on. If None, this function will
        create one.
    color_bounds: List[float] or None
        The lower and upper values of the color scale. If None, will
        automatically set it to low=1st_quartile and
        high=min(3rd_quartile, 10*1st_quartile)
    color_norm: str
        Sets the 'lin' linear or 'log' logarithmic color normalization.
    title: bool
        Toggles a default plot title with the format "date mission-station keogram".

    Returns
    -------
    ax: plt.Axes
        The subplot object to modify the axis, labels, etc.
    im: plt.AxesImage
        The plt.pcolormesh image object. Common use for im is to add a colorbar.

    Raises
    ------
    AssertionError
        If len(time_range) != 2. Also if map_alt does not equal the mapped 
        altitudes in the calibration mapped values.
    """

    # Run a few checks to make sure that the time_range parameter has length 2 and
    # convert time_range to datetime objects if it is a string.
    assert len(time_range) == 2, f'len(time_range) = {len(time_range)} is not 2.'
    for i, t_i in enumerate(time_range):
        if isinstance(t_i, str):
            time_range[i] = dateutil.parser.parse(t_i)

    frame_times, frames = get_frames(time_range, mission, station)

    # Find the pixel at the center of the camera.
    center_pixel = int(frames.shape[1]/2)

    if map_alt is not None:
        cal = load_cal_file(mission, station)
        assert map_alt in cal['FULL_MAP_ALTITUDE']/1000, \
            f'{map_alt} km is not in calibration altitudes: {cal["FULL_MAP_ALTITUDE"]/1000} km'
        alt_index = np.where(cal['FULL_MAP_ALTITUDE']/1000 == map_alt)[0][0]

        keogram_latitude = cal['FULL_MAP_LATITUDE'][alt_index, :, center_pixel]

    keo = np.nan*np.zeros((frames.shape[0], frames.shape[2]))

    for i, frame in enumerate(frames):
        keo[i, :] = frame[center_pixel, :]

    if map_alt is not None:
        # Since keogram_latitude values are NaNs near the image edges, we want to filter
        # out those indices from keogram_latitude and keo.
        valid_lats = np.where(~np.isnan(keogram_latitude))[0]
        keogram_latitude = keogram_latitude[valid_lats]
        keo = keo[:, valid_lats]

    if ax is None:
        _, ax = plt.subplots()

    # Figure out the color_bounds from the frame data.
    if color_bounds is None:
        lower, upper = np.quantile(keo, (0.25, 0.98))
        color_bounds = [lower, np.min([upper, lower * 10])]

    if color_norm == 'log':
        norm = colors.LogNorm(vmin=color_bounds[0], vmax=color_bounds[1])
    elif color_norm == 'lin':
        norm = colors.Normalize(vmin=color_bounds[0], vmax=color_bounds[1])
    else:
        raise ValueError('color_norm must be either "log" or "lin".')

    if map_alt is None:
        im = ax.pcolormesh(frame_times, np.arange(keo.shape[1]), keo.T, 
                        norm=norm, shading='auto')
    else:
        im = ax.pcolormesh(frame_times, keogram_latitude[::-1], keo.T, 
                        norm=norm, shading='auto')

    if title:
        ax.set_title(f'{time_range[0].date()} {mission.upper()}-{station.upper()} keogram')
    return ax, im


if __name__ == '__main__':
    ax, im = keogram(['2017-09-27T07:00:00', '2017-09-27T09:00:00'], 'REGO', 'LUCK', map_alt=230)
    plt.colorbar(im)
    plt.show()