"""
Tests the asilib's Downloader class.
"""
import pathlib
import os
import tempfile
from datetime import datetime

import pytest
import requests

import asilib
from asilib.io.download import Downloader


def test_bad_url():
    """
    Checks that Downloader() raises an error for a non-existant URL.
    """
    d = Downloader('https://data.phys.ucalgary.ca/DOES_NOT_EXIST_9876')
    with pytest.raises(requests.exceptions.HTTPError):
        d.ls()
    return


def test_ls_and_download():
    """
    Tests the list files (ls) method, .url and .name attributes,
    and the download method when navigating down the rather complex
    https://data.phys.ucalgary.ca/sort_by_project/THEMIS/asi/stream0/
    folder structure.
    """
    date = datetime(2014, 5, 5, 5, 10)
    location = 'gill'

    base_url = (
        f'https://data.phys.ucalgary.ca/sort_by_project/THEMIS/asi/stream0/'
        f'{date.year}/{date.month:02}/{date.day:02}/'
    )
    d = Downloader(base_url)

    # Check that Downloader.ls finds the unique online subdirectory
    matched_downloaders = d.ls(f'{location.lower()}_themis*')
    assert len(matched_downloaders) == 1
    assert matched_downloaders[0].url == (
        'https://data.phys.ucalgary.ca/'
        'sort_by_project/THEMIS/asi/stream0/2014/05/05/gill_themis19/'
    )

    # Navigate further down the subdirectory structure and find the file.
    d2 = Downloader(matched_downloaders[0].url + f'ut{date.hour:02}/')
    file_search_str = f'{date.strftime("%Y%m%d_%H%M")}_{location.lower()}*.pgm.gz'
    matched_downloaders2 = d2.ls(file_search_str)

    assert len(matched_downloaders2) == 1
    assert matched_downloaders2[0].url == (
        'https://data.phys.ucalgary.ca/'
        'sort_by_project/THEMIS/asi/stream0/2014/05/05/gill_themis19/ut05/'
        '20140505_0510_gill_themis19_full.pgm.gz'
    )
    assert matched_downloaders2[0].name == '20140505_0510_gill_themis19_full.pgm.gz'

    with tempfile.TemporaryDirectory() as tmp:
        download_path = matched_downloaders2[0].download(tmp, redownload=True)
        assert download_path.name == '20140505_0510_gill_themis19_full.pgm.gz'
        assert os.path.getsize(download_path) == 1957270
    return


def test_download_file_no_subdirectories():
    """
    Test Download.download() for the case where no subdirectories were provided (the filename)
    is in the base_url.
    """
    d = Downloader(
        'https://data.phys.ucalgary.ca/sort_by_project/THEMIS/asi/stream0/'
        '2014/05/05/gill_themis19/ut08/20140505_0807_gill_themis19_full.pgm.gz'
    )
    with tempfile.TemporaryDirectory() as tmp:
        download_path = d.download(tmp, redownload=True)
        assert download_path.name == '20140505_0807_gill_themis19_full.pgm.gz'
        assert os.path.getsize(download_path) == 1980541
    return
