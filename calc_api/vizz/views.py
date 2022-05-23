from pathlib import Path
from django.http import FileResponse

from climada_calc.settings import STATIC_ROOT


def get_result_image(request, filename):
    """
    Get sample image result from file system
    """
    filepath = Path(STATIC_ROOT, "results", filename)
    return FileResponse(open(filepath, 'rb'))
