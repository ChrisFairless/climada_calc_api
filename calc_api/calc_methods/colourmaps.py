import numpy as np
import colorcet as cc

# Default colour palettes. All are inverted.
PALETTE_HAZARD_COLORCET = "fire"
PALETTE_EXPOSURE_COLORCET = "bmy"
PALETTE_IMPACT_COLORCET = "CET_L9"

def values_to_colours(values, colourscheme, range=None, reverse=False):
    value_min = range[0] if range else np.nanmin(values)
    value_max = range[1] if range else np.nanmax(values)

    colourscale = getattr(cc, colourscheme)
    if reverse:
        colourscale = colourscale[::-1]

    n_cols = len(colourscale)
    step = (value_max - value_min)/n_cols
    intervals = np.arange(value_min, value_max, step)[0:n_cols]  # subsetting is to avoid errors from step rounding

    values_bin = np.digitize(values, intervals, right=False) - 1
    return [colourscale[i] for i in values_bin], list(intervals), colourscale
