from logging import getLogger
from typing import Tuple, Union, Callable, Optional  # noqa

from ...common.enums import MarketStatus, MarketType, PriceFormat, SelectionStatus, Lang, Currency
from ..utils import strip_leading_e
from .head import Head
from .frame import Frame
from .base import MessageMeta
from . import fields as f

L = getLogger(__name__)
# All topic names are taken directly from the documentation


class TopicTitle(Frame):
    def __init__(self, field: f.BaseField, field_name=None, normalize: Callable = None, **kw):
        super(TopicTitle, self).__init__(**kw)
        self.field = field
        self.normalize = normalize
        if field_name is not None:
            self.field.name = field_name

    def load(self, value: str):
        if self.normalize is not None:
            value = self.normalize(value)
        return self.field.load(value, self)


class BaseTopic(Frame):
    topic = None  # type: Union[str, TopicTitle]
    children = ()  # type: Tuple[BaseTopic]

    @classmethod
    def topic_name_to_cls(cls, next_part):
        if len(cls.children) == 1:
            return cls.children[0]
        for child in cls.children:
            if child.topic == next_part:
                return child
        return None

    @classmethod
    def populate_kwargs(cls, topic_part, kwargs):
        if isinstance(cls.topic, TopicTitle):
            value = cls.topic.load(topic_part)
            if isinstance(value, dict):
                kwargs.update(value)
            else:
                kwargs.update({cls.topic.field.name: value})

    @classmethod
    def load(cls, body: dict, **kw) -> Optional['BaseTopic']:
        topic = cls(**kw)
        topic_fields = getattr(cls, MessageMeta.fields_key)
        for order, raw_value in body.items():
            field = topic_fields.get(order)
            if field is None:
                L.debug({'message': 'Unknown field in data message',
                         'topic': cls.__name__, 'field_order': order, 'field_value': raw_value})
                continue
            value = field.load(raw_value, topic)
            setattr(topic, field.name, value)
        return topic

    def __init__(self, head: Head, topic_kwargs: dict, **kw):
        super(BaseTopic, self).__init__(**kw)
        self.topic_kwargs = topic_kwargs
        self.head = head


class Currency3(BaseTopic):
    topic = TopicTitle(field=f.Enum(order=0, enum_cls=Currency), field_name='currency')
    for_side_amount = f.Float(order=1)
    against_side_amount = f.Float(order=2)


class Language2(BaseTopic):
    topic = TopicTitle(field=f.Enum(enum_cls=Lang, order=0, name='exchange_info_language'))
    name = f.Str(order=1, max_length=256)
    race_grade = f.Str(order=2, max_length=2048, required=False)


class Language3(BaseTopic):
    topic = TopicTitle(field=f.Enum(enum_cls=Lang, order=0, name='market_exchange_info_language'))
    name = f.Str(order=1, max_length=256)
    description = f.Str(order=2, max_length=2048, required=False)
    market_blurb = f.Str(order=3, required=False)


class Language4(BaseTopic):
    topic = TopicTitle(field=f.Enum(enum_cls=Lang, order=0, name='event_language'))
    name = f.Str(order=1, max_length=256)


class Language5(BaseTopic):
    topic = TopicTitle(field=f.Enum(enum_cls=Lang, order=0, name='selection_language'))
    name = f.Str(order=1, max_length=256)


class Language6(BaseTopic):
    topic = TopicTitle(field=f.Enum(enum_cls=Lang, order=0, name='selection_exchange_info_language'))
    name = f.Str(order=1, max_length=256)
    selection_blurb = f.Str(order=2, max_length=256)


class Language7(BaseTopic):
    topic = TopicTitle(field=f.Enum(enum_cls=Lang, order=0, name='market_language'))
    name = f.Str(order=1, max_length=256)


class MMatchedAmount(BaseTopic):
    topic = 'MMA'
    children = (Currency3,)


class MExchangeLanguage(BaseTopic):
    topic = 'MEL'
    children = (Language3,)


class BackLayVolumeCurrencyFormat(BaseTopic):
    topic = TopicTitle(field=f.ReadOnlyStrJoinedNestedField(fields=dict(
        desired_back_prices=f.Int(order=0),
        desired_lay_prices=f.Int(order=1),
        desired_market_by_volume=f.Int(order=2),
        currency_code=f.Enum(enum_cls=Currency, order=3),
        price_format=f.Enum(enum_cls=PriceFormat, parse_func=int, order=4)
    )))
    selections = f.ReadOnlyNestedField(order=1, fields=dict(
        selection_id=f.Int(order=1),
        back_prices=f.ReadOnlyNestedField(order=2, fields=dict(
            display_price=f.Float(order=1),
            stake=f.Float(order=2, required=False, default=0.)
        )),
        lay_prices=f.ReadOnlyNestedField(order=3, fields=dict(
            display_price=f.Float(order=1),
            stake=f.Float(order=2, required=False, default=0.)
        )),
        redbox_display_price=f.Str(order=4, max_length=6),
        redbox_fractional_price=f.Str(order=5)
    ))


class MarketDetailedPrices(BaseTopic):
    topic = 'MDP'
    children = (BackLayVolumeCurrencyFormat,)


class MExchangeInfo(BaseTopic):
    topic = 'MEI'
    children = (MMatchedAmount, MExchangeLanguage, MarketDetailedPrices)  # SMatchedAmounts, MarketSummaryPrices
    market_id = f.Int(order=1)
    market_type = f.Enum(order=2, enum_cls=MarketType, parse_func=int)
    is_play_market = f.Bool(order=3)
    can_be_in_running = f.Bool(order=4)
    managed_when_in_running = f.Bool(order=5)
    is_visible_as_trading_market = f.Bool(order=6)
    is_visible_as_priced_market = f.Bool(order=7)
    is_enabled_for_multiples = f.Bool(order=8)
    is_currently_in_running = f.Bool(order=9)
    status = f.Enum(order=10, enum_cls=MarketStatus, parse_func=int)
    withdraw_action = f.Str(order=11)  # todo: check type
    ballot_out_action = f.Str(order=12)
    can_be_dead_heated = f.Bool(order=13)
    start_time = f.DateTime(order=14, required=False)
    delay_factor = f.Int(order=15, required=False)
    number_of_winning_selections = f.Int(order=16)
    withdrawal_sequence_number = f.Int(order=17)
    result_string = f.Str(order=18, max_length=256, required=False)
    number_of_selections = f.Int(order=19)
    place_payout = f.Str(order=20)  # todo: check type
    redbox_sp_available = f.Bool(order=21, required=False)
    b_og_available = f.Bool(order=22, required=False)
    number_winning_places = f.Int(order=23, required=False)
    place_fraction = f.Str(order=24, max_length=3)


class SelectionBlurb(BaseTopic):
    topic = 'SB'
    blurb = f.Str(order=1, max_length=256)


class SExchangeLanguage(BaseTopic):
    topic = 'SEL'
    children = (Language6,)


class SExchangeInfo(BaseTopic):
    topic = 'SEI'
    children = (SelectionBlurb, SExchangeLanguage)
    selection_id = f.Int(order=1)
    status = f.Enum(order=2, enum_cls=SelectionStatus, parse_func=int)
    selection_reset_count = f.Int(order=3)
    withdrawal_factor = f.Float(order=4, required=False)
    settled_time = f.DateTime(order=5, required=False)
    result_string = f.Str(order=6, max_length=256, required=False)
    void_percentage = f.Str(order=7)
    left_side_factor = f.Str(order=8)
    right_side_factor = f.Str(order=9)


class SelectionLanguage(BaseTopic):
    topic = 'SL'
    children = (Language5,)


class Selection1(BaseTopic):
    topic = TopicTitle(field=f.Int(order=0, name='selection_id'), normalize=strip_leading_e)
    children = (SExchangeInfo, SelectionLanguage)
    display_order = f.Int(order=1)
    selection_icon = f.Str(order=2)


class Selections(BaseTopic):
    topic = 'S'
    children = (Selection1,)


class TaggedValue2(BaseTopic):
    topic = TopicTitle(field=f.Str(order=0, name='tagged_value'))
    value = f.Str(order=1)


class MarketTaggedValues(BaseTopic):
    topic = 'TV'
    children = (TaggedValue2,)


class MarketLanguage(BaseTopic):
    topic = 'ML'
    children = (Language7,)


class Market1(BaseTopic):
    topic = TopicTitle(field=f.Int(order=0, name='market_id'), normalize=strip_leading_e)
    children = (MExchangeInfo, Selections, MarketTaggedValues, MarketLanguage)
    display_order = f.Int(order=1)
    scores = f.ReadOnlyNestedField(order=2, fields=dict(
        occured_at=f.DateTime(order=1),
        score=f.Str(order=2, max_length=1024)
    ))


class Markets(BaseTopic):
    topic = 'M'
    children = (Market1,)


class Language14(BaseTopic):
    topic = TopicTitle(field=f.Enum(enum_cls=Lang, order=0, name='tab_language'))
    name = f.Str(order=1, max_length=256)


class TabLanguage(BaseTopic):
    topic = 'TL'
    children = (Language14,)


class Tab1(BaseTopic):
    topic = TopicTitle(field=f.Str(order=0, name='grouping_name'))
    children = (TabLanguage,)
    display_order = f.Int(order=1)
    market_ids = f.Str(order=2)
    number_of_markets_to_expand = f.Int(order=3, required=False)


class Tabs(BaseTopic):
    topic = 'TAB'
    children = (Tab1,)


class EExchangeLanguage(BaseTopic):
    topic = 'EEL'
    children = (Language2,)


class EExchangeInfo(BaseTopic):
    topic = 'EEI'
    children = (Tabs, EExchangeLanguage)
    event_classifier_id = f.Int(order=1)
    is_enabled_for_multiples = f.Bool(order=2)
    start_time = f.DateTime(order=3, required=False)


class EventLanguage(BaseTopic):
    topic = 'EL'
    children = (Language4,)


class Event1(BaseTopic):
    topic = TopicTitle(field=f.Int(order=0, name='event_classifier_id'), normalize=strip_leading_e)
    children = (Markets, EExchangeInfo, EventLanguage)  # EventTaggedValues
    display_order = f.Int(order=1)
    score = f.ReadOnlyNestedField(order=2, fields=dict(
        occured_ad=f.DateTime(order=1, required=False),
        score=f.Str(order=2, max_length=1024)
    ))
    significance_times = f.ReadOnlyNestedField(order=3, fields=dict(
        occurence_type=f.Str(order=1, max_length=64),
        predicted_time=f.DateTime(order=2, required=False),
        actual_time=f.DateTime(order=3, required=False)
    ))

    @classmethod
    def populate_kwargs(cls, topic_part, kwargs):
        key_names = ['parent', 'sport_id', 'sport_group_id', 'location_id', 'event_id']
        classifier_ids = kwargs.setdefault(cls.topic.field.name, {})
        key = key_names[len(classifier_ids)]
        value = cls.topic.load(topic_part)
        classifier_ids[key] = value


class Events(BaseTopic):
    topic = 'E'
    children = (Event1,)


Event1.children += (Events,)


class TaggedValue1(BaseTopic):
    topic = TopicTitle(field=f.Str(order=0, name='topic_name'))
    value = f.Str(order=1)


def resolve_data_message(topic_name):
    topic_parts = topic_name.split('/')[3:]
    assert len(topic_parts), "Invalid topic {!r}".format(topic_name)
    topic_cls = Events
    topic_kwargs = dict()
    next_part = None
    while topic_parts:
        if topic_cls is None:
            L.debug({'message': 'Failed to extract data message handler',
                     'topic_name': topic_name})
            return None, None
        topic_cls.populate_kwargs(next_part, topic_kwargs)
        next_part = topic_parts.pop(0)
        topic_cls = topic_cls.topic_name_to_cls(next_part)
    if topic_cls is not None:
        topic_cls.populate_kwargs(next_part, topic_kwargs)
    return topic_cls, topic_kwargs
