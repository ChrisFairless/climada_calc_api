import cProfile
import pstats
from functools import wraps
import logging

from calc_api.config import ClimadaCalcApiConfig
conf = ClimadaCalcApiConfig()

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(conf.LOG_LEVEL)


def profile(sort_by='cumulative', lines_to_print=30, strip_dirs=True, log_level="DEBUG"):
    """A time profiler decorator.
    Inspired by and modified the profile decorator of Ehsan Khodabandeh
    https://towardsdatascience.com/how-to-profile-your-code-in-python-e70c834fad89
    In turn inspired by and modified from Giampaolo Rodola:
    http://code.activestate.com/recipes/577817-profile-decorator/
    Args:
        sort_by: str or SortKey enum or tuple/list of str/SortKey enum
            Sorting criteria for the Stats object.
            For a list of valid string and SortKey refer to:
            https://docs.python.org/3/library/profile.html#pstats.Stats.sort_stats
        lines_to_print: int or None
            Number of lines to print. Default (None) is for all the lines.
            This is useful in reducing the size of the printout, especially
            that sorting by 'cumulative', the time consuming operations
            are printed toward the top of the file.
        strip_dirs: bool
            Whether to remove the leading path info from file names.
            This is also useful in reducing the size of the printout
        log_level: str
            Profiling is only performed at this logging level or lower. Default "DEBUG"
    Returns:
        Profile of the decorated function
    """

    def inner(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if LOGGER.level <= getattr(logging, log_level):
                pr = cProfile.Profile()
                pr.enable()
                retval = func(*args, **kwargs)
                pr.disable()

                ps = pstats.Stats(pr)
                if strip_dirs:
                    ps.strip_dirs()
                if isinstance(sort_by, (tuple, list)):
                    ps.sort_stats(*sort_by)
                else:
                    ps.sort_stats(sort_by)
                ps.print_stats(lines_to_print)
            return retval

        return wrapper

    return inner