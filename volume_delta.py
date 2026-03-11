

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
interval = "5"
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


def calculate_volume_delta(add_data):
    all_data['Direction'] = np.where(
        all_data['close'] > all_data['open'], 1,
        np.where(all_data['close'] < all_data['open'], -1, 0)
    )


    all_data['Delta']= all_data['volume']*all_data['Direction']
    # all_data['cum_delta'] = all_data['Delta']

    all_data["CumDelta"] = all_data["Delta"].cumsum()
    all_data['avg_delta']=ta.sma(all_data['Delta'].abs(),length=20)
    all_data['20_d_avg_volume'] = ta.sma(all_data['volume'], length=20)

    # Delta_Ratio = Delta / avg_delta
    all_data['Delta_ratio']=all_data['Delta']/all_data['avg_delta']


    all_data['signal'] = 'Neutral'

    all_data.loc[
        (all_data['Delta'] > 2*all_data['avg_delta']) &
        (all_data['volume'] > all_data['20_d_avg_volume']),
        'signal'
    ] = 'Strong Buy'

    all_data.loc[
        (all_data['Delta'] < -2*all_data['avg_delta']) &
        (all_data['volume'] > all_data['20_d_avg_volume']),
        'signal'
    ] = 'Strong Sell'

    return all_data

df = calculate_volume_delta(all_data)

print(df.tail(20))


