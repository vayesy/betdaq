from enum import Enum


class Lang(Enum):
    en = 'en'


class Currency(Enum):
    GBP = 'GBP'
    USD = 'USD'
    EUR = 'EUR'
    INR = 'INR'
    JPY = 'JPY'
    NOK = 'NOK'


class Sport(Enum):
    HORSE_RACING = 100004
    GREYHOUND_RACING = 100008


class MarketStatus(Enum):
    Inactive = 1
    Active = 2
    Suspended = 3
    Completed = 4
    Settled = 6
    Voided = 7


class MarketType(Enum):
    Win = 1
    Place = 2
    MatchOdds = 3
    OverUnder = 4
    AsianHandicap = 10
    TwoBall = 11
    ThreeBall = 12
    Unspecified = 13
    MatchMarket = 14
    SetMarket = 15
    Moneyline = 16
    Total = 17
    Handicap = 18
    EachWayNonHandicap = 19
    EachWayHandicap = 20
    EachWayTournament = 21
    RunningBall = 22
    MatchBetting = 23
    MatchBettingInclDraw = 24
    CorrectScore = 25
    HalfTimeFullTime = 26
    TotalGoals = 27
    GoalsScored = 28
    Corners = 29
    OddsOrEvens = 30
    HalfTimeResult = 31
    HalfTimeScore = 32
    MatchOddsExtraTime = 33
    CorrectScoreExtraTime = 34
    OverUnderExtraTime = 35
    ToQualify = 36
    DrawNoBet = 37
    HalftimeAsianHcp = 39
    HalftimeOverUnder = 40
    NextGoal = 41
    FirstGoalscorer = 42
    LastGoalscorer = 43
    PlayerToScore = 44
    FirstHalfHandicap = 45
    FirstHalfTotal = 46
    SetBetting = 47
    GroupBetting = 48
    MatchplaySingle = 49
    MatchplayFourball = 50
    MatchplayFoursome = 51
    TiedMatch = 52
    TopBatsman = 53
    InningsRuns = 54
    TotalTries = 55
    TotalPoints = 56
    FrameBetting = 57
    ToScoreFirst = 58
    ToScoreLast = 59
    FirstScoringPlay = 60
    LastScoringPlay = 61
    HighestScoringQtr = 62
    RunLine = 63
    RoundBetting = 64


class OrderActionType(Enum):
    Placed = 1
    ExplicitlyUpdated = 2
    Matched = 3
    CancelledExplicitly = 4
    CancelledByReset = 5
    CancelledOnInRunning = 6
    Expired = 7
    MatchedPortionRepricedByR4 = 8
    UnmatchedPortionRepricedByR4 = 9
    UnmatchedPortionCancelledByWithdrawal = 10
    Voided = 11
    Settled = 12
    Suspended = 13
    Unsuspended = 14
    ExpiredByMatching = 15
    Unsettled = 16
    Unmatched = 17
    MatchedPortionRepriced = 18
    CreatedFromLightweightPrice = 19
    CancelledOnComplete = 20


class OrderFillType(Enum):
    Normal = 1
    FillAndKill = 2
    FillOrKill = 3
    FillOrKillDontCancel = 4
    SPIfUnmatched = 5


class OrderStatus(Enum):
    Unmatched = 1
    Matched = 2
    Cancelled = 3
    Settled = 4
    Void = 5
    Suspended = 6


class Polarity(Enum):
    For = 1
    Against = 2


class TradeType(Enum):
    Back = 1
    Lay = 2


class PostingCategory(Enum):
    Settlement = 1
    Commission = 2
    Other = 3


class PriceFormat(Enum):
    Decimal = 1
    Fractional = 2
    American = 3


class SelectionStatus(Enum):
    Inactive = 1
    Active = 2
    Suspended = 3
    Withdrawn = 4
    Voided = 5
    Completed = 6
    Settled = 8
    BallotedOut = 9


class WithdrawRepriceOption(Enum):
    Reprice = 1
    Cancel = 2
    DontReprice = 3


class ReturnCode(Enum):

    Success = 0
    ResourceError = 1
    SystemError = 2
    EventClassifierDoesNotExist = 5
    CurrencyNotValid = 23
    LanguageDoesNotExist = 71
    CurrencyDoesNotExist = 105
    ParameterFormatError = 113
    ParameterMissingError = 134
    PunterSuspended = 208
    IncorrectVersionNumber = 308
    PunterIsBlacklisted = 406
    UnacceptableIPAddress = 437
    PunterNotRegisteredToIntegrationPartner = 500
    IntegrationPartnerDoesNotExist = 504
    PartnerTokenNotAuthenticated = 511
    SessionTokenNotAuthenticated = 512
    PunterIntegrationPartnerMismatch = 513
    SessionTokenNoLongerValid = 514
    UsernameDoesNotExist = 518
    PasswordAuthenticationNotAllowed = 521
    DeprecatedAPIVersion = 531
    PunterNotAuthenticated = 612  # invalid credentials
    AAPIDoesNotExist = 658
    ConcurrentSessionLimitReached = 671
    ConnectionInInvalidState = 672
    PunterNotAuthorisedForAAPI = 673
    PunterIsBanned = 675
    AAPINotSupported = 701
    MaximumSubscribedMarketsReached = 961
