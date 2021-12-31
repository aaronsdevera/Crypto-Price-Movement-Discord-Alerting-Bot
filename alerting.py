import os
import sys
import time
import base64
import hmac
import hashlib
import requests
import json
import datetime

#####################################
# Constants
#####################################

# get the input configuration file
INFILE = sys.argv[1]
CONFIG = json.load(open(INFILE,'r'))

# create constants based on the configuration file
API_KEY = CONFIG['key']
API_SECRET = CONFIG['secret']
API_PASSPHRASE = CONFIG['pass']
WEBHOOK_URL = CONFIG['webhook']
WINDOW = CONFIG['time_window']
DELTA = CONFIG['delta']
SYMBOL = CONFIG['symbol']

# these are specific to the KuCoin Futures API.
# in the future, other data sources will need to be managed better here.
MODULE = 'ticker'
BASE_URL = 'https://api-futures.kucoin.com'
ENDPOINT_URI = f'/api/v1/{MODULE}?symbol={SYMBOL}'
TARGET_URL = f'{BASE_URL}{ENDPOINT_URI}'

#####################################
# Functions
#####################################

# windowShift - returns the input array with the first element removed
def arrayShift(arr: list):
    return arr[1:]

# writeLog - writes the input dict to a JSON file in an organized folder
def writeLog(data: dict):
    try:
        os.mkdir('logs')
        os.mkdir(f'logs/{MODULE}')
        os.mkdir(f'logs/{MODULE}/{SYMBOL}')
    except:
        pass
    log_file = f'logs/{MODULE}/{SYMBOL}/{SYMBOL}_{MODULE}_{str(timestamp)}.json'
    open(log_file,'w+').write(json.dumps(data,indent=4))

# sendAlert - takes the input str (msg) and sends to the discord webhook url
def sendAlert(url: str,msg: str):
    headers = {
        'Content-Type': 'application/json'
    }
    data = {
        'content':msg
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))

# generateMessage - takes the input data and generates a string message
def generateMessage(data: dict,pct_change: float):
    ts = data['ts']
    price = data['price']
    size = data['size']
    bid = data['bestBidPrice']
    bidSize = data['bestBidSize']
    ask = data['bestAskPrice']
    askSize = data['bestAskSize']
    symbol = data['symbol']

    dt = datetime.datetime.fromtimestamp(ts/1000000000)
    timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')

    # what if the lower bounds (floor) given our DELTA?
    floor = 1-DELTA
    # what is the upper bounds (ceiling) given our DELTA?
    ceiling = 1+DELTA
    # initialize alert and pct change message
    alert_msg = ''
    change_msg = ''
    # if we're above ceiling, specialize the alert message
    if pct_change > ceiling:
        alert_msg = f':chart_with_upwards_trend: **{SYMBOL} UP MORE THAN {DELTA*100}% in past {WINDOW} seconds**'
        change_msg = f'PCT CHANGE: +{pct_change*100} in past {WINDOW} seconds'
    # if we're below flor, specialize the alert message
    if pct_change < floor:
        alert_msg = f':chart_with_downwards_trend: **{SYMBOL} DOWN MORE THEN {DELTA*100}% in past {WINDOW} seconds**'
        change_msg = f'PCT CHANGE: -{pct_change*100} in past {WINDOW} seconds'

    ticker_msg = f'{timestamp}UTC - {symbol}'
    price_msg = f'LAST ORDER: {price} @ {size} lots'
    bid_msg = f'BID: {bid} @ {bidSize} lots'
    ask_msg = f'ASK: {ask} @ {askSize} lots'
    
    url_msg = f'`https://www.tradingview.com/chart/?symbol={symbol}`'
    msg = f'{alert_msg}\n{ticker_msg}\n{price_msg}\n{bid_msg}\n{ask_msg}\n{url_msg}'
    return msg

#####################################
# KuCoin Authentication
#####################################
# 
# this is super specific to how KuCoin does authentication.
# see https://docs.kucoin.com/futures/#authentication

# required for timestamp header
timestamp = int(time.time() * 1000)
# signature before encryption
str_to_sign = str(timestamp) + 'GET' + ENDPOINT_URI

# required for signature header
generated_signature = base64.b64encode(
    hmac.new(API_SECRET.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest()
)
# required for passphrase header
generated_passphrase = base64.b64encode(
    hmac.new(API_SECRET.encode('utf-8'), API_PASSPHRASE.encode('utf-8'), hashlib.sha256).digest()
)
# set up the headers
headers = {
    "KC-API-SIGN": generated_signature,
    "KC-API-TIMESTAMP": str(timestamp),
    "KC-API-KEY": API_KEY,
    "KC-API-PASSPHRASE": generated_passphrase,
    "KC-API-KEY-VERSION": "2"
}

#####################################
# Detection logic
#####################################
# 
# the major concept here is using the WINDOW
# variable as the amount of data retained in memory
# with which to make any sort of calculation.

# determinePctPriceMovement - given input data, see if our conditions are met
# WINDOW_LIST is a data container of frames
# DELTA is the percentage multiplier we want to detect in a given window.
def determinePctPriceMovement(WINDOW_LIST: list, DELTA: float):
    # get the element at the start of the window
    first_frame = WINDOW_LIST[0]
    # get the element at the end of the window (the most recent addition)
    last_frame = WINDOW_LIST[-1]
    # calculate percentage change
    pct_change = (float(last_frame)-float(first_frame))/first_frame
    # absolute change
    absolute_change = 1-pct_change
    # what if the lower bounds (floor) given our DELTA?
    floor = 1-DELTA
    # what is the upper bounds (ceiling) given our DELTA?
    ceiling = 1+DELTA
    # time to determine if the pct_change is out of bounds
    if absolute_change > ceiling:
        return True,pct_change
    if absolute_change < floor:
        return True,pct_change
    else:
        return False,pct_change


# initialize window data container
WINDOW_LIST = []
# initalize the amount of elements (frames) since last alert fired.
frames_since_last_hit = 0
# initialize the alerting criteria (hit)
hit = False
# initalize the alert message variable
alert_msg = ''


#####################################
# Main runtime 
#####################################
# while running, run forever
# do we wanna live forever, forever 
while True:
    try:
        # get data from KuCoin API
        response = requests.get(TARGET_URL, headers=headers)
        # we want the good stuff
        data = response.json()['data']
        # add newest price data to the window list
        WINDOW_LIST.append(float(data['price']))

        # so there are some conditions we want to check before running detections.
        # first, we actually want a dilated window just in case there were any missed frames
        # this means not having the EXACT amount of
        # determined WINDOW length that is set up in the config file.
        # this is a hack. lol
        WINDOW_LENGTH_DILATION = 1.05
        
        # CONDITION 1: Do we have enough data in the window container?
        #
        # we do this because we want to be working with a full bodied WINDOW_LIST
        # data container with enough frames to make meaningful calculations.
        if len(WINDOW_LIST) > WINDOW*WINDOW_LENGTH_DILATION:

            # CONDITION 2: Have enough frames passed since last alert fired?
            #
            # likewise, we want to make sure a reasonable amount of
            # time has passed since the last alert fired.
            if frames_since_last_hit > WINDOW*WINDOW_LENGTH_DILATION:   
                # CONDITION 3: Main detection logic
                #
                # 
                DETECTION = determinePctPriceMovement(WINDOW_LIST,DELTA)
                print(DETECTION)
                # when our alerting criteria (hit) is true
                if DETECTION[0] == True:
                    # send alert to discord channgel
                    #sendAlert(msg=generateMessage(data=data, pct_change=DETECTION[1]))
                    # write log to disk
                    #writeLog(data)
                    # reset time window - this is mostly because spam
                    WINDOW_LIST = []
                    # reset alerting criteria to false
                    hit = False
                    # update the count since last time alert fired
                    frames_since_last_hit = 0

            #else:
                # run this for every frame where there is no hit
            #    continue
            # run this for every frame where window size is above dilation
            WINDOW_LIST = arrayShift(WINDOW_LIST)
        # run this every frame
        frames_since_last_hit += 1
    
        # to get close to running our bot every second
        # establishes the rate with which new data is obtained
        time.sleep(0.9)
    except Exception as e:
        # with exception handling like this we will reallllly live forever!
        print(e)
        pass