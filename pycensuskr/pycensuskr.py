import pandas as pd
import geopandas as gpd
import os
"""
Example module for pycensuskr package.

This module defines all functionalities in tidycensuskr.
"""

class CensusKR:
    """
    A placeholder class for tidycensuskr functionalities.

    This class can be extended to handle Korean census data tidying.
    """

    def __init__(self):
        """
        Initialize CensusKR.
        """
        self.gdf = None
        self.df = None
        self.crosswalk = None

    def load_data(year: int):
        """
        Get the dataframe data.

        Returns:
            str: A message indicating boundary retrieval
        """
        file_name = os.path.join("data", f"census_{year}.csv")
        df = pd.read_csv(file_name)
        return df
    
    def load_districts(year: int):
        """
        Load district data.

        Returns:
            str: A message indicating boundary data loading
        """
        name_lyr = f"adm2_{year}"
        path_bound = os.path.join("data", "boundaries.gpkg")
        districts = gpd.read_file(path_bound, layer = name_lyr)
        return districts
        

    def create_crosswalk(year1: int, year2: int):
        """
        create the crosswalk data.

        Parameters:
            year1 (int): The first year for crosswalk
            year2 (int): The second year for crosswalk

        Returns:
            gpd.GeoDataFrame: A message indicating crosswalk retrieval
        """
        # fails if neither year1 nor year2 is populated
        if not year1 and not year2:
            raise ValueError("At least one of year1 or year2 must be provided.")
        districts1 = load_districts(year1)
        districts2 = load_districts(year2)
        UserWarning("This function runs a heavy intersection operation. It may take a while.")
        districts12 = districts1.intersect(districts2)
        return districts12


    def unify_boundaries():
        """
        Unify the census boundaries.

        Returns:
            str: A message indicating unification
        """
        return "Census data unified."
    



class CensusData:
    """
    A placeholder class for census data operations.

    This class can be extended to handle Korean census data processing.
    """

    def __init__(self, data=None):
        """
        Initialize CensusData.

        Args:
            data: Optional data to initialize with
        """
        self.data = data or {}

    def get_data(self):
        """
        Get the current data.

        Returns:
            dict: The stored data
        """
        return self.data

    def set_data(self, data):
        """
        Set new data.

        Args:
            data: The data to store
        """
        self.data = data
