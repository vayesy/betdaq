from enum import Enum


# flake8: noqa
class LWPActionType(Enum):
    CancelledExplicitly = 1  # LWP cancelled by `CancelLightweightPrices` command
    CancelledAll = 2  # LWP cancelled by `CancelAllLightweightPrices` command
    Matched = 3  # LWP matched fully or partially
    ChangedExplicitly = 4  # LWP changed or added by `AddLightweightPrices` command
    SelectionCompleted = 5  # LWP cancelled because selection closed (e.g. abandoned or market closed)
    ResetOccurred = 6  # LWP cancelled because the selection has been explicitly reset
    WithdrawalOccurred = 7  # LWP cancelled because a withdrawal has occurred on the market concerned
    Expired = 8  # LWP cancelled because the expiry_at time most recent AddLightPrices command has been reached
    CancelledAllOnSelection = 9  # LWP cancelled as a result of CancelAllLightweightPricesOnSelections command
    CancelledOnPunterDisabled = 10  # LWP has been cancelled because the Punter has been explicitly disabled
    LWPDoesNotExist = 11  # LWP specified does not exist, can occur when cancelling a LWP that does not exist
    CancelledInvalidPrice = 12  # LWP was cancelled because the  price was not recognised on the odds ladder
    CancelledInvalidWithdrawalSequenceNumber = 13  # LWP cancelled  because withdrawal sequence number was incorrect
    CancelledInvalidSelectionResetCount = 14  # LWP cancelled because the selection reset count specified was incorrect
    CancelledInvalidCurrency = 15  # LWP cancelled because currency doesn't exist or not a punter account currency
    CancelledAllOnMarket = 16  # LWP cancelled as a result of a CancelAllLightweightPricesOnMarkets command
    CancelledIncorrectMarketId = 18  # LWP cancelled because specified market_id is invalid
    CancelledPlayForFreeViolation = 19  # LWP cancelled because market is a real market and the punter is a play-for-free or viceversa
    CancelledRingfencedLiquidityViolation = 20  # LWP cancelled because market and the punter do not have compatible ring-fenced liquidity pools
    CancelledAnUnmatchableAmount = 21  # LWP cancelled because the combination of price and amount of unmatched stake of the LWP is such that it would not be possible to match it


class ProtocolEvents(Enum):
    connection_made = 0  # connection to GBEi server established. Accepts no parameters
    data_received = 1  # data received from GBEi server. Accepts single parameter, parsed GBEi message as dictionary
    data_sent = 2  # data sent to GBEi server. Accepts single parameter, message dictionary object
    connection_lost = 3  # connection with GBEi lost for any reason. Accepts one parameter, optional exception


class GBEiMessageType(Enum):
    addLightweightPrices = 'addlightweightprices'
    cancelAllLightweightPrices = 'cancelalllightweightprices'
    cancelAllLightweightPricesOnMarkets = 'cancelalllightweightpricesonmarkets'
    cancelAllLightweightPricesOnSelections = 'cancelalllightweightpricesonselections'
    cancelLightweightPrices = 'cancellightweightprices'
    ping = 'ping'
    queryAllLightweightPrices = 'queryalllightweightprices'
    queryAllLightweightPricesOnMarkets = 'queryalllightweightpricesonmarkets'
    queryAllLightweightPricesOnSelections = 'queryalllightweightpricesonselections'
    lightweightPriceSummary = 'lightweightpricesummary'
    LWPChangeNotification = 'lwpchangenotification'
    pingResponse = 'pingresponse'
    resetOccurred = 'resetoccurred'
