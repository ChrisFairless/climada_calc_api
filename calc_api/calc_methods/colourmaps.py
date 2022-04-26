import numpy as np
import colorcet as cc
from millify import millify

# Default color palettes. All are inverted.
PALETTE_HAZARD_COLORCET = "fire"
PALETTE_EXPOSURE_COLORCET = "bmy"
PALETTE_IMPACT_COLORCET = "CET_L9"

class Legend:

    def __init__(self, values, colorscheme, n_cols=None, range=None, reverse=False):
        value_min = range[0] if range else np.nanmin(values)
        value_max = range[1] if range else np.nanmax(values)

        colorscale = getattr(cc, colorscheme)
        if reverse:
            colorscale = colorscale[::-1]

        colorscale_len = len(colorscale)
        if n_cols:
            if n_cols < 3:
                raise ValueError('Need at least three color bands to make a legend')
            # bandmapping_source = np.arange(colorscale_len)
            # bandmapping_interval_boundaries = self._get_interval_boundaries(0, colorscale_len, n_cols)
            # bandmapping_bin = np.digitize(bandmapping_source, bandmapping_interval_boundaries, right=False) - 1
            bandmapping_color_index = self._get_interval_boundaries(0, colorscale_len-1, n_cols-1)
            colorscale = [colorscale[int(i)] for i in bandmapping_color_index]
            # bandmapping = bandmapping_color_interval_boundaries[bandmapping_bin]
        else:
            n_cols = len(colorscale)
            # bandmapping = np.arange(colorscale_len)

        intervals = self._get_interval_boundaries(value_min, value_max * 1.01, n_cols)
        values_bin = np.digitize(values, intervals, right=False) - 1

        self.values = values
        self.colors = [colorscale[i] for i in values_bin]
        self.intervals = list(intervals)
        self.colorscale = colorscale

    def prettify_intervals(self, precision=1):
        return [
            (millify(lo, precision), millify(hi, precision))
            for lo, hi in zip(self.intervals[:-1], self.intervals[1:])
        ]

    @staticmethod
    def _get_interval_boundaries(value_min, value_max, n):
        step = (value_max - value_min) / n
        return np.arange(value_min, value_max + step/10, step)[0:n+1]  # extra step/10 is to avoid errors from rounding

