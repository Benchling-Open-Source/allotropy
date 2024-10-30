from pandas import DataFrame


def write_parquet(file_path: str, dataframe: DataFrame) -> None:
    dataframe.to_parquet(file_path, index=False)
