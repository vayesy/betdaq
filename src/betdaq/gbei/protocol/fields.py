import struct
from enum import EnumMeta
from typing import Any, Tuple, Union
from datetime import datetime, timedelta
from decimal import Decimal as DecimalNative

from pytz import UTC


class Serializable:

    def dumps(self, value) -> bytes:
        raise NotImplementedError

    def loads(self, bts: memoryview) -> Tuple[Any, memoryview]:
        raise NotImplementedError


class BaseField(Serializable):
    f: str = None
    name: str = None
    size: int = None

    def get_args(self, value):
        return (value,)

    def dumps(self, value):
        return struct.pack(self.f, *self.get_args(value))

    def loads(self, bts: memoryview):
        sub_bts = bts[:self.size]
        return struct.unpack(self.f, sub_bts)[0], bts[self.size:]


class Byte(BaseField):
    f = '<b'
    size = struct.calcsize(f)


class Int(BaseField):
    f = '<i'
    size = struct.calcsize(f)


class ReversedInt(Int):
    f = '>i'


class Long(BaseField):
    f = '<q'
    size = struct.calcsize(f)


class DateTime(Long):

    def __init__(self, as_timestamp: bool = False):
        self.dt = datetime(1, 1, 1)
        self.m = 10000000
        self.as_timestamp = as_timestamp

    def ticks(self, dt):
        return int((dt - self.dt).total_seconds() * self.m)

    def dumps(self, value):
        if self.as_timestamp:
            value = datetime.utcfromtimestamp(value)
        return super().dumps(self.ticks(value))

    def loads(self, bts: memoryview):
        ticks, bts = super().loads(bts)
        if not ticks:
            return None, bts
        dt = self.dt + timedelta(microseconds=ticks * 0.1)
        if self.as_timestamp:
            dt = UTC.localize(dt).timestamp()
        return dt, bts


class Decimal(BaseField):
    f = '<QIhBB'
    size = struct.calcsize(f)
    max_8_bytes_integer = int('1'*63, 2)  # 63 bits all set to 1

    def __init__(self, as_string: bool = False):
        self.as_string = as_string

    def dumps(self, value: Union[DecimalNative, str]):
        if self.as_string:
            value = DecimalNative(value)
        parts = value.as_tuple()
        exp = abs(parts.exponent)
        integer = abs(int(value * (10 ** exp)))
        integer1 = integer & self.max_8_bytes_integer
        integer2 = integer >> 64
        result = struct.pack(self.f, integer1, integer2, 0, exp, parts.sign << 7)
        return result

    def loads(self, bts: memoryview):
        b = bts[:self.size]
        integer1, integer2, _, exp, sign = struct.unpack(self.f, b)
        value = integer2 << 64
        value |= (integer1 & self.max_8_bytes_integer)
        value = DecimalNative(value) / (10 ** exp)
        sign = sign >> 7
        if sign:
            value = -value
        if self.as_string:
            value = str(value)
        return value, bts[self.size:]


class Length(BaseField):

    def dumps(self, value):
        parts = [value & 127]
        value = value >> 7
        while value:
            parts.insert(0, (value & 127) | 128)
            value = value >> 7
        bts = struct.pack('<%sB' % len(parts), *parts)
        return bts

    def loads(self, bts: memoryview):
        value = 0
        for i in range(10):
            b = struct.unpack('<B', bts[0:1])[0]
            bts = bts[1:]
            value = (value << 7) | (b & 127)
            if not (b & 128):
                break
        return value, bts


class String(BaseField):

    def encode_length(self, length: int):
        parts = []
        while length > 127:
            parts.append((length & 127) | 128)
            length = length >> 7
        parts.append(length & 127)
        bts = struct.pack('<%sB' % len(parts), *parts)
        return bts

    def dumps(self, value):
        value = bytes(value, 'utf-8')
        length = len(value)
        encoded_length = self.encode_length(length)
        return b''.join((encoded_length, value))

    def loads(self, bts: memoryview):
        size = 0
        for i in range(10):
            b = struct.unpack('<B', bts[0:1])[0]
            bts = bts[1:]
            sub = (b & 127) << (i * 7)
            size |= sub
            if not b & 128:  # if largest bit of current byte is 0
                break
        if size:
            s = bytes(bts[:size]).decode()
        else:
            s = ''
        return s, bts[size:]


class Enum(BaseField):

    def __init__(self, base_field: Union[Int, String], enum_cls: EnumMeta, raw: bool = False):
        self.enum_cls = enum_cls
        self.field = base_field
        self.raw = raw

    def loads(self, bts: memoryview):
        enum_value, bts = self.field.loads(bts)
        if not self.raw:
            enum_value = self.enum_cls(enum_value)
        return enum_value, bts

    def dumps(self, value):
        if not self.raw:
            value = value.value
        return self.field.dumps(value)


class MoneyAmount(BaseField):
    # decimal + string of 3 symbols

    def __init__(self, currency: str, as_string: bool = False):
        """
        :param currency: 3-letter currency code, which is used by account
        """
        self.currency = currency
        self.decimal = Decimal(as_string=as_string)
        self.str = String()

    def dumps(self, value: DecimalNative):
        stake = self.decimal.dumps(value)
        currency = self.str.dumps(self.currency)
        return b''.join((stake, currency))

    def loads(self, bts: memoryview):
        stake, bts = self.decimal.loads(bts)
        currency, bts = self.str.loads(bts)
        return stake, bts


class Array(BaseField):

    def __init__(self, field: Serializable):
        self.len = Length()
        self.field = field

    def dumps(self, value):
        size = self.len.dumps(len(value))
        items = [self.field.dumps(_) for _ in value]
        return b''.join((size, b''.join(items)))

    def loads(self, bts: memoryview):
        size, bts = self.len.loads(bts)
        items = []
        for i in range(size):
            item, bts = self.field.loads(bts)
            items.append(item)
        return items, bts


class Optional(BaseField):
    exists = b'\x01'
    doesnt_exist = b'\x00'

    def __init__(self, field):
        self.field = field

    def dumps(self, value):
        if value is None:
            return self.doesnt_exist
        return b''.join((self.exists, self.field.dumps(value)))

    def loads(self, bts: memoryview):
        flag = bytes(bts[0:1])
        bts = bts[1:]
        if flag == self.doesnt_exist:
            value = None
        else:
            value, bts = self.field.loads(bts)
        return value, bts
