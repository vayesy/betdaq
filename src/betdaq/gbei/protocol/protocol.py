import asyncio
from logging import getLogger
from datetime import datetime
from typing import Optional, Dict, List, Callable

from .. import settings as s
from ...aapi.utils import on_future_task_callback
from .enums import ProtocolEvents
from .request_encoder import GBEiRequestEncoder


L = getLogger(__name__)


class GBEiProtocol(asyncio.Protocol):

    def __init__(self, encoder: GBEiRequestEncoder, heartbeat_interval: float = 60):
        """
        :param encoder: initialized encoder to follow GBEi communication protocol
        :param heartbeat_interval: frequency (in seconds) of sending ping command to GBEi server
        """
        self._callbacks: Dict[ProtocolEvents, List[Callable]] = {_: [] for _ in ProtocolEvents}
        self._encoder = encoder
        self._heartbeat_interval = heartbeat_interval
        self._transport = None
        self._heartbeat_loop = None
        self._stopped = asyncio.Event()
        self._buff = b''
        self._error_seen = False

    def _apply_callbacks(self, event: ProtocolEvents, *a, **kw):
        for cb in self._callbacks[event]:
            try:
                cb(*a, **kw)
            except Exception:
                L.exception('Callback %s for %s event failed', getattr(cb, '__name__', 'empty'), event.name)

    def update_callbacks(self, other: 'GBEiProtocol'):
        """Add callbacks from another instance of protocol"""
        for k, v in other._callbacks.items():
            if v:
                self._callbacks[k].extend(v)

    def add_callback(self, event: ProtocolEvents, callback: Callable):
        self._callbacks[event].append(callback)

    def connection_made(self, transport) -> None:
        L.debug('Connection to GBEi established')
        self._transport = transport
        self._apply_callbacks(ProtocolEvents.connection_made)
        self._heartbeat_loop = asyncio.get_running_loop().create_task(self.heartbeat_cycle())
        self._heartbeat_loop.add_done_callback(on_future_task_callback)

    def connection_lost(self, exc: Optional[Exception]) -> None:
        L.debug('Connection to GBEi closed', exc_info=exc)
        self._transport = None
        self._heartbeat_loop.cancel()
        self._apply_callbacks(ProtocolEvents.connection_lost, exc)

    def data_received(self, data: bytes) -> None:
        data, self._buff = self._buff + data, b''
        while data:
            try:
                parsed = self._encoder.parse_response(data)
            except Exception:
                if self._error_seen:
                    L.error('Failed to parse incoming message %s', data)
                    self._error_seen = False
                else:
                    self._error_seen = True
                    self._buff = bytes(data)
                break
            else:
                self._error_seen = False
                if parsed is not None:
                    parsed, data = parsed
                    data = bytes(data)
                    L.debug('Received %s data', parsed)
                    self._apply_callbacks(ProtocolEvents.data_received, parsed)
                if not data:
                    break

    def on_stop(self):
        self._stopped.set()
        self._transport.close()

    def keep_alive(self):
        self._transport.write(self._encoder.keep_alive())

    def send(self, message_type: str, message_body: dict):
        """Send custom message to GBEi server. Message should contain all fields"""
        env = self._encoder.get_envelope(message_type, message_body)
        data = self._encoder.e.dumps(env)
        self._transport.write(data)
        self._apply_callbacks(ProtocolEvents.data_sent, env)

    def send_add_lightweight_prices(self, prices: List[dict], expire_at: Optional[datetime] = None):
        L.debug('Calling add prices %s', prices)
        env = self._encoder.add_lightweight_prices(prices, expire_at)
        data = self._encoder.e.dumps(env)
        self._transport.write(data)
        self._apply_callbacks(ProtocolEvents.data_sent, env)

    def send_cancel_lightweight_prices(self, prices: List[dict], expire_at: Optional[datetime] = None):
        L.debug('Calling cancel prices %s', prices)
        env = self._encoder.cancel_lightweight_prices(prices, expire_at)
        data = self._encoder.e.dumps(env)
        self._transport.write(data)
        self._apply_callbacks(ProtocolEvents.data_sent, env)

    async def heartbeat_cycle(self):
        L.debug('Starting heartbeat cycle')
        try:
            while not self._stopped.is_set() and self._transport is not None:
                L.debug('Sending keep alive')
                self.keep_alive()
                await asyncio.sleep(self._heartbeat_interval)
        except asyncio.CancelledError:
            L.debug('Stopping heartbeat cycle')
        L.debug('Heartbeat cycle finished')

    @classmethod
    async def create(cls, existing_protocol: Optional['GBEiProtocol'] = None,
                     encoder: GBEiRequestEncoder = None) -> 'GBEiProtocol':
        host, port = s.URL.split(':', 1)
        if encoder is None:
            encoder = GBEiRequestEncoder(s.PUNTER_ID, s.PUNTER_SESSION_KEY,
                                         decimal_as_string=True, datetime_as_timestamp=True)
        loop = asyncio.get_running_loop()
        factory = lambda: cls(encoder, heartbeat_interval=60)  # noqa E731
        transport, protocol = await loop.create_connection(protocol_factory=factory, host=host, port=int(port))
        if existing_protocol is not None and isinstance(protocol, cls):
            protocol.update_callbacks(existing_protocol)
        return protocol
