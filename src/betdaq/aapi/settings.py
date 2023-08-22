from environs import Env

env = Env()
with env.prefixed('BETDAQ_AAPI_'):
    AAPI_VERSION = env('VERSION', '2.2')
    STREAM_URL = env('STREAM_URL')
    TIMEOUT = env.float('TIMEOUT', 10)
    CONNECTION_TIMEOUT = env.float('CONNECTION_TIMEOUT', 60)
    RECEIVE_TIMEOUT = env.float('RECEIVE_TIMEOUT', 5)
    PING_FREQUENCY = env.float('PING_FREQUENCY', 15)
    USERNAME = env('USERNAME', None)
    PASSWORD = env('PASSWORD', None)

    REFRESH_PERIOD = env.int('REFRESH_PERIOD', 1)
    META_REFRESH_PERIOD = env.float('META_REFRESH_PERIOD', 3600)
    META_REFRESH_CLASSIFIERS = env.dict('META_REFRESH_CLASSIFIERS', subcast_keys=int, default={
        190538: 'UK Racing',
        190539: 'Irish Racing',
        422497: 'Daily Cards',
        1190579: 'RPTV (Sky Ch431)',
        1049075: 'AU Races',
        1048931: 'US Races'
    })
    PRICES_NUMBER = env.int('PRICES_NUMBER', 10)
    FILTER_BY_VOLUME = env.int('FILTER_BY_VOLUME', 1)
    CALL_TIMEOUTS = {
        'global': 0.2,
        **dict.fromkeys(['SubscribeEventHierarchy', 'SubscribeDetailedMarketPrices',
                         'SubscribeMarketInformation', 'SubscribeMarketMatchedAmounts'], 1.)
    }
