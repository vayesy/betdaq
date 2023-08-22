from ...common.enums import Currency
from .enums import LWPActionType, GBEiMessageType
from .fields import Int, String, DateTime, Long, Array, Decimal, MoneyAmount,\
    Optional, Serializable, Length, Byte, ReversedInt, Enum


length = Length()
currency = Currency.GBP.value


class Meta(type):
    fields_key = '__fields__'

    def __new__(mcs, name, bases, attrs):
        class_fields = {}
        for base in bases:
            base_fields = getattr(base, mcs.fields_key, None)
            if base_fields:
                class_fields.update(base_fields)
        for k, v in attrs.items():
            if isinstance(v, Serializable):
                # if v.name is None:
                v.name = k
                class_fields[v.name] = v
        res = super(Meta, mcs).__new__(mcs, name, bases, attrs)
        setattr(res, mcs.fields_key, class_fields)
        return res


class BaseFrame(Serializable, metaclass=Meta):
    include_length = False

    def dumps(self, item):
        fields = getattr(self, Meta.fields_key)
        buff = b''
        for name, field in fields.items():
            try:
                value = item[name]
            except KeyError:
                if not isinstance(field, Optional):
                    raise ValueError('Missing required field %s' % name)
                value = None
            dumped = field.dumps(value)
            buff += dumped
        if self.include_length:
            size = length.dumps(len(buff))
            buff = b''.join((size, buff))
        return buff

    def loads(self, bts: memoryview):
        fields = getattr(self, Meta.fields_key)
        data = {}
        if self.include_length:
            l, bts = length.loads(bts)
            remaining = bts[l:]
            bts = bts[:l]
        else:
            remaining = bts
        for name, field in fields.items():
            value, bts = field.loads(bts)
            data[name] = value
        if not self.include_length:
            remaining = bts
        return data, remaining


class ProtocolHeader(BaseFrame):
    include_length = True
    version = Byte()  # always 1 (if above field is 0, ignore)


class EnvelopeHeader(BaseFrame):
    include_length = True
    version = Byte()  # always 01
    item_count = Byte()  # always 02


class MessageHeader(BaseFrame):
    include_length = True
    version = ReversedInt()  # always 1

    # fields
    type = Enum(String(), GBEiMessageType, raw=True)
    type_version = Int()
    format = String()  # always binary
    source = String()  # unique per connection, usually virtual punter id
    transport = String()  # set to lwps_tcp1
    priority = Int()  # set to 3
    interface = String()  # lightweightpriceserverexternal or authorisedvirtualpunter


class MessageBody(BaseFrame):
    include_length = True
    type: GBEiMessageType = None
    command_version = Int()
    command_time = DateTime()
    expire_at = DateTime()
    virtual_punter_id = Long()
    virtual_punter_session_key = Long()


class LightWeightPriceToAdd(BaseFrame):
    selection_id = Long()
    market_id = Long()
    polarity = Int()  # 0 = Against, 1 = For
    odds = Decimal()
    delta_stake = MoneyAmount(currency)
    expire_price_at = DateTime()
    expected_selection_reset_count = Int()
    expected_withdrawal_sequence_number = Int()
    punter_reference_number = Long()


class LightWeightPriceNotificationBase(BaseFrame):
    market_id = Long()
    selection_id = Long()
    polarity = Int()  # 0 = Against, 1 = For
    odds = Decimal()
    punter_reference_number = Long()
    expire_at = DateTime()
    expected_selection_reset_count = Int()
    expected_withdrawal_sequence_number = Int()


class LightWeightPriceNotification(LightWeightPriceNotificationBase):
    remaining_stake = MoneyAmount(currency)


class LightWeightPriceToCancel(BaseFrame):
    selection_id = Long()
    polarity = Int()  # 0 = Against, 1 = For
    odds = Decimal()
    punter_reference_number = Long()


class LightWeightPriceChangeNotification(LightWeightPriceNotificationBase):
    lwp_action_type = Enum(Int(), LWPActionType, raw=True)
    remaining_stake = MoneyAmount(currency)
    matched_stake = Optional(MoneyAmount(currency))
    order_id = Optional(Long())
    matched_against_side_stake = Optional(MoneyAmount(currency))


# REQUESTS ###

class AddLightweightPrices(MessageBody):
    type = GBEiMessageType.addLightweightPrices.value
    prices = Array(LightWeightPriceToAdd())


class CancelAllLightweightPrices(MessageBody):
    type = GBEiMessageType.cancelAllLightweightPrices.value


class CancelAllLightweightPricesOnMarkets(MessageBody):
    type = GBEiMessageType.cancelAllLightweightPricesOnMarkets.value
    market_ids = Array(Long())


class CancelAllLightweightPricesOnSelections(MessageBody):
    type = GBEiMessageType.cancelAllLightweightPricesOnSelections.value
    selection_ids = Array(Long())


class CancelLightweightPrices(MessageBody):
    type = GBEiMessageType.cancelLightweightPrices.value
    prices = Array(LightWeightPriceToCancel())


class Ping(MessageBody):
    type = GBEiMessageType.ping.value
    punter_query_reference_number = Long()


class QueryAllLightweightPrices(MessageBody):
    type = GBEiMessageType.queryAllLightweightPrices.value
    punter_query_reference_number = Long()


class QueryAllLightweightPricesOnMarkets(MessageBody):
    type = GBEiMessageType.queryAllLightweightPricesOnMarkets.value
    punter_query_reference_number = Long()
    market_ids = Array(Long())


class QueryAllLightweightPricesOnSelections(MessageBody):
    type = GBEiMessageType.queryAllLightweightPricesOnSelections.value
    punter_query_reference_number = Long()
    selection_ids = Array(Long())


# RESPONSES ###

class LightWeightPriceSummary(MessageBody):
    type = GBEiMessageType.lightweightPriceSummary.value
    punter_query_reference_number = Long()
    total_summary_notifications = Int()
    prices = Array(LightWeightPriceNotification())


class LWPChangeNotification(MessageBody):
    type = GBEiMessageType.LWPChangeNotification.value
    prices = Array(LightWeightPriceChangeNotification())


class PingResponse(MessageBody):
    type = GBEiMessageType.pingResponse.value
    punter_query_reference_number = Long()
    total_summary_notifications = Int()


class ResetOccurred(MessageBody):
    type = GBEiMessageType.resetOccurred.value


class Envelope(BaseFrame):
    protocol_header = ProtocolHeader()
    envelope_header = EnvelopeHeader()
    message_header = MessageHeader()
    message = MessageBody()

    body_mapping = {
        _.type: _()
        for _ in MessageBody.__subclasses__()
    }

    def dumps(self, data: dict):
        ph = self.protocol_header.dumps(data['protocol_header'])
        eh = self.envelope_header.dumps(data['envelope_header'])
        mh = self.message_header.dumps(data['message_header'])
        message = self.body_mapping[data['message_header']['type']].dumps(data['message'])
        return b''.join((ph, eh, mh, message))

    def loads(self, bts: bytes):
        if not bts:
            return None
        bts = memoryview(bts)
        ph, bts = self.protocol_header.loads(bts)
        eh, bts = self.envelope_header.loads(bts)
        mh, bts = self.message_header.loads(bts)
        message, bts = self.body_mapping[mh['type']].loads(bts)
        data = {
            'protocol_header': ph,
            'envelope_header': eh,
            'message_header': mh,
            'message': message
        }
        return data, bts
