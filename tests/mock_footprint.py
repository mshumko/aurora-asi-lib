from datetime import datetime, timedelta
from typing import Tuple

import numpy as np
import matplotlib.pyplot as plt

import asilib.asi.themis


def footprint(
    center_lon: float,
    alt: float = 110,
    obit_period: float = 95 * 60,
    precession_rate: float = 10,
    cadence: float = 6,
    time_range: tuple = (datetime(2015, 1, 1), datetime(2015, 1, 2)),
) -> Tuple[np.array, np.array]:
    """
    Create a fake ephemeris for a LEO satellite.

    Parameters
    ----------
    center_lon:float
        The longitude at the midpoint of the time range.
    alt:float
        The footprint altitude in kilometers.
    obit_period:float
        The orbit period in seconds.
    precession_rate:float
        Controls how much the longitude change during the time_range,
        with the center_lon in the middle times.
    cadence:float
        The cadence of the footprint timestamps in seconds.
    time_range:tuple
        The start and end times that bound the footprint path.

    Returns
    -------
    np.array
        Footprint timestamps in datetime.datetime format.
    np.array
        An array of floats shaped (n_times, 3) with the footprint's
        lat, lon, alt coordinates.
    """
    n_seconds = (time_range[1] - time_range[0]).total_seconds()
    n_time_stamps = int(n_seconds / cadence)
    times = np.array([time_range[0] + timedelta(seconds=i * cadence) for i in range(n_time_stamps)])
    seconds_from_start = np.array([(time - times[0]).total_seconds() for time in times])

    lats = 90 * np.sin(2 * np.pi * seconds_from_start / obit_period)
    lons = np.linspace(
        center_lon - precession_rate / 2, center_lon + precession_rate, num=n_time_stamps
    )
    alts = alt * np.ones(n_time_stamps)
    lla = np.stack((lats, lons, alts)).T
    return times, lla


def visualize_footprint():
    """
    Visualize and validate that the footprint lons and lats are correct.
    """
    asi = asilib.asi.themis.themis('GILL', time='2015-01-01', load_images=False)
    times, lla = footprint(asi.meta['lon'])

    fig, ax = plt.subplots(3, 1)
    ax[0].plot(times, lla[:, 0])
    ax[1].plot(times, lla[:, 1])
    ax[2].plot(lla[:, 1], lla[:, 0])

    ax[0].set(xlabel='time', ylabel='lat [deg]')
    ax[1].set(xlabel='time', ylabel='lon [deg]')
    ax[2].set(xlabel='lon [deg]', ylabel='lat [deg]')
    return


if __name__ == '__main__':
    visualize_footprint()
    plt.show()
