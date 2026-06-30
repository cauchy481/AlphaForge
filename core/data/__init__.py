"""数据引擎"""
from pathlib import Path
from typing import  List, Optional
import pandas as pd
import tushare as ts


class DataLoader:
    """优先读本地缓存，不存在时通过 Tushare 下载"""

    def __init__(
        self,
        token: str,
        cache_dir: str = "./data_cache",
    ):
        ts.set_token(token)
        self.pro = ts.pro_api()
        self.cache_dir = Path(cache_dir)
        self._ensure_dirs()

    def _ensure_dirs(self):
        for sub in ["daily", "daily_basic", "fundamental", "industry", "calendar", "index"]:
            (self.cache_dir / sub).mkdir(parents=True, exist_ok=True)

    # 交易日历

    def get_trade_calendar(
        self,
        start_date: str = "20100101",
        end_date: str = "20991231",
        force_update: bool = False,
    ) -> List[str]:
        """获取交易日列表，自动缓存"""
        cal_path = self.cache_dir / "calendar" / "trade_dates.csv"
        if cal_path.exists() and not force_update:
            df = pd.read_csv(cal_path, dtype=str)
            dates = df["cal_date"].tolist()
        else:
            df = self.pro.trade_cal(
                exchange="SSE",
                start_date="20100101",
                end_date="20991231",
                is_open="1",
            )
            dates = sorted(df["cal_date"].tolist())
            pd.DataFrame({"cal_date": dates}).to_csv(cal_path, index=False)

     
        dates = [d for d in dates if start_date <= d <= end_date]
        return dates

    # 股票列表 

    def get_stock_list(
        self,
        list_status: str = "L",
        fields: str = "ts_code,symbol,name,area,industry,list_date",
        force_update: bool = False,
    ) -> pd.DataFrame:
        """获取A股股票列表，自动缓存"""
        cache_path = self.cache_dir / "stock_list.csv"
        if cache_path.exists() and not force_update:
            return pd.read_csv(cache_path, dtype=str)
        df = self.pro.stock_basic(
            exchange="",
            list_status=list_status,
            fields=fields,
        )
        df.to_csv(cache_path, index=False)
        return df

    # 日线行情

    def download_daily_batch(
        self,
        start_date: str,
        end_date: str,
        force_update: bool = False,
    ) -> None:
        """批量下载日线数据到本地缓存目录，按日期分文件存储"""
        daily_dir = self.cache_dir / "daily"
        dates = self.get_trade_calendar(start_date, end_date)

        for dt in dates:
            file_path = daily_dir / f"{dt}.csv"
            if file_path.exists() and not force_update:
                continue
            try:
                df = self.pro.daily(trade_date=dt)
                if not df.empty:
                    df.to_csv(file_path, index=False)
            except Exception:
                continue

    def download_daily_basic(
        self,
        start_date: str,
        end_date: str,
        force_update: bool = False,
    ) -> None:
        """批量下载每日基本面指标（PE/PB/市值/ROE等），价值和质量因子依赖此数据"""
        basic_dir = self.cache_dir / "daily_basic"
        dates = self.get_trade_calendar(start_date, end_date)

        for dt in dates:
            file_path = basic_dir / f"{dt}.csv"
            if file_path.exists() and not force_update:
                continue
            try:
                df = self.pro.daily_basic(
                    trade_date=dt,
                    fields="ts_code,pe_ttm,pb,ps_ttm,dv_ttm,total_mv,circ_mv",
                )
                if not df.empty:
                    df.to_csv(file_path, index=False)
            except Exception:
                continue

    def download_index_daily(
        self,
        index_codes: Optional[List[str]] = None,
        start_date: str = "20100101",
        end_date: str = "20991231",
        force_update: bool = False,
    ) -> None:
        """下载指数日线数据（默认下载沪深300、中证500、上证指数）"""
        if index_codes is None:
            index_codes = ["000300.SH", "000905.SH", "000001.SH"]
        index_dir = self.cache_dir / "index"

        for code in index_codes:
            safe_code = code.replace(".", "_")
            file_path = index_dir / f"{safe_code}.csv"
            if file_path.exists() and not force_update:
                continue
            try:
                df = self.pro.index_daily(
                    ts_code=code,
                    start_date=start_date,
                    end_date=end_date,
                )
                if not df.empty:
                    df = df.sort_values("trade_date").reset_index(drop=True)
                    df.to_csv(file_path, index=False)
            except Exception:
                continue

    def get_daily_data(self, date: str) -> pd.DataFrame:
        """读取单日行情数据"""
        raw_path = self.cache_dir / "daily" / f"{date}.csv"
        if not raw_path.exists():
            return pd.DataFrame()

        df = pd.read_csv(raw_path)

        rename_map = {}
        if "ts_code" in df.columns and "code" not in df.columns:
            rename_map["ts_code"] = "code"
        if "vol" in df.columns and "volume" not in df.columns:
            rename_map["vol"] = "volume"
        if rename_map:
            df = df.rename(columns=rename_map)

        # 合并 daily_basic
        basic_path = self.cache_dir / "daily_basic" / f"{date}.csv"
        if basic_path.exists():
            basic = pd.read_csv(basic_path)
            key = "ts_code" if "ts_code" in basic.columns else "code"
            if key == "ts_code" and "ts_code" not in df.columns:
                df["ts_code"] = df["code"].apply(
                    lambda x: x + (".SH" if x.startswith("6") else ".SZ")
                    if isinstance(x, str) and not x.endswith((".SH", ".SZ", ".BJ"))
                    else x
                )
            merge_cols = [key] + [c for c in ["pe_ttm", "pb", "roe"] if c in basic.columns]
            if merge_cols:
                df = df.merge(basic[merge_cols], on=key, how="left")

        df["date"] = date
        return df

    def get_daily_data_range(
        self,
        dates: List[str],
        fields: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """批量读取多日行情，返回拼接后的 DataFrame"""
        frames = []
        for dt in dates:
            df = self.get_daily_data(dt)
            if not df.empty:
                if fields:
                    available = [f for f in fields if f in df.columns]
                    df = df[available]
                frames.append(df)
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True)

    def get_index_daily(self, index_code: str = "000300.SH") -> pd.DataFrame:
        """读取指数日线数据，含 trade_date 和 pct_chg 列"""
        safe_code = index_code.replace(".", "_")
        file_path = self.cache_dir / "index" / f"{safe_code}.csv"
        if not file_path.exists():
            return pd.DataFrame()
        return pd.read_csv(file_path, dtype={"trade_date": str})

    def get_limit_status(self, date: str) -> pd.DataFrame:
        """
        获取指定日期的涨跌停状态。
        返回 DataFrame(index=code, columns=['is_limit_up', 'is_limit_down'])。
        涨停判断：pct_chg >= 9.8%（普通股）；ST股阈值为 4.8%。
        """
        df = self.get_daily_data(date)
        if df.empty:
            return pd.DataFrame()
        if "code" not in df.columns and "ts_code" in df.columns:
            df["code"] = df["ts_code"]
        df = df.set_index("code")
        result = pd.DataFrame(index=df.index)
        if "pct_chg" not in df.columns:
            return result
        pct = df["pct_chg"].astype(float)
        # ST股涨跌幅限制±5%，普通股±10%；用 name 列区分
        if "name" in df.columns:
            is_st = df["name"].str.contains("ST|\\*ST", na=False)
            up_thresh = is_st.map({True: 4.8, False: 9.8})
            down_thresh = is_st.map({True: -4.8, False: -9.8})
        else:
            up_thresh = 9.8
            down_thresh = -9.8
        result["is_limit_up"] = pct >= up_thresh
        result["is_limit_down"] = pct <= down_thresh
        return result

    def get_daily_returns(self, date: str) -> pd.DataFrame:
        """返回指定日期的行情数据（含 pct_chg 当日涨跌幅）。
        注意：这不是 forward return；如需 T+1 收益，请直接读取下一交易日数据。"""
        df = self.get_daily_data(date)
        if df.empty:
            return df
        return df

    # 基本面数据 

    def download_fundamental(
        self,
        ts_code: str,
        start_date: str = "20220101",
        end_date: str = "20260601",
    ) -> pd.DataFrame:
        """下载单只股票的基本面数据"""
        cache_path = self.cache_dir / "fundamental" / f"{ts_code}.csv"
        try:
            df = self.pro.income(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
            )
            if not df.empty:
                df.to_csv(cache_path, index=False)
            return df
        except Exception:
            if cache_path.exists():
                return pd.read_csv(cache_path, dtype=str)
            return pd.DataFrame()

    def get_fundamental(self, ts_code: str) -> pd.DataFrame:
        """读取缓存的基本面数据"""
        cache_path = self.cache_dir / "fundamental" / f"{ts_code}.csv"
        if cache_path.exists():
            return pd.read_csv(cache_path, dtype=str)
        return pd.DataFrame()

    # 行业分类

    def get_industry(self, date: str) -> pd.Series:
        """获取某日的行业分类"""
        # 简化实现：从 stock_list 获取行业字段
        stocks = self.get_stock_list()
        if stocks.empty:
            return pd.Series(dtype=str)
        series = stocks.set_index("ts_code")["industry"]
        series.name = "industry"
        return series


    def get_close_price(
        self,
        date: str,
        ts_codes: Optional[List[str]] = None,
    ) -> pd.Series:
        """获取某日所有股票（或指定股票列表）的收盘价"""
        df = self.get_daily_data(date)
        if df.empty:
            return pd.Series(dtype=float)
        if "code" not in df.columns and "ts_code" in df.columns:
            df["code"] = df["ts_code"]
        df = df.set_index("code")
        series = df["close"].astype(float)
        if ts_codes:
            series = series[series.index.isin(ts_codes)]
        return series

    def get_volume(self, date: str) -> pd.Series:
        """获取某日所有股票的成交量"""
        df = self.get_daily_data(date)
        if df.empty:
            return pd.Series(dtype=float)
        if "code" not in df.columns and "ts_code" in df.columns:
            df["code"] = df["ts_code"]
        return df.set_index("code")["volume"].astype(float)

    def get_amount(self, date: str) -> pd.Series:
        """获取某日所有股票的成交额"""
        df = self.get_daily_data(date)
        if df.empty:
            return pd.Series(dtype=float)
        if "code" not in df.columns and "ts_code" in df.columns:
            df["code"] = df["ts_code"]
        return df.set_index("code")["amount"].astype(float)
