"""Helper functions for economic correlation visualization."""

import os
import pickle
import urllib.request

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
import pandas_datareader.data as web
from datetime import datetime, timedelta

# Default date range for data fetching
DEFAULT_START_DATE = datetime(1960, 1, 1)
DEFAULT_CACHE_DIR = "data_cache"


def load_or_download(cache_file, download_func, description, cache_dir=DEFAULT_CACHE_DIR):
    """Load from cache if exists, otherwise download and cache."""
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, cache_file)
    if os.path.exists(cache_path):
        print(f"  Loading {description} from cache...")
        with open(cache_path, 'rb') as f:
            return pickle.load(f)
    else:
        print(f"  Downloading {description}...")
        data = download_func()
        with open(cache_path, 'wb') as f:
            pickle.dump(data, f)
        return data


def get_recession_periods(df):
    """Find contiguous recession periods for shading."""
    if 'Recession' not in df.columns:
        return []

    rec = df[df['Recession'] == 1]
    if len(rec) == 0:
        return []

    periods = []
    rec_dates = rec.index.to_series()
    gaps = rec_dates.diff() > pd.Timedelta(days=45)
    groups = gaps.cumsum()

    for group_id in groups.unique():
        group_dates = rec_dates[groups == group_id]
        periods.append((group_dates.iloc[0], group_dates.iloc[-1]))

    return periods


def get_inversion_periods(df, spread_col='Yield Spread'):
    """Find contiguous yield curve inversion periods."""
    inverted = df[df[spread_col] < 0]
    if len(inverted) == 0:
        return []

    periods = []
    inv_dates = inverted.index.to_series()
    gaps = inv_dates.diff() > pd.Timedelta(days=45)
    groups = gaps.cumsum()

    for group_id in groups.unique():
        group_dates = inv_dates[groups == group_id]
        periods.append((group_dates.iloc[0], group_dates.iloc[-1]))

    return periods


def load_nasdaq_data(start_date=None, end_date=None, cache_dir=DEFAULT_CACHE_DIR):
    """Load NASDAQ data, downloading if not cached."""
    start_date = start_date or DEFAULT_START_DATE
    end_date = end_date or datetime.now()

    print("Loading NASDAQ data...")
    def download():
        data = yf.download("^IXIC", start=start_date, end=end_date, progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        return data

    nasdaq = load_or_download("nasdaq.pkl", download, "NASDAQ", cache_dir)
    nasdaq_price = nasdaq['Close']
    nasdaq_monthly = nasdaq_price.resample('ME').last()
    nasdaq_pct = nasdaq_monthly.pct_change(periods=6) * 100
    return nasdaq, nasdaq_monthly, nasdaq_pct


def load_sp500_data(start_date=None, end_date=None, cache_dir=DEFAULT_CACHE_DIR):
    """Load S&P 500 data, downloading if not cached."""
    start_date = start_date or DEFAULT_START_DATE
    end_date = end_date or datetime.now()

    print("Loading S&P 500 data...")
    def download():
        data = yf.download("^GSPC", start=start_date, end=end_date, progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        return data

    sp500 = load_or_download("sp500.pkl", download, "S&P 500", cache_dir)
    sp500_price = sp500['Close']
    sp500_monthly = sp500_price.resample('ME').last()
    sp500_pct = sp500_monthly.pct_change(periods=6) * 100
    return sp500, sp500_monthly, sp500_pct


def load_gold_silver_data(start_date=None, end_date=None, cache_dir=DEFAULT_CACHE_DIR):
    """Load Gold and Silver data from World Bank (historical) and Yahoo Finance (recent)."""
    start_date = start_date or DEFAULT_START_DATE
    end_date = end_date or datetime.now()

    print("Loading Gold and Silver data...")
    wb_file = os.path.join(cache_dir, "CMO-Historical-Data-Monthly.xlsx")
    wb_url = "https://thedocs.worldbank.org/en/doc/5d903e848db1d1b83e0ec8f744e55570-0350012021/related/CMO-Historical-Data-Monthly.xlsx"

    # Check old location and move if needed
    if os.path.exists("CMO-Historical-Data-Monthly.xlsx") and not os.path.exists(wb_file):
        os.makedirs(cache_dir, exist_ok=True)
        os.rename("CMO-Historical-Data-Monthly.xlsx", wb_file)

    try:
        # Load World Bank historical data
        if not os.path.exists(wb_file):
            print("  Downloading World Bank data...")
            os.makedirs(cache_dir, exist_ok=True)
            urllib.request.urlretrieve(wb_url, wb_file)
        else:
            print("  Loading World Bank data from cache...")

        wb_data = pd.read_excel(wb_file, sheet_name='Monthly Prices', header=4)
        wb_data = wb_data.iloc[1:]  # Skip the units row
        wb_data['Date'] = pd.to_datetime(wb_data.iloc[:, 0].str.replace('M', '-'), format='%Y-%m') + pd.offsets.MonthEnd(0)
        wb_data = wb_data.set_index('Date')

        wb_gold = pd.to_numeric(wb_data['Gold'], errors='coerce')
        wb_silver = pd.to_numeric(wb_data['Silver'], errors='coerce')
        wb_end_date = wb_gold.dropna().index[-1]
        print(f"  World Bank data: 1960-01 to {wb_end_date.strftime('%Y-%m')}")

        # Get recent data from Yahoo Finance to fill the gap
        print("  Fetching recent Gold/Silver from Yahoo Finance...")

        def download_yf_gold():
            data = yf.download("GC=F", start=wb_end_date, end=end_date, progress=False)
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            return data

        def download_yf_silver():
            data = yf.download("SI=F", start=wb_end_date, end=end_date, progress=False)
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            return data

        yf_gold = load_or_download("yf_gold.pkl", download_yf_gold, "Yahoo Finance Gold", cache_dir)
        yf_silver = load_or_download("yf_silver.pkl", download_yf_silver, "Yahoo Finance Silver", cache_dir)

        # Convert Yahoo Finance to monthly
        yf_gold_monthly = yf_gold['Close'].resample('ME').last()
        yf_silver_monthly = yf_silver['Close'].resample('ME').last()

        # Combine: use World Bank for historical, Yahoo Finance for recent
        gold_monthly = wb_gold.copy()
        silver_monthly = wb_silver.copy()

        for date in yf_gold_monthly.index:
            if date > wb_end_date and pd.notna(yf_gold_monthly[date]):
                gold_monthly[date] = yf_gold_monthly[date]

        for date in yf_silver_monthly.index:
            if date > wb_end_date and pd.notna(yf_silver_monthly[date]):
                silver_monthly[date] = yf_silver_monthly[date]

        gold_monthly = gold_monthly.sort_index()
        silver_monthly = silver_monthly.sort_index()

        gold_pct = gold_monthly.pct_change(periods=6) * 100
        silver_pct = silver_monthly.pct_change(periods=6) * 100

        print(f"  Gold: {gold_monthly.dropna().index[0].strftime('%Y-%m')} to {gold_monthly.dropna().index[-1].strftime('%Y-%m')} ({len(gold_monthly.dropna())} points)")
        print(f"  Silver: {silver_monthly.dropna().index[0].strftime('%Y-%m')} to {silver_monthly.dropna().index[-1].strftime('%Y-%m')} ({len(silver_monthly.dropna())} points)")

        return gold_monthly, gold_pct, silver_monthly, silver_pct

    except Exception as e:
        print(f"Warning: Could not load Gold/Silver data: {e}")
        return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)


def load_yield_data(start_date=None, end_date=None, cache_dir=DEFAULT_CACHE_DIR):
    """Load Treasury yield data from FRED."""
    start_date = start_date or DEFAULT_START_DATE
    end_date = end_date or datetime.now()

    print("Loading yield curve data from FRED...")
    def download():
        series = {'DGS2': '2Y Treasury', 'DGS10': '10Y Treasury', 'DGS3MO': '3M Treasury', 'DGS30': '30Y Treasury'}
        data = {}
        for series_id, name in series.items():
            try:
                df = web.DataReader(series_id, 'fred', start_date, end_date)
                data[name] = df[series_id]
                print(f"    {name}: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
            except Exception as e:
                print(f"    Warning: Could not download {name}: {e}")
        return pd.DataFrame(data)

    yields_df = load_or_download("yields.pkl", download, "Treasury yields", cache_dir)
    yields_df['10Y-2Y Spread'] = yields_df['10Y Treasury'] - yields_df['2Y Treasury']
    yields_df['10Y-3M Spread'] = yields_df['10Y Treasury'] - yields_df['3M Treasury']
    yields_monthly = yields_df.resample('ME').last()
    return yields_df, yields_monthly


def load_recession_data(start_date=None, end_date=None, cache_dir=DEFAULT_CACHE_DIR):
    """Load recession indicator data from FRED."""
    start_date = start_date or DEFAULT_START_DATE
    end_date = end_date or datetime.now()

    print("Loading recession data from FRED...")
    def download():
        return web.DataReader('USREC', 'fred', start_date, end_date)

    try:
        recessions = load_or_download("recessions.pkl", download, "recession indicators", cache_dir)
        recessions_monthly = recessions.resample('ME').max()
        return recessions, recessions_monthly
    except Exception as e:
        print(f"Warning: Could not load recession data: {e}")
        return None, None


def load_all_data(start_date=None, end_date=None, cache_dir=DEFAULT_CACHE_DIR):
    """Load all economic data and combine into a single DataFrame."""
    start_date = start_date or DEFAULT_START_DATE
    end_date = end_date or datetime.now()

    os.makedirs(cache_dir, exist_ok=True)

    # Load all data sources
    nasdaq, nasdaq_monthly, nasdaq_pct = load_nasdaq_data(start_date, end_date, cache_dir)
    sp500, sp500_monthly, sp500_pct = load_sp500_data(start_date, end_date, cache_dir)
    gold_monthly, gold_pct, silver_monthly, silver_pct = load_gold_silver_data(start_date, end_date, cache_dir)
    yields_df, yields_monthly = load_yield_data(start_date, end_date, cache_dir)
    recessions, recessions_monthly = load_recession_data(start_date, end_date, cache_dir)

    # Combine into single DataFrame
    combined = pd.DataFrame({
        'NASDAQ 6M %': nasdaq_pct,
        'S&P 500 6M %': sp500_pct,
        'Yield Spread': yields_monthly['10Y-2Y Spread'],
        'Gold 6M %': gold_pct,
        'Silver 6M %': silver_pct
    })

    # Add recession indicator
    if recessions_monthly is not None:
        combined['Recession'] = recessions_monthly['USREC']
    else:
        combined['Recession'] = 0

    combined = combined.dropna(subset=['NASDAQ 6M %', 'Yield Spread'])

    # Print summary
    print(f"\nData summary:")
    print(f"  NASDAQ: {nasdaq.index[0].strftime('%Y-%m-%d')} to {nasdaq.index[-1].strftime('%Y-%m-%d')} ({len(nasdaq_monthly)} monthly)")
    print(f"  S&P 500: {sp500.index[0].strftime('%Y-%m-%d')} to {sp500.index[-1].strftime('%Y-%m-%d')} ({len(sp500_monthly)} monthly)")
    if len(gold_monthly.dropna()) > 0:
        print(f"  Gold: {gold_monthly.dropna().index[0].strftime('%Y-%m')} to {gold_monthly.dropna().index[-1].strftime('%Y-%m')} ({len(gold_monthly.dropna())} monthly)")
        print(f"  Silver: {silver_monthly.dropna().index[0].strftime('%Y-%m')} to {silver_monthly.dropna().index[-1].strftime('%Y-%m')} ({len(silver_monthly.dropna())} monthly)")
    print(f"  Yields: {yields_df.index[0].strftime('%Y-%m-%d')} to {yields_df.index[-1].strftime('%Y-%m-%d')}")
    print(f"\nCombined data range: {combined.index[0].strftime('%Y-%m-%d')} to {combined.index[-1].strftime('%Y-%m-%d')}")
    print(f"Total data points: {len(combined)} months")

    return combined
