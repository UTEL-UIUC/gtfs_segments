import os
from threading import RLock
from typing import Any, Dict, Optional, Union
import pandas as pd
from .utilities import detect_encoding
from .parsers import transforms_dict
View = Dict[str, Dict[str, Any]]


def _read_file(filename: str) -> property:
    def getter(self) -> pd.DataFrame:
        return self.get(filename)

    return property(getter)


class Feed(object):
    def __init__(
        self,
        source: Union[str, "Feed"],
        view: Optional[View] = None,
    ):
        self._view: View = {} if view is None else view
        self._cache: Dict[str, pd.DataFrame] = {}
        self._pathmap: Dict[str, str] = {}
        self._delete_after_reading: bool = False
        self._shared_lock = RLock()
        self._locks: Dict[str, RLock] = {}
        self._transforms_dict = transforms_dict()
        if isinstance(source, self.__class__):
            self._read = source.get
        elif isinstance(source, str) and os.path.isdir(source):
            self._read = self._read_csv
            self._bootstrap(source)
        else:
            raise ValueError("Invalid source")

    def get(self, filename: str) -> pd.DataFrame:
        lock = self._locks.get(filename, self._shared_lock)
        with lock:
            df = self._cache.get(filename)
            if df is None:
                df = self._read(filename)
                df = self._filter(filename, df)
                self._convert_types(filename, df)
                df = df.reset_index(drop=True)
                df = self._transform(filename, df)
                self.set(filename, df)
            return self._cache[filename]

    def set(self, filename: str, df: pd.DataFrame) -> None:
        lock = self._locks.get(filename, self._shared_lock)
        with lock:
            self._cache[filename] = df

    # Required files
    agency = _read_file("agency.txt")
    calendar = _read_file("calendar.txt")
    calendar_dates = _read_file("calendar_dates.txt")
    routes = _read_file("routes.txt")
    trips = _read_file("trips.txt")
    shapes = _read_file("shapes.txt")
    stop_times = _read_file("stop_times.txt")
    stops = _read_file("stops.txt")

    # Optional files
    fare_attributes = _read_file("fare_attributes.txt")
    fare_rules = _read_file("fare_rules.txt")
    feed_info = _read_file("feed_info.txt")
    frequencies = _read_file("frequencies.txt")
    transfers = _read_file("transfers.txt")

    def _bootstrap(self, path: str) -> None:
        # Walk recursively through the directory
        for root, _subdirs, files in os.walk(path):
            for fname in files:
                basename = os.path.basename(fname)
                if basename in self._pathmap:
                    # Verify that the folder does not contain multiple files of the same name.
                    raise ValueError("More than one {} in folder".format(basename))
                # Index paths by their basename.
                self._pathmap[basename] = os.path.join(root, fname)
                # Build a lock for each file to synchronize reads.
                self._locks[basename] = RLock()

    def _read_csv(self, filename: str) -> pd.DataFrame:
        path = self._pathmap.get(filename)

        if path is None or os.path.getsize(path) == 0:
            # The file is missing or empty. Return an empty
            # DataFrame containing any required columns.
            return pd.DataFrame()

        # If the file isn't in the zip, return an empty DataFrame.
        with open(path, "rb") as f:
            encoding = detect_encoding(f)

        df = pd.read_csv(path, dtype=str, encoding=encoding, index_col=False)

        # Strip leading/trailing whitespace from column names
        df.rename(columns=lambda x: x.strip(), inplace=True)

        if not df.empty:
            # Strip leading/trailing whitespace from column values
            for col in df.columns:
                df.loc[:, col] = df[col].str.strip()

        return df

    def _filter(self, filename: str, df: pd.DataFrame) -> pd.DataFrame:
        """Apply view filters"""
        view = self._view.get(filename)
        if view is None:
            return df

        for col, values in view.items():
            # If applicable, filter this dataframe by the given set of values
            if col in df.columns:
                df = df[df[col].isin(set(values))]
        return df

    def _convert_types(self, filename: str, df: pd.DataFrame) -> None:
        """
        Apply type conversions
        """
        if df.empty:
            return

        converters = self._transforms_dict[filename].get("converters", {})
        for col, converter in converters.items():
            if col in df.columns:
                df.loc[:,col] = converter(df.loc[:,col])

    def _transform(self, filename: str, df: pd.DataFrame) -> pd.DataFrame:
        transformations = self._transforms_dict[filename].get("transformations", [])
        if "geometry" not in df.columns:
            for transform in transformations:
                df = transform(df)

        return df
