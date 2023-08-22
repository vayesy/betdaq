from datetime import datetime
from pytest import mark

from betdaq.common.enums import MarketType, Currency
from betdaq.aapi.structures import fields as f


class TestFields:

    @classmethod
    def setup_class(cls):
        cls.instance = type('InstanceForTestFields', (object,), {})()

    @mark.parametrize('field_cls, raw_value, parsed_value', (
        (f.Str, 'test', 'test'),
        (f.Int, '10', 10),
        (f.Float, '11.53', 11.53),
        (f.Bool, 'F', False),
        (f.Bool, 'T', True),
        (f.DateTime, '2020-12-31T23:59:59.000000Z', datetime(2020, 12, 31, 23, 59, 59, 0))
    ))
    def test_base_fields(self, field_cls, raw_value, parsed_value):
        field = field_cls(order=0, name='test_load_field')
        assert field.load(raw_value, self.instance) == parsed_value
        assert field.dump(parsed_value, self.instance, False) == raw_value

    def test_enum(self):
        field = f.Enum(Currency, order=0)
        assert field.load('GBP', self.instance) == Currency.GBP
        assert field.dump(Currency.GBP, self.instance, False) == Currency.GBP.value

        field = f.Enum(MarketType, parse_func=int, order=1)
        assert field.load('1', self.instance) == MarketType.Win
        assert field.dump(MarketType.Win, self.instance, False) == str(MarketType.Win.value)

    def test_readonly_nested_field(self):
        field = f.ReadOnlyNestedField(order=1, fields={'test1': f.Int(order=1), 'test3': f.Float(order=2)})
        single = field.load({1: '15', 2: '5.1', 3: 'Unknown field'}, self.instance)
        assert single.__dict__ == {'test1': 15, 'test3': 5.1}
        field.name = 'Test'
        as_list = field.load([{1: '10', 2: '0.1'}, {1: '15'}], self.instance)
        assert isinstance(as_list, list) and len(as_list) == 2
        assert as_list[0].__dict__ == {'test1': 10, 'test3': 0.1}
        assert as_list[1].__dict__ == {'test1': 15}

    def test_str_joined_field(self):
        field = f.StrJoinedField(f.Int(order=0), '~', order=0, name='market_ids')
        raw, parsed = '123~456~789', [123, 456, 789]
        assert field.load(raw, self.instance) == parsed
        assert field.dump(parsed, self.instance, False)

    def test_read_only_str_joined_nested_field(self):
        field = f.ReadOnlyStrJoinedNestedField(separator='_', fields=dict(
            success=f.Bool(order=0, name='success'),
            market_id=f.Int(order=1),
            market_type=f.Enum(MarketType, int, order=2)
        ))
        res = field.load(f'_10_{MarketType.Win.value}_', self.instance)
        assert res == {'success': None, 'market_id': 10, 'market_type': MarketType.Win}
