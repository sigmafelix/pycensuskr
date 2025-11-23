"""
pycensuskr - A Python package for Korean census data processing
"""

__version__ = "0.2.5"
__author__ = "Insang Song"
__email__ = "geoissong@snu.ac.kr"

# Import main functionality here as the package grows
from .pycensuskr import CensusKR
__all__ = ["__version__", "CensusKR"]