from logging import getLogger
from datetime import datetime
from typing import List, Dict, Any, Union
from enum import Enum as EnumBase, EnumMeta

from .frame import Frame
from .base import BaseField, MessageMeta


L = getLogger(__name__)


class Str(BaseField):
    def __init__(self, *a, max_length=None, **kw):
        super(Str, self).__init__(*a, **kw)
        self.max_length = max_length


class Int(BaseField):
    def dump_value(self, value: int) -> str:
        return str(value)

    def _load(self, value: str, instance: Any) -> int:
        return int(value)


class Float(BaseField):
    def dump_value(self, value: float) -> str:
        return str(value)

    def _load(self, value: str, instance: Any) -> float:
        return float(value)


class Bool(BaseField):
    def dump_value(self, value: bool) -> str:
        return 'T' if value else 'F'

    def _load(self, value: str, instance: Any) -> bool:
        return value == 'T'


class Enum(BaseField):
    def __init__(self, enum_cls: EnumMeta, parse_func=None, *a, **kw):
        super(Enum, self).__init__(*a, **kw)
        self.enum_cls = enum_cls
        self.parse_func = parse_func

    def dump_value(self, value: EnumBase) -> str:
        return str(value.value)

    def _load(self, value: str, instance: Any) -> EnumBase:
        if self.parse_func is not None:
            value = self.parse_func(value)
        return self.enum_cls(value)


class DateTime(BaseField):
    def __init__(self, dt_format='%Y-%m-%dT%H:%M:%S.%fZ', *a, **kw):
        super(DateTime, self).__init__(*a, **kw)
        self.dt_format = dt_format

    def dump_value(self, value: datetime):
        return value.strftime(self.dt_format)

    def _load(self, value: str, instance: Any) -> datetime:
        return datetime.strptime(value, self.dt_format)


class ReadOnlyNestedField(BaseField):
    def __init__(self, fields: Dict[str, BaseField], *a, **kw):
        super(ReadOnlyNestedField, self).__init__(*a, **kw)
        self.frame_cls = type(self.name or '', (Frame,), dict(**fields, check_required=False))

    def _process_single(self, fields, value, instance):
        obj = self.frame_cls()
        for key, raw_value in value.items():
            field = fields.get(key)
            if field is not None:
                parsed_value = field.load(raw_value, instance)
                setattr(obj, field.name, parsed_value)
            else:
                L.debug({'message': 'Skipping unknown field in nested field',
                         'field_class': self.name,
                         'field_index': key, 'field_value': raw_value})
        return obj

    def _load(self, value: Union[Dict[int, str], List[Dict]], instance: Any):
        if not self.frame_cls.__name__ and self.name:
            self.frame_cls.__name__ = self.name
        fields = getattr(self.frame_cls, MessageMeta.fields_key)
        if isinstance(value, list):
            return [self._process_single(fields, _, instance) for _ in value]
        else:
            return self._process_single(fields, value, instance)


class ReadOnlyStrJoinedNestedField(BaseField):
    def __init__(self, fields: Dict[str, BaseField], separator='_', *a, **kw):
        kw.setdefault('order', 0)
        super(ReadOnlyStrJoinedNestedField, self).__init__(*a, **kw)
        for k, f in fields.items():
            if f.name is None:
                f.name = k
        self.fields = {f.order: f for f in fields.values()}
        self.separator = separator

    def _load(self, value: str, instance: Any):
        parts = value.split(self.separator)
        results = dict()
        for i, value in enumerate(parts):
            field = self.fields.get(i)
            if field is None:
                L.debug({'message': 'Unknown nested field',
                         'field_name': self.name, 'field_raw_value': value,
                         'instance': type(instance).__name__})
                continue
            results[field.name] = field.load(value, instance)
        return results


class StrJoinedField(BaseField):
    def __init__(self, field: BaseField, separator='~', *a, **kw):
        super(StrJoinedField, self).__init__(*a, **kw)
        self.field = field
        self.separator = separator

    def _load(self, value: str, instance: Any):
        return list(self.field.load(_, instance) for _ in value.split(self.separator))

    def dump_value(self, value: List[Any]):
        return self.separator.join(map(self.field.dump_value, value))
