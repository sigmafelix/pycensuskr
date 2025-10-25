"""
pycensuskr - A Python package for Korean census data processing
"""

__version__ = "0.1.0"
__author__ = "Insang Song"
__email__ = "geoissong@snu.ac.kr"

# Import main functionality here as the package grows
# For now, just expose the version
from .pycensuskr import CensusKR
__all__ = ["__version__"]
