from enum import Enum


class MessageType(Enum):
    TopicLoad = 'T'
    Delete = 'X'
    Delta = 'F'


class CommandIdentifier(Enum):

    # Session Management Commands
    SetAnonymousSessionContext = 1
    LogonPunter = 2
    LogoffPunter = 3
    SetRefreshPeriod = 60
    GetRefreshPeriod = 61

    # Subscription Commands
    SubscribeMarketInformation = 9
    SubscribeDetailedMarketPrices = 10
    SubscribeEventHierarchy = 12
    SubscribeMarketMatchedAmounts = 14
    Unsubscribe = 20

    # General Application Commands
    Ping = 22
