from betdaq.common.enums import PriceFormat, Currency
from betdaq.aapi.structures import topics as t


class TestTopicTitle:

    def test_title_ok(self):
        title = t.TopicTitle(t.f.Int(order=0))
        assert title.load('15') == 15

    def test_title_normalize(self):
        title = t.TopicTitle(t.f.Int(order=0, name='market_id'), normalize=lambda x: x.strip('_'))
        assert title.load('_123456_') == 123456

    def test_title_invalid(self):
        title = t.TopicTitle(t.f.Int(order=0, name='market_id'))
        assert title.load('NaN') is None


class TestResolveTopic:
    def test_resolve_event1(self):
        topic = 'AAPI/3/E/E_1'
        cls, kwargs = t.resolve_data_message(topic)
        assert cls is t.Event1
        assert kwargs == {'event_classifier_id': {'parent': 1}}

    def test_resolve_market1(self):
        topic = 'AAPI/3/E/E_1/E/E_100004/E/E_100289/E/E_5100309/E/E_5100394/M/E_12759206'
        cls, kwargs = t.resolve_data_message(topic)
        assert cls is t.Market1
        assert kwargs == {'event_classifier_id': {'parent': 1, 'sport_id': 100004, 'sport_group_id': 100289,
                                                  'location_id': 5100309, 'event_id': 5100394}, 'market_id': 12759206}

    def test_resolve_back_lay_volume_currency_format(self):
        topic = 'AAPI/6/E/E_1/E/E_100004/E/E_190538/E/E_4100115/E/E_4100118/M/E_333542/MEI/MDP/3_3_100_EUR_1'
        cls, kwargs = t.resolve_data_message(topic)
        assert cls is t.BackLayVolumeCurrencyFormat
        assert kwargs == {
            'event_classifier_id': {
                'parent': 1, 'sport_id': 100004, 'sport_group_id': 190538,
                'location_id': 4100115, 'event_id': 4100118
            },
            'market_id': 333542,
            'desired_back_prices': 3,
            'desired_lay_prices': 3,
            'desired_market_by_volume': 100,
            'currency_code': Currency.EUR,
            'price_format': PriceFormat.Decimal
        }

    def test_unknown_topic(self):
        topic = 'AAPI/3/E/E_1/INVALID'
        cls, kwargs = t.resolve_data_message(topic)
        assert cls is None
        assert kwargs == {'event_classifier_id': {'parent': 1}}
        topic += '/ANOTHER'
        cls, kwargs = t.resolve_data_message(topic)
        assert cls is kwargs is None


def test_topic_load():
    topic_cls = type('TestTopic', (t.BaseTopic,), {'test1': t.f.Int(order=1)})
    topic = topic_cls.load({1: '2', 2: 'unknown'}, head=None, topic_kwargs={})
    assert topic.test1 == 2
