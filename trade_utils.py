import pandas as pd
from binance_utils import update_historical_data
from technical_indicator_utils import sma
from message_utils import telegram_bot_sendtext

def initialize_ohlc_df():
    df = pd.DataFrame(columns=[
        'OpenTime', 
        'OpenPrice', 
        'HighPrice', 
        'LowPrice', 
        'ClosePrice', 
        'Volume'])
    
    df.set_index('OpenTime', inplace=True)

    return df

def get_historical_data(csv_file='BTCUSDT-1m-binance.csv', symbol='BTCUSDT', interval='1m'):
    #csv_file = 'BTCUSDT-1m-binance.csv'
    df = pd.read_csv('data/' + csv_file)
    df['OpenTime'] = pd.to_datetime(df['OpenTime'])
    df.set_index('OpenTime', inplace=True)

    df = update_historical_data(df, symbol, interval)
    df.to_csv('data/' + csv_file)

    return df

def add_row(df, row):
    df.loc[pd.to_datetime(row['OpenTime'])] = [pd.to_numeric(row['OpenPrice']),
        pd.to_numeric(row['HighPrice']),
        pd.to_numeric(row['LowPrice']),
        pd.to_numeric(row['ClosePrice']),
        pd.to_numeric(row['Volume'])]
 
    return df

def resample_data(df, time_resample):
    df_resample = df.copy()
    summaries = {'OpenPrice': 'first', 'HighPrice': 'max', 'LowPrice': 'min', 'ClosePrice': 'last', 'Volume': 'sum'}

    df_resample = df.resample(time_resample).agg(summaries)
    df_resample.dropna(inplace=True)
    # remove incomplete candle
    df_resample = df_resample[:-1]

    return df_resample

def generate_technical_indicators(df):
    df['SMA50'] = sma(df['ClosePrice'], 50)

    return df

def update_signal_by_strategy(df):
    df = generate_technical_indicators(df)

    signal = df[['ClosePrice']].copy()
    signal[df['ClosePrice'] > df['SMA50']] = 1.0
    signal[df['ClosePrice'] <= df['SMA50']] = -1.0
    #TODO update NaN and 0 to last signal 1 or -1
    #signal[signal.isnull()] = 0.0

    df['signal'] = signal

    return df

def process_candle(df, new_row):
    df = add_row(df, new_row)

    # TODO add parameter to trade in different intervals/strategies or add a list of intervals to trade
    # 1h trade
    if df.index.hour[-2] != df.index.hour[-1]:
        df_trade = resample_data(df, '1H')
        df_trade = update_signal_by_strategy(df_trade)

        print(df_trade[['ClosePrice', 'SMA50', 'signal']].tail(1))

        if df_trade['signal'][-2] != df_trade['signal'][-1]:
            if df_trade['signal'][-1] == 1:
                message = '1h Trade: Price cross above SMA 50 -> BUY!'
            else:
                message = '1h Trade: Price cross below SMA 50 -> SELL!'
            
            telegram_bot_sendtext(message)

    # 1D trade
    if df.index.day[-2] != df.index.day[-1]:
        df_trade = resample_data(df, '1D')
        df_trade = update_signal_by_strategy(df_trade)

        if df_trade['signal'][-2] != df_trade['signal'][-1]:
            if df_trade['signal'][-1] == 1:
                message = '1D Trade: Price cross above SMA 50 -> BUY!!!'
            else:
                message = '1D Trade: Price cross below SMA 50 -> SELL!!!'
            
            telegram_bot_sendtext(message)

    return df

def get_data(pair, interval, save=True):
    try:
        df = pd.read_csv('data/' + pair + '-1m-binance-all.csv')
        df['OpenTime'] = pd.to_datetime(df['OpenTime'])
        df.set_index('OpenTime', inplace=True)
    except FileNotFoundError:
        df = initialize_ohlc_df()

    df = update_historical_data(df, pair, '1m')
    
    if save:
        # save all data
        filename = 'data/' + pair + '-1m-binance-all.csv'
        df.to_csv(filename)

        # create data file with data from 2020 until now for share (github)
        df_from_2020 = df['2020-1-1':]
        filename = 'data/' + pair + '-1m-binance.csv'
        df_from_2020.to_csv(filename)
    
    # valid intervals - 1min, 3min, 5min, 15min, 30min, 1H, 2H, 4H, 6H, 8H, 12H, 1D, 3D, 1W, 1M
    # TODO validate input
    if interval == '1min':
        return df
    else:
        summaries = {'OpenPrice': 'first', 'HighPrice': 'max', 'LowPrice': 'min', 'ClosePrice': 'last', 'Volume': 'sum'}
        df = df.resample(interval).agg(summaries)
        df.dropna(inplace=True)
        
        return df
