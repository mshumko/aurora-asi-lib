from datetime import datetime

import numpy as np
import matplotlib.testing.decorators

from asilib.asi.fake_asi import fake_asi


##########################################
########## TEST DATA ACCESS ##############
##########################################
def test_time():
    """
    Test if the fake_asi timestamp is correctly accessed.
    """
    asi = fake_asi('GILL', time='2015-01-01T15:14:00.17')
    assert asi.data.times == datetime(2015, 1, 1, 15, 14)
    assert asi.data.images.shape == (512, 512)
    assert np.isclose(asi.data.images.mean(), 14.4014892578125)
    # See https://numpy.org/doc/stable/reference/generated/numpy.argmax.html for the
    # unravel_index example to get the maximum index for a N-d array.
    ind = np.unravel_index(np.argmax(asi.data.images, axis=None), asi.data.images.shape)
    assert ind == (318, 0)
    return


def test_time_range():
    """
    Test if fake_asi timestamps are correctly accessed.
    """
    asi = fake_asi('GILL', time_range=('2015-01-01T15:00:15.17', '2015-01-01T20:00'))
    assert asi.data.times.shape == (1798,)
    assert asi.data.images.shape == (1798, 512, 512)
    assert np.isclose(asi.data.images.mean(), 14.048684923216552)
    assert asi._data['path'] == [
        '20150101_150000_GILL_fake_asi.images',
        '20150101_160000_GILL_fake_asi.images',
        '20150101_170000_GILL_fake_asi.images',
        '20150101_180000_GILL_fake_asi.images',
        '20150101_190000_GILL_fake_asi.images',
    ]
    return


def test_iter_files():
    """
    Test Imager.iter_files()
    """
    asi = fake_asi('GILL', time_range=('2015-01-01T15:00:15.17', '2015-01-01T19:30'))
    n_timestamps_reference = [358, 360, 360, 360, 181]

    counter = 0
    for (_times, _images), ref_n in zip(asi.iter_files(), n_timestamps_reference):
        assert _times.shape[0] == ref_n
        assert _images.shape[0] == ref_n
        counter += 1

    assert counter == len(n_timestamps_reference)
    return


##########################################
############# TEST PLOTTING ##############
##########################################
@matplotlib.testing.decorators.image_comparison(
    baseline_images=['test_fisheye'], tol=10, remove_text=True, extensions=['png']
)
def test_fisheye():
    """
    Tests that the fake_asi produces the correct image.
    """
    asi = fake_asi('GILL', time='2015-01-01T15:14:00.17')
    asi.plot_fisheye(color_bounds=(1, 255), origin=(0.85, 0.15), cardinal_directions='NEWS')
    return


@matplotlib.testing.decorators.image_comparison(
    baseline_images=['test_plot_keogram'], tol=10, remove_text=True, extensions=['png']
)
def test_plot_keogram():
    """
    Tests that the fake_asi produces the correct keogram.
    """
    asi = fake_asi('GILL', time_range=('2015-01-01T15:00:15.17', '2015-01-01T19:30'))
    asi.plot_keogram()
    return

##########################################
############# TEST EXAMPLES ##############
##########################################

@matplotlib.testing.decorators.image_comparison(
    baseline_images=['test_plot_fisheye_example'], tol=10, remove_text=True, extensions=['png']
)
def test_plot_fisheye_example():
    """
    Test that asilib.Imager plots a bright auroral arc that was analyzed by 
    Imajo et al., 2021 "Active auroral arc powered by accelerated electrons 
    from very high altitudes"
    """
    from datetime import datetime
    import matplotlib.pyplot as plt
    import asilib
    asi = asilib.themis('RANK', time=datetime(2017, 9, 15, 2, 34, 0))
    ax, im = asi.plot_fisheye(cardinal_directions='NE', origin=(0.95, 0.05))
    plt.colorbar(im)
    ax.axis('off')

@matplotlib.testing.decorators.image_comparison(
    baseline_images=['test_plot_map_example'], tol=10, remove_text=True, extensions=['png']
)
def test_plot_map_example():
    """
    Test a mapped image of STEVE.
    """
    from datetime import datetime
    import numpy as np
    import matplotlib.pyplot as plt
    import asilib
    asi = asilib.themis('ATHA', time=datetime(2010, 4, 5, 6, 7, 0))
    asi.plot_map(lon_bounds=(-127, -100), lat_bounds=(45, 65))
    plt.tight_layout()
    return


def test_animate_fisheye_example():
    """
    Test that asilib.Imager.animate_fisheye() method works. Since I have not 
    found a way to compare animations, lets assume that the plot_fisheye() 
    tests in the underlying plotting methods pass, and we just need
    to check that the movie exists with the correct number of underlying plots.
    """
    from datetime import datetime
    import asilib
    time_range = (datetime(2015, 3, 26, 6, 7), datetime(2015, 3, 26, 6, 12))
    asi = asilib.themis('FSMI', time_range=time_range)
    asi.animate_fisheye(cardinal_directions='NE', origin=(0.95, 0.05), overwrite=True)
    print(f'Animation saved in {asilib.config["ASI_DATA_DIR"] / "animations" / asi.animation_name}')

    # End of example. 
    animation_path = asilib.config["ASI_DATA_DIR"] / "animations" / asi.animation_name
    image_parent_dir_chunks = asi.animation_name.split('_')
    image_parent_dir = '_'.join(image_parent_dir_chunks[0:2]) + '_'
    image_parent_dir = image_parent_dir + '_'.join(image_parent_dir_chunks[3:])
    image_parent_dir = image_parent_dir.split('.')[0]
    plot_dir = asilib.config["ASI_DATA_DIR"] / "animations" / 'images' / image_parent_dir
    image_paths = list(plot_dir.glob('*.png'))

    assert animation_path.exists()
    assert plot_dir.exists()
    assert len(image_paths) == 100
    return

def test_animate_map_example():
    """
    Test that asilib.Imager.animate_map() method works. Since I have not 
    found a way to compare animations, lets assume that the plot_map() 
    tests in the underlying plotting methods pass, and we just need
    to check that the movie exists with the correct number of underlying plots.
    """
    from datetime import datetime
    import matplotlib.pyplot as plt
    import asilib
    location = 'FSMI'
    time_range = (datetime(2015, 3, 26, 6, 7), datetime(2015, 3, 26, 6, 12))
    asi = asilib.themis(location, time_range=time_range)
    asi.animate_map(overwrite=True)
    print(f'Animation saved in {asilib.config["ASI_DATA_DIR"] / "animations" / asi.animation_name}')

    # End of example.
    animation_path = asilib.config["ASI_DATA_DIR"] / "animations" / asi.animation_name
    image_parent_dir_chunks = asi.animation_name.split('_')
    image_parent_dir = '_'.join(image_parent_dir_chunks[0:2]) + '_'
    image_parent_dir = image_parent_dir + '_'.join(image_parent_dir_chunks[3:])
    image_parent_dir = image_parent_dir.split('.')[0]
    plot_dir = asilib.config["ASI_DATA_DIR"] / "animations" / 'images' / image_parent_dir
    image_paths = list(plot_dir.glob('*.png'))

    assert animation_path.exists()
    assert plot_dir.exists()
    assert len(image_paths) == 100
    return

@matplotlib.testing.decorators.image_comparison(
    baseline_images=['test_plot_keogram_geographic_example'], tol=10, remove_text=True, extensions=['png']
)
def test_plot_keogram_geographic_example():
    """
    Tests that the keogram is correctly plotted with geographic lats
    Event from https://doi.org/10.1029/2021GL094696
    """
    import matplotlib.pyplot as plt
    import asilib
    
    time_range=['2008-01-16T10', '2008-01-16T12']
    
    asi = asilib.themis('GILL', time_range=time_range)
    ax, p = asi.plot_keogram(color_map='turbo')
    
    ax.set_ylabel('Geographic Lat [deg]')
    plt.colorbar(p)
    return

@matplotlib.testing.decorators.image_comparison(
    baseline_images=['test_plot_keogram_magnetic_example'], tol=10, remove_text=True, extensions=['png']
)
def test_plot_keogram_magnetic_example():
    """
    Tests that the keogram is correctly plotted with magnetic lats
    Event from https://doi.org/10.1029/2021GL094696
    """
    import matplotlib.pyplot as plt
    import asilib
    
    time_range=['2008-01-16T10', '2008-01-16T12']
    
    asi = asilib.themis('GILL', time_range=time_range)
    ax, p = asi.plot_keogram(color_map='turbo', aacgm=True, title=False)
    ax.set_ylabel('Magnetic Lat [deg]')
    plt.colorbar(p)
    return

@matplotlib.testing.decorators.image_comparison(
    baseline_images=['test_plot_keogram_magnetic_path_example'], tol=10, remove_text=True, extensions=['png']
)
def test_plot_keogram_magnetic_path_example():
    """
    Tests that the keogram is correctly plotted with magnetic lats
    Event from https://doi.org/10.1029/2021GL094696
    """
    import matplotlib.pyplot as plt
    import asilib
    
    time_range=['2008-01-16T10', '2008-01-16T12']
    
    asi = asilib.themis('GILL', time_range=time_range)

    latlon = np.column_stack(
        (
            asi.skymap['lat'][:, asi.meta['resolution'][0] // 3],
            asi.skymap['lon'][:, asi.meta['resolution'][0] // 3],
        )
    )
    latlon = latlon[np.where(~np.isnan(latlon[:, 0]))[0], :]
    ax, p = asi.plot_keogram(color_map='turbo', aacgm=True, title=False, 
        path=latlon)
    ax.set_ylabel('Magnetic Lat [deg]\nCustom path')
    plt.colorbar(p)
    return

def test_getitem():
    """
    Tests the __getitem__() for time slicing.
    """
    raise NotImplementedError
    return

def test_str():
    """
    Tests the __str__() for printing user-readable information about the imager
    """
    raise NotImplementedError
    return

def test_repr():
    """
    Tests the __repr__() for printing machine-readable information about the imager
    """
    raise NotImplementedError
    return