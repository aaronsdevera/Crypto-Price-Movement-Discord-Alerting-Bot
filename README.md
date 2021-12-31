# Crypto Price Movement Discord Alerting Bot
A simple program to watch price movements of cryptocurrencies, and then alert a Discord channel when certain criterion are met.

By simple I mean
* standard Python libraries only
* no databases
* single config + program + calculation + ticker symbol

## Data sources
Currently supported price data:
* [KuCoin Futures API](https://docs.kucoin.com/futures/#general)
To do:
* [KuCoin Ticker API](https://docs.kucoin.com/#get-symbols-list)
* [Coinbase Price Data API](https://developers.coinbase.com/docs/wallet/guides/price-data)

## Price movement detections
Currently supported price movements:
* % change over time

To do:
* ???

Also requires a Discord Webhook endpoint that is specific to the Discord server and channel. [Read here on how to get one.](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks)

# Configuring the alerts bot
The `alerting.py` program requires a configuration file to determine what cryptocurrency it will be looking at and what calculations it will be making. the configuration file will also contain secrets like you API key to KuCoin.

An example configuration file looks like this. It may need to change for future calculations types as well as looking at ticker symbols other than cryptocurrency futures.

## config.json
```
{
    "name":"<key name>", // name of your KuCoin Futures API key
    "key":"<key id>", // key ID of your KuCoin Futures API key
    "secret":"<key secret>", // the secret key of your KuCoin Futures API key
    "pass":"<key pass>", // the password your KuCoin Futures API key
    "webhook":"<url>", // Discord webhook URL
    "time_window":60, // the time, in seconds, for the time window to analyze
    "delta":0.01, // percentage change to be analyzed in the time window. 0.01 = 1%
    "symbol":"ETHUSDTM" // ticker symbol of the futures contract
}
```

If you plan on having multiple configurations running at once, it helps to name them like `config-SYMBOL-TIMEWINDOW-PCT.json` or something.

## Logs for fired alerts appear in `logs/` directory
The logs directory will produce a file structure organized by the symbol and contract type.

The tree structure looks like this:
```
logs
└── ticker
    ├── ETHUSDTM
    ├── PEOPLEUSDTM
    ├── SUSHIUSDTM
    └── XBTUSDTM
```
Future endpoints will produce directories under `logs/` next to the `ticker` endpoint, e.g. `level2/`.