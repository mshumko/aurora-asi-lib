"""
The Imagers class combines multiple Imager objects to coordinate plotting and animating multiple
fisheye lens images, as well as mapped images (also called mosaics).   
"""

from typing import Tuple
from datetime import datetime

import numpy as np
import matplotlib.pyplot as plt

from asilib.imager import Imager, _haversine


class Imagers:
    def __init__(self, imagers:Tuple[Imager]) -> None:
        self.imagers = imagers
        return
    
    def plot_fisheye(self, ax):
        raise NotImplementedError
    
    def plot_map(self, ax=None, min_elevation=10, overlap=False):
        if overlap:
            self._calc_overlap_mask()

        for imager in self.imagers:
            imager.plot_map(ax=ax, min_elevation=min_elevation)
        return
    
    def animate_fisheye(self):
        raise NotImplementedError
    
    def animate_fisheye_gen(self):
        raise NotImplementedError
    
    def animate_map(self):
        
        raise NotImplementedError
    
    def animate_map_gen(self, overlap=False):
        if overlap:
            self._calc_overlap_mask()
        raise NotImplementedError
    
    def _calc_overlap_mask(self):
        """
        Calculate which pixels to plot for overlapping imagers by the criteria that the ith 
        imager's pixel must be closest to that imager (and not a neighboring one).

        Algorithm:
        1. Loop over ith imager
        2. Loop over jth imager within 500 km distance of the ith imager
        3. Mask low-elevations with np.nan
        4. Create a distance array with shape (resolution[0], resolution[1], j_total)
        5. For all pixels in ith imager, calculate the haversine distance to jth imager and 
        assign it to distance[..., j].
        6. For all pixels calculate the nearest imager out of all j's.
        7. If the minimum j is not the ith imager, mask the imager.skymap['lat'] and 
        imager.skymap['lon'] as np.nan.
        """
        if hasattr(self, '_overlap_masks'):
            return self._overlap_masks
        
        self._overlap_masks = {}
        for imager in self.imagers:
            self._overlap_masks[imager.meta['location']] = np.ones_like(imager.skymap['lat'])

        for i, imager in enumerate(self.imagers):
            _distances = np.nan*np.ones((*imager.skymap['lat'].shape, len(self.imagers)))
            for j, other_imager in enumerate(self.imagers):
                _distances[:, :, j] = _haversine(
                    imager.skymap['lat'], imager.skymap['lon'],
                    np.broadcast_to(other_imager.meta['lat'], imager.skymap['lat'].shape), 
                    np.broadcast_to(other_imager.meta['lon'], imager.skymap['lat'].shape)
                    )
            # Need a masked array so that np.nanargmin correctly handles all NaN slices.
            _distances = np.ma.masked_array(_distances, np.isnan(_distances))
            min_distances = np.argmin(_distances, axis=2)
            far_pixels = np.where(min_distances != i)
            imager.skymap['lat'][far_pixels] = np.nan
            imager.skymap['lon'][far_pixels] = np.nan
        return
    
    
if __name__ == '__main__':
    import asilib.map
    import asilib.asi

    time = datetime(2007, 3, 13, 5, 8, 45)
    location_codes = ['FSIM', 'ATHA', 'TPAS', 'SNKQ']
    map_alt = 110
    min_elevation = 2

    ax = asilib.map.create_map(lon_bounds=(-140, -60), lat_bounds=(40, 82))

    _imagers = []

    for location_code in location_codes:
        _imagers.append(asilib.asi.themis(location_code, time=time, alt=map_alt))

    asis = Imagers(_imagers)
    asis.plot_map(ax=ax, overlap=True, min_elevation=min_elevation)

    ax.set_title('Donovan et al. 2008 | First breakup of an auroral arc')
    plt.show()