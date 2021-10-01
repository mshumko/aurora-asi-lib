# Version 0.7.3
- The biggest API change is the parameter order for `download_rego_img` and `download_themis_img`. Now it is `(location code (i.e. station), time, and time_range)`. Beware that now the parameter order API is inconsistent across all of the functions---I will standardize it to (`asi_array_code`, `location code (i.e. station)`, `time`, and `time_range`) in the next minor (0.X.0 release).

# Version 0.7.2
- For consistency, I removed most instances of the word "frame" and changed them to "image". This propagated to the following function renaming (deprecation of the old name).
- Deprecated the get_frame and get_frames functions for load_image. It is a wrapper for _load_image and _load_images functions that were once get_frame and get_frames. I added this function to standardize the load/download names. It returns either one or multiple images, depending on if the time or time_range keyword arguments are given; it will raise an error unless time or time_range is passed (not both).
- Renamed the plot_frame function to plot_image; plot_frame is now deprecated.

# Version 0.7.1
- Removed deprecated functions