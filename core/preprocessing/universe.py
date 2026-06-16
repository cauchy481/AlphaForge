"""股票池过滤"""
import pandas as pd


class UniverseFilter:

    def __init__(
        self,
        min_list_days: int = 60,
        min_daily_amount: float = 5_000_000,
        exclude_st: bool = True,
    ):
        self.min_list_days = min_list_days
        self.min_daily_amount = min_daily_amount
        self.exclude_st = exclude_st

    def filter(self, df: pd.DataFrame, date: str, stock_list: pd.DataFrame = None) -> pd.DataFrame:
        """
        df: 包含 code 列的 DataFrame
        stock_list: 股票列表（含 list_date, name 等字段）
        返回过滤后的 DataFrame
        """
        if df.empty:
            return df

        mask = pd.Series(True, index=df.index)

        # 剔除 ST / *ST
        if self.exclude_st and "name" in df.columns:
            st_mask = ~df["name"].str.contains("ST|\\*ST", na=False)
            mask = mask & st_mask.values

        # 剔除上市不足 min_list_days 的次新股
        if stock_list is not None and "list_date" in stock_list.columns:
            stocks = stock_list.set_index("ts_code")
            if "code" in df.columns:
                common = df["code"].isin(stocks.index)
                if common.any():
                    list_dates = stocks.loc[df.loc[common, "code"], "list_date"]
                    list_days = (pd.Timestamp(date) - pd.to_datetime(list_dates.values)).days
                    mask[common] = mask[common] & (list_days >= self.min_list_days)

        # 剔除流动性不足的股票
        if "amount" in df.columns:
            amount = df["amount"].astype(float)
            mask = mask & (amount >= self.min_daily_amount)

        return df.loc[mask]
