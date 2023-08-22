import time
import asyncio
from uuid import uuid4
from itertools import count
from logging import getLogger
from datetime import datetime
import signal
from typing import Union, Optional, List

import aiohttp

from ..common.enums import Currency, Lang, PriceFormat, ReturnCode, MarketType
from . import settings as s, __version__ as version
from .message_parser import parse_response
from .utils import clear_queue, on_future_task_callback
from .structures.enums import MessageType
from .structures import commands as c, responses as r, topics as t


L = getLogger(__name__)


class BetdaqAsyncClient(object):

    # noinspection PyTypeChecker
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.s: aiohttp.ClientSession = None
        self.ws: aiohttp.ClientWebSocketResponse = None
        self.loop = loop
        self._meta_task = None
        self._cor_id: count = None
        self._subscribed_events = set()
        self._next_ws_commands_schedule = {
            c.SubscribeEventHierarchy: [],
            c.SubscribeDetailedMarketPrices: [],
            c.SubscribeMarketInformation: [],
            c.SubscribeMarketMatchedAmounts: []
        }  # command type: commands list
        self._next_ws_command_timestamps = dict.fromkeys([
            c.SubscribeEventHierarchy, c.SubscribeDetailedMarketPrices,
            c.SubscribeMarketInformation, c.SubscribeMarketMatchedAmounts], 0)  # command type: timestamp
        self._ws_queue = asyncio.PriorityQueue()
        self._ws_event: asyncio.Event = None
        self._ws_handlers = {
            r.LogonPunter: self.on_login,
            r.SetAnonymousSessionContext: self.on_login,
            r.SetRefreshPeriod: self.on_set_refresh_period,
            r.SubscribeEventHierarchy: self.on_market_event,
            r.SubscribeMarketInformation: self.on_market_event,
            r.SubscribeDetailedMarketPrices: self.on_market_event,
            r.SubscribeMarketMatchedAmounts: self.on_market_event,

            t.Language4: self.on_language4,
            t.MExchangeInfo: self.on_mexchangeinfo
        }

    @property
    def client_identifier(self):
        return f'betdaq-price-server-{version}'

    def _get_ws_connection_kwargs(self):
        kwargs = dict(url=s.STREAM_URL, receive_timeout=s.RECEIVE_TIMEOUT, timeout=s.TIMEOUT)
        return kwargs

    async def init_ws(self, first_attempt: bool = False):
        self._cor_id = iter(count())
        self.s = aiohttp.ClientSession(loop=self.loop)
        kwargs = self._get_ws_connection_kwargs()
        if first_attempt:
            attempts = range(5)
        else:
            attempts = count()
        pause_times = iter([5, 30, 60])
        for attempt in attempts:
            if self._ws_event.is_set():
                await self.s.close()
                break
            try:
                self.ws = await self.s.ws_connect(**kwargs)
            except Exception:
                L.warning({'message': 'Failed to initialize connection', 'attempt': attempt}, exc_info=True)
                pause_time = next(pause_times, s.CONNECTION_TIMEOUT)
                await asyncio.sleep(pause_time)
            else:
                break
        else:
            L.error({'message': 'All connection attempts failed, stopping'})
            return None
        return self.ws

    def queue_ws_command(self, cmd: c.Command, priority: int):
        cmd.correlation_id = next(self._cor_id)
        self._ws_queue.put_nowait((priority, cmd))

    def queue_command_with_limit(self, cmd: Union[c.SubscribeEventHierarchy, c.SubscribeDetailedMarketPrices,
                                                  c.SubscribeMarketInformation, c.SubscribeMarketMatchedAmounts]):
        """Make sure commands of this type get executed only once per second due to API limitations"""
        cmd.correlation_id = next(self._cor_id)
        key = type(cmd)
        self._next_ws_commands_schedule[key].append(cmd)

    async def send_ws_command(self, cmd: c.Command, assign_cor_id: bool = True):
        sent = False
        if self.ws is None:
            return sent
        if assign_cor_id:
            cmd.correlation_id = next(self._cor_id)
        L.debug({'message': 'Sending WS command', 'command_type': type(cmd).__name__, 'msg': cmd.dump()})
        try:
            await self.ws.send_str(cmd.dump())
        except Exception:
            L.error({'message': 'Failed to send command'}, exc_info=True)
        else:
            sent = True
        return sent

    def get_next_messages_to_send(self) -> List[c.Command]:
        commands = []
        ts = time.time()
        for command_type, next_ts in self._next_ws_command_timestamps.items():
            if ts >= next_ts:
                items = self._next_ws_commands_schedule[command_type]
                if items:
                    commands.append(items.pop(0))
        try:
            priority, cmd = self._ws_queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
        else:
            self._ws_queue.task_done()
            commands.append(cmd)
        return commands

    async def subscribe_events_loop(self):
        L.info('Starting subscribe events loop')
        try:
            while not self._ws_event.is_set():
                for group_id in s.META_REFRESH_CLASSIFIERS:
                    cmd = c.SubscribeEventHierarchy(
                        event_classifier_id=group_id,
                        want_selection_information=False,
                        want_selection_blurb=False,
                        want_direct_descendants_only=True,
                        market_types_to_include=[MarketType.Win]
                    )
                    self.queue_command_with_limit(cmd)
                await asyncio.sleep(s.META_REFRESH_PERIOD)
        except asyncio.CancelledError:
            L.debug('Stopping subscribe events loop')
        except Exception:
            L.exception('Error in subscribe events loop')
        L.info('End of subscribe events loop')

    async def queue_login(self):
        """Initialize communication with server by sending
        LogonPunter or SetAnonymousSessionContext command
        """
        cmd_kwargs = dict(
            currency=Currency.GBP, aapi_version=s.AAPI_VERSION,
            client_identifier=self.client_identifier,
            client_specified_guid=str(uuid4()), language=Lang.en
        )
        if s.USERNAME and s.PASSWORD:
            cmd = c.LogonPunter(
                partner_username=s.USERNAME,
                cleartext_password=s.PASSWORD,
                **cmd_kwargs
            )
            L.debug({'message': 'API credentials provided, initializing user session'})
        else:
            cmd = c.SetAnonymousSessionContext(
                price_format=PriceFormat.Decimal,
                **cmd_kwargs
            )
            L.debug({'message': 'API credentials not provided, initializing anonymous session'})
        self.queue_ws_command(cmd, 1)

    async def unsubscribe(self):
        cmd = c.Unsubscribe()
        self.queue_ws_command(cmd, 0)

    async def on_login(self, resp: Union[r.LogonPunter, r.SetAnonymousSessionContext]):
        if resp.return_code != ReturnCode.Success:
            L.error({'message': 'Failed to initialize session, received invalid return code',
                     'return_code': resp.return_code.name})
            return
        cmd = c.SetRefreshPeriod(refresh_period_ms=s.REFRESH_PERIOD * 1000)
        self.queue_ws_command(cmd, 1)

    async def on_set_refresh_period(self, resp: r.SetRefreshPeriod):
        L.info('Setting refresh period to %s ms', resp.refresh_period_ms)
        task = self.loop.create_task(self.subscribe_events_loop())
        task.add_done_callback(on_future_task_callback)
        self._meta_task = task

    async def on_market_event(self, resp):
        if resp.available_markets_count == 0:
            L.error({'message': 'No more market subscriptions allowed'})
            return

    async def on_language4(self, resp: t.Language4):
        classifiers = resp.topic_kwargs.get('event_classifier_id', {})
        event_id = classifiers.get('event_id')
        if resp.head.message_type == MessageType.Delete:
            self._subscribed_events.discard(event_id)
            return
        if event_id is not None:
            if event_id in self._subscribed_events:
                return
            cmd = c.SubscribeMarketInformation(
                event_classifier_id=event_id,
                want_direct_descendants_only=True,
                want_selection_information=True,
                market_types_to_include=[MarketType.Win]
            )
            self.queue_command_with_limit(cmd)
            self._subscribed_events.add(event_id)
        else:
            location_id = classifiers.get('location_id')
            if location_id:
                cmd = c.SubscribeEventHierarchy(
                    event_classifier_id=location_id,
                    want_selection_information=False,
                    want_selection_blurb=False,
                    want_direct_descendants_only=True,
                    market_types_to_include=[MarketType.Win]
                )
                self.queue_command_with_limit(cmd)

    async def on_mexchangeinfo(self, resp: t.MExchangeInfo):
        if resp.head.message_type == MessageType.Delete:
            return
        market_id = resp.market_id or resp.topic_kwargs.get('market_id')
        if market_id is None:
            return
        if resp.number_winning_places:
            L.debug('Skipping sportsbook win market %s', market_id)
            return

        cmd = c.SubscribeDetailedMarketPrices(
            number_back_prices=s.PRICES_NUMBER,
            number_lay_prices=s.PRICES_NUMBER,
            filter_by_volume=s.FILTER_BY_VOLUME,
            market_ids=[market_id]
        )  # when changing filter_by_volume, prices can differ from the ones on site
        self.queue_command_with_limit(cmd)

        cmd = c.SubscribeMarketMatchedAmounts(
            market_ids=[market_id]
        )
        self.queue_command_with_limit(cmd)

    async def handle_ws_response(self, response: Optional[Union[t.BaseTopic, r.Response]]):
        if response is None:
            return
        response_type = type(response)
        L.debug({'message': 'Incoming ws message', 'response_type': response_type.__name__})
        if issubclass(response_type, r.Response):
            allowed_codes = {ReturnCode.Success, ReturnCode.EventClassifierDoesNotExist}
            if response.return_code not in allowed_codes:
                L.error({'message': 'Unexpected return code for command',
                         'return_code': response.return_code.name,
                         'command_name': type(response).__name__})
                await self.ws.close()
                return
        handler = self._ws_handlers.get(response_type)
        if handler is not None:
            # noinspection PyArgumentList
            await handler(response)

    async def ping_loop(self, frequency: float = 30):
        L.info('Starting ping loop')
        while not self._ws_event.is_set():
            cmd = c.Ping(current_client_time=datetime.utcnow())
            try:
                sent = await self.send_ws_command(cmd)
                L.debug({'message': 'Sent ping request', 'result': sent})
                if not sent:
                    break
                await asyncio.sleep(frequency)
            except asyncio.CancelledError:
                break
            except Exception:
                L.warning('Exception happened during ping loop', exc_info=True)
                await asyncio.sleep(frequency)
        L.info('Finished ping loop')

    async def receive_messages_loop(self, cnt_func):
        while not self._ws_event.is_set():
            if self.ws is None or self.ws.closed or self.ws._closing:
                L.info('WS connection closed, stop receiving messages')
                break
            try:
                async for msg in self.ws:
                    if msg.type != aiohttp.WSMsgType.TEXT:
                        break
                    next(cnt_func)
                    resp = parse_response(msg.data)
                    try:
                        await self.handle_ws_response(resp)
                    except Exception:
                        L.error({'message': 'Failed to process response', 'response': repr(resp)}, exc_info=True)
                    if self._ws_event.is_set():
                        break
                # when for loop finished, connection is closed
                return
            except (asyncio.CancelledError, asyncio.TimeoutError):
                continue
            except Exception:
                L.warning('Received error during messages receive loop', exc_info=True)
                continue

    def on_stop(self):
        L.debug({'message': 'Close event triggered'})
        if self._ws_event is not None:
            self._ws_event.set()

    async def run_send(self):
        while self._ws_event is None:
            await asyncio.sleep(0.1)

        global_send_timeout = s.CALL_TIMEOUTS['global']
        L.debug('Starting AAPI send loop')
        while not self._ws_event.is_set():
            if self.ws is None or self.ws.closed or self.ws._closing:
                await asyncio.sleep(global_send_timeout)
                continue
            messages = self.get_next_messages_to_send()
            for msg in messages:
                msg_type = type(msg)
                await self.send_ws_command(msg, False)
                msg_timeout = s.CALL_TIMEOUTS.get(msg_type.__name__)
                if msg_timeout is not None:
                    self._next_ws_command_timestamps[msg_type] = time.time() + msg_timeout
                await asyncio.sleep(global_send_timeout)
            await asyncio.sleep(global_send_timeout)
        L.debug('Finished AAPI send loop')

    async def run_receive(self):
        for sig in (signal.SIGINT, signal.SIGTERM):
            self.loop.add_signal_handler(sig, self.on_stop)
        self._ws_event = asyncio.Event(loop=self.loop)
        first = True
        L.info('Starting AAPI receive loop')
        while not self._ws_event.is_set():
            ws = await self.init_ws(first)
            if ws is None:
                L.info('Connection closed after initialization')
                if first:
                    L.info('Stopping client due to failed initialized connection')
                    break
                else:
                    continue
            first = False
            await self.queue_login()
            ping_loop = self.ping_loop(s.PING_FREQUENCY)
            ping_loop = self.loop.create_task(ping_loop)
            ping_loop.add_done_callback(on_future_task_callback)
            cnt = iter(count())
            await self.receive_messages_loop(cnt)
            L.info({'message': 'Connection closed', 'processed_messages': next(cnt)})
            self._subscribed_events.clear()
            clear_queue(self._ws_queue)
            for k in self._next_ws_commands_schedule:
                self._next_ws_commands_schedule[k].clear()
                self._next_ws_command_timestamps[k] = 0
            if self._meta_task is not None and not self._meta_task.cancelled():
                self._meta_task.cancel()
                try:
                    await self._meta_task
                except asyncio.CancelledError:
                    pass
            if not ping_loop.cancelled():
                ping_loop.cancel()
                try:
                    await ping_loop
                except asyncio.CancelledError:
                    pass
            if self.ws is not None:
                if not self.ws.closed:
                    await self.unsubscribe()
                await self.ws.close()
                self.ws = None
                # noinspection PyUnresolvedReferences
                await self.s.close()
                self.s = None
            await asyncio.sleep(1)
        clear_queue(self._ws_queue)
        L.info('AAPI client finished')
