from pytest import fixture

pytest_plugins = 'aiohttp.pytest_plugin'


@fixture()
def coro_mock(mocker):
    def inner(return_value):
        async def coro(*a, **kw):
            return return_value
        return mocker.Mock(wraps=coro)
    return inner
