from datetime import datetime
from decimal import Decimal as DecimalNative

from pytest import mark

from betdaq.gbei.protocol.fields import DateTime, Decimal, Int, Length, Long,\
    String, MoneyAmount, Optional, Array, Enum
from betdaq.gbei.protocol.enums import LWPActionType


@mark.parametrize('dt, as_timestamp', [
    (datetime(2020, 1, 1), False),
    (datetime(2020, 1, 2, 3, 4, 5), False),
    (1605801993, True)
])
def test_datetime(dt, as_timestamp):
    f = DateTime(as_timestamp=as_timestamp)
    dumped = f.dumps(dt)
    loaded, remaining_bts = f.loads(memoryview(dumped))
    assert loaded == dt
    assert not bytes(remaining_bts)


@mark.parametrize('as_string, value, bts', [
    (False, DecimalNative('1'), b'\x01' + b'\x00' * 15),
    (False, DecimalNative('1.0'), b'\x0a' + b'\x00' * 13 + b'\x01\x00'),
    (False, DecimalNative('-1.0'), b'\x0a' + b'\x00' * 13 + b'\x01\x80'),
    (False, DecimalNative('100000.00000'), b'\x00\xe4\x0b\x54\x02' + b'\x00' * 9 + b'\x05\x00'),
    (False, DecimalNative('1234567890123456789012345678'), b'\x4e\xf3\x38\xbe\x91\x7a\x79\x6d\xeb\x35\xfd\x03\x00\x00\x00\x00'),
    (False, DecimalNative('1234567890.123456789012345678'), b'\x4e\xf3\x38\xbe\x91\x7a\x79\x6d\xeb\x35\xfd\x03\x00\x00\x12\x00'),
    (True, '1', b'\x01' + b'\x00' * 15),
    (True, '-1', b'\x01' + b'\x00' * 14 + b'\x80'),
    (True, '1234567890123456789012345678', b'\x4e\xf3\x38\xbe\x91\x7a\x79\x6d\xeb\x35\xfd\x03\x00\x00\x00\x00'),
    (True, '1234567890.123456789012345678', b'\x4e\xf3\x38\xbe\x91\x7a\x79\x6d\xeb\x35\xfd\x03\x00\x00\x12\x00')
])
def test_decimal(as_string, value, bts):
    f = Decimal(as_string)
    dumped = f.dumps(value)
    assert dumped == bts
    loaded, remaining_bts = f.loads(memoryview(dumped))
    assert loaded == value
    assert not bytes(remaining_bts)


@mark.parametrize('value, bts', [
    (1, b'\x01\x00\x00\x00'),
    (1234567890, b'\xd2\x02\x96\x49'),
    (-1234567890, b'\x2e\xfd\x69\xb6'),
    (-2147483647, b'\x01\x00\x00\x80'),
    (-2147483648, b'\x00\x00\x00\x80')
])
def test_int(value, bts):
    f = Int()
    dumped = f.dumps(value)
    assert dumped == bts
    loaded, remaining_bts = f.loads(memoryview(dumped))
    assert loaded == value
    assert not bytes(remaining_bts)


@mark.parametrize('value, bts, raw', [
    (LWPActionType.Expired, b'\x08\x00\x00\x00', False),
    (LWPActionType.CancelledExplicitly, b'\x01\x00\x00\x00', False),
    (LWPActionType.LWPDoesNotExist, b'\x0b\x00\x00\x00', False),
    (LWPActionType.LWPDoesNotExist.value, b'\x0b\x00\x00\x00', True)
])
def test_enum(value, bts, raw):
    f = Enum(Int(), LWPActionType, raw)
    dumped = f.dumps(value)
    assert dumped == bts
    loaded, remaining_bts = f.loads(memoryview(dumped))
    assert loaded == value
    assert not bytes(remaining_bts)


@mark.parametrize('value, bts', [
    (0, b'\x00'),
    (1, b'\x01'),
    (255, b'\x81\x7f'),
    (1234, b'\x89\x52'),
    (123456, b'\x87\xc4\x40')
])
def test_length(value, bts):
    f = Length()
    dumped = f.dumps(value)
    assert dumped == bts
    loaded, remaining_bts = f.loads(memoryview(dumped))
    assert loaded == value
    assert not bytes(remaining_bts)


@mark.parametrize('value, bts', [
    (1, b'\x01' + b'\x00'*7),
    (1234567890, b'\xd2\x02\x96\x49\x00\x00\x00\x00'),
    (-1234567890, b'\x2e\xfd\x69\xb6\xff\xff\xff\xff'),
    (2147483647, b'\xff\xff\xff\x7f\x00\x00\x00\x00'),
    (-2147483647, b'\x01\x00\x00\x80\xff\xff\xff\xff'),
    (-2147483648, b'\x00\x00\x00\x80\xff\xff\xff\xff')
])
def test_long(value, bts):
    f = Long()
    dumped = f.dumps(value)
    assert dumped == bts
    loaded, remaining_bts = f.loads(memoryview(dumped))
    assert loaded == value
    assert not bytes(remaining_bts)


@mark.parametrize('length, length_bts', [
    (0, b'\x00'),
    (1, b'\x01'),
    (255, b'\xff\x01'),
    (1234, b'\xd2\x09'),
    (123456, b'\xc0\xc4\x07')
])
def test_string_length(length, length_bts):
    string = 'a' * length
    f = String()
    dumped = f.dumps(string)
    assert dumped.startswith((length_bts + b'a') if length else length_bts)
    loaded, remaining_bts = f.loads(memoryview(dumped))
    assert loaded == string
    assert not bytes(remaining_bts)


@mark.parametrize('as_string, money, currency, bts', [
    (False, DecimalNative('3'), 'EUR', b'\x03' + b'\x00' * 15 + b'\x03EUR'),
    (False, DecimalNative('1.0'), 'EUR', b'\x0a' + b'\x00' * 13 + b'\x01\x00\x03EUR'),
    (False, DecimalNative('100000.00000'), 'GBP', b'\x00\xe4\x0b\x54\x02' + b'\x00'*9 + b'\x05\x00\x03GBP'),
    (True, '3', 'EUR', b'\x03' + b'\x00' * 15 + b'\x03EUR'),
    (True, '1.2', 'EUR', b'\x0c' + b'\x00' * 13 + b'\x01\x00\x03EUR'),
])
def test_money_amount(as_string, money, currency, bts):
    f = MoneyAmount(currency, as_string=as_string)
    dumped = f.dumps(money)
    assert dumped == bts
    loaded, remaining_bts = f.loads(memoryview(dumped))
    assert loaded == money
    assert not bytes(remaining_bts)


@mark.parametrize('value, bts', [
    (None, b'\x00'),
    ('s', b'\x01\x01s')
])
def test_optional(value, bts):
    f = Optional(String())
    dumped = f.dumps(value)
    assert dumped == bts
    loaded, remaining_bts = f.loads(dumped)
    assert loaded == value
    assert not bytes(remaining_bts)


@mark.parametrize('value, bts', [
    ([], b'\x00'),
    (['s'], b'\x01\x01s'),
    (['s', 's'], b'\x02\x01s\x01s')
])
def test_array(value, bts):
    f = Array(String())
    dumped = f.dumps(value)
    assert dumped == bts
    loaded, remaining_bts = f.loads(dumped)
    assert loaded == value
    assert not bytes(remaining_bts)
