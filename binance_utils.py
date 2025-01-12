import pandas as pd
import yaml
from datetime import datetime
from binance.client import Client
from binance import ThreadedWebsocketManager
from binance.exceptions import BinanceAPIException, BinanceOrderException
from binance.helpers import round_step_size
from binance.enums import *

""" To read a cfg file
import configparser

# Loading keys from config file
config = configparser.ConfigParser()
config.read_file(open('<path-to-your-config-file>'))
actual_api_key = config.get('BINANCE', 'ACTUAL_API_KEY')
actual_secret_key = config.get('BINANCE', 'ACTUAL_SECRET_KEY')
 """

def get_credentials(test=False):
    with open("config.yml", 'r') as ymlfile:
        cfg = yaml.safe_load(ymlfile)
    
    if test:
        api_key = cfg['api_test_creds']['binance_test_access_code']
        api_secret = cfg['api_test_creds']['binance_test_secret_code']
    else:
        api_key = cfg['api_creds']['binance1_access_code']
        api_secret = cfg['api_creds']['binance1_secret_code']
    
    return api_key, api_secret

def init():
    api_key, api_secret = get_credentials()

    return Client(api_key, api_secret)

def init_test():
    api_key, api_secret = get_credentials(test=True)

    client = Client(api_key, api_secret)
    client.API_URL = 'https://testnet.binance.vision/api'

    return client

def get_last_timestamp_from(df):
    if df.size > 0:
        last_timestamp_from_df = df.index[-1]
        last_timestamp_from_df = int(datetime.timestamp(last_timestamp_from_df))
    else:
        last_timestamp_from_df = 0
    
    return last_timestamp_from_df * 1000

def update_historical_data(client, df, pair, interval):
    last_timestamp_from_df = get_last_timestamp_from(df)

    # get timestamp of earliest date data is available
    timestamp = client._get_earliest_valid_timestamp(pair, interval)

    if last_timestamp_from_df > timestamp:
        timestamp = last_timestamp_from_df

    df_binance = get_crypto_data(client, pair, interval, timestamp)
    # remove incomplete candle
    df_binance = df_binance[:-1]

    if df.size > 0:
        df_binance_before = df_binance[df_binance.index < df.index[0]]
        df_binance_after = df_binance[df_binance.index > df.index[-1]]

        df = pd.concat([df_binance_before, df, df_binance_after])
        df.drop_duplicates(inplace=True)

        return df
    else:
        return df_binance

def get_twm():
    api_key, api_secret = get_credentials()

    return ThreadedWebsocketManager(api_key = api_key, api_secret = api_secret)

def get_crypto_data(client, pair, interval, timestamp):
    # request historical candle (or klines) data
    data = client.get_historical_klines(pair, interval, timestamp, limit=1000)

    df_crypto = pd.DataFrame(data, columns=[
        'OpenTime', 
        'OpenPrice', 
        'HighPrice', 
        'LowPrice', 
        'ClosePrice', 
        'Volume', 
        'CloseTime', 
        'QuoteVolume', 
        'Trades', 
        'TakerBuyBaseVolume', 
        'TakerBuyQuoteVolume', 
        'Ignore'
    ])

    df_crypto['OpenTime'] = pd.to_datetime(df_crypto['OpenTime'], unit='ms')
    df_crypto.set_index('OpenTime', inplace=True)

    df_crypto = df_crypto[[ 
        'OpenPrice', 
        'HighPrice', 
        'LowPrice', 
        'ClosePrice', 
        'Volume']]
    
    df_crypto['OpenPrice'] = df_crypto['OpenPrice'].astype('float')
    df_crypto['HighPrice'] = df_crypto['HighPrice'].astype('float')
    df_crypto['LowPrice'] = df_crypto['LowPrice'].astype('float')
    df_crypto['ClosePrice'] = df_crypto['ClosePrice'].astype('float')
    df_crypto['Volume'] = df_crypto['Volume'].astype('float')

    return df_crypto

""" Some of the helper functions from python-binance api:
    order_limit_buy()
    order_limit_sell()
    order_market_buy()
    order_market_sell()
    order_oco_buy()
    order_oco_sell() """
def create_market_order(client, symbol, side, quantity):
    """ Create a market order in binance.

    Parameters
    - client: binance.client.Client
    - symbol: pair to create order, example: 'BTCUSDT' or 'BTCEUR' or 'ETHBTC' ...
    - side: must be 'BUY' or 'SELL'
    - quantity: quantity to create a order.
                - to BUY: quantity of quote_asset;
                - to SELL: quantity of base_asset. 

    Return: order created
    """
    order = {}

    try:
        if side == 'BUY':
            order = client.order_market_buy(symbol=symbol, quoteOrderQty=quantity)
        elif side == 'SELL':
            order = client.order_market_sell(symbol=symbol, quantity=quantity)
        else:
            # TODO handle wrong side
            print('Wrong side, must be \'BUY\' or \'SELL\'! ' + side)
    except BinanceAPIException as e:
        # error handling
        print(e)
        raise
    
    return order

def create_oco_order(client, symbol, side, quantity, stop_price, price):
    order = {}
    
    if side == 'BUY':
        print('BUY is not implemented yet!')
    elif side == 'SELL':
        """         
        try:
            order = client.create_oco_order(
                symbol=symbol,
                side=side,
                stopLimitTimeInForce=TIME_IN_FORCE_GTC,
                quantity=quantity,
                stopPrice=stop_price,
                stopLimitPrice=stop_price,
                price=price)
        except BinanceAPIException as e:
            # error handling
            print(e)
            raise
        """
        order = 'Create an oco order (quantity: ' + str(quantity) + ', stop: ' + str(stop_price) + ', price: ' + str(price) + ')'
    else:
        # TODO handle wrong side
        print('Wrong side, must be \'BUY\' or \'SELL\'! ' + side)
    
    return order

def cancel_order(client, symbol, order_id):
    """
    try:
        result =  client.cancel_order(symbol=symbol, orderId=order_id)
    except BinanceAPIException as e:
        # error handling
        print(e)
        raise

    return result
    """
    return str(order_id)

def get_asset_balance(client, asset):
    balance = client.get_asset_balance(asset=asset)
    
    if balance is None:
        return float(0.0), float(0.0)

    return float(balance['free']), float(balance['locked'])

def get_trade_info(client, symbol):
    info = client.get_symbol_info(symbol)

    base_asset_precision = info['baseAssetPrecision']
    quote_asset_precision = info['quoteAssetPrecision']

    # filters
    for filter in info['filters']:
        if filter['filterType'] == 'PRICE_FILTER':
            min_price = filter['minPrice']
            max_price = filter['maxPrice']
            tick_size = filter['tickSize']
        elif filter['filterType'] == 'LOT_SIZE':
            base_asset_min_qty = filter['minQty']
            base_asset_max_qty = filter['maxQty']
            base_asset_step_size = filter['stepSize']
        elif filter['filterType'] == 'MIN_NOTIONAL':
            quote_asset_min_value = filter['minNotional']

    return {'base_asset_precision': base_asset_precision, 
            'quote_asset_precision': quote_asset_precision,
            'min_price': min_price,
            'max_price': max_price,
            'tick_size': tick_size,
            'base_asset_min_qty': base_asset_min_qty,
            'base_asset_max_qty': base_asset_max_qty,
            'base_asset_step_size': base_asset_step_size,
            'quote_asset_min_value': quote_asset_min_value,
            'exchange_fee': 0.001}

def get_round_value(value, precision):
    return round_step_size(value, precision)

def get_lastest_price(client, symbol):
    btc_price = client.get_symbol_ticker(symbol=symbol)
    
    return float(btc_price['price'])

def get_open_orders(client, symbol):
    return client.get_open_orders(symbol=symbol)
