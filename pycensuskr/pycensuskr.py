import pandas as pd
import geopandas as gpd
import os
import re
import numpy as np
"""
Main module of pycensuskr.

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

    def load_data(self, year: int):
        """
        Get the dataframe data.

        Returns:
            str: A message indicating boundary retrieval
        """
        location = os.path.dirname(os.path.realpath(__file__))
        file_name = os.path.join(location, "data", f"censuskor.csv")
        df = pd.read_csv(file_name)
        dfe = df.loc[df['year'] == year].copy()
        return dfe
    
    def load_districts(self, year: int):
        """
        Load district data.

        Returns:
            str: A message indicating boundary data loading
        """
        name_lyr = f"adm2_{year}"

        location = os.path.dirname(os.path.realpath(__file__))
        path_bound = os.path.join(location, "data", "boundaries.gpkg")
        districts = gpd.read_file(path_bound, layer = name_lyr)
        return districts
        

    def anycensus(
        self,
        year: int = 2020,
        codes=None,
        type: str = "population",
        level: str = "adm2",
        aggregator=None,
        **agg_kwargs,
    ):
        """
        Python equivalent of the R anycensus() using pandas/geopandas.

        Parameters:
            year (int): Census year to query.
            codes (list|None): Region codes or names (adm1/adm2). If None, uses all.
            type (str): One of ["population","housing","tax","mortality","economy"].
            level (str): "adm2" or "adm1".
            aggregator (callable|None): Aggregation function (default: numpy.sum).
            **agg_kwargs: Extra kwargs passed to the aggregator where applicable.

        Returns:
            pd.DataFrame: Wide-format census table.
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

        return out


    def create_crosswalkboundary(self, year1: int, year2: int):
        """
        Create the crosswalk boundaries.

        Parameters:
            year1 (int): The first year for crosswalk
            year2 (int): The second year for crosswalk

        Returns:
            gpd.GeoDataFrame: Crosswalk boundaries
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
        Unify the census boundaries.

        Returns:
            gpd.GeoDataFrame 
        """
        raise NotImplementedError
        # return "Census data unified."
    



