import time
from logging import getLogger
from typing import List, Tuple, Optional
from datetime import datetime, timedelta

from .enums import GBEiMessageType
from .fields import DateTime, Decimal, MoneyAmount, Optional as Opt, Array
from .items import Envelope, Meta, BaseFrame


L = getLogger(__name__)


class GBEiRequestEncoder(object):

    def __init__(self, punter_id: int, punter_session_key: int, version: int = 1,
                 source: str = None, format: str = 'binary', transport: str = 'lwps_tcp1',
                 interface: str = 'lightweightpriceserverexternal', priority: int = 3,
                 default_expire_timeout: timedelta = None,
                 decimal_as_string: bool = False, datetime_as_timestamp: bool = False):
        """Class to follow GBEi protocol. Responsible for encoding and parsing data.
        :param punter_id: <virtual-punter-id> assigned to account by GBEi
        :param punter_session_key: <virtual-punter-session-key> assigned to account by GBEi
        :param version: GBEi protocol version number
        :param source: source of the messages. There must be unique source per connection.
                       If not specified, string version of `punter_id` is used
        :param format: encoding format of the message. Only `binary` supported for now
        :param transport: transport name the message is being sent over
        :param interface: the name of the interface that the message belongs
        :param priority: default priority for messages sent to GBEi. Only 3 value is currently supported
        :param default_expire_timeout: default time for commands expiration time, set with `expire_at` parameter
        :param decimal_as_string: should decimals be represented as strings. Decimal is used otherwise.
        :param datetime_as_timestamp: should datetime objects be represented as floats. Datetime is used otherwise.
        """
        self.version = version
        self.punter_id = punter_id
        self.punter_session_key = punter_session_key
        self.format = format
        self.transport = transport
        self.interface = interface
        self.priority = priority
        self.expire_timeout = (default_expire_timeout or timedelta(hours=1)).total_seconds()
        if source:
            self.source = source
        else:
            self.source = str(punter_id)

        self._assign_field_parameters(decimal_as_string, datetime_as_timestamp, Envelope.body_mapping)

        self.e = Envelope()
        self.protocol_header = {'version': self.version}
        self.envelope_header = {'version': self.version, 'item_count': 2}
        self.message_base_fields = {
            'command_version': self.version,
            'virtual_punter_id': self.punter_id,
            'virtual_punter_session_key': self.punter_session_key,
        }

    def _assign_field_parameters(self, decimal_as_string: bool, datetime_as_timestamp: bool, fields: dict):
        for k, v in fields.items():
            self._check_field(v, decimal_as_string, datetime_as_timestamp)

    def _check_field(self, f, decimal_as_string, datetime_as_timestamp):
        if isinstance(f, DateTime):
            f.as_timestamp = datetime_as_timestamp
        elif isinstance(f, Decimal):
            f.as_string = decimal_as_string
        elif isinstance(f, MoneyAmount):
            f.decimal.as_string = decimal_as_string
        elif isinstance(f, Opt):
            self._check_field(f.field, decimal_as_string, datetime_as_timestamp)
        elif isinstance(f, Array):
            self._check_field(f.field, decimal_as_string, datetime_as_timestamp)
        elif isinstance(f, BaseFrame):
            self._assign_field_parameters(decimal_as_string, datetime_as_timestamp, getattr(f, Meta.fields_key))

    def _get_message_header(self, message_type: str) -> dict:
        return {
            'version': self.version,
            'type': message_type,
            'type_version': self.version,
            'format': self.format,
            'source': self.source,
            'transport': self.transport,
            'priority': self.priority,
            'interface': self.interface
        }

    def _get_expire_at(self, ts: Optional[float] = None) -> float:
        if ts is None:
            ts = time.time() + self.expire_timeout
        return ts

    def _get_command_time(self) -> float:
        return time.time()

    def _get_envelop(self, message_header: dict, message_body: dict) -> dict:
        message_body.update(command_time=self._get_command_time(), **self.message_base_fields)
        return {
            'protocol_header': self.protocol_header,
            'envelope_header': self.envelope_header,
            'message_header': message_header,
            'message': message_body
        }

    def add_lightweight_price(self, selection_id: int, market_id: int, polarity: int, odds: str,
                              delta_stake: str, expire_price_at: float, expected_selection_reset_count: int,
                              expected_withdrawal_sequence_number: int, punter_reference_number: int,
                              expire_at: Optional[float] = None) -> bytes:
        """Add lightweight price for specified selection.
        If given lightweight price already exists (combination of selection, polarity, odds, reference number),
        it's stake is altered by the new one.
        Negative stake can be passed to reduce amount on the selection.
        :param selection_id: ID of selection to add lightweight price for
        :param market_id: ID of selection market
        :param polarity: polarity (bet side), 0 is Against (Lay), 1 is For (Back)
        :param odds: odds at which to add price
        :param delta_stake: stake to add to given lightweight price
        :param expire_price_at: every price has an expiry time; value in the past has the effect of cancelling the price
                                if price is not matched until this time, it will never be matched
        :param expected_selection_reset_count: selection reset count value, used to avoid data collision
        :param expected_withdrawal_sequence_number: market withdraw. seq. number, used to avoid data collision
        :param punter_reference_number: unique request reference number, specified by user
        :param expire_at: time, when command will be considered as expired and so cancelled
        """
        message_header = self._get_message_header(GBEiMessageType.addLightweightPrices.value)
        message_body = {
            'prices': [{
                'selection_id': selection_id,
                'market_id': market_id,
                'polarity': polarity,
                'odds': odds,
                'delta_stake': delta_stake,
                'expire_price_at': expire_price_at,
                'expected_selection_reset_count': expected_selection_reset_count,
                'expected_withdrawal_sequence_number': expected_withdrawal_sequence_number,
                'punter_reference_number': punter_reference_number
            }],
            'expire_at': self._get_expire_at(expire_at)
        }
        envelope = self._get_envelop(message_header, message_body)
        result = self.e.dumps(envelope)
        return result

    def add_lightweight_prices(self, prices: List[dict], expire_at: Optional[float] = None) -> dict:
        """Add multiple lightweight prices in single request.
        For detailed description see `add_lightweight_price` method"""
        message_header = self._get_message_header(GBEiMessageType.addLightweightPrices.value)
        message_body = {
            'prices': prices,
            'expire_at': self._get_expire_at(expire_at),
        }
        envelope = self._get_envelop(message_header, message_body)
        return envelope
        # result = self.e.dumps(envelope)
        # return result

    def cancel_all_lightweight_prices(self, expire_at: Optional[float] = None) -> bytes:
        """Cancel all existing lightweight prices for given punter id"""
        message_header = self._get_message_header(GBEiMessageType.cancelAllLightweightPrices.value)
        message_body = {
            'expire_at': self._get_expire_at(expire_at)
        }
        envelope = self._get_envelop(message_header, message_body)
        result = self.e.dumps(envelope)
        return result

    def cancel_all_lightweight_prices_on_markets(self, market_ids: List[int],
                                                 expire_at: Optional[float] = None) -> bytes:
        """Cancel all lightweight prices for markets with given ids"""
        message_header = self._get_message_header(GBEiMessageType.cancelAllLightweightPricesOnMarkets.value)
        message_body = {
            'market_ids': market_ids,
            'expire_at': self._get_expire_at(expire_at)
        }
        envelope = self._get_envelop(message_header, message_body)
        result = self.e.dumps(envelope)
        return result

    def cancel_all_lightweight_prices_on_selections(self, selection_ids: List[int],
                                                    expire_at: Optional[float] = None) -> bytes:
        """Cancel all lightweight prices for selections with given ids"""
        message_header = self._get_message_header(GBEiMessageType.cancelAllLightweightPricesOnSelections.value)
        message_body = {
            'selection_ids': selection_ids,
            'expire_at': self._get_expire_at(expire_at)
        }
        envelope = self._get_envelop(message_header, message_body)
        result = self.e.dumps(envelope)
        return result

    def cancel_lightweight_price(self, selection_id: int, polarity: int, odds: str,
                                 punter_reference_number: int, expire_at: Optional[float] = None) -> bytes:
        """Cancel single lightweight price for given combination of parameters"""
        message_header = self._get_message_header(GBEiMessageType.cancelLightweightPrices.value)
        message_body = {
            'prices': [{
                'selection_id': selection_id,
                'polarity': polarity,
                'odds': odds,
                'punter_reference_number': punter_reference_number
            }],
            'expire_at': self._get_expire_at(expire_at)
        }
        envelope = self._get_envelop(message_header, message_body)
        result = self.e.dumps(envelope)
        return result

    def cancel_lightweight_prices(self, prices: List[dict], expire_at: Optional[float] = None) -> dict:
        """Cancel multiple lightweight prices.
        For detailed description see `cancel_lightweight_price` method"""
        message_header = self._get_message_header(GBEiMessageType.cancelLightweightPrices.value)
        message_body = {
            'prices': prices,
            'expire_at': self._get_expire_at(expire_at)
        }
        envelope = self._get_envelop(message_header, message_body)
        return envelope

    def query_all_lightweight_prices(self, punter_reference_number: int, expire_at: Optional[float] = None) -> bytes:
        """Request all currently active lightweight prices for punter.
        Useful after connection reset to sync current state.
        :param punter_reference_number: unique request id, specified by the user
        :param expire_at: time when command will expire and cancel
        """
        message_header = self._get_message_header(GBEiMessageType.queryAllLightweightPrices.value)
        message_body = {
            'punter_query_reference_number': punter_reference_number,
            'expire_at': self._get_expire_at(expire_at)
        }
        envelope = self._get_envelop(message_header, message_body)
        result = self.e.dumps(envelope)
        return result

    def query_all_lightweight_prices_on_markets(self, markets_id: List[int], punter_reference_number: int,
                                                expire_at: Optional[float] = None) -> bytes:
        """Request all currently active lightweight prices for current punter for markets with specified ids.
        Useful after connection reset to sync current state.
        :param markets_id: list of market ids to request prices for
        :param punter_reference_number: unique request id, specified by the user
        :param expire_at: time, when command will be considered as expired and so cancelled
        """
        message_header = self._get_message_header(GBEiMessageType.queryAllLightweightPricesOnMarkets.value)
        message_body = {
            'market_ids': markets_id,
            'punter_query_reference_number': punter_reference_number,
            'expire_at': self._get_expire_at(expire_at)
        }
        envelope = self._get_envelop(message_header, message_body)
        result = self.e.dumps(envelope)
        return result

    def query_all_lightweight_prices_on_selections(self, selection_ids: List[int], punter_reference_number: int,
                                                   expire_at: Optional[float] = None) -> bytes:
        """Request all currently active lightweight prices for current punter for selection with specified ids.
        Useful after connection reset to sync current state.
        :param selection_ids: list selection market ids to request prices for
        :param punter_reference_number: unique request id, specified by the user
        :param expire_at: time, when command will be considered as expired and so cancelled
        """
        message_header = self._get_message_header(GBEiMessageType.queryAllLightweightPricesOnSelections.value)
        message_body = {
            'selection_ids': selection_ids,
            'punter_query_reference_number': punter_reference_number,
            'expire_at': self._get_expire_at(expire_at)
        }
        envelope = self._get_envelop(message_header, message_body)
        result = self.e.dumps(envelope)
        return result

    def ping(self, punter_reference_number: int, expire_at: Optional[float] = None) -> bytes:
        """Ping request"""
        message_header = self._get_message_header(GBEiMessageType.ping.value)
        message_body = {
            'punter_query_reference_number': punter_reference_number,
            'expire_at': self._get_expire_at(expire_at)
        }
        envelope = self._get_envelop(message_header, message_body)
        result = self.e.dumps(envelope)
        return result

    def get_envelope(self, message_type: str, message_body: dict):
        if message_body.get('expire_at') is None:
            message_body['expire_at'] = self._get_expire_at()
        return self._get_envelop(self._get_message_header(message_type), message_body)

    def encode_request(self, message_type: str, message_body: dict):
        """Create envelope bytes from message type and body.
        `message_body` will be updated with additional values
        """
        if message_body.get('expire_at') is None:
            message_body['expire_at'] = self._get_expire_at()
        envelope = self._get_envelop(self._get_message_header(message_type), message_body)
        result = self.e.dumps(envelope)
        return result

    def keep_alive(self) -> bytes:
        """Generate empty request to keep connection alive.
        It differs from ping request in that server will not respond to this request
        whilst Ping request generates PingResponse answer from the server
        """
        return b'\x00'

    def parse_response(self, response: bytes) -> Optional[Tuple[dict, memoryview]]:
        """Parse response, generated by the server.
        Response can be of the following formats:
         LightweightPriceSummary - information about single currently active lightweight price
         LWPChangeNotification - whenever any of active prices state is changed (matched or cancelled etc)
         PingResponse - response to Ping request (`ping` method)
         ResetOccurred - reset occurred and all lightweight prices have been cancelled, so user should resubmit all
        """
        return self.e.loads(response)


if __name__ == '__main__':

    def pretty_print_bytes(b: bytes):
        from binascii import hexlify

        def chunks(lst, n):
            for i in range(0, len(lst), n):
                yield lst[i:i + n]

        b = list(chunks(hexlify(b).decode(), 2))
        b = list(chunks(b, 16))
        for row in b:
            parts = list(chunks(row, 8))
            s = ' '.join(parts[0])
            if len(parts) > 1:
                s += '   ' + ' '.join(parts[1])
            print(s)

    e = GBEiRequestEncoder(3233, 1, transport='lwps1_tcp1', decimal_as_string=True, datetime_as_timestamp=True)
    expected = dict(
        protocol_header={'version': 1},
        envelope_header={'version': 1, 'item_count': 2},
        message_header={
            'version': 1, 'type': GBEiMessageType.addLightweightPrices.value, 'type_version': 1, 'format': 'binary',
            'source': '3233', 'transport': 'lwps1_tcp1', 'priority': 3, 'interface': 'lightweightpriceserverexternal'
        },
        message={
            'command_version': 1,
            # 'command_time': datetime(2007, 6, 12, 6, 46, 42),
            'expire_at': datetime(2007, 6, 13, 6, 46, 42).timestamp(),
            'virtual_punter_id': 3233,
            'virtual_punter_session_key': 1,
            'prices': [{
                'selection_id': 1807723,
                'market_id': 338396,
                'polarity': 1,
                'odds': '3',
                'delta_stake': '3',
                'expire_price_at': datetime(2007, 6, 13, 6, 46, 42).timestamp(),
                'expected_selection_reset_count': 0,
                'expected_withdrawal_sequence_number': 0,
                'punter_reference_number': 1
            }]
        }
    )

    bts = e.add_lightweight_price(selection_id=1807723, market_id=338396, polarity=1, odds='3',
                                  delta_stake='3', expire_price_at=datetime(2007, 6, 13, 6, 46, 42).timestamp(),
                                  expected_selection_reset_count=0, expected_withdrawal_sequence_number=0,
                                  punter_reference_number=1, expire_at=datetime(2007, 6, 13, 6, 46, 42).timestamp())
    pretty_print_bytes(bts)
    parsed = e.parse_response(bts)
    if parsed:
        parsed[0]['message'].pop('command_time')
    assert parsed == expected
