from ...common.enums import MarketType, PriceFormat, Lang, Currency
from ..utils import BLOCK_DELIMITER, VALUE_DELIMITER
from .enums import CommandIdentifier
from .frame import Frame, MessageMeta
from . import fields as f


class Command(Frame):
    identifier = None
    check_required = True

    correlation_id = f.Int(order=0)

    def dump_header(self):
        return VALUE_DELIMITER + str(self.identifier.value)

    def dump_body(self):
        res = BLOCK_DELIMITER
        own_fields = getattr(self, MessageMeta.fields_key)
        for field_cls in own_fields.values():  # type: f.BaseField
            field_val = getattr(self, field_cls.name, None)
            if field_val is not None:
                res += field_cls.dump(field_val, self, True) + BLOCK_DELIMITER
        return res

    def dump(self):
        return self.dump_header() + self.dump_body()

    def __gt__(self, other):
        return self.correlation_id > other.correlation_id

    def __lt__(self, other):
        return self.correlation_id < other.correlation_id


class Ping(Command):
    identifier = CommandIdentifier.Ping
    current_client_time = f.DateTime(order=1, required=False)
    last_ping_roundtrip_ms = f.Int(order=2, required=False)
    last_pinged_at = f.Int(order=3, required=False)


class SetAnonymousSessionContext(Command):
    """Initialize anonymous session, which doesn't require login credentials"""

    identifier = CommandIdentifier.SetAnonymousSessionContext
    currency = f.Enum(enum_cls=Currency, order=1)
    language = f.Enum(enum_cls=Lang, order=2)
    price_format = f.Enum(enum_cls=PriceFormat, parse_func=int, order=3)
    integration_partner_id = f.Int(order=5, required=False)
    aapi_version = f.Str(order=6, max_length=8)
    client_specified_guid = f.Str(order=7)
    granular_channel_type = f.Str(order=8, required=False)
    channel_information = f.Str(order=9, max_length=256, required=False)
    client_identifier = f.Str(order=10, max_length=64, required=False)


class LogonPunter(Command):
    identifier = CommandIdentifier.LogonPunter
    partner_token = f.Str(order=1, required=False)
    aapi_session_token = f.Str(order=2, required=False)
    integration_partner_id = f.Int(order=3, required=False, name='integration_partner_id')
    partner_username = f.Str(max_length=64, order=4, required=False)
    cleartext_password = f.Str(max_length=256, order=5, required=False)
    currency = f.Enum(enum_cls=Currency, order=6, required=False)
    language = f.Enum(enum_cls=Lang, order=7, required=False)
    aapi_version = f.Str(order=8)
    client_specified_guid = f.Str(order=9)
    granular_channel_type = f.Str(order=10, required=False)
    channel_information = f.Str(order=12, max_length=256, required=False)
    client_identifier = f.Str(order=13, max_length=64, required=False)
    integration_partner_id2 = f.Int(order=14, required=False, name='integration_partner_id')
    session_token = f.Str(order=15, required=False)


class LogoffPunter(Command):
    identifier = CommandIdentifier.LogoffPunter


class SetRefreshPeriod(Command):
    identifier = CommandIdentifier.SetRefreshPeriod
    refresh_period_ms = f.Int(order=1)


class GetRefreshPeriod(Command):
    identifier = CommandIdentifier.GetRefreshPeriod


class SubscribeMarketInformation(Command):
    identifier = CommandIdentifier.SubscribeMarketInformation
    event_classifier_id = f.Int(order=2, required=False)
    market_types_to_exclude = f.StrJoinedField(field=f.Enum(enum_cls=MarketType, order=0), required=False, order=3)
    market_types_to_include = f.StrJoinedField(field=f.Enum(enum_cls=MarketType, order=0), required=False, order=4)
    want_direct_descendants_only = f.Bool(required=False, order=5)
    market_ids = f.StrJoinedField(field=f.Int(order=0), required=False, order=6)
    fetch_only = f.Bool(default=False, required=False, order=7)
    want_selection_information = f.Bool(default=True, required=False, order=8)
    want_exchange_language_information_only = f.Bool(required=False, order=9)
    market_tagged_value_topic_names = f.Str(required=False, order=10)
    exclude_language_topics = f.Bool(required=False, order=11)
    want_selection_blurb = f.Bool(required=False, default=False, order=12)


class SubscribeDetailedMarketPrices(Command):
    identifier = CommandIdentifier.SubscribeDetailedMarketPrices
    event_classifier_id = f.Int(order=1, required=False)
    market_types_to_exclude = f.StrJoinedField(required=False, order=2, field=f.Enum(enum_cls=MarketType, order=0))
    market_types_to_include = f.StrJoinedField(required=False, order=3, field=f.Enum(enum_cls=MarketType, order=0))
    want_direct_descendants_only = f.Bool(required=False, order=4)
    market_ids = f.StrJoinedField(required=False, order=5, field=f.Int(order=0))
    number_back_prices = f.Int(order=6)
    number_lay_prices = f.Int(order=7)
    filter_by_volume = f.Float(order=8)
    fetch_only = f.Bool(required=False, default=False, order=11)


class SubscribeEventHierarchy(Command):
    identifier = CommandIdentifier.SubscribeEventHierarchy
    event_classifier_id = f.Int(order=2)
    want_direct_descendants_only = f.Bool(order=3)
    want_selection_information = f.Bool(order=4)
    fetch_only = f.Bool(required=False, default=False, order=5)
    market_types_to_exclude = f.StrJoinedField(required=False, order=6, field=f.Enum(enum_cls=MarketType, order=0))
    market_types_to_include = f.StrJoinedField(required=False, order=7, field=f.Enum(enum_cls=MarketType, order=0))
    want_exchange_language_information_only = f.Bool(required=False, order=8)
    event_tagged_value_topic_names = f.Str(required=False, order=9)
    market_tagged_value_topic_names = f.Str(required=False, order=10)
    exclude_market_information = f.Bool(required=False, order=11)
    want_tab_information = f.Bool(required=False, order=12)
    exclude_language_topics = f.Bool(required=False, order=13)
    want_selection_blurb = f.Bool(required=False, default=False, order=14)


class SubscribeMarketMatchedAmounts(Command):
    identifier = CommandIdentifier.SubscribeMarketMatchedAmounts
    event_classifier_id = f.Int(required=False, order=1)
    market_types_to_exclude = f.StrJoinedField(required=False, order=2, field=f.Enum(enum_cls=MarketType, order=0))
    market_types_to_include = f.StrJoinedField(required=False, order=3, field=f.Enum(enum_cls=MarketType, order=0))
    want_direct_descendants_only = f.Bool(required=False, order=4)
    market_ids = f.StrJoinedField(required=False, order=5, field=f.Int(order=0))
    fetch_only = f.Bool(default=False, required=False, order=7)


class Unsubscribe(Command):
    identifier = CommandIdentifier.Unsubscribe
    subscription_ids = f.StrJoinedField(field=f.Int(order=0), order=3, required=False)
