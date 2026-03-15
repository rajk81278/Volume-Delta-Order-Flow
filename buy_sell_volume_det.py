

from fyers_apiv3 import fyersModel
import pandas as pd
import datetime as dt
import time
import pandas_ta as ta
import numpy as np
import datetime


# ---------------- LOGIN ---------------- #

with open('access.txt','r') as a:
    access_token = a.read().strip()

client_id = 'XZ5S16H9QE-100'

fyers = fyersModel.FyersModel(
    client_id=client_id,
    is_async=False,
    token=access_token,
    log_path=""
)

# ---------------- SAFE FETCH FUNCTION ---------------- #

def fetch_chunk(ticker, interval, start_date, end_date):

    data = {
        "symbol": ticker,
        "resolution": interval,
        "date_format": "1",
        "range_from": start_date.strftime("%Y-%m-%d"),
        "range_to": end_date.strftime("%Y-%m-%d"),
        "cont_flag": "1"
    }

    response = fyers.history(data)

    # 🔥 FULL SAFETY CHECK
    if not isinstance(response, dict):
        print("Invalid API response")
        return pd.DataFrame()

    if response.get("s") != "ok":
        print("API returned error:", response)
        return pd.DataFrame()

    candles = response.get("candles", [])

    if len(candles) == 0:
        print(f"No data: {start_date} to {end_date}")
        return pd.DataFrame()

    df = pd.DataFrame(candles)

    if df.empty or df.shape[1] < 6:
        print("Unexpected data format")
        return pd.DataFrame()

    df.columns = ['date','open','high','low','close','volume']

    df['date'] = pd.to_datetime(df['date'], unit='s')
    df['date'] = df['date'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
    df['date'] = df['date'].dt.tz_localize(None)

    df.set_index('date', inplace=True)

    return df


# ---------------- SETTINGS ---------------- #

ticker = "NSE:RELIANCE-EQ"
interval = "1"
day = 20

end_date = dt.date.today()
start_date = end_date - dt.timedelta(days=day)

all_data = pd.DataFrame()
current_start = start_date

chunk_days = 20   # intraday safe limit

print(f"\nDownloading {day} years of 60-min data...\n")

# ---------------- LOOP ---------------- #

while current_start < end_date:

    current_end = current_start + dt.timedelta(days=chunk_days)

    if current_end > end_date:
        current_end = end_date

    print(f"Downloading: {current_start} to {current_end}")

    df = fetch_chunk(
        ticker,
        interval,
        current_start,
        current_end
    )

    if not df.empty:
        all_data = pd.concat([all_data, df])

    current_start = current_end + dt.timedelta(days=1)

    time.sleep(0.5)


# ---------------- FINAL CLEAN ---------------- #

if not all_data.empty:

    all_data = all_data[~all_data.index.duplicated(keep='first')]
    all_data.sort_index(inplace=True)

    # filename = f"NIFTY_{years}Y_{interval}min.csv"
    # all_data.to_csv(filename)

    # print("\n✅ Download Completed Successfully")
    # print(f"Saved as: {filename}")
    print(all_data.tail())

else:
    print("\n❌ No data downloaded.")


for i, raw in all_data.iterrows():


    if raw['open']>raw['close']:
        all_data.loc[i,'buy_volume']=raw['volume']
        all_data.loc[i,'sell_volume']=0
    else : 
        all_data.loc[i,'buy_volume']=0
        all_data.loc[i,'sell_volume']=raw['volume']

for i, raw in all_data.iterrows():
            
    if raw['buy_volume']>0:
        all_data.loc[i,'delta']=raw['buy_volume']
    elif raw['sell_volume']>0:
        all_data.loc[i,'delta']=-raw['sell_volume']

all_data['cum_del']=all_data['delta'].cumsum()



all_data['price_change'] = all_data['close'].diff()
all_data['delta_change'] = all_data['delta'].diff()

all_data['divergence'] = ''

all_data.loc[
    (all_data['price_change'] > 0) & (all_data['delta_change'] < 0),
    'divergence'
] = 'Bearish Divergence'

all_data.loc[
    (all_data['price_change'] < 0) & (all_data['delta_change'] > 0),
    'divergence'
] = 'Bullish Divergence'


print(all_data)

import mplfinance as mpf
import numpy as np

# -------- PREPARE DATA --------

plot_data = all_data.tail(300).copy()

# VWAP calculation
plot_data['vwap'] = (
    (plot_data['volume'] * (plot_data['high'] + plot_data['low'] + plot_data['close']) / 3).cumsum()
    / plot_data['volume'].cumsum()
)

# -------- CREATE MARKER COLUMNS --------

plot_data['bearish_marker'] = np.where(
    plot_data['divergence'] == 'Bearish Divergence',
    plot_data['close'],
    np.nan
)

plot_data['bullish_marker'] = np.where(
    plot_data['divergence'] == 'Bullish Divergence',
    plot_data['close'],
    np.nan
)

# -------- ADDITIONAL PLOTS --------

apds = []

# VWAP line
apds.append(
    mpf.make_addplot(
        plot_data['vwap'],
        color='blue',
        width=1
    )
)

# Bearish divergence marker
apds.append(
    mpf.make_addplot(
        plot_data['bearish_marker'],
        type='scatter',
        marker='v',
        markersize=120,
        color='red'
    )
)

# Bullish divergence marker
apds.append(
    mpf.make_addplot(
        plot_data['bullish_marker'],
        type='scatter',
        marker='^',
        markersize=120,
        color='green'
    )
)

# Cumulative Delta panel
apds.append(
    mpf.make_addplot(
        plot_data['cum_del'],
        panel=2,
        color='purple',
        ylabel='Cum Delta'
    )
)

# -------- PLOT CHART --------

mpf.plot(
    plot_data,
    type='candle',
    style='charles',
    addplot=apds,
    volume=True,
    panel_ratios=(3,1,1),
    figsize=(14,8),
    title='Order Flow Analysis: Price vs Cumulative Delta',
    savefig='quant_orderflow_chart.png'
)