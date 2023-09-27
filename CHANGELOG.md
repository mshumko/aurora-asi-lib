# Changelog

## [unreleased]

### Added
- An advertisement figure and script. The script in `examples/global_coverage_map.py` plots a geographic map showing the spatial coverage (low-elevation field of view rings) of all imagers supported by aurora-asi-lib. The resulting plot is located in `docs/_static/global_coverage.png` and is shown in the `README.md` and `index.rst` files. 
- An `overlap` kwarg for Imagers.get_points().

## [0.20.1]

### Fixed
- A bug in `Imager._calc_cardinal_direction()` method that manifested in non-orthogonal directions when the ASI (az, el) skymaps are offset such that the low elevations are outside of the field of view. 
- A bug in the REGO example.

### Changed
- Shortened the namespace paths in the Imager API Reference page. Their namespace is the same as it would be imported.

## [0.20.0] - 2023-08-20

### Added
- RGB auroral intensities in `asilib.Conjunction.intensity()`.
- An auroral intensity test (from the nearest pixel and equal area) using the TREx-RGB data.
- `asilib.skymap.geodetic.skymap()` function that maps the (az, el) skymaps to (lat, lon) skymaps assuming Earth is a sphere (i.e., not an ellipsoid).
- Added a plot test comparing the official and the asilib THEMIS GILL (lat, lon) skymaps.

### Changed
- The `asilib.Conjunction()` class had am ambiguity regarding whether if the satellite ephemeris was interpolated (or downsampled to) the ASI time stamps, or kept at the original cadence. This ambiguity made calculating auroral intensity error-prone, so now `asilib.Conjunction.intensity()` automatically interpolates the satellite ephemeris.

### Fixed
- A bug in the asilib.Imager.data property that relied on hard-coded filtering of unfilled images using `np.where()`. This led to duplicate time stamps for RGB images, and a crash with `asilib.Conjunction.intensity()`.
- Removed the THEMIS and REGO imports at the top-level of asilib, i.e., in `asilib/__init__.py`. Now they are imported in `asilib/asi/__init__.py`, so users must always import asilib.asi when using ASI modules contained within the `asi/` folder.

## [0.19.0] - 2023-08-05

### Added
- The TREx-RGB loader, `asilib.asi.trex_rgb()`, courtesy of C. McKenna.
- `asilib.asi.trex_rgb()` tests
- `Conjunction.lla_footprint` tests
- `asilib.asi.trex_rgb()` to the online documentation.

## Fixed
- A bug in `Imager.keogram()` that calculated the incorrect pixels that is used for slicing images when assembling a keogram. While this bug does not affect ASIs with square pixel resolution, it did for TREx-RGB which is rectangular. The fix slightly modified the keograms, by about a pixel, so I regenerated the baseline keogram plots.
- A bug in `Conjunction.lla_footprint` where the `alt` variable was rewritten. As a result, IRBEM did not map to the requested altitude.

## [0.18.1] - 2023-07-23

### Added
- `asilib.Imagers.get_points()` method to get the (lon, lat) and pixel intensity points.
- Tests for `asilib.Imagers.get_points()`

## [0.18.0] - 2023-07-22

### Added
- `asilib.Imagers()` class to make mosaics and synchronize plotting multiple imagers. The first two methods implemented are:
  - `asilib.Imagers.plot_fisheye()` to plot fisheye lens images from multiple imagers, and
  - `asilib.Imagers.plot_map()` to project images from multiple imagers onto a map. This method has an `overlap` kwarg that by default masks out the (lat, lon) skymaps that map to pixels that overlap with a neighboring imager. This is a surprisingly efficient method that needs to be run just once (tested for up to five imagers; I'm unsure how a 10 or a 20 imager array will fare).
- Added plot tests for the two `Imagers` methods.
- Added an `Imagers()` description in the Get Started and API pages.
### Changed
- Refactored the Donovan+2008 auroral arc example to use `asilib.Imagers.plot_map()`.
- Added a check to allow custom `matplotlib.colors.Normalization` object to be passed for `color_norm`.

## [0.17.3] - 2023-07-02

### Added
- Support for RGB images in `asilib.Imager.keogram()`.

### Changed
- Simplified `asilib.Imager.__getitem__()` to repay the technical debt. Before the method was difficult to reason about and it processed the [time] and [start_time:end_time] slice cases separately. Now `__getitem__` handles both of those cases in the same way.
- Simplified how the `Imager._keogram` array is allocated when `asilib.Imager.keogram()` is called.
- Edited the Imager flowchart.

## [0.17.2] - 2023-06-28 
### Added
- Deprecation warnings to the legacy asilib plotting functions and in the API reference. They will be removed in or after December 2023.

## [0.17.1] - 2023-06-28
### Changed
- Fixed the `color_norm` keyword argument in `asilib.Imager()` methods. Now it defaults to `None` so the normalization is correctly overridden. Also, the `color_norm` docstring is updated to clarify the hierarchy.
- Changed the `data` to `file_info` argument in `asilib.Imager()`, and all ASI loaders, to more clearly convey the purpose of the variable.

## [0.17.0] - 2023-06-24

### Added
- A tutorial using `asilib.Imager()`.
- Documentation in contribute.rst describing the `asilib.Imager()` interface. Simplified the `asilib.Imager().__init__()` docstring and point to the thorough interface description in the new Contribute section.

### Changed
- Refactored how `asilib.Imager()` deals with single- and multi-image instances. Now, each ASI `wrapper` function does not need to load a single image if `time` is specified, `asilib.Imager()` does this instead.
- Refactored the `themis`, `rego`, `trex_nir`, `lamp_phantom`, and `psa_emccd` wrapper functions with the new `asilib.Imager()` interface.
- Due to this change, the `asilib.Imager.__getitem__()` method significantly simplified.

## [0.16.2] - 2023-06-10

### Added
- Refactored all examples from `examples/v0/` and saved them in `examples/v1/`.
- Added the v1 examples to the Examples documentation tab. During the v0->v1 transition, users can see the examples in both the v0 and v1 interfaces.
- Removed experimental warning from Imager API Reference and moved it to the Legacy API Reference. 

## [0.16.1] - 2023-05-31

### Fixed
- The example in `examples/v1/animate_conjunction.py`.

### Changed
- Bumped the Calgary dependencies to avoid the freeze support multiprocessing bug for windows users
  - rego-imager-readfile>=1.2.0
  - themis-imager-readfile>=1.2.1
  - trex-imager-readfile>=1.4.0

## [0.16.0] - 2023-05-24

### Added
- TREx-NIR loader
- TREx-NIR API documentation with examples
- TREx-NIR tests 

### Fixed
- A bug in `asilib.Imager.keogram()`. If the data was already loaded (via the `.data` method), any subsequent calls to `asilib.Imager.keogram()` or `asilib.Imager.plot_keogram()` crashed.

### Changed
- ASI loader functions for `asilib.Imager()` should now be imported as:
```python
import asilib.asi

asi = asilib.asi.themis(...)
```

(old version is)
```python
import asilib

asi = asilib.themis(...)
```
## Version 0.15.0
- Finalizing the `asilib.Conjunction` API
- Added `asilib.Conjunction.intensity` method. Depending on if the `box` argument is specified or not, this method will calculate either the auoral intensity for the nearest pixel to the footprint (`box=None`) or in a rectangular area around the footprint otherwise (e.g., `box=(10x10)`).
- Added tests for `asilib.Conjunction.map_azel()`.
- Angular distances in `asilib.Conjunction.map_azel()` (and elsewhere) are now calculated using the _haversine equation.
- Moved original examples to `examples/v0/` folder and started writing the examples using `Imager()` and  `Conjunction()` to the `examples/v1/` folder.
## Version 0.14.4
- Updated GitHub Actions:
  - test the `cartopy` maps,
  - test using `ubuntu-latest`.

## Version 0.14.3
- The following `asilib.Imager` methods are now tested:
1. `plot_fisheye()`,
2. `plot_map()`,
3. `animate_fisheye()`,
4. `animate_map()`,
5. `plot_keogram()`,
6. `iter_files`,
7. `__getitem__`,
8. `__str__`, and
9. `__repr__`.

- The `asilib.themis()` and `asilib.rego()` examples are now tested as well.

- Fixed a `asilib.Imager` bug that was triggered when the time slicing is outside of the time_range. Before, it raised an unhelpful `AssertionError`, but now it raises an informative `FileNotFoundError`.

## Version 0.14.2
- Added a `asilib.asi.fake_asi` function to quickly test `asilib.Imager`. 
- Using the `fake_asi` I found and fixed a few errors in `asilib.Imager`.
- Added more tests for `asilib.asi.themis()`, `asilib.map.create_map()` and began adding tests for `asilib.Imager`.

## Version 0.14.1
- Added tests for `asilib.themis()` plotting functions
- Moved map creating examples to `asilib.map.create_map()`.
- Fixed numerous minor bugs in `asilib.Imager()`.

## Version 0.14.0
- Added `Imager.plot_map()`, `Imager.animate_map()`, `Imager.animate_map_gen()` methods and documentation that project images, or a series of images, onto a geographic map.
- Added `Imager.keogram()`, and `Imager.plot_keogram()` methods to make keograms
  - Along the meridian or a custom path
  - With geographic or magnetic latitudes, depending on the `aacgm` kwarg.
- `asilib.Imager` functionality is complete, with a first draft of the documentation & examples.

## Version 0.13.0
- Added an Active Development warning in the `asilib` docs.
- Simplified the `Downloader` class.
- Fixed a download bug. It arose because the `overwrite` kwarg played two overlapping roles: to redownload data and overwrite animations (the ffmpeg argument). I fixed the bug with the `redownload` kwarg reserved only for downloading data, and `overwrite` kwarg reserved for overwriting animations.
- Added cardinal directions to `asilib.imager.plot_fisheye()` and `asilib.imager.plot_fisheye_gen()` methods. To use it, set the `cardinal_directions` kwarg to one or more directions, e.g., 'NE' for north and east directions (default), or 'NEWS' for all directions.
- Improved the `asilib.Downloader` class. 
  - Replaced the `_check_url_status()` implementation that checked if the server is online. Turns out, if the url argument includes a path to a large file, `asilib.Downloader` will download the file just to check the server status. I replaced it with `request.raise_for_status()` that doesn't download the file.
  - Added a try-catch block for streaming large files. This addresses the bug where a file is partially-downloaded if the stream is interrupted. This goes unnoticed until `asilib` raises file-corrupted errors that are hard to track down. The fix first deletes the partially-downloaded file if the stream is interrupted, and then raises the error.
- Added functions, documentaion, and examples for `asilib.map.create_map()`, `asilib.map.create_cartopy_map()`, and `asilib.map.create_simple_map()` to use with `asilib.Imager`.

## Version 0.12.0
- First merge of the Imager class. The `asilib.Imager` and `asilib.Conjunction` classes are still under development, but you can try it out! Call the `asilib.themis()` function to play around with an Imager instance.
- Removed the deprecated functions. Once Imager is fully implemented, most of the original functions will be deprecated. 

## Version 0.11.0
- Removed the cartopy dependency. While some users were able to install it, overall it proved to be difficult to reliably build across multiple operating systems. Instead, I use the pyshp pure python library to read in the Esri shapefile files to make the map. Currently, only the mercator projection is supported. However, in the future, I plan to add other projections such as orthographic.
- Renamed asilib.create_cartopy_map() to asilib.make_map()

## Version 0.10.1
- Added a `path` kwarg to `keogram` and `plot_keogram` to create a keogram along a custom (lat, lon) path.
- Clarified the documentation.

## Version 0.10.0
- Added `animate_map` and `animate_map_generator` functions to asilib. I also added examples to the examples and tutorial sections of the docs. 
- Added a warning in `equal_area` if the lat/lon values are outside of the skymap range.

## Version 0.9.5
- Renamed and deprecated `plot_movie` and `plot_movie_generator` for `animate_fisheye` and `animate_fisheye_generator` functions. This change is necessary for consistency with new functions such as `animate_map` and `animate_map_generator` functions.
- Updated the examples.
- Combined the download functions to `download_image` and `download_skymap`.

## Version 0.9.3
- Renamed the `_make_map` function to `create_cartopy_map()` so users can use this function to create maps from now on.
- Updated the information in `CONTRIBUTE.md`.

## Version 0.9.2
- Fixed a bug where the `color_bounds` in `plot_movie_generator()` were static after the first image.
- Renamed and deprecated `plot_image` for `plot_fisheye`.

## Version 0.9.0
- Rotated the 2- and 3-D `skymap` arrays and fixed a bug in `keogram.py` where the skymap latitudes were a few pixels off.

## Version 0.8.0 
- Swapped the order of most functions to `asi_array_code, location_code, time`. This is a major API change that is not backwards-compatible. 
- Many edits the the docstrings.
- Renamed the example scripts and added example scripts for `plot_map`.
- Finished a first complete draft of tutorial.ipynb.

## Version 0.7.5
- Changed all instances of the word `station` and replaced it with `location_code`.

## Version 0.7.4
- The main change is the `ignore_missing_files` parameter that is passed to the download functions. When True, the `download_themis_img` and `download_rego_img` will not raise a missing file error when data from that hour does not exist.

## Version 0.7.3
- The biggest API change is the parameter order for `download_rego_img` and `download_themis_img`. Now it is `(location code (i.e. station), time, and time_range)`. Beware that now the parameter order API is inconsistent across all of the functions---I will standardize it to (`asi_array_code`, `location code (i.e. station)`, `time`, and `time_range`) in the next minor (0.X.0 release).

## Version 0.7.2
- For consistency, I removed most instances of the word "frame" and changed them to "image". This propagated to the following function renaming (deprecation of the old name).
- Deprecated the get_frame and get_frames functions for load_image. It is a wrapper for _load_image and _load_images functions that were once get_frame and get_frames. I added this function to standardize the load/download names. It returns either one or multiple images, depending on if the time or time_range keyword arguments are given; it will raise an error unless time or time_range is passed (not both).
- Renamed the plot_frame function to `plot_image`; plot_frame is now deprecated.

## Version 0.7.1
- Removed deprecated functions