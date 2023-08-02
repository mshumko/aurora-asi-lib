from datetime import datetime, timedelta
import dateutil.parser

import pytest

import asilib.utils as utils

str_time = '2010-01-01T10:29:32.000000'
obj_time = datetime(2010, 1, 1, 10, 29, 32, 0)
valid_times = [(str_time, obj_time), (obj_time, obj_time)]


@pytest.mark.parametrize("test_input,expected", valid_times)
def test_validate_time(test_input, expected):
    assert utils.validate_time(test_input) == expected


invalid_times = [1, 1.0]


@pytest.mark.parametrize("test_input", invalid_times)
def test_invalid_validate_time(test_input):
    with pytest.raises(ValueError):
        utils.validate_time(test_input)


def test_invalid_validate_time_year():
    with pytest.raises(ValueError):
        utils.validate_time(datetime(1900, 1, 1, 10, 29, 32, 0))
    with pytest.raises(ValueError):
        future_year = datetime.now().year + 1
        utils.validate_time(datetime.now().replace(year=future_year))


valid_time_ranges = [
    ([str_time, str_time], [obj_time, obj_time]),
    ([str_time, obj_time], [obj_time, obj_time]),
    ([obj_time, obj_time], [obj_time, obj_time]),
]


@pytest.mark.parametrize("test_input,expected", valid_time_ranges)
def test_validate_time_range(test_input, expected):
    assert utils.validate_time_range(test_input) == expected


invalid_time_ranges = [[], [obj_time], [obj_time, obj_time, obj_time]]


@pytest.mark.parametrize("test_input", invalid_time_ranges)
def test_validate_time_range_invalid(test_input):
    with pytest.raises(AssertionError):
        utils.validate_time_range(test_input)


def test_get_filename_times_partial_day():
    time_range = (datetime(2010, 1, 1), datetime(2010, 1, 5, 12))
    file_times = [
        datetime(2010, 1, 1),
        datetime(2010, 1, 2),
        datetime(2010, 1, 3),
        datetime(2010, 1, 4),
        datetime(2010, 1, 5),
    ]
    dt = 'days'
    assert utils.get_filename_times(time_range, dt=dt) == file_times


def test_get_filename_times_end_day():
    time_range = (datetime(2010, 1, 1), datetime(2010, 1, 5))
    file_times = [
        datetime(2010, 1, 1),
        datetime(2010, 1, 2),
        datetime(2010, 1, 3),
        datetime(2010, 1, 4),
    ]
    dt = 'days'
    assert utils.get_filename_times(time_range, dt=dt) == file_times


def test_get_filename_times_partial_hour():
    time_range = (datetime(2010, 1, 1, 10, 29, 32, 0), datetime(2010, 1, 1, 12, 29, 32, 0))
    file_times = [
        datetime(2010, 1, 1, 10, 0, 0, 0),
        datetime(2010, 1, 1, 11, 0, 0, 0),
        datetime(2010, 1, 1, 12, 0, 0, 0),
    ]
    dt = 'hours'
    assert utils.get_filename_times(time_range, dt=dt) == file_times


def test_get_filename_times_end_hour():
    time_range = (datetime(2010, 1, 1, 10, 0, 0, 0), datetime(2010, 1, 1, 12, 0, 0, 0))
    file_times = [datetime(2010, 1, 1, 10, 0, 0, 0), datetime(2010, 1, 1, 11, 0, 0, 0)]
    dt = 'hours'
    assert utils.get_filename_times(time_range, dt=dt) == file_times


def test_get_filename_times_partial_minute():
    time_range = (datetime(2010, 1, 1, 10, 29, 32, 0), datetime(2010, 1, 1, 10, 31, 32, 0))
    file_times = [
        datetime(2010, 1, 1, 10, 29, 0, 0),
        datetime(2010, 1, 1, 10, 30, 0, 0),
        datetime(2010, 1, 1, 10, 31, 0, 0),
    ]
    dt = 'minutes'
    assert utils.get_filename_times(time_range, dt=dt) == file_times


def test_get_filename_times_end_minute():
    time_range = (datetime(2010, 1, 1, 10, 29, 32, 0), datetime(2010, 1, 1, 10, 31, 0, 0))
    file_times = [
        datetime(2010, 1, 1, 10, 29, 0, 0),
        datetime(2010, 1, 1, 10, 30, 0, 0),
    ]
    dt = 'minutes'
    assert utils.get_filename_times(time_range, dt=dt) == file_times
