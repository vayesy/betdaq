from environs import Env

env = Env()
with env.prefixed('BETDAQ_GBEI_'):
    URL = env('URL')
    PUNTER_ID = env('PUNTER_ID')
    PUNTER_SESSION_KEY = env('PUNTER_SESSION_KEY')
