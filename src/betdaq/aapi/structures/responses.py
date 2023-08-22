from logging import getLogger

from ...common.enums import PriceFormat, Lang, Currency, ReturnCode
from .head import Head
from .enums import CommandIdentifier
from .frame import Frame, MessageMeta
from . import fields as f


L = getLogger(__name__)


class Response(Frame):
    correlation_id = f.Int(order=0)
    return_code = f.Enum(enum_cls=ReturnCode, parse_func=int, order=1)

    def __init__(self, head: Head, **kw):
        super(Response, self).__init__(**kw)
        self.head = head

    @classmethod
    def load(cls, head: Head, body: dict):
        response = cls(head=head)
        cls_fields = getattr(cls, MessageMeta.fields_key)
        for key, raw_value in body.items():
            field = cls_fields.get(key)
            if field is None:
                L.debug({'message': 'Skipping unknown field in response',
                         'response_class': cls.__name__,
                         'field_index': key, 'field_value': raw_value})
                continue
            value = field.load(raw_value, response)
            setattr(response, field.name, value)
        return response


class Ping(Response):
    identifier = CommandIdentifier.Ping
    messages_in_queue = f.Int(order=2)


class SetAnonymousSessionContext(Response):
    identifier = CommandIdentifier.SetAnonymousSessionContext
    maximum_message_size = f.Int(order=2)
    maximum_market_information_marketsCount = f.Int(order=3, required=False)
    maximum_market_prices_markets_count = f.Int(order=4, required=False)
    maximum_market_matched_amounts_markets_count = f.Int(order=5, required=False)


class LogonPunter(Response):
    identifier = CommandIdentifier.LogonPunter
    debit_sportsbook_stake = f.Bool(order=2)
    debit_exchange_stake = f.Bool(order=3)
    purse_integration_mode = f.Str(order=4)  # fixme: type missing from docs
    can_place_for_side_orders = f.Bool(order=5)
    can_place_against_side_orders = f.Bool(order=6)
    restricted_to_fill_kill_orders = f.Bool(order=7)
    currency = f.Enum(enum_cls=Currency, order=8)
    language = f.Enum(enum_cls=Lang, order=9)
    price_format = f.Enum(enum_cls=PriceFormat, parse_func=int, order=10)
    market_by_volume_amount = f.Float(order=11)
    aapi_session_token = f.Str(order=13)  # fixme: check it's type
    maximum_message_size = f.Int(order=14)
    maximum_market_information_markets_count = f.Int(order=15)
    maximum_market_prices_markets_count = f.Int(order=16)
    maximum_market_matched_amounts_markets_count = f.Int(17)


class SetRefreshPeriod(Response):
    identifier = CommandIdentifier.SetRefreshPeriod
    refresh_period_ms = f.Int(order=2)


class GetRefreshPeriod(Response):
    identifier = CommandIdentifier.GetRefreshPeriod
    refresh_period_ms = f.Int(order=2)


class SubscribeMarketInformation(Response):
    identifier = CommandIdentifier.SubscribeMarketInformation
    subscription_id = f.Int(order=2, required=False)
    market_ids = f.Str(order=3, required=False)
    available_markets_count = f.Int(order=4)


class SubscribeDetailedMarketPrices(Response):
    identifier = CommandIdentifier.SubscribeDetailedMarketPrices
    subscription_id = f.Int(order=2, required=False)
    market_ids = f.Str(order=3, required=False)
    available_markets_count = f.Int(order=4, required=False)


class SubscribeEventHierarchy(Response):
    identifier = CommandIdentifier.SubscribeEventHierarchy
    subscription_id = f.Int(order=2, required=False)
    available_markets_count = f.Int(order=4, required=False)


class SubscribeMarketMatchedAmounts(Response):
    identifier = CommandIdentifier.SubscribeMarketMatchedAmounts
    subscription_id = f.Int(order=2, required=False)
    market_ids = f.Str(order=3, required=False)
    available_markets_count = f.Int(order=4, required=False)


class Unsubscribe(Response):
    identifier = CommandIdentifier.Unsubscribe
    subscription_ids = f.StrJoinedField(order=3, field=f.Int(order=0), required=False)


RESPONSE_TYPES = {
    f.identifier.value: f for f in (SetAnonymousSessionContext, LogonPunter, Ping,
                                    SetRefreshPeriod, GetRefreshPeriod,
                                    SubscribeMarketInformation, SubscribeDetailedMarketPrices,
                                    SubscribeEventHierarchy, SubscribeMarketMatchedAmounts,
                                    Unsubscribe)
}
