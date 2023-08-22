from datetime import datetime
from pytest import fixture

from betdaq.gbei.protocol.request_encoder import GBEiRequestEncoder


@fixture(scope='session')
def encoder():
    return GBEiRequestEncoder(punter_id=3233, punter_session_key=1, decimal_as_string=True, datetime_as_timestamp=True)


def test_ping(encoder):
    bts = encoder.ping(1, datetime(2020, 1, 2, 3, 4, 5).timestamp())
    encoder.parse_response(bts)


def test_cancel_all_lightweight_prices(encoder):
    bts = encoder.cancel_all_lightweight_prices()
    encoder.parse_response(bts)


def test_cancel_all_lightweight_prices_on_markets(encoder):
    bts = encoder.cancel_all_lightweight_prices_on_markets([12345, 67890])
    encoder.parse_response(bts)


def test_cancel_all_lightweight_prices_on_selections(encoder):
    bts = encoder.cancel_all_lightweight_prices_on_selections([12345, 67890])
    encoder.parse_response(bts)


def test_cancel_lightweight_price(encoder):
    bts = encoder.cancel_lightweight_price(12345, 1, '2.0', 1)
    encoder.parse_response(bts)


def test_cancel_lightweight_prices(encoder):
    e = encoder.cancel_lightweight_prices([{'selection_id': 12345, 'polarity': 0, 'odds': '3.0',
                                            'punter_reference_number': 1}])
    encoder.parse_response(encoder.e.dumps(e))


def test_query_all_lightweight_prices(encoder):
    bts = encoder.query_all_lightweight_prices(1)
    encoder.parse_response(bts)


def test_query_all_lightweight_prices_on_markets(encoder):
    bts = encoder.query_all_lightweight_prices_on_markets([12345, 67890], 1)
    encoder.parse_response(bts)


def test_query_all_lightweight_prices_on_selections(encoder):
    bts = encoder.query_all_lightweight_prices_on_selections([12345, 67890], 1)
    encoder.parse_response(bts)


def test_add_lightweight_price(encoder):
    bts = encoder.add_lightweight_price(12345, 67890, 1, '2.0', '100',
                                        datetime(2021, 1, 2, 3, 4, 5).timestamp(), 0, 0, 1)
    encoder.parse_response(bts)


def test_add_lightweight_prices(encoder):
    e = encoder.add_lightweight_prices([{'selection_id': 12345, 'market_id': 67890, 'polarity': 1,
                                         'odds': '2.0', 'delta_stake': '100',
                                         'expire_price_at': datetime(2021, 1, 2, 3, 4, 5).timestamp(),
                                         'expected_selection_reset_count': 0,
                                         'expected_withdrawal_sequence_number': 0,
                                         'punter_reference_number': 1}])
    encoder.parse_response(encoder.e.dumps(e))
