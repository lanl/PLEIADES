import numpy as np
from skimage.measure import block_reduce


def rebin(data: np.ndarray, binning_factor: int) -> np.ndarray:
    """
    Rebin a 2D array by averaging over blocks of size binning_factor x binning_factor."""

    block_size = (1, binning_factor, binning_factor)

    rebinned_data = block_reduce(data,
                                 block_size=block_size,
                                 func=np.mean,
                                 func_kwargs={'dtype': np.float16})

    return rebinned_data
