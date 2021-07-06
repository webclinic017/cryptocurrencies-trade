import sys
import pandas as pd
from datetime import datetime

from binance_utils import get_twm
from trade_utils import get_historical_data, resample_data, process_candle

symbol = 'BTCUSDT'
# valid intervals - 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
interval = '1h'

df = pd.DataFrame()

def handle_socket_message(msg):
    #print(f"message type: {msg['e']}")
    #print(msg)

    global df

    candle = msg['k']
    timestamp = candle['t'] / 1000
    timestamp = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

    is_candle_closed = candle['x']

    if is_candle_closed:
        new_row = {
            'OpenTime':timestamp, 
            'OpenPrice':candle['o'], 
            'HighPrice':candle['h'], 
            'LowPrice':candle['l'], 
            'ClosePrice':candle['c'], 
            'Volume':candle['v']}
        
        if df.size == 0:
            df = get_historical_data()
            df = resample_data(df, '1H')
        
        #print(df.tail())
        #print(candle)

        #process data
        df = process_candle(df, new_row)

def main():
    twm = get_twm()
    twm.start()

    twm.start_kline_socket(callback=handle_socket_message, symbol=symbol, interval=interval)
    
    while 1:
        selection = input('Your selection? (h for help) ')    #python 3.x, for 2.x use raw_input
        
        if len(selection) > 1:
            print('Enter one character only.')
        elif selection == 'h':
            print('Select only one character option from available list:')
            print('\n\t h : help')
            print('\n\t e : exit')
            print('\n\t p : print total stored candles')
        elif selection == 'e':
            print('Exiting the program and stopping all processes.')
            # close connection
            twm.stop()
            sys.exit('Finished and exiting.')
        elif selection == 'p':
            print(df.tail())
        else:
            print('Unknown option.')    

if __name__ == "__main__":
    main()
