from pathlib import Path
from django.http import FileResponse

from climada_calc.settings import MEDIA_ROOT


def get_result_image(request, filename):
    """
    Get sample image result from file system
    """
    filepath = Path(MEDIA_ROOT, "sample_data", filename)
    return FileResponse(open(filepath, 'rb'))
