"""
Tests for the asilib.Imagers class.
"""
import matplotlib.testing.decorators
import numpy as np


@matplotlib.testing.decorators.image_comparison(
    baseline_images=['test_donovan_arc_example'],
    tol=10,
    remove_text=True,
    extensions=['png'],
)
def test_donovan_arc_example():
    from datetime import datetime
    import matplotlib.pyplot as plt
    import asilib
    import asilib.map
    import asilib.asi
    time = datetime(2007, 3, 13, 5, 8, 45)
    location_codes = ['FSIM', 'ATHA', 'TPAS', 'SNKQ']
    map_alt = 110
    min_elevation = 2
    ax = asilib.map.create_simple_map(lon_bounds=(-140, -60), lat_bounds=(40, 82))
    _imagers = []
    for location_code in location_codes:
        _imagers.append(asilib.asi.themis(location_code, time=time, alt=map_alt))
    asis = asilib.Imagers(_imagers)
    asis.plot_map(ax=ax, overlap=False, min_elevation=min_elevation)
    ax.set_title('Donovan et al. 2008 | First breakup of an auroral arc')
    return


@matplotlib.testing.decorators.image_comparison(
    baseline_images=['test_plot_fisheye'],
    tol=10,
    remove_text=True,
    extensions=['png'],
)
def test_plot_fisheye():
    from datetime import datetime

    import matplotlib.pyplot as plt
    import asilib
    import asilib.asi

    time = datetime(2007, 3, 13, 5, 8, 45)
    location_codes = ['FSIM', 'ATHA', 'TPAS', 'SNKQ']

    fig, ax = plt.subplots(1, len(location_codes), figsize=(12, 3.5))

    _imagers = []

    for location_code in location_codes:
        _imagers.append(asilib.asi.themis(location_code, time=time))

    for ax_i in ax:
        ax_i.axis('off')

    asis = asilib.Imagers(_imagers)
    asis.plot_fisheye(ax=ax)

    plt.suptitle('Donovan et al. 2008 | First breakup of an auroral arc')
    plt.tight_layout()
    return


def test_get_points():
    from datetime import datetime
    
    import asilib
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
    assert lat_lon_points.shape == (174411, 2)
    assert intensities.shape == (174411,)
    np.testing.assert_almost_equal(
        lat_lon_points[:10, :],
        np.array([
            [54.36151505, -126.16152954],
            [54.36903,    -126.27648926],
            [54.37219238, -126.39419556],
            [54.37098694, -126.51489258],
            [54.36539459, -126.63867188],
            [54.35538483, -126.76580811],
            [54.34091568, -126.89642334],
            [54.32193756, -127.0307312 ],
            [54.29838562, -127.16894531],
            [54.27019119, -127.31124878]])
       )
    np.testing.assert_almost_equal(
        lat_lon_points[-10:, :],
        np.array([
            [ 64.15480804, -82.1703186 ],
            [ 64.12185669, -82.30700684],
            [ 64.09317017, -82.44506836],
            [ 64.06869507, -82.58477783],
            [ 64.04837036, -82.72647095],
            [ 64.03216553, -82.87042236],
            [ 64.02003479, -83.01693726],
            [ 64.01195526, -83.16635132],
            [ 64.00791168, -83.31893921],
            [ 64.00789642, -83.47509766]
            ])
       )
    np.testing.assert_equal(
        intensities[:10],
        np.array([2930., 2949., 2954., 2881., 2865., 2823., 2752., 2738., 2738., 2746.])
    )
    return

def test_iterate_imagers():
    """
    Test the imagers (time, image) iterations are in sync, and if not, that the image is 
    correctly masked. 
    """
    import asilib
    import asilib.asi

    time_range = ('2023-02-24T05:10', '2023-02-24T05:15')
    time_tol = 1
    # Load all TREx imagers.
    trex_metadata = asilib.asi.trex_rgb_info()
    asis = asilib.Imagers(
        [asilib.asi.trex_rgb(location_code, time_range=time_range) 
        for location_code in trex_metadata['location_code']]
        )

    _guide_times = []
    _times = []
    _images = [] 
    for _guide_time, _asi_times, _asi_images in asis:
        _guide_times.append(_guide_time)
        _times.append(_asi_times)
        _images.append(_asi_images)

    dt = np.full(np.array(_times).shape, np.nan)
    for i, (_guide_time, imager_times_i) in enumerate(zip(_guide_times, _times)):
        dt[i, :] = [(_guide_time-j).total_seconds() for j in imager_times_i]
    
    dt[np.abs(dt) > 3600*24] = np.nan

    assert np.nanmax(np.abs(dt)) == 3.297666
    assert np.all(~np.isnan(dt[:-1, :]))
    assert np.all(np.isnan(dt[-1, :]) == np.array([False, False, False,  True, False, False]))
    return