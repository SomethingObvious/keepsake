import numpy as np
from numpy.typing import NDArray

class DCTJPEG:
    Y: NDArray[np.int16]
    Cb: NDArray[np.int16] | None
    Cr: NDArray[np.int16] | None
    qt: NDArray[np.uint16]
    quant_tbl_no: NDArray[np.int8]
    samp_factor: NDArray[np.int32]
    def write_dct(self, path: str) -> None: ...

class SpatialJPEG:
    samp_factor: NDArray[np.int32]
    def write_spatial(
        self,
        path: str,
        qt: NDArray[np.uint16] | None = ...,
        quant_tbl_no: NDArray[np.int8] | None = ...,
    ) -> None: ...

def read_dct(path: str) -> DCTJPEG: ...
def from_spatial(spatial: NDArray[np.uint8]) -> SpatialJPEG: ...
