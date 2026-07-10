import pandas as pd
import geopandas as gpd
import os
import re
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

    def load_data(self, year) -> pd.DataFrame:
        """
        Load census data for one or more years.

        This method loads the bundled census data from the parquet file for the
        specified year(s). The data contains various census metrics organized by
        administrative regions.

        Parameters:
            year (int or list): Census year(s) to load. Each must be one of
                2010, 2015, or 2020. A single int or a list/tuple of ints.

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

        The method queries bundled census data which is limited to certain quintennial
        years (2010, 2015, and 2020). The bundled data includes 54K+ rows and 10 columns
        covering various demographic, economic, and social indicators.

        Parameters:
            year (int or list, optional): Census year(s) to query. Each one of
                2010, 2015, or 2020. Accepts a single int or a list/tuple of ints
                to query multiple years at once. Defaults to 2020.
            codes (list, optional): Integer list of admin codes (e.g. [11, 26])
                or character administrative area names (e.g. [\"Seoul\", \"Daejeon\"]).
                If None, returns all available codes. Defaults to an empty list.
            type (str or list, optional): Census data type(s). Each one of
                \"population\", \"housing\", \"tax\", \"economy\", \"medicine\",
                \"migration\", \"environment\", or \"mortality\". Accepts a single
                string or a list/tuple of strings to query multiple types at once.
                Defaults to \"population\".
            level (str, optional): Administrative level. \"adm1\" for province-level or
                \"adm2\" for municipal-level. Defaults to \"adm2\".
            adm2_type (str, optional): Which municipal code type to keep before
                returning adm2 results or aggregating to adm1. \"all\" keeps the
                data as queried, \"atn\" keeps autonomous/basic local government
                rows, and \"non\" keeps non-autonomous rows where available. For
                weighted aggregation with \"atn\", autonomous/basic local government
                rate rows are recalculated from their non-autonomous component rows
                using the supplied weights before being returned or aggregated to
                adm1. Defaults to \"all\".
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
                result. If True, returns a GeoDataFrame. Defaults to False.
            **agg_kwargs: Additional arguments passed to the aggregator function
                (e.g., when using custom aggregation functions).

        Returns:
            pd.DataFrame or gpd.GeoDataFrame: A data frame containing census data for
                the specified codes and year in wide format. If geometry=True, returns
                a GeoDataFrame with spatial boundaries included.

        Raises:
            ValueError: If level is not 'adm1' or 'adm2', if adm2_type is not 'all',
                'atn', or 'non', if mixed types are provided in codes, if weighted
                adm2-level computation is requested without adm2_type='atn', or if
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
        """

        if level not in ("adm2", "adm1"):
            raise ValueError("level must be 'adm2' or 'adm1'")

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
        else:
            raise ValueError("'codes' must be a list of integers or strings.")

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
            # Collapses raw duplicate (year, type, adm1, adm2, class1, class2, unit) rows,
            # which do occur in the bundled data. Always sums rather than reusing the
            # user-supplied 'aggregator', since that may require a 'weights' kwarg meant
            # for the level="adm1"/weighted adm2 aggregation stages below, not this reshape.
            out = dfe.pivot_table(
                index=index_cols,
                columns="__colname__",
                values="value",
                aggfunc=np.sum,
            ).reset_index()
            # Clean column names
            out.columns = [str(c).lower().replace("_na", "") for c in out.columns]
        else:
            out = dfe
            out.columns = [str(c).lower().replace("_na", "") for c in out.columns]

        # Non-weighted adm2_type filtering (weighted 'atn' is handled via
        # weighted collapsing below, since it recalculates rather than drops rows)
        if adm2_type == "non" or (adm2_type == "atn" and not has_weighting):
            out = self.detect_adm2_type(out, mode=adm2_type)

        # Weighted adm2-level recalculation: fold non-autonomous rows into their
        # autonomous/basic local government parent using weighted aggregation
        if level == "adm2" and has_weighting:
            out = self._apply_weighted_adm2(
                out, years, types, codes, weight_type, weight_column, aggregator, agg_kwargs
            )

        # If level is adm1, aggregate adm2 to adm1
        if level == "adm1":
            if has_weighting:
                out = self._aggregate_adm1_weighted(
                    out, years, types, codes, adm2_type, weight_type, weight_column,
                    aggregator, agg_kwargs
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
            geo_merge_col = f"{level}_code"
            frames = []
            districts = None
            for yr in years:
                districts = self.load_districts(yr)
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

    def _collapse_weighted_adm2_to_atn(self, df, weight_df, weight_column, aggregator, agg_kwargs):
        """
        Recalculate autonomous/basic local government adm2 rows from their
        non-autonomous component rows using weighted aggregation.

        Rows whose adm2_code is already autonomous (or has no non-autonomous
        children) are kept as-is. Rows whose adm2_code is non-autonomous and
        whose parent (first 4 digits + "0") is present among the autonomous
        rows are folded into that parent using ``aggregator(values, weights=w,
        **agg_kwargs)`` for every value column, and the parent's weight column
        is recomputed as the sum of the children's weights.

        Returns a tuple of (collapsed data, collapsed weights) where the
        latter is a two-column (adm2_code, weight_column) frame.
        """
        adm2_code = "adm2_code"
        exclude = {"year", "adm1", "adm1_code", "adm2", "adm2_code", "type", weight_column}
        value_columns = [c for c in df.columns if c not in exclude]

        atn_df = self.detect_adm2_type(df, mode="atn").reset_index(drop=True)
        atn_weight_df = self.detect_adm2_type(weight_df, mode="atn").reset_index(drop=True)
        atn_df[adm2_code] = atn_df[adm2_code].astype(str)
        atn_weight_df[adm2_code] = atn_weight_df[adm2_code].astype(str)

        code_chr = df[adm2_code].astype(str)
        parent_code = code_chr.str[:4] + "0"
        nonauto = code_chr.str[-1] != "0"
        parent_has_atn = parent_code.isin(atn_df[adm2_code])
        nonauto_df = df.loc[(nonauto & parent_has_atn).to_numpy()].copy()

        if nonauto_df.empty:
            return atn_df, atn_weight_df[[adm2_code, weight_column]].copy()

        weight_values = weight_df[[adm2_code, weight_column]].copy()
        weight_values[adm2_code] = weight_values[adm2_code].astype(str)
        weight_values = weight_values.rename(columns={weight_column: "_aggregation_weight"})
        nonauto_df[adm2_code] = nonauto_df[adm2_code].astype(str)
        nonauto_df = nonauto_df.merge(weight_values, on=adm2_code, how="left")
        nonauto_df["_parent_adm2_code"] = nonauto_df[adm2_code].str[:4] + "0"

        for parent, group in nonauto_df.groupby("_parent_adm2_code"):
            idx = atn_df.index[atn_df[adm2_code] == parent]
            if len(idx) == 0:
                continue
            i = idx[0]
            w = group["_aggregation_weight"].to_numpy()
            for column in value_columns:
                atn_df.loc[i, column] = self._call_weighted_aggregator(
                    aggregator, group[column].to_numpy(), w, agg_kwargs
                )

        weight_code_chr = weight_df[adm2_code].astype(str)
        weight_parent_code = weight_code_chr.str[:4] + "0"
        weight_nonauto = weight_code_chr.str[-1] != "0"
        weight_parent_has_atn = weight_parent_code.isin(atn_weight_df[adm2_code])
        nonauto_weight_df = weight_df.loc[(weight_nonauto & weight_parent_has_atn).to_numpy()].copy()

        collapsed_weights = atn_weight_df[[adm2_code, weight_column]].copy()
        if not nonauto_weight_df.empty:
            nonauto_weight_df[adm2_code] = nonauto_weight_df[adm2_code].astype(str)
            nonauto_weight_df["_parent_adm2_code"] = nonauto_weight_df[adm2_code].str[:4] + "0"
            sums = nonauto_weight_df.groupby("_parent_adm2_code")[weight_column].sum(min_count=1)
            codes_str = collapsed_weights[adm2_code]
            mask = codes_str.isin(sums.index)
            collapsed_weights.loc[mask, weight_column] = codes_str[mask].map(sums).to_numpy()

        return atn_df, collapsed_weights

    def _apply_weighted_adm2(
        self, out, years, types, codes, weight_type, weight_column, aggregator, agg_kwargs
    ):
        """Recalculate adm2_type='atn' rows for a weighted adm2-level query."""
        weight_pool = self._resolve_weight_pool(
            out, years, codes, types, weight_type, weight_column, adm2_type="all"
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
                sub, w_sub, weight_column, aggregator, agg_kwargs
            )
            if weight_column in collapsed_data.columns:
                collapsed_data = collapsed_data.drop(columns=[weight_column])
            collapsed_data = collapsed_data.merge(collapsed_weights, on="adm2_code", how="left")
            frames.append(collapsed_data)
        return pd.concat(frames, ignore_index=True) if frames else out

    def _aggregate_adm1_weighted(
        self, out, years, types, codes, adm2_type, weight_type, weight_column,
        aggregator, agg_kwargs
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
                        sub, w_sub, weight_column, aggregator, agg_kwargs
                    )
                else:
                    sub_data = sub
                    weight_values = w_sub[["adm2_code", weight_column]].copy()
            else:
                if weight_column not in sub.columns:
                    raise KeyError(f"Weight column '{weight_column}' was not found in the data.")
                if adm2_type == "atn":
                    sub_data, weight_values = self._collapse_weighted_adm2_to_atn(
                        sub, sub, weight_column, aggregator, agg_kwargs
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
                row = dict(zip(group_cols, gkey_vals))
                for col in value_cols:
                    row[col] = self._call_weighted_aggregator(
                        aggregator, g[col].to_numpy(), w, agg_kwargs
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
            year (int | None): Optional year filter.
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

        code_series = dfe[adm2_code].astype(str)
        adm2_nonauto_flag = code_series.str[-1] != "0"

        if adm2_nonauto_flag.any():
            adm2_nonauto = pd.Series(code_series.loc[adm2_nonauto_flag].unique())
            adm2_nonauto_upper = adm2_nonauto.str[:4]
            adm2_nonauto_upper_str = adm2_nonauto_upper + "0"

            adm2_auto = dfe.loc[code_series.isin(adm2_nonauto_upper_str)]
            adm2_auto_upper = pd.Series(adm2_auto[adm2_code].astype(str).unique()).str[:4]
            adm2_auto_upper_str = adm2_auto_upper + "0"

            if mode == "atn":
                return dfe.loc[~adm2_nonauto_flag].copy()

            auto_nonauto_cond = adm2_nonauto_upper.isin(adm2_auto_upper)
            if not auto_nonauto_cond.all():
                warnings.warn(
                    "Inconsistent codes: Some non-autonomous Gu codes do not have "
                    "corresponding upper level administrative codes.",
                    UserWarning,
                    stacklevel=2,
                )
            return dfe.loc[~code_series.isin(adm2_auto_upper_str)].copy()

        return dfe
