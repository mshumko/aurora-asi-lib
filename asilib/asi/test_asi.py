"""
An ASI for testing asilib.Imager.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import pytest

import asilib
import asilib.utils as utils

@pytest.mark.skip(reason='This is an ASI wrapper and not a test.')
def test_asi(location_code:str, time: utils._time_type=None,
    time_range: utils._time_range_type=None, alt:int=110, 
    pixel_center:bool=True)-> asilib.Imager:
    """
    Create an Imager instance with the test_asi images and skymaps.

    Parameters
    ----------
    location_code: str
        The ASI's location code (four letters). Can be either GILL, ATHA, or TPAS.
        Case insensitive.
    time: str or datetime.datetime
        A time to look for the ASI data at. Either the time or the time_range
        must be specified.
    time_range: list of str or datetime.datetime
        A length 2 list of string-formatted times or datetimes to bracket
        the ASI data time interval.
    alt: int
        The reference skymap altitude, in kilometers.
    pixel_center: bool
        If True, then the skymap specifies the pixel centers, otherwise the skymap specifies 
        the pixel vertices. Specifying the vertices more accurately describes how the pixels
        field of view transforms from a square to a polynomial.

    Returns
    -------
    :py:meth:`~asilib.imager.Imager`
        The an Imager instance with the test_asi data.
    """
    location_code = location_code.upper()
    locations = asi_info()
    _location = locations.loc[locations.index == location_code, :]

    meta = get_meta(_location)
    skymap = get_skymap(meta, alt=alt, pixel_center=pixel_center)
    data = get_data(meta, time=time, time_range=time_range)
    return asilib.Imager(data, meta, skymap)

def asi_info()->pd.DataFrame:
    """
    The test ASI has three locations, a, b, and c.
    """
    locations = pd.DataFrame(data=np.array([
        [56.3494, -94.7056, 500],
        [54.7213, -113.285, 1000],
        [53.8255, -101.2427, 0],
        ]), 
        columns=['lat', 'lon', 'alt'],
        index=['GILL', 'ATHA', 'TPAS']
        )
    return locations

def get_meta(location_dict):
    """
    Get the ASI metadata.
    """
    meta = {
        'array': 'TEST',
        'location': location_dict.index,
        'lat': location_dict['lat'].to_numpy(),
        'lon': location_dict['lon'].to_numpy(),
        'alt': location_dict['alt'].to_numpy() / 1e3,  # km 
        'cadence': 10,
        'resolution': (512, 512),
    }
    return meta

def get_skymap(meta:dict, alt:int, pixel_center:bool=True):
    """
    Create a skymap based on the ASI location in the metadata.

    Parameters
    ----------
    meta: dict
        The ASI metadata with the imager resolution and cadence.
    alt: int
        The reference skymap altitude, in kilometers.
    pixel_center: bool
        If True, then the skymap specifies the pixel centers, otherwise the skymap specifies 
        the pixel vertices. Specifying the vertices more accurately describes how the pixels
        field of view transforms from a square to a polynomial.
    """
    assert alt in [90, 110, 150], (f'The {alt} km altitude does not have a corresponding map: '
                                   'valid_altitudes=[90, 110, 150].')
    skymap = {}
    lon_bounds = [meta['lon']-10*(alt/110), meta['lon']+10*(alt/110)]
    lat_bounds = [meta['lat']-10*(alt/110), meta['lat']+10*(alt/110)]

    if pixel_center:
        pad = 0
    else:
        pad = 1

    # TODO: Add 1 to test map edges too.
    _lons, _lats = np.meshgrid(
        np.linspace(*lon_bounds, num=meta['resolution'][0]+pad),
        np.linspace(*lat_bounds, num=meta['resolution'][1]+pad)
        )
    std = 5*(alt/110)
    dst = np.sqrt((_lons-meta['lon'])**2 + (_lats-meta['lat'])**2)
    # the 105 multiplier could be 90, but I chose 105 (and -15 offset) to make the 
    # skymap realistic: the edges are NaNs.
    elevations =  105*np.exp(-dst**2 / (2.0 * std**2))-15
    elevations[elevations < 0] = np.nan
    # These are the required skymap keys for asilib.Imager to work.
    skymap['el'] = elevations
    skymap['alt'] = alt
    skymap['lon'] = _lons
    skymap['lon'][~np.isfinite(skymap['el'])] = np.nan
    skymap['lat'] = _lats
    skymap['lat'][~np.isfinite(skymap['el'])] = np.nan
    skymap['path'] = __file__ 

    # Calculate the azimuthal angle using cross product between a northward-pointing unit vector 
    # and the (_lons, _lats) grid. See https://stackoverflow.com/a/16544330 for an explanation.
    dot_product = 0*(_lons-meta['lon']) + 1*(_lats-meta['lat'])
    determinant = 0*(_lats-meta['lat']) - 1*(_lons-meta['lon'])
    skymap['az'] = (180/np.pi)*np.arctan2(determinant, dot_product)
    # transform so it goes 0->360 in a clockwise direction.
    skymap['az'] = -1*skymap['az']
    skymap['az'][skymap['az'] < 0] = 360 + skymap['az'][skymap['az'] < 0]
    return skymap


def get_data(meta: dict, time: utils._time_type=None, time_range: utils._time_range_type=None) -> dict:
    """
    Get some images and time stamps. One image and time stamp if time is specified,
    or multiple images if time_range is specified.

    Parameters
    ----------
    meta: dict
        The ASI metadata with the imager resolution and cadence.
    time: str or datetime.datetime
        A time to look for the ASI data at. Either the time or the time_range
        must be specified.
    time_range: list of str or datetime.datetime
        A length 2 list of string-formatted times or datetimes to bracket
        the ASI data time interval.
    """
    if (time is not None) and (time_range is not None):
        raise ValueError("time and time_range can't be simultaneously specified.")
    if (time is None) and (time_range is None):
        raise ValueError("Either time or time_range must be specified.")
    
    if time is not None:
        time = utils.validate_time(time)
        file_path = _get_file_path(meta, time)
        image_times, images = _data_loader(file_path)

        # find the nearest image to the requested time.
        dt = np.array([(image_time-time).total_seconds() for image_time in image_times])
        dt = np.abs(dt)
        min_idt = np.argmin(dt)
        assert abs((image_times[min_idt] - time).total_seconds()) < 10, ('Requested image is'
            ' more than 10 seconds away from the nearest image time.')
        return {'time':image_times[min_idt], 'image':images[min_idt, ...]}
        
    else:
        time_range = utils.validate_time_range(time_range)
        start_file_time = time_range[0].replace(minute=0, second=0, microsecond=0)
        hours = (time_range[1]-time_range[0]).hour + 1  # +1 to load the final hour.
        
        # These are all of the keys required by asilib.Imager.
        _data = {
            'time_range':time_range,
            'path': [_get_file_path(start_file_time+timedelta(hours=i)) for i in range(hours)],
            'start_time':[start_file_time+timedelta(hours=i) for i in range(hours)],
            'end_time':[start_file_time+timedelta(hours=1+i) for i in range(hours)],
            'loader':_data_loader
        }
    return _data

def _data_loader(file_path):
    """
    Given a file_path, open the file and return the time stamps and images.

    Time stamps are every 10 seconds. The images are all 0s except a horizontal and a vertical 
    line whose position is determined by seconds_since_start modulo resolution (516).
    """
    # Assume that the image time stamps are at exact seconds
    file_time = datetime.strptime(file_path.split('_')[:2], '%Y%m%d_%H')
    location = file_path.split('_')[2]

    times = np.array([file_time + timedelta(seconds=i*10) for i in np.arange(3600//10)])  # 10 s cadence
    
    images = np.zeros((times.shape[0], 516, 516))
    for i, time in enumerate(times):
        sec = (time-file_time).total_seconds()
        images[i, sec % 516, :] = 255
        images[i, :, sec % 516] = 100
    return times, images

def _get_file_path(meta, time):
    return f'{time:%Y%m%d_%H}0000_{meta["location"]}_test_asi.file'  # does not exist.

def plot_skymap(location_code, alt=110, pixel_center=True):
    """
    Visualize the skymap to get a better idea on what a realistic one looks like 
    (if perfectly aligned).
    """
    location_code = location_code.upper()
    locations = asi_info()
    _location = locations.loc[locations.index == location_code, :]
    meta = get_meta(_location)

    skymap = get_skymap(meta, alt=alt, pixel_center=pixel_center)
    keys = ['el', 'az', 'lat', 'lon']
    fig, ax = plt.subplots(1, len(keys), sharex=True, sharey=True, figsize=(3.7*len(keys), 4))

    for ax_i, key in zip(ax, keys):
        p = ax_i.pcolormesh(skymap[key])
        plt.colorbar(p, ax=ax_i)
        ax_i.set_title(key)
    plt.suptitle('asilib | test ASI skymap')
    plt.tight_layout()
    return

if __name__ == '__main__':
    plot_skymap('GILL', pixel_center=False)
    plt.show()