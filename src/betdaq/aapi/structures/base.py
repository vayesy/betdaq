from typing import Any
from logging import getLogger
from collections import OrderedDict

from ..utils import VALUE_DELIMITER


L = getLogger(__name__)


class BaseField(object):
    """Implementation of base logic for all fields"""

    def __init__(self, order: int, required: bool = True, default: Any = None, name: str = None):
        self.order = order
        self.required = required
        self.default = default
        self.name = name

    def dump_key(self) -> str:
        """Turn field into string representation"""
        return str(self.order)

    def dump_value(self, value: Any) -> str:
        """Turn field value into string representation"""
        return value

    def dump(self, value: Any, instance: Any, include_key=False) -> str:
        """Turn field to string representation, including it's key if needed, and value"""
        res = ''
        if include_key:
            res += self.dump_key() + VALUE_DELIMITER
        try:
            res += self.dump_value(value)
        except Exception:
            L.warning({'message': 'Failed to dump field', 'instance': type(instance).__name__,
                       'field_name': self.name, 'field_value': value}, exc_info=True)
            res = ''
        return res

    def load(self, value: Any, instance: Any) -> Any:
        """Parse field value for specified container instance"""
        if value:
            try:
                result = self._load(value, instance)
            except Exception:
                L.warning({'message': 'Failed to load field', 'instance': type(instance).__name__,
                           'field_name': self.name, 'field_value': value}, exc_info=True)
                result = None
        else:
            result = self.default
        return result

    def _load(self, value: str, instance: Any) -> Any:
        return value

    def __set__(self, instance, value):
        instance.__dict__[self.name] = value

    def __get__(self, instance, owner):
        if instance is None:
            return self
        val = instance.__dict__.get(self.name, self.default)
        if val is self.default and self.required and getattr(instance, 'check_required', False):
            raise AttributeError(f'{owner.__name__} missing required field "{self.name}"')
        return val

    def __str__(self):
        return '{0.__class__.__name__}(order={0.order}, name={0.name})'.format(self)

    __repr__ = __str__


class MessageMeta(type):
    """Meta class to populate field names and check uniqueness of fields order"""

    fields_key = '__fields__'

    def __new__(mcs, name, bases, attrs):
        class_fields = {}
        for base in bases:
            base_fields = getattr(base, mcs.fields_key, None)
            if base_fields:
                class_fields.update(base_fields)
        for k, v in attrs.items():
            if isinstance(v, BaseField):
                if v.order in class_fields:
                    raise ValueError('Class {} contains multiple fields with same order={}'.format(name, v.order))
                if v.name is None:
                    v.name = k
                class_fields[v.order] = v
        res = super(MessageMeta, mcs).__new__(mcs, name, bases, attrs)
        setattr(res, mcs.fields_key, OrderedDict(sorted(class_fields.items())))
        return res
