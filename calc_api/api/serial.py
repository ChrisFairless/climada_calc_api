import base64
import io
from scipy import sparse
from numpy import ndarray, frombuffer


def serialize_ndarray(arr: ndarray) -> dict:
    return {
        "bytes": base64.b64encode(arr).decode('ascii'),
        "dtype": arr.dtype.name
    }


def deserialize_ndarray(data: dict) -> ndarray:
    return frombuffer(base64.b64decode(data['bytes']), data['dtype'])


def serialize_csr_matrix(csr: sparse.csr_matrix) -> str:
    with io.BytesIO() as bio:
        sparse.save_npz(bio, csr)
        return base64.b64encode(bio.getvalue()).decode('ascii')


def deserialize_csr_matrix(data: str) -> sparse.csr_matrix:
    byt = base64.b64decode(data)
    with io.BytesIO(byt) as bio:
        return sparse.load_npz(bio)
