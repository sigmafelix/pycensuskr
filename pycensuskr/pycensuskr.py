import pandas as pd
import geopandas as gpd
import os
import re
import numpy as np
"""
Main module of pycensuskr.

This module defines a core class in tidycensuskr.
"""

class CensusKR:
    """
    A class for Korean census data retrieval and boundary management.

    This class provides methods to query Korean census data by administrative codes
    (province or municipality) and year, and to manage district boundaries. It is
    the Python equivalent of the tidycensuskr R package functionality.

    The class works with bundled census data which is limited to certain quintennial
    years (2010, 2015, and 2020). The bundled data includes 54K+ rows and 10 columns
    covering various census types including population, housing, tax, mortality,
    economy, medicine, migration, and environment data.

    Attributes:
        gdf (gpd.GeoDataFrame): GeoDataFrame for spatial data.
        df (pd.DataFrame): DataFrame for tabular data.
        crosswalk (gpd.GeoDataFrame): Crosswalk boundaries between different years.

    Methods:
        load_data(year): Load census data for a specific year.
        load_districts(year): Load district boundaries for a specific year.
        convert_basic_adm2(gdf): Convert level 2 boundaries to basic local government boundaries.
        anycensus(year, codes, type, level, aggregator, **agg_kwargs): Query census data
            by admin code and year.
        create_crosswalkboundary(year1, year2): Create crosswalk boundaries between
            two years.
        unify_boundaries(year_standard): Unify census boundaries to a standard year.

    Notes:
        - Administrative levels: "adm1" (province-level), "adm2" (municipal-level)
        - Available data types: "population", "housing", "tax", "mortality", "economy",
          "medicine", "migration", "environment"
        - Supported years: 2010, 2015, 2020
        - Data is returned in wide format with separate columns for each class1,
          class2, and unit combination
    """

    def __init__(self):
        """
        Initialize a new CensusKR instance.

        Creates a new instance of the CensusKR class with empty attributes for
        storing geodata, tabular data, and crosswalk boundaries. All attributes
        are initialized as None and will be populated through method calls.

        Attributes initialized:
            gdf (gpd.GeoDataFrame): Will store GeoDataFrame for spatial data
            df (pd.DataFrame): Will store DataFrame for tabular census data
            crosswalk (gpd.GeoDataFrame): Will store crosswalk boundaries between years

        Examples:
            >>> census = CensusKR()
            >>> data = census.anycensus(year=2020, type="population")
        """
        self.gdf = None
        self.df = None
        self.crosswalk = None

    def load_data(self, year: int) -> pd.DataFrame:
        """
        Load census data for a specific year.

        This method loads the bundled census data from the parquet file for the
        specified year. The data contains various census metrics organized by
        administrative regions.

        Parameters:
            year (int): Census year to load. Must be one of 2010, 2015, or 2020.

        Returns:
            pd.DataFrame: A DataFrame containing census data for the specified year,
                filtered from the complete dataset. Contains columns for year, type,
                administrative regions (adm1, adm2), codes, classes, units, and values.

        Raises:
            ValueError: If the specified year is not available in the dataset.

        Notes:
            - The returned DataFrame is filtered to contain only data for the
              specified year
            - Data includes multiple census types (population, housing, tax, etc.)
            - Administrative codes and names are preserved for both adm1 and adm2 levels
        """
        location = os.path.dirname(os.path.realpath(__file__))
        file_name = os.path.join(location, "data", f"censuskor.parquet")
        df = pd.read_parquet(file_name)
        dfe = df.loc[df['year'] == year].copy()
        return dfe
    
    def load_districts(self, year: int) -> gpd.GeoDataFrame:
        """
        Load district boundaries for a specific year.

        This method loads administrative district boundaries from the bundled
        GeoPackage file for the specified year. The boundaries are stored as
        spatial data (sf/GeoDataFrame objects) and can be used for mapping
        and spatial analysis.

        Parameters:
            year (int): The year for which to load district boundaries.
                Must be one of 2010, 2015, or 2020.

        Returns:
            gpd.GeoDataFrame: A GeoDataFrame containing district boundaries
                for the specified year, including geometry and administrative
                codes and names.

        Raises:
            ValueError: If the specified year is not available.
            FileNotFoundError: If the boundaries data file is not found.

        Notes:
            - Returns adm2 (municipal-level) boundaries by default
            - Boundaries are stored in GeoPackage format with separate layers per year
            - Each boundary includes administrative codes, names, and geometry
            - Compatible with spatial operations and mapping libraries
        """
        name_lyr = f"adm2_{year}"

        location = os.path.dirname(os.path.realpath(__file__))
        path_bound = os.path.join(location, "data", "boundaries.gpkg")
        districts = gpd.read_file(path_bound, layer = name_lyr)
        return districts
    
    def convert_basic_adm2(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Convert pycensuskr standard level 2 administrative boundaries to basic local government boundaries.

        This method dissolves the level 2 administrative GeoDataFrame to
        a basic local government boundary GeoDataFrame by eliminating sub-levels
        in some municipalities. It standardizes the GeoDataFrame
        by ensuring adm2_code will contain five digits with ending "0".
        The geometry column is preserved and the boundaries are dissolved
        accordingly.

        Parameters:
            gdf (gpd.GeoDataFrame): Input GeoDataFrame containing district boundaries.

        Returns:
            gpd.GeoDataFrame: A converted GeoDataFrame.
        """
        gdf_conv = gdf.copy()
        # Ensure adm2_code is string
        gdf_conv["adm2_code"] = gdf_conv["adm2_code"].astype(str)
        # Create basic adm2_code by replacing last digit with "0"
        gdf_conv["adm2_code_basic"] = gdf_conv["adm2_code"].str[:-1] + "0"
        # Dissolve by basic adm2_code
        gdf_basic = gdf_conv.dissolve(by="adm2_code_basic", as_index=False)
        # Update adm2_code and adm2 columns
        gdf_basic["adm2_code"] = gdf_basic["adm2_code_basic"]
        gdf_basic = gdf_basic.drop(columns=["adm2_code_basic"])
        return gdf_basic
            
    def anycensus(
        self,
        year: int = 2020,
        codes=None,
        type: str = "population",
        level: str = "adm2",
        aggregator=None,
        geometry=False,
        **agg_kwargs,
    ):
        """
        Query Korean census data by administrative code (province or municipality) and year.

        This method queries the long format census data frame for specific administrative
        codes (if provided) and returns data in wide format. It is the Python equivalent
        of the anycensus() function in the tidycensuskr R package.

        The method queries bundled census data which is limited to certain quintennial
        years (2010, 2015, and 2020). The bundled data includes 54K+ rows and 10 columns
        covering various demographic, economic, and social indicators.

        Parameters:
            year (int, optional): Census year to query. One of 2010, 2015, or 2020.
                Defaults to 2020.
            codes (list or None, optional): Integer list of admin codes (e.g. [11, 26])
                or character administrative area names (e.g. [\"Seoul\", \"Daejeon\"]).
                If None, returns all available codes. Defaults to None.
            type (str, optional): Census data type. One of \"population\", \"housing\",
                \"tax\", \"economy\", \"medicine\", \"migration\", \"environment\", or
                \"mortality\". Defaults to \"population\".
            level (str, optional): Administrative level. \"adm1\" for province-level or
                \"adm2\" for municipal-level. Defaults to \"adm2\".
            aggregator (callable or None, optional): Function to aggregate values when
                level = \"adm1\". Defaults to numpy.sum.
            geometry (bool, optional): Whether to include spatial geometry data in the
                result. If True, returns a GeoDataFrame. Defaults to False.
            **agg_kwargs: Additional arguments passed to the aggregator function
                (e.g., when using custom aggregation functions).

        Returns:
            pd.DataFrame or gpd.GeoDataFrame: A data frame containing census data for
                the specified codes and year in wide format. If geometry=True, returns
                a GeoDataFrame with spatial boundaries included.

        Raises:
            ValueError: If level is not 'adm1' or 'adm2', if mixed types are provided
                in codes, or if data loading fails.
            KeyError: If required columns are missing from the data.

        Notes:
            - Using character strings in codes has a side effect of returning all rows
              in the dataset that match year and type through prefix matching
            - The returned table is in wide format with separate columns for each
              class1, class2, and unit (abbreviated) combination
            - When level=\"adm1\", adm2 data is aggregated to province level using
              the specified aggregator function
            - Column names are cleaned and lowercased in the output
            - Units are abbreviated to minimum length of 3 characters

        Examples:
            Query mortality data for administrative code 21 (Busan):
            >>> census = CensusKR()
            >>> data = census.anycensus(codes=[21], type=\"mortality\")

            Query population data for Seoul and Daejeon with housing data for 2015:
            >>> data = census.anycensus(codes=[\"Seoul\", \"Daejeon\"],
            ...                        type=\"housing\", year=2015)

            Aggregate to province level tax data using sum:
            >>> data = census.anycensus(codes=[11, 23, 31], type=\"tax\",
            ...                        year=2020, level=\"adm1\",
            ...                        aggregator=np.sum)

            Get data with spatial geometry:
            >>> gdf = census.anycensus(codes=[11], geometry=True)
        """

        if level not in ("adm2", "adm1"):
            raise ValueError("level must be 'adm2' or 'adm1'")

        # Default aggregator
        aggregator = aggregator or np.sum

        # Load data for the requested year
        df = self.load_data(year)
        if df is None or not isinstance(df, pd.DataFrame):
            raise ValueError("Failed to load census data. Ensure load_data(year) returns a DataFrame.")

        # Filter by year and type (create columns if not present)
        if "year" in df.columns:
            df_year_type = df[(df["year"] == year) & (df["type"] == type)] if "type" in df.columns else df[df["year"] == year].copy()
        else:
            df_year_type = df.copy()
            df_year_type["year"] = year
            if "type" not in df_year_type.columns:
                df_year_type["type"] = type
            else:
                df_year_type = df_year_type[df_year_type["type"] == type]

        # Determine if 'codes' are integers
        is_int_code = all(isinstance(c, (int, np.integer)) for c in (codes or []))
        try:
            try_code_integer = [int(c) for c in codes] if codes is not None else None
        except Exception:
            try_code_integer = None
        try_code_all_alpha = all(bool(re.search(r"[A-Za-z]+", str(c))) for c in (codes or []))

        if codes is not None and not is_int_code:
            if try_code_integer is not None and any(c is None for c in try_code_integer) and not try_code_all_alpha:
                raise ValueError("Mixed types in 'codes' are not allowed.")
            if try_code_integer is not None:
                # All convertible to integer
                codes = try_code_integer
                is_int_code = True

        query_col = f"{level}_code" if is_int_code else level

        # Default codes: all admx codes used
        if codes is None:
            if query_col not in df_year_type.columns:
                raise KeyError(f"Column '{query_col}' not found in data.")
            codes = df_year_type[query_col].dropna().astype(str).unique().tolist()
        else:
            codes = [str(c) for c in codes]
            # If codes are names and level is adm2, try searching adm1 names first
            if not is_int_code and level == "adm2":
                def strip_space(s): return re.sub(r"\s+", "", str(s))
                patt = re.compile(r"^(%s)" % "|".join(re.escape(c) for c in codes))
                matched_adm1 = []
                if "adm1" in df_year_type.columns:
                    mask_adm1 = df_year_type["adm1"].map(strip_space).str.match(patt)
                    matched_adm1 = df_year_type.loc[mask_adm1, "adm1"].dropna().unique().tolist()
                if len(matched_adm1) == 0 and "adm2" in df_year_type.columns:
                    mask_adm2 = df_year_type["adm2"].map(strip_space).str.match(patt)
                    matched_adm2 = df_year_type.loc[mask_adm2, "adm2"].dropna().unique().tolist()
                    codes = matched_adm2
                else:
                    codes = matched_adm1
                    query_col = "adm1"

        # Apply codes filter (prefix match OR exact membership)
        def strip_space(s): return re.sub(r"\s+", "", str(s))
        patt = re.compile(r"^(%s)" % "|".join(re.escape(c) for c in codes)) if codes else None
        left = df_year_type[query_col].map(strip_space).str.match(patt) if patt else pd.Series(False, index=df_year_type.index)
        right = df_year_type[query_col].astype(str).isin(codes) if codes else pd.Series(False, index=df_year_type.index)
        dfe = df_year_type[left | right].copy()

        # Abbreviate 'unit' to minlength=3
        if "unit" in dfe.columns:
            dfe["unit"] = dfe["unit"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip().str[:3]

        # Pivot wider: names from (class1, class2, unit), values from 'value'
        have_pivot_cols = {"class1", "class2", "unit"}.issubset(dfe.columns) and "value" in dfe.columns
        if have_pivot_cols:
            dfe["__colname__"] = (
                dfe["class1"].astype(str) + "_" +
                dfe["class2"].astype(str) + "_" +
                dfe["unit"].astype(str)
            )
            index_cols = [c for c in ["year", "type", "adm1", "adm1_code", "adm2", "adm2_code"] if c in dfe.columns]
            out = dfe.pivot_table(
                index=index_cols,
                columns="__colname__",
                values="value",
                aggfunc=aggregator,
                **agg_kwargs
            ).reset_index()
            # Clean column names
            out.columns = [str(c).lower().replace("_na", "") for c in out.columns]
        else:
            out = dfe
            out.columns = [str(c).lower().replace("_na", "") for c in out.columns]

        # If level is adm1, aggregate adm2 to adm1
        if level == "adm1":
            cols_to_drop = [c for c in ["adm2", "adm2_code"] if c in out.columns]
            tmp = out.drop(columns=cols_to_drop, errors="ignore")
            group_cols = [c for c in ["year", "type", "adm1", "adm1_code"] if c in tmp.columns]
            num_cols = tmp.select_dtypes(include=["number"]).columns.tolist()
            if num_cols:
                out = tmp.groupby(group_cols, as_index=False)[num_cols].agg(aggregator, **agg_kwargs)
            else:
                out = tmp.drop_duplicates(group_cols)

        # Optionally merge geometry
        if geometry:
            districts = self.load_districts(year)
            geo_merge_col = f"{level}_code"
            if geo_merge_col not in districts.columns:
                raise KeyError(f"Column '{geo_merge_col}' not found in district boundaries.")
            out = out.merge(
                districts[[geo_merge_col, "geometry"]],
                left_on=f"{level}_code",
                right_on=geo_merge_col,
                how="left"
            )
            out = gpd.GeoDataFrame(out, geometry="geometry", crs=districts.crs)

        return out


    def create_crosswalkboundary(self, year1: int, year2: int):
        """
        Create crosswalk boundaries between two different census years.

        This method creates spatial crosswalk boundaries by computing the geometric
        intersection between district boundaries from two different years. This is
        useful for analyzing boundary changes over time and for harmonizing data
        across different administrative boundary systems.

        Parameters:
            year1 (int): The first census year for crosswalk. Must be one of
                2010, 2015, or 2020.
            year2 (int): The second census year for crosswalk. Must be one of
                2010, 2015, or 2020.

        Returns:
            gpd.GeoDataFrame: A GeoDataFrame containing the intersected boundaries
                from both years, with attributes from both time periods. Each polygon
                represents the spatial intersection between boundaries from year1 and year2.

        Raises:
            ValueError: If neither year1 nor year2 is provided, or if invalid
                years are specified.
            FileNotFoundError: If boundary data is not available for the specified years.

        Warnings:
            UserWarning: This function performs a computationally intensive geometric
                intersection operation that may take considerable time to complete,
                especially for large datasets.

        Notes:
            - This is a computationally heavy operation that may take significant time
            - The resulting crosswalk can be used to transfer data between different
              boundary systems or to analyze boundary changes over time
            - Each resulting polygon contains attributes from both input years
            - Useful for temporal analysis and data harmonization across years

        Examples:
            Create crosswalk between 2015 and 2020 boundaries:
            >>> census = CensusKR()
            >>> crosswalk = census.create_crosswalkboundary(2015, 2020)
        """
        # fails if neither year1 nor year2 is populated
        if not year1 and not year2:
            raise ValueError("At least one of year1 or year2 must be provided.")
        districts1 = self.load_districts(year1)
        districts2 = self.load_districts(year2)
        UserWarning("This function runs a heavy intersection operation. It may take a while.")
        districts12 = districts1.overlay(districts2)
        return districts12


    def unify_boundaries(self, year_standard: int):
        """
        Unify census boundaries to a standard reference year.

        This method harmonizes census boundaries across different years by projecting
        all data to a common boundary system defined by the standard year. This allows
        for consistent temporal analysis and comparison of census data across years
        while maintaining spatial consistency.

        Parameters:
            year_standard (int): The reference year to use as the standard boundary
                system. Must be one of 2010, 2015, or 2020.

        Returns:
            gpd.GeoDataFrame: A unified GeoDataFrame with boundaries standardized
                to the reference year, allowing for consistent spatial analysis
                across different time periods.

        Raises:
            NotImplementedError: This method is not yet implemented.
            ValueError: If an invalid standard year is provided.

        Notes:
            - This method is currently not implemented and will raise a
              NotImplementedError when called
            - When implemented, it will allow for temporal analysis using consistent
              boundary definitions
            - Useful for time-series analysis where boundary changes would otherwise
              complicate comparisons
            - The standard year should be chosen based on the analysis requirements
              and data availability

        Future Implementation:
            This method will use spatial interpolation and crosswalk boundaries
            to project data from different years onto a common boundary system.
        """
        raise NotImplementedError
        # return "Census data unified."
    



