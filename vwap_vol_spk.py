

from fyers_apiv3 import fyersModel
import pandas as pd
import datetime as dt
import time

import nsepython as nse
import pandas_ta as ta

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

# ticker = "NSE:ANGELONE-EQ"
interval = "5"
day = 2

def get_data(ticker, interval, day):
    end_date = dt.date.today()
    start_date = end_date - dt.timedelta(days=day)

    all_data = pd.DataFrame()
    current_start = start_date

    chunk_days = 20   # intraday safe limit

    print(f"\nDownloading {day} day of {interval}-min data...\n")

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

        filename = f"{ticker}_{day}_{interval}.csv"
        # all_data.to_csv(filename)

        print("\n✅ Download Completed Successfully")
        print(f"Saved as: {filename}")
        # print(all_data.tail())

    else:
        print("\n❌ No data downloaded.")

    data= all_data

    return data


# data = get_data(ticker=ticker, interval=interval, years=years)

# print(data)
def symbol_list():
    symbol_list =nse.fnolist()

    l1= []
    for i in symbol_list:
        symbol = f'NSE:{i}-EQ'
        l1.append(symbol)
    return l1
# print(l1)

symbol_list = symbol_list()
print(symbol_list)



# def get_dataframe(symbol_list):

#     signal = pd.DataFrame(columns=['datetime', 'symbol', 'entry_price'])
    
#     for i in symbol_list[3:]:
#         print(i)
#         data = get_data(ticker=i, interval=interval, day=day)
#         data['vwap']= ta.vwap(data['high'], data['low'], data['close'], data['volume'])
#         data['vol_10_sma']= ta.sma(data['volume'], length=10)
#         data['vol_spike']= data['volume']> 2*data['vol_10_sma']
#         data['prev_10_high'] = data['high'].rolling(10).max().shift(1)
#         data['prev_10_low'] = data['low'].rolling(10).min().shift(1)

#         data =data.dropna()
#         data= round(data,2)
#         # print(data)

#         data['buy_signal']= ((data['close']>data['prev_10_high']) & 
#                             (data['close']> data['vwap']) &
#                             (data['vol_spike']))
        
#         data['sell_signal']= ((data['close']<data['prev_10_low']) & 
#                             (data['close']< data['vwap']) &
#                             (data['vol_spike']))
        
#         latest = data.iloc[-2]
#         # print(latest)

#         if latest['buy_signal']:
#             print(f"{i} | BUY | Price: {latest['close']:.2f} | VWAP: {latest['vwap']:.2f}")
#             # signal['date']= latest['date']
#             signal['symbol'] = i
#             signal['entry_price']= latest['close']
           

#         elif latest['sell_signal']:
#             print(f"{i} | SELL | Price: {latest['close']:.2f} | VWAP: {latest['vwap']:.2f}")
#             # signal['date']= latest['date']
#             signal['symbol'] = i
#             signal['entry_price']= latest['close']

#         else:
#             print(f"{i} | No Trade")
        
#     return  signal

#         # print(data)


def get_dataframe(symbol_list):

    signal = pd.DataFrame(columns=[
        'datetime', 'symbol', 'entry_price',
        'sl', 'target', 'risk', 'type'
    ])

    for i in symbol_list[3:]:
        print(i)

        data = get_data(ticker=i, interval=interval, day=day)

        # 🔒 Safety check
        if data.empty or len(data) < 20:
            print(f"{i} | Not enough data")
            continue

        # ---------------- INDICATORS ---------------- #
        data['vwap'] = ta.vwap(data['high'], data['low'], data['close'], data['volume'])
        data['vol_10_sma'] = ta.sma(data['volume'], length=10)
        data['vol_spike'] = data['volume'] > 2 * data['vol_10_sma']
        data['prev_10_high'] = data['high'].rolling(10).max().shift(1)
        data['prev_10_low'] = data['low'].rolling(10).min().shift(1)

        data = data.dropna()
        data = round(data, 2)

        # ---------------- SIGNAL LOGIC ---------------- #
        data['buy_signal'] = (
            (data['close'] > data['prev_10_high']) &
            (data['close'] > data['vwap']) &
            (data['vol_spike'])
        )

        data['sell_signal'] = (
            (data['close'] < data['prev_10_low']) &
            (data['close'] < data['vwap']) &
            (data['vol_spike'])
        )

        if len(data) < 2:
            continue

        latest = data.iloc[-2]

        # ================= BUY ================= #
        if latest['buy_signal']:

            entry = latest['close']
            sl = latest['low']   # 🔥 Candle-based SL
            risk = entry - sl
            target = entry + (2 * risk)   # 🔥 1:2 RR

            print(f"{i} | BUY | Entry: {entry:.2f} | SL: {sl:.2f} | Target: {target:.2f}")

            new_row = {
                'datetime': latest.name,
                'symbol': i,
                'entry_price': entry,
                'sl': sl,
                'target': target,
                'risk': risk,
                'type': 'BUY'
            }

            signal = pd.concat([signal, pd.DataFrame([new_row])], ignore_index=True)

        # ================= SELL ================= #
        elif latest['sell_signal']:

            entry = latest['close']
            sl = latest['high']
            risk = sl - entry
            target = entry - (2 * risk)

            print(f"{i} | SELL | Entry: {entry:.2f} | SL: {sl:.2f} | Target: {target:.2f}")

            new_row = {
                'datetime': latest.name,
                'symbol': i,
                'entry_price': entry,
                'sl': sl,
                'target': target,
                'risk': risk,
                'type': 'SELL'
            }

            signal = pd.concat([signal, pd.DataFrame([new_row])], ignore_index=True)

        else:
            print(f"{i} | No Trade")

    return signal


# ================== MAIN ==================
def main():

    

    while True:

        from datetime import datetime, timedelta

        now = datetime.now()

        wait_sec = (5-(now.minute%5))*60-now.second
        if wait_sec < 0:
            wait_sec += 300

        data = get_dataframe(symbol_list=symbol_list)
        
        print(data)

        print()

        print(f"\nWaiting {wait_sec}s...\n")
        time.sleep(wait_sec)



# ================== RUN ==================
if __name__ == "__main__":
    main()
