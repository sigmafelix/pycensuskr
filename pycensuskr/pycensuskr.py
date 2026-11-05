import pandas as pd
import geopandas as gpd
import os
import re
import lzma
import shutil
import tempfile
import numpy as np
import warnings
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

    The bundled dataset has 836,707 rows (103,572 for ADM2 and 733,135 for
    ADM3 data) and 12 columns. Its main census years are
    2010, 2015, and 2020, with additional ADM3-level household and housing data
    for 2015, 2020, and 2025.

    Attributes:
        gdf (gpd.GeoDataFrame): GeoDataFrame for spatial data.
        df (pd.DataFrame): DataFrame for tabular data.
        crosswalk (gpd.GeoDataFrame): Crosswalk boundaries between different years.

    Methods:
        load_data(year): Load census data for a specific year.
        load_districts(year, level): Load district boundaries for a specific year.
        convert_basic_adm2(gdf): Convert level 2 boundaries to basic local government boundaries.
        anycensus(year, codes, type, level, aggregator, **agg_kwargs): Query census data
            by admin code and year.
        create_crosswalkboundary(year1, year2): Create crosswalk boundaries between
            two years.
        unify_boundaries(year_standard): Unify census boundaries to a standard year.

    Notes:
        - Administrative levels: "adm1" (province-level), "adm2" (municipal-level),
          and "adm3" (sub-district/dong-level; boundaries are available through 2025)
        - ADM3 census data covers population and housing in 2015, 2020, and 2025;
          economy and mortality ADM3 data is available for 2020
        - Available data types: "population", "housing", "tax", "mortality", "economy",
          "medicine", "migration", "environment"
        - Census years: 2010, 2015, and 2020, plus ADM3 household and housing data in 2025
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

    def load_data(self, year) -> pd.DataFrame:
        """
        Load census data for one or more years.

        This method loads the bundled census data from the parquet file for the
        specified year(s). The data contains various census metrics organized by
        administrative regions.

        Parameters:
            year (int or list): Census year(s) to load. Each must be one of
                2010, 2015, 2020, or 2025. Coverage for 2025 is limited to
                ADM3-level household and housing data. A single int or a list/tuple of ints.

        Returns:
            pd.DataFrame: A DataFrame containing census data for the specified
                year(s), filtered from the complete dataset. Contains columns for
                year, type, administrative regions (adm1, adm2), codes, classes,
                units, and values.

        Raises:
            ValueError: If the specified year is not available in the dataset.

        Notes:
            - The returned DataFrame is filtered to contain only data for the
              specified year(s)
            - Data includes multiple census types (population, housing, tax, etc.)
            - Administrative codes and names are preserved for both adm1 and adm2 levels
        """
        years = year if isinstance(year, (list, tuple, set)) else [year]
        location = os.path.dirname(os.path.realpath(__file__))
        file_name = os.path.join(location, "data", f"censuskor.parquet")
        df = pd.read_parquet(file_name)
        dfe = df.loc[df['year'].isin(years)].copy()
        return dfe
    
    def load_districts(self, year: int, level: str = "adm2") -> gpd.GeoDataFrame:
        """
        Load district boundaries for a specific year.

        This method loads administrative district boundaries from the bundled
        GeoPackage file for the specified year. The boundaries are stored as
        spatial data (sf/GeoDataFrame objects) and can be used for mapping
        and spatial analysis.

        Parameters:
            year (int): The year for which to load district boundaries.
                For level="adm2", one of 2010, 2015, 2020, or 2025. The 2025
                ADM2 boundary is dated 2025-06-30 (KOSTAT second quarter).
                For level="adm3", one of 2010, 2015, 2020, or 2025.
            level (str, optional): Administrative level to load. "adm2" for
                municipal-level or "adm3" for sub-district (dong/myeon/eup)
                level boundaries. Defaults to "adm2".

        Returns:
            gpd.GeoDataFrame: A GeoDataFrame with the existing boundary layer
                fields and geometry for the specified year and level.

        Raises:
            ValueError: If the requested year is unavailable for the level, or
                if level is not 'adm2' or 'adm3'.
            FileNotFoundError: If the boundaries data file is not found.

        Notes:
            - All ADM2 years have validated, edge-matched, non-overlapping coverage.
              2010/2015 repairs use same-year geometry; 2020 uses 2015 historical
              evidence. 2025 contacts match the same-year unsimplified source.
              Source holes, original fields and row order are retained.
            - Returns adm2 (municipal-level) boundaries by default
            - adm3 boundaries carry adm3_code and adm3_name_kr instead of a
              year column, since each year has its own gpkg layer
            - The compressed GeoPackage is unpacked temporarily for each call;
              its layers, geometry and attributes are preserved
            - Each boundary includes administrative codes, names, and geometry
            - Compatible with spatial operations and mapping libraries
        """
        if level not in ("adm2", "adm3"):
            raise ValueError("level must be 'adm2' or 'adm3'")
        supported_years = (2010, 2015, 2020, 2025)
        if year not in supported_years:
            raise ValueError(f"year must be one of {supported_years} for level='{level}'")

        name_lyr = f"{level}_{year}"

        location = os.path.dirname(os.path.realpath(__file__))
        archive = os.path.join(location, "data", "boundaries.gpkg.xz")
        with tempfile.TemporaryDirectory(prefix="pycensuskr-") as temp_dir:
            path_bound = os.path.join(temp_dir, "boundaries.gpkg")
            with lzma.open(archive, "rb") as source, open(path_bound, "wb") as target:
                shutil.copyfileobj(source, target)
            return gpd.read_file(path_bound, layer=name_lyr)
    
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
        year=2020,
        codes: list = [],
        type: str = "population",
        level: str = "adm2",
        adm2_type: str = "all",
        aggregator = np.sum,
        weight_type=None,
        weight_column=None,
        geometry=False,
        **agg_kwargs,
    ):
        """
        Query Korean census data by administrative code (province or municipality) and year.

        This method queries the long format census data frame for specific administrative
        codes (if provided) and returns data in wide format. It is the Python equivalent
        of the anycensus() function in the tidycensuskr R package.

        The method queries the bundled 12-column census dataset. It covers 2010,
        2015, and 2020, with additional ADM3-level household and housing records
        for 2015, 2020, and 2025.

        Parameters:
            year (int or list, optional): Census year(s) to query. Each one of
                2010, 2015, 2020, or 2025. Coverage varies by type, year, and
                geographic level. Accepts a single int or a list/tuple of ints
                to query multiple years at once. Defaults to 2020.
            codes (list, optional): Integer list of admin codes (e.g. [11, 26])
                or character administrative area names (e.g. [\"Seoul\", \"Daejeon\"]).
                If None, returns all available codes. Defaults to an empty list.
            type (str or list, optional): Census data type(s). Each one of
                \"population\", \"housing\", \"tax\", \"economy\", \"medicine\",
                \"migration\", \"environment\", or \"mortality\". Accepts a single
                string or a list/tuple of strings to query multiple types at once.
                Defaults to \"population\".
            level (str, optional): Administrative level. \"adm1\" for province-level,
                \"adm2\" for municipal-level, or \"adm3\" for sub-district
                (dong/myeon/eup) level. adm3-level census data is only available
                where the bundled data has adm3 granularity. Population and
                housing are available at adm3 level for 2015, 2020, and 2025;
                economy and mortality are available at adm3 level for 2020.
                Other type/year combinations return no rows at level=\"adm3\".
                Defaults to \"adm2\".
            adm2_type (str, optional): Municipal level to return or aggregate.
                For a city and its non-autonomous Gu with the same indicator,
                "all" removes the source city count when Gu values are available,
                but retains city and Gu rates; the city count is missing in a
                mixed wide row. "atn" returns cities with available Gu counts
                summed and the city rate retained. "non" returns Gu rows where
                available. Incomplete Gu sums raise a warning. If a city rate is
                missing, "atn" uses the Gu mean; supplied weights recalculate
                city rates from the Gu. Rate units are per 100,000 population,
                births per 1,000, births per woman, and percent. Other units are
                treated as additive counts. Selecting a city code with "atn" or
                "non" also selects its Gu. "all" retains both city and Gu rates;
                choose the intended level and aggregator when aggregating rates.
                Defaults to "all".
            aggregator (callable, optional): Function to aggregate values when
                level = \"adm1\" or when weighted adm2_type=\"atn\" recalculates
                autonomous/basic local government rows. Defaults to numpy.sum.
                When weight_type or weight_column is supplied, aggregator must
                accept a `weights` keyword argument (e.g. a wrapper around
                numpy.average).
            weight_type (str, optional): Census data type used to supply weights
                when aggregating (e.g. rate variables in type=\"mortality\" can be
                weighted by population counts from weight_type=\"population\").
                Defaults to None (no separate weight query; weight_column must
                already exist in the queried type's own data).
            weight_column (str, optional): Column name used as weights when
                aggregating. If weight_type=\"population\" and weight_column is
                omitted, \"all households_total_per\" is used. Defaults to None.
            geometry (bool, optional): Whether to include spatial geometry data in the
                result. If True, returns a GeoDataFrame. Boundaries are available for
                2010, 2015, and 2020; 2025 census rows are tabular only. Defaults to False.
            **agg_kwargs: Additional arguments passed to the aggregator function
                (e.g., when using custom aggregation functions).

        Returns:
            pd.DataFrame or gpd.GeoDataFrame: A data frame containing census data for
                the specified codes and year in wide format. If geometry=True, returns
                a GeoDataFrame with spatial boundaries included.

        Raises:
            ValueError: If level is not 'adm1' or 'adm2', if adm2_type is not 'all',
                'atn', or 'non', if mixed types are provided in codes, if weighted
                adm2-level computation is requested without adm2_type='atn', if
                geometry is requested for a year without bundled boundaries, or if
                data loading fails.
            KeyError: If required columns (including the weight column) are missing
                from the data.

        Notes:
            - Using character strings in codes has a side effect of returning all rows
              in the dataset that match year and type through prefix matching
            - The returned table is in wide format with separate columns for each
              class1, class2, and unit (abbreviated) combination
            - When level=\"adm1\", adm2 data is aggregated to province level using
              the specified aggregator function
            - Weighted adm2-level computation (weight_type or weight_column supplied)
              is only available when adm2_type=\"atn\"
            - Column names are cleaned and lowercased in the output
            - Units are abbreviated to minimum length of 3 characters
            - ADM3 rows with a valid code but no mapped name are retained with
              a missing value in the adm3 column

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

            Query population data for multiple years at once:
            >>> data = census.anycensus(codes=[11], year=[2010, 2015, 2020])

            Aggregate mortality rates to adm1 using population weights:
            >>> def weighted_mean(x, weights, **kw):
            ...     return np.average(x, weights=weights)
            >>> data = census.anycensus(codes=[\"Seoul\"], type=\"mortality\",
            ...                        year=2020, level=\"adm1\",
            ...                        aggregator=weighted_mean,
            ...                        weight_type=\"population\")

            Recalculate adm2 rates after cleaning to autonomous/basic local governments:
            >>> data = census.anycensus(codes=[\"Gyeonggi-do\"], type=\"mortality\",
            ...                        year=2020, level=\"adm2\", adm2_type=\"atn\",
            ...                        aggregator=weighted_mean,
            ...                        weight_type=\"population\")

            Query multiple census types at once:
            >>> data = census.anycensus(codes=[11], type=["population", "housing"])

            Query the added 2025 neighborhood-level housing data:
            >>> data = census.anycensus(year=2025, type="housing", level="adm3")
        """

        if level not in ("adm2", "adm1", "adm3"):
            raise ValueError("level must be 'adm2', 'adm1', or 'adm3'")

        if adm2_type not in ("all", "atn", "non"):
            raise ValueError("adm2_type must be 'all', 'atn', or 'non'")

        # Default aggregator
        aggregator = aggregator or np.sum

        # Normalize year and type to lists so single and multiple values share one code path
        years = list(year) if isinstance(year, (list, tuple, set)) else [year]
        types = list(type) if isinstance(type, (list, tuple, set)) else [type]

        has_weighting = weight_type is not None or weight_column is not None
        if level == "adm2" and has_weighting and adm2_type != "atn":
            raise ValueError("Weighted adm2 computation is only available when adm2_type='atn'.")
        if level == "adm3" and has_weighting:
            raise ValueError("Weighted aggregation is not supported for level='adm3'.")
        if has_weighting and weight_column is None:
            if weight_type == "population":
                weight_column = "all households_total_per"
            else:
                raise ValueError("'weight_column' must be supplied when weighted aggregation is requested.")

        # Load data for the requested year(s)
        df = self.load_data(years)
        if df is None or not isinstance(df, pd.DataFrame):
            raise ValueError("Failed to load census data. Ensure load_data(year) returns a DataFrame.")

        # Filter by year and type (create columns if not present)
        if "year" in df.columns:
            year_mask = df["year"].isin(years)
            df_year_type = df[year_mask & (df["type"].isin(types))] if "type" in df.columns else df[year_mask].copy()
        else:
            df_year_type = df.copy()
            if len(years) == 1:
                df_year_type["year"] = years[0]
            else:
                raise ValueError("Multiple years requested but data has no 'year' column to filter on.")
            if "type" not in df_year_type.columns:
                if len(types) == 1:
                    df_year_type["type"] = types[0]
                else:
                    raise ValueError("Multiple types requested but data has no 'type' column to filter on.")
            else:
                df_year_type = df_year_type[df_year_type["type"].isin(types)]

        # Keep the caller's codes for weight queries; 'codes' is expanded below
        requested_codes = codes

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
        if isinstance(codes, list):
            if len(codes) == 0:
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
                # If codes are names and level is adm3, try adm1 then adm2 names before
                # falling back to matching adm3 (dong-level) names directly
                elif not is_int_code and level == "adm3":
                    def strip_space(s): return re.sub(r"\s+", "", str(s))
                    patt = re.compile(r"^(%s)" % "|".join(re.escape(c) for c in codes))
                    matched_adm1 = []
                    if "adm1" in df_year_type.columns:
                        mask_adm1 = df_year_type["adm1"].map(strip_space).str.match(patt)
                        matched_adm1 = df_year_type.loc[mask_adm1, "adm1"].dropna().unique().tolist()
                    matched_adm2 = []
                    if not matched_adm1 and "adm2" in df_year_type.columns:
                        mask_adm2 = df_year_type["adm2"].map(strip_space).str.match(patt)
                        matched_adm2 = df_year_type.loc[mask_adm2, "adm2"].dropna().unique().tolist()
                    if matched_adm1:
                        codes = matched_adm1
                        query_col = "adm1"
                    elif matched_adm2:
                        codes = matched_adm2
                        query_col = "adm2"
                    # else: keep codes/query_col as-is to match adm3 (dong) names directly
        else:
            raise ValueError("'codes' must be a list of integers or strings.")

        # Apply codes filter (prefix match OR exact membership)
        def strip_space(s): return re.sub(r"\s+", "", str(s))
        patt = re.compile(r"^(%s)" % "|".join(re.escape(c) for c in codes)) if codes else None
        left = df_year_type[query_col].map(strip_space).str.match(patt) if patt else pd.Series(False, index=df_year_type.index)
        right = df_year_type[query_col].astype(str).isin(codes) if codes else pd.Series(False, index=df_year_type.index)
        selected = left | right
        if level == "adm2" and adm2_type in ("atn", "non"):
            area_codes = self._code_str(df_year_type["adm2_code"])
            city_prefixes = area_codes[selected & area_codes.str.endswith("0")].str[:4].unique()
            selected |= area_codes.str[:4].isin(city_prefixes) & ~area_codes.str.endswith("0")
        dfe = df_year_type[selected].copy()

        # For level="adm3", a name query may have matched via the adm1/adm2 column
        # (see cascading match above), which would otherwise let in rows that lack
        # adm3 granularity. Restrict to rows that actually have adm3 data.
        if level == "adm3" and "adm3_code" in dfe.columns:
            dfe = dfe[dfe["adm3_code"].notna()]
        # Conversely, adm1/adm2 queries must not sum ADM3 rows into their parents
        elif "adm3_code" in dfe.columns:
            dfe = dfe[dfe["adm3_code"].isna()]

        # In all mode, keep city rates while removing overlapping city counts.
        excluded_count_columns = set()
        if level != "adm3" and adm2_type == "all":
            reference = df_year_type
            if "adm3_code" in reference.columns:
                reference = reference[reference["adm3_code"].isna()]
            excluded = self._overlapping_city_counts(dfe, reference)
            removed = dfe.loc[excluded]
            excluded_count_columns = set(
                (removed["class1"].astype(str) + "_" + removed["class2"].astype(str) + "_" +
                 removed["unit"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip().str[:3])
                .str.lower().str.replace("_na", "", regex=False)
            )
            dfe = dfe.loc[~excluded].copy()

        # Keep the full unit to tell rate columns from count columns after pivoting
        if "unit" in dfe.columns:
            dfe["_unit_full"] = dfe["unit"]

        # Abbreviate 'unit' to minlength=3
        if "unit" in dfe.columns:
            dfe["unit"] = dfe["unit"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip().str[:3]

        # Keep ADM3 rows with a valid code even when their name is unmapped;
        # pandas pivot_table otherwise drops rows with a missing index value.
        missing_adm3_name = "__censuskr_missing_adm3_name__"
        if level == "adm3" and "adm3" in dfe.columns:
            dfe["adm3"] = dfe["adm3"].fillna(missing_adm3_name)

        # Pivot wider: names from (class1, class2, unit), values from 'value'
        have_pivot_cols = {"class1", "class2", "unit"}.issubset(dfe.columns) and "value" in dfe.columns
        if have_pivot_cols:
            dfe["__colname__"] = (
                dfe["class1"].astype(str) + "_" +
                dfe["class2"].astype(str) + "_" +
                dfe["unit"].astype(str)
            )
            index_cols = [c for c in ["year", "type", "adm1", "adm1_code", "adm2", "adm2_code"] if c in dfe.columns]
            if level == "adm3":
                index_cols += [c for c in ["adm3", "adm3_code"] if c in dfe.columns]
            # Collapses raw duplicate (year, type, adm1, adm2, class1, class2, unit) rows,
            # which do occur in the bundled data. Always sums rather than reusing the
            # user-supplied 'aggregator', since that may require a 'weights' kwarg meant
            # for the level="adm1"/weighted adm2 aggregation stages below, not this reshape.
            # min_count=1 keeps omitted (NA) values as NA instead of turning them into 0.
            out = (
                dfe.groupby(index_cols + ["__colname__"])["value"]
                .sum(min_count=1)
                .unstack("__colname__")
                .reset_index()
            )
            # Clean column names
            out.columns = [str(c).lower().replace("_na", "") for c in out.columns]
            rate_columns = {
                str(c).lower().replace("_na", "")
                for c in dfe.loc[dfe["_unit_full"].isin(self.RATE_UNITS), "__colname__"].unique()
            }
            if level == "adm3" and "adm3" in out.columns:
                out["adm3"] = out["adm3"].replace(missing_adm3_name, np.nan)
        else:
            out = dfe
            out.columns = [str(c).lower().replace("_na", "") for c in out.columns]
            rate_columns = set()

        for column in excluded_count_columns.difference(out.columns):
            out[column] = np.nan

        # Gu codes of each city in the requested years, taken from all types
        ref_gu = self._reference_gu(df) if adm2_type == "atn" else {}

        # Non-weighted adm2_type handling (weighted 'atn' is resolved below,
        # since rate variables are then recalculated with the supplied weights)
        if adm2_type == "atn" and not has_weighting and "adm2_code" in out.columns and level != "adm3":
            out = self._collapse_to_atn(out, ref_gu, rate_columns)
        elif adm2_type == "non" or (adm2_type == "atn" and not has_weighting):
            out = self.detect_adm2_type(out, mode=adm2_type)

        # Weighted adm2-level recalculation: fold non-autonomous rows into their
        # autonomous/basic local government parent using weighted aggregation
        if level == "adm2" and has_weighting:
            out = self._apply_weighted_adm2(
                out, years, types, requested_codes, weight_type, weight_column, aggregator, agg_kwargs,
                ref_gu, rate_columns
            )

        # If level is adm1, aggregate adm2 to adm1
        if level == "adm1":
            if has_weighting:
                out = self._aggregate_adm1_weighted(
                    out, years, types, requested_codes, adm2_type, weight_type, weight_column,
                    aggregator, agg_kwargs, ref_gu, rate_columns
                )
            else:
                cols_to_drop = [c for c in ["adm2", "adm2_code"] if c in out.columns]
                tmp = out.drop(columns=cols_to_drop, errors="ignore")
                group_cols = [c for c in ["year", "type", "adm1", "adm1_code"] if c in tmp.columns]
                num_cols = [c for c in tmp.select_dtypes(include=["number"]).columns if c not in group_cols]
                if num_cols:
                    out = tmp.groupby(group_cols, as_index=False)[num_cols].agg(aggregator, **agg_kwargs)
                else:
                    out = tmp.drop_duplicates(group_cols)

        # Optionally merge geometry
        if geometry:
            available_boundary_years = {2010, 2015, 2020}
            missing_boundary_years = sorted(set(years) - available_boundary_years)
            if missing_boundary_years:
                raise ValueError(
                    "Boundary geometry is available only for 2010, 2015, and 2020; "
                    f"no geometry is bundled for requested year(s): {missing_boundary_years}."
                )
            geo_merge_col = f"{level}_code"
            frames = []
            districts = None
            districts_level = level if level == "adm3" else "adm2"
            for yr in years:
                districts = self.load_districts(yr, level=districts_level)
                if geo_merge_col not in districts.columns:
                    raise KeyError(f"Column '{geo_merge_col}' not found in district boundaries.")
                out_yr = out[out["year"] == yr] if "year" in out.columns else out
                merged = out_yr.merge(
                    districts[[geo_merge_col, "geometry"]],
                    left_on=f"{level}_code",
                    right_on=geo_merge_col,
                    how="left"
                )
                frames.append(merged)
            out = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
            out = gpd.GeoDataFrame(out, geometry="geometry", crs=districts.crs)

        return out

    # Units whose values are rates; every other unit is treated as an additive count
    RATE_UNITS = {"per 100k population", "births per 1000", "births per woman", "percent"}

    @staticmethod
    def _code_str(codes):
        """Codes as strings without a float suffix (31011.0 -> "31011")."""
        return codes.astype(str).str.replace(r"\.0$", "", regex=True)

    @staticmethod
    def _overlapping_city_counts(df, reference):
        """Mark city counts with an observed Gu value for the same indicator."""
        keys = ["year", "type", "class1", "class2", "unit"]
        ref_codes = CensusKR._code_str(reference["adm2_code"])
        is_gu = ~ref_codes.str.endswith("0")
        is_count = ~reference["unit"].isin(CensusKR.RATE_UNITS)
        child_mask = is_gu & is_count & reference["value"].notna()
        children = reference.loc[child_mask, keys].copy()
        children["_parent"] = (ref_codes.loc[child_mask].str[:4] + "0").to_numpy()
        child_keys = pd.MultiIndex.from_frame(children)

        codes = CensusKR._code_str(df["adm2_code"])
        candidates = df[keys].copy()
        candidates["_parent"] = codes.to_numpy()
        return (codes.str.endswith("0") & ~df["unit"].isin(CensusKR.RATE_UNITS)
                & pd.MultiIndex.from_frame(candidates).isin(child_keys))

    @staticmethod
    def _reference_gu(df):
        """Non-autonomous Gu codes of each (year, city code), taken from all types in ``df``."""
        if "adm3_code" in df.columns:
            df = df[df["adm3_code"].isna()]
        df = df[df["adm2_code"].notna()]
        codes = CensusKR._code_str(df["adm2_code"])
        is_gu = codes.str[-1] != "0"
        ref = {}
        for year, code in zip(df.loc[is_gu, "year"], codes[is_gu]):
            ref.setdefault((year, code[:4] + "0"), set()).add(code)
        return ref

    def _collapse_to_atn(self, df, ref_gu, rate_columns=(), weights=None,
                         aggregator=None, agg_kwargs=None):
        """
        Return autonomous/basic local government rows of ``df``, resolving each
        city with non-autonomous Gu variable by variable within a year and type.

        - Count variables use the sum of the Gu when every Gu of that year
          (``ref_gu``) has a value, since city rows can be missing, zero or
          averaged. When some Gu values are unavailable, the partial Gu sum is
          used with a warning.
        - Rate variables (``rate_columns``) are recalculated from the Gu with
          ``aggregator`` when ``weights`` (Gu code -> weight) are given.
          Otherwise the city rate is kept, or the unweighted Gu mean is used
          when the city rate is missing.

        Values built from an incomplete set of Gu are reported in one warning.
        """
        keys = [c for c in ["year", "type"] if c in df.columns]
        id_cols = keys + [c for c in ["adm1", "adm1_code", "adm2", "adm2_code"] if c in df.columns]
        value_cols = [c for c in df.columns if c not in id_cols]
        codes = self._code_str(df["adm2_code"])
        parents = codes.str[:4] + "0"
        is_gu = (codes != parents).to_numpy()

        out = df.loc[~is_gu].copy()
        city_index = dict(zip(zip(*[out[k] for k in keys], codes[~is_gu]), out.index))
        gu_df = df.loc[is_gu].assign(_code=codes[is_gu].to_numpy(), _parent=parents[is_gu].to_numpy())
        new_rows, partial = [], []

        for gkey, g in gu_df.groupby(keys + ["_parent"], sort=False):
            gkey = gkey if isinstance(gkey, tuple) else (gkey,)
            year = gkey[keys.index("year")] if "year" in keys else None
            expected = ref_gu.get((year, gkey[-1]), set(g["_code"]))
            i = city_index.get(gkey)
            if i is None:
                # The city row is missing: start from its first Gu row
                row = g.iloc[0][id_cols].copy()
                row["adm2_code"] = (float(gkey[-1]) if pd.api.types.is_numeric_dtype(df["adm2_code"])
                                    else gkey[-1])
                # Gu names read "<gu> <city>", e.g. "Jangan-gu Suwon-si"
                if "adm2" in row.index:
                    row["adm2"] = str(row["adm2"]).split(" ", 1)[-1]
                city = pd.Series(np.nan, index=value_cols)
            else:
                row, city = out.loc[i, id_cols], out.loc[i, value_cols]
            w = None if weights is None else g["_code"].map(weights).to_numpy(dtype=float)

            resolved = {}
            for col in value_cols:
                v = g[col].to_numpy(dtype=float)
                ok = ~np.isnan(v)
                if not ok.any():
                    continue
                complete = set(g["_code"][ok]) >= expected
                if col in rate_columns:
                    if w is not None:
                        resolved[col] = self._call_weighted_aggregator(aggregator, v[ok], w[ok], agg_kwargs or {})
                    elif pd.isna(city[col]):
                        resolved[col] = v[ok].mean()
                    else:
                        continue
                else:
                    resolved[col] = v[ok].sum()
                if not complete:
                    partial.append(f"{year:.0f} {row.get('adm2', gkey[-1])}: {col}" if year is not None
                                   else f"{row.get('adm2', gkey[-1])}: {col}")

            if i is None:
                new_rows.append({**row.to_dict(), **resolved})
            else:
                for col, value in resolved.items():
                    out.at[i, col] = value

        if partial:
            warnings.warn(
                f"adm2_type='atn' used an incomplete set of non-autonomous Gu for "
                f"{len(partial)} value(s), e.g. {partial[0]}.",
                UserWarning,
                stacklevel=3,
            )
        if new_rows:
            out = pd.concat([out, pd.DataFrame(new_rows)], ignore_index=True)
        return out

    @staticmethod
    def _call_weighted_aggregator(aggregator, values, weights, agg_kwargs):
        """Call aggregator(values, weights=weights, **agg_kwargs) with a clear error
        if aggregator doesn't accept a 'weights' keyword (e.g. the default np.sum)."""
        try:
            return aggregator(values, weights=weights, **agg_kwargs)
        except TypeError as exc:
            if "weights" in str(exc):
                raise ValueError(
                    "'aggregator' must accept a 'weights' keyword argument when "
                    "weight_type or weight_column is supplied (the default, "
                    "np.sum, does not). Example: "
                    "lambda x, weights, **kw: np.average(x, weights=weights)"
                ) from exc
            raise

    def _resolve_weight_pool(
        self, out, years, codes, types, weight_type, weight_column, adm2_type
    ):
        """
        Resolve the adm2-level data used as the source of aggregation weights.

        If ``weight_type`` names one of the types already present in ``out``,
        that slice of ``out`` is reused. Otherwise a separate adm2-level query
        is issued for ``weight_type`` over the same years and codes.

        Returns None if ``weight_type`` is None (meaning ``weight_column`` is
        expected to already live inside each type's own data).
        """
        if weight_type is None:
            return None
        if weight_type in types:
            pool = out[out["type"] == weight_type] if "type" in out.columns else out
        else:
            pool = self.anycensus(
                year=years, codes=codes, type=weight_type, level="adm2",
                adm2_type=adm2_type, geometry=False,
            )
        if weight_column not in pool.columns:
            raise KeyError(
                f"Weight column '{weight_column}' was not found in the '{weight_type}' query output."
            )
        return pool

    def _collapse_weighted_adm2_to_atn(
        self, df, weight_df, weight_column, aggregator, agg_kwargs, ref_gu, rate_columns
    ):
        """
        Weighted adm2_type="atn" collapse of ``df`` (see ``_collapse_to_atn``).

        Rate columns are recalculated from the Gu with weights from
        ``weight_df``; the weight column itself is resolved as a count.
        Returns (collapsed data, collapsed weights) with string adm2 codes,
        the latter being a two-column (adm2_code, weight_column) frame.
        """
        weights = pd.Series(
            weight_df[weight_column].to_numpy(dtype=float),
            index=self._code_str(weight_df["adm2_code"]).to_numpy(),
        )
        weights = weights[~weights.index.duplicated()]
        data = self._collapse_to_atn(
            df.drop(columns=[weight_column], errors="ignore"),
            ref_gu, rate_columns, weights, aggregator, agg_kwargs,
        )
        id_cols = [c for c in ["year", "type", "adm1", "adm1_code", "adm2", "adm2_code"] if c in weight_df.columns]
        collapsed_weights = self._collapse_to_atn(weight_df[id_cols + [weight_column]], ref_gu)
        data["adm2_code"] = self._code_str(data["adm2_code"])
        collapsed_weights["adm2_code"] = self._code_str(collapsed_weights["adm2_code"])
        return data, collapsed_weights[["adm2_code", weight_column]]

    def _apply_weighted_adm2(
        self, out, years, types, codes, weight_type, weight_column, aggregator, agg_kwargs,
        ref_gu, rate_columns
    ):
        """Recalculate adm2_type='atn' rows for a weighted adm2-level query."""
        weight_codes = self._code_str(out["adm2_code"]).unique().tolist() if codes else codes
        weight_pool = self._resolve_weight_pool(
            out, years, weight_codes, types, weight_type, weight_column, adm2_type="all"
        )

        group_keys = [c for c in ["year", "type"] if c in out.columns]
        iterator = out.groupby(group_keys) if group_keys else [((), out)]
        frames = []
        for key, sub in iterator:
            key_vals = key if isinstance(key, tuple) else (key,)
            key_map = dict(zip(group_keys, key_vals))
            if weight_pool is not None:
                w_sub = weight_pool
                if "year" in key_map and "year" in w_sub.columns:
                    w_sub = w_sub[w_sub["year"] == key_map["year"]]
            else:
                w_sub = sub
            collapsed_data, collapsed_weights = self._collapse_weighted_adm2_to_atn(
                sub, w_sub, weight_column, aggregator, agg_kwargs, ref_gu, rate_columns
            )
            if weight_column in collapsed_data.columns:
                collapsed_data = collapsed_data.drop(columns=[weight_column])
            collapsed_data = collapsed_data.merge(collapsed_weights, on="adm2_code", how="left")
            frames.append(collapsed_data)
        return pd.concat(frames, ignore_index=True) if frames else out

    def _aggregate_adm1_weighted(
        self, out, years, types, codes, adm2_type, weight_type, weight_column,
        aggregator, agg_kwargs, ref_gu, rate_columns
    ):
        """Aggregate adm2 rows to adm1 using weighted aggregation."""
        pool_adm2_type = "all" if adm2_type == "atn" else adm2_type
        weight_pool = self._resolve_weight_pool(
            out, years, codes, types, weight_type, weight_column, adm2_type=pool_adm2_type
        )

        group_keys = [c for c in ["year", "type"] if c in out.columns]
        iterator = out.groupby(group_keys) if group_keys else [((), out)]
        frames = []
        for key, sub in iterator:
            key_vals = key if isinstance(key, tuple) else (key,)
            key_map = dict(zip(group_keys, key_vals))

            if weight_pool is not None:
                w_sub = weight_pool
                if "year" in key_map and "year" in w_sub.columns:
                    w_sub = w_sub[w_sub["year"] == key_map["year"]]
                if adm2_type == "atn":
                    sub_data, weight_values = self._collapse_weighted_adm2_to_atn(
                        sub, w_sub, weight_column, aggregator, agg_kwargs, ref_gu, rate_columns
                    )
                else:
                    sub_data = sub
                    weight_values = w_sub[["adm2_code", weight_column]].copy()
            else:
                if weight_column not in sub.columns:
                    raise KeyError(f"Weight column '{weight_column}' was not found in the data.")
                if adm2_type == "atn":
                    sub_data, weight_values = self._collapse_weighted_adm2_to_atn(
                        sub, sub, weight_column, aggregator, agg_kwargs, ref_gu, rate_columns
                    )
                else:
                    sub_data = sub
                    weight_values = sub[["adm2_code", weight_column]].copy()

            weight_values = weight_values.rename(columns={weight_column: "_aggregation_weight"})
            sub_data = sub_data.drop(columns=[weight_column], errors="ignore")
            sub_data = sub_data.merge(weight_values, on="adm2_code", how="left")

            group_cols = [c for c in ["year", "type", "adm1", "adm1_code"] if c in sub_data.columns]
            value_cols = [
                c for c in sub_data.columns
                if c not in group_cols and c not in ("adm2", "adm2_code", "_aggregation_weight")
            ]

            rows = []
            for gkey, g in sub_data.groupby(group_cols):
                gkey_vals = gkey if isinstance(gkey, tuple) else (gkey,)
                w = g["_aggregation_weight"].to_numpy()
                codes = self._code_str(g["adm2_code"])
                parents = codes.str[:4] + "0"
                is_city = codes == parents
                child_weights = parents[~is_city & pd.notna(w)]
                missing_city_weight = (is_city & pd.isna(w) & parents.isin(child_weights)).to_numpy()
                row = dict(zip(group_cols, gkey_vals))
                for col in value_cols:
                    keep = ~missing_city_weight
                    if col not in rate_columns:
                        child_values = parents[~is_city & g[col].notna()]
                        keep &= ~(is_city & parents.isin(child_values)).to_numpy()
                    row[col] = self._call_weighted_aggregator(
                        aggregator, g[col].to_numpy()[keep], w[keep], agg_kwargs
                    )
                row[weight_column] = np.nansum(w)
                rows.append(row)
            frames.append(pd.DataFrame(rows))

        return pd.concat(frames, ignore_index=True) if frames else out


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

    def detect_adm2_type(
        self,
        df: pd.DataFrame,
        year: int | None = None,
        mode: str = "non",
        adm2_code: str = "adm2_code",
    ) -> pd.DataFrame:
        """
        Detect adm2 code type and return exact autonomous/non-autonomous rows.

        The adm2 code may include both autonomous Gu codes (ending with "0") and
        non-autonomous Gu codes (ending with non-zero digit). This method detects
        code type from ``adm2_code`` and returns rows according to ``mode``.

        Parameters:
            df (pd.DataFrame): Input census table.
            year (int | None): Optional year filter. If omitted and a year
                column is present, codes are compared within each year.
            mode (str): "atn" for autonomous or "non" for non-autonomous.
            adm2_code (str): Column name containing adm2 codes.

        Returns:
            pd.DataFrame: Filtered table with exact adm2 code type.

        Raises:
            ValueError: If ``mode`` is not one of "atn" or "non".
            KeyError: If required columns are missing.
        """
        if mode not in ("atn", "non"):
            raise ValueError("mode must be 'atn' or 'non'")

        if adm2_code not in df.columns:
            raise KeyError(f"Column '{adm2_code}' not found in data.")

        dfe = df.copy()
        if year is not None:
            if "year" not in dfe.columns:
                raise KeyError("Column 'year' not found in data.")
            dfe = dfe.loc[dfe["year"] == year].copy()

        code_series = self._code_str(dfe[adm2_code])
        nonauto = code_series.str[-1] != "0"
        if mode == "atn":
            return dfe.loc[~nonauto].copy()

        # Parent codes only replace their component districts in the same year.
        if "year" in dfe.columns:
            year_groups, _ = pd.factorize(dfe["year"], sort=False, use_na_sentinel=False)
            groups = (np.flatnonzero(year_groups == value) for value in np.unique(year_groups))
        else:
            groups = [np.arange(len(dfe))]
        keep = np.ones(len(dfe), dtype=bool)
        for positions in groups:
            codes = code_series.iloc[positions]
            group_nonauto = nonauto.iloc[positions]
            parents = codes[group_nonauto].str[:4].unique()
            parents = pd.Index(parents) + "0"
            present_parents = parents[parents.isin(codes)]
            if not parents.isin(present_parents).all():
                warnings.warn(
                    "Inconsistent codes: Some non-autonomous Gu codes do not have "
                    "corresponding upper level administrative codes.",
                    UserWarning,
                    stacklevel=2,
                )
            keep[positions] = ~codes.isin(present_parents).to_numpy()
        return dfe.iloc[keep].copy()
