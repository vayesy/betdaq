import asyncio
from itertools import count
import time

from pytest import fixture, mark
from aiohttp import WSMessage, WSMsgType, ClientConnectionError

from betdaq.common.enums import ReturnCode
from betdaq.aapi import settings as s
from betdaq.aapi.client import BetdaqAsyncClient
from betdaq.aapi.structures.head import Head, MessageType
from betdaq.aapi.structures import commands, responses, topics


@fixture()
def aapi_client(event_loop, mocker, coro_mock):
    ws_event = mocker.Mock()
    ws_event.is_set.return_value = False
    cli = BetdaqAsyncClient(event_loop)
    mocker.patch.multiple(cli, send_ws_command=coro_mock(return_value=None),
                          _ws_event=ws_event, _cor_id=iter(count()))
    mocker.patch.object(commands.Command.correlation_id, 'required', False)
    yield cli


@fixture()
def test_settings(mocker):
    mocker.patch.multiple(
        s,
        STREAM_URL='wss://betdaq-test-url.com/websocket',
        RECEIVE_TIMEOUT=10.,
        PRICES_NUMBER=3,
        FILTER_BY_VOLUME=1,
        REFRESH_PERIOD=1,
        USERNAME='testU',
        PASSWORD='testP',
    )
    yield s


@fixture()
def async_for_object():

    class AsyncForMock(object):

        def __init__(self, items, **kw):
            self.iterable = iter(items)
            self.__dict__.update(**kw)

        def __aiter__(self):
            return self

        async def __anext__(self):
            try:
                return next(self.iterable)
            except StopIteration:
                raise StopAsyncIteration

    return AsyncForMock


class TestInitWs:

    @mark.asyncio
    async def test_init_ws_ok(self, mocker, coro_mock, test_settings, aapi_client):
        session_cls = mocker.patch(f'{BetdaqAsyncClient.__module__}.aiohttp.ClientSession')
        ws_connect = coro_mock(return_value=mocker.Mock())
        session_cls.return_value.ws_connect = ws_connect
        await aapi_client.init_ws(mocker.Mock())
        session_cls.assert_called_once()
        ws_connect.assert_called_once_with(
            url=test_settings.STREAM_URL,
            receive_timeout=10.,
            timeout=10
        )

    @mark.asyncio
    async def test_init_ws_retries_first_attempt(self, mocker, coro_mock, aapi_client):
        session_cls = mocker.patch(f'{BetdaqAsyncClient.__module__}.aiohttp.ClientSession')
        sleep = mocker.patch(f'{BetdaqAsyncClient.__module__}.asyncio.sleep', coro_mock(None))
        side_effect = iter((ClientConnectionError,)*4 + (mocker.Mock(),))

        async def ws_connect(*a, **kw):
            result = next(side_effect)
            if isinstance(result, type) and issubclass(result, Exception):
                raise result
            return result

        ws_connect = mocker.Mock(wraps=ws_connect)
        session_cls.return_value.ws_connect = ws_connect
        await aapi_client.init_ws(first_attempt=True)
        assert ws_connect.call_count == 5
        assert sleep.mock_calls == [mocker.call(pause) for pause in (5, 30, 60, 60)]
        assert aapi_client.ws is not None

    @mark.asyncio
    async def test_init_ws_retries_second_attempt(self, mocker, coro_mock, aapi_client):
        mocker.patch.object(s, 'CONNECTION_TIMEOUT', 100)
        session_cls = mocker.patch(f'{BetdaqAsyncClient.__module__}.aiohttp.ClientSession')
        sleep = mocker.patch(f'{BetdaqAsyncClient.__module__}.asyncio.sleep', coro_mock(None))
        side_effect = iter((ClientConnectionError,) * 5 + (mocker.Mock(),))

        async def ws_connect(*a, **kw):
            result = next(side_effect)
            if isinstance(result, type) and issubclass(result, Exception):
                raise result
            return result

        ws_connect = mocker.Mock(wraps=ws_connect)
        session_cls.return_value.ws_connect = ws_connect
        await aapi_client.init_ws(first_attempt=False)
        assert ws_connect.call_count == 6
        assert sleep.mock_calls == [mocker.call(pause) for pause in (5, 30, 60, 100, 100)]
        assert aapi_client.ws is not None


class TestSendLogin:

    @mark.asyncio
    async def test_login_username(self, aapi_client, test_settings, mocker):
        mocker.patch.multiple(aapi_client, loop=mocker.Mock(), queue_ws_command=mocker.Mock())
        await aapi_client.queue_login()
        aapi_client.queue_ws_command.assert_called_once()
        aapi_client.send_ws_command.assert_not_called()
        command = aapi_client.queue_ws_command.call_args[0][0]
        assert isinstance(command, commands.LogonPunter)
        assert command.partner_username == test_settings.USERNAME
        assert command.cleartext_password == test_settings.PASSWORD

    @mark.asyncio
    async def test_login_anonymous(self, aapi_client, test_settings, mocker):
        mocker.patch.multiple(test_settings, USERNAME=None, PASSWORD=None)
        mocker.patch.multiple(aapi_client, loop=mocker.Mock(), queue_ws_command=mocker.Mock())
        await aapi_client.queue_login()
        aapi_client.queue_ws_command.assert_called_once_with(commands.SetAnonymousSessionContext(
            currency=mocker.ANY, aapi_version=mocker.ANY,
            client_identifier=mocker.ANY, client_specified_guid=mocker.ANY,
            language=mocker.ANY, price_format=mocker.ANY
        ), 1)


class TestStartSubscription:

    @mark.asyncio
    async def test_subscribed(self, aapi_client, test_settings, mocker):
        mocker.patch.multiple(aapi_client, loop=mocker.Mock(), queue_command_with_limit=mocker.Mock())
        mocker.patch.object(s, 'META_REFRESH_PERIOD', 0.1)
        aapi_client._ws_event.is_set.side_effect = (False, True)
        await aapi_client.subscribe_events_loop()
        calls = []
        for classifier_id in s.META_REFRESH_CLASSIFIERS:
            calls.append(mocker.call(commands.SubscribeEventHierarchy(
                event_classifier_id=classifier_id, want_selection_information=False,
                want_selection_blurb=False, want_direct_descendants_only=True,
                market_types_to_include=[commands.MarketType.Win]
            )))
        aapi_client.queue_command_with_limit.assert_has_calls(calls)


class TestResponseHandling:

    @mark.asyncio
    async def test_on_login(self, aapi_client, mocker, test_settings):
        mocker.patch.object(aapi_client, 'queue_ws_command', mocker.Mock())
        response = responses.SetAnonymousSessionContext(Head(), return_code=ReturnCode.Success)
        await aapi_client.on_login(response)
        aapi_client.queue_ws_command.assert_called_once_with(commands.SetRefreshPeriod(
            refresh_period_ms=test_settings.REFRESH_PERIOD * 1000
        ), 1)

    @mark.asyncio
    async def test_on_set_refresh_period_response(self, aapi_client, mocker, coro_mock):
        coro = coro_mock(None)
        mocker.patch.object(aapi_client, 'subscribe_events_loop', coro)
        response = responses.SetRefreshPeriod(Head())
        await aapi_client.on_set_refresh_period(response)
        coro.assert_called_once()

    @mark.asyncio
    async def test_on_language4_response_with_location(self, aapi_client, mocker):
        mocker.patch.object(aapi_client, 'queue_ws_command')
        mocker.patch.object(aapi_client, 'queue_command_with_limit')
        location_id = 123
        response = topics.Language4(
            name='Daily Events', head=Head(),
            topic_kwargs={'event_classifier_id': {'location_id': location_id}}
        )
        await aapi_client.on_language4(response)
        aapi_client.queue_command_with_limit.assert_called_once_with(commands.SubscribeEventHierarchy(
            event_classifier_id=location_id, want_selection_information=False,
            want_selection_blurb=False, want_direct_descendants_only=True,
            market_types_to_include=[commands.MarketType.Win]
        ))
        aapi_client.queue_ws_command.assert_not_called()

    @mark.asyncio
    async def test_on_language4_response_with_event(self, aapi_client, mocker):
        mocker.patch.object(aapi_client, 'queue_ws_command')
        mocker.patch.object(aapi_client, 'queue_command_with_limit')
        event_id = 123
        response = topics.Language4(
            name='Ayr (Today)', head=Head(),
            topic_kwargs={'event_classifier_id': {'event_id': event_id}}
        )
        await aapi_client.on_language4(response)
        aapi_client.queue_command_with_limit.assert_called_once_with(commands.SubscribeMarketInformation(
            event_classifier_id=event_id, want_direct_descendants_only=True,
            want_selection_information=True, market_types_to_include=mocker.ANY
        ))
        aapi_client.queue_ws_command.assert_not_called()

    @mark.asyncio
    async def test_on_mexchangeinfo(self, aapi_client, mocker):
        mocker.patch.object(aapi_client, 'queue_ws_command')
        event_id = 123
        response = topics.MExchangeInfo(
            name='Ayr (Today)', head=Head(message_type=MessageType.Delete),
            topic_kwargs={'event_classifier_id': {'event_id': event_id}}
        )
        await aapi_client.on_mexchangeinfo(response)
        aapi_client.queue_ws_command.assert_not_called()

    @mark.asyncio
    async def test_on_market_event(self, aapi_client):
        response = responses.SubscribeMarketInformation(Head())
        await aapi_client.on_market_event(response)


@mark.asyncio
async def test_run_receive(event_loop, aapi_client, mocker, coro_mock, async_for_object):
    messages = [
        'AAPI/6/D\u000220\u0002F\u00010\u00021984840034\u00011\u00020\u00013\u00022~3\u0001'  # unsubscribe
    ]
    messages = [WSMessage(WSMsgType.TEXT, _, '') for _ in messages]
    messages.append(WSMessage(WSMsgType.CLOSE, '', ''))
    ws = async_for_object(messages, closed=False, close=coro_mock(None))
    ws._closing = False
    ws_connect = coro_mock(ws)
    ping_loop = coro_mock(None)
    ping_loop.cancelled = mocker.Mock(return_value=True)
    ping_loop.add_done_callback = mocker.Mock()
    mocker.patch.object(aapi_client, 'ping_loop', return_value=ping_loop)
    queue_login = coro_mock(None)
    create_task = mocker.patch.object(event_loop, 'create_task')
    session_cls = mocker.patch(f'{BetdaqAsyncClient.__module__}.aiohttp.ClientSession')
    session_cls.return_value.ws_connect = ws_connect
    session_cls.return_value.close = coro_mock(None)
    mocker.patch.multiple(aapi_client, queue_login=queue_login, ping_loop=ping_loop)
    event_loop.call_later(1, lambda: aapi_client._ws_event.set())
    await aapi_client.run_receive()
    queue_login.assert_called_once()
    create_task.assert_called_once()


@mark.asyncio
async def test_run_send_no_commands(event_loop, aapi_client, mocker):
    mocker.patch.multiple(aapi_client, get_next_messages_to_send=mocker.Mock(return_value=[]), ws=mocker.Mock())
    aapi_client.ws.closed = False
    aapi_client.ws._closing = False
    aapi_client._ws_event.is_set.side_effect = [False, True]
    await aapi_client.run_send()
    aapi_client.get_next_messages_to_send.assert_called_once()


@mark.asyncio
async def test_run_send_with_command(event_loop, aapi_client, mocker, coro_mock):
    mocker.patch.object(asyncio, 'sleep', coro_mock(None))
    mocker.patch.multiple(aapi_client, get_next_messages_to_send=mocker.Mock(return_value=[
        commands.SetAnonymousSessionContext(),
        commands.SetRefreshPeriod(refresh_period_ms=1000),
        commands.SubscribeEventHierarchy(event_classifier_id=1),
        commands.Unsubscribe()
    ]), ws=mocker.Mock())
    aapi_client.ws.closed = False
    aapi_client.ws._closing = False
    aapi_client._ws_event.is_set.side_effect = [False, True]
    await aapi_client.run_send()
    assert aapi_client.send_ws_command.call_count == 4
    assert asyncio.sleep.call_count == 5
    ts_from = time.time() + 0.9
    ts_to = time.time() + 1.1
    assert ts_to >= aapi_client._next_ws_command_timestamps[commands.SubscribeEventHierarchy] >= ts_from


def test_get_next_messages_to_send_empty(aapi_client):
    assert aapi_client.get_next_messages_to_send() == []


def test_get_next_messages_to_send_on_timeout(aapi_client):
    cmd = commands.SubscribeEventHierarchy(event_classifier_id=1, want_direct_descendants_only=True,
                                           want_selection_information=False)
    aapi_client._next_ws_commands_schedule[commands.SubscribeEventHierarchy].append(cmd)
    aapi_client._next_ws_command_timestamps[commands.SubscribeEventHierarchy] = time.time() + 5
    assert aapi_client.get_next_messages_to_send() == []


def test_get_next_messages_to_send_commands(aapi_client):
    cmd1 = commands.SubscribeEventHierarchy(event_classifier_id=1, want_direct_descendants_only=True,
                                            want_selection_information=False)
    cmd2 = commands.SubscribeMarketMatchedAmounts(event_classifier_id=1)
    cmd3 = commands.SubscribeMarketMatchedAmounts(event_classifier_id=2)
    for cmd in (cmd1, cmd2, cmd3):
        aapi_client._next_ws_commands_schedule[type(cmd)].append(cmd)
        aapi_client._next_ws_command_timestamps[type(cmd)] = time.time()
    cmd4 = commands.SetRefreshPeriod(refresh_period_ms=1000)
    aapi_client.queue_ws_command(cmd4, 1)
    assert aapi_client.get_next_messages_to_send() == [cmd1, cmd2, cmd4]


def test_get_next_messages_to_send_mixed(aapi_client):
    cmd1 = commands.SubscribeEventHierarchy(event_classifier_id=1, want_direct_descendants_only=True,
                                            want_selection_information=False)
    cmd2 = commands.SubscribeMarketMatchedAmounts(event_classifier_id=1)
    cmd3 = commands.SubscribeMarketMatchedAmounts(event_classifier_id=2)
    for cmd in (cmd1, cmd2, cmd3):
        aapi_client._next_ws_commands_schedule[type(cmd)].append(cmd)
    aapi_client._next_ws_command_timestamps[type(cmd1)] = time.time()
    aapi_client._next_ws_command_timestamps[type(cmd2)] = time.time() + 5
    cmd4 = commands.SetRefreshPeriod(refresh_period_ms=1000)
    aapi_client.queue_ws_command(cmd4, 1)
    assert aapi_client.get_next_messages_to_send() == [cmd1, cmd4]
