from .base import MessageMeta


class Frame(object, metaclass=MessageMeta):

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __eq__(self, other):
        if type(other) != type(self):
            return False
        fields = getattr(self, MessageMeta.fields_key)
        for field in fields.values():
            value_self = getattr(self, field.name)
            value_other = getattr(other, field.name)
            if value_other != value_self:
                return False
        return True

    def __str__(self):
        return '{}(...)'.format(type(self).__name__)

    def __repr__(self):
        fields = getattr(self, MessageMeta.fields_key)
        values = []
        for field in fields.values():
            val = getattr(self, field.name)
            if val is not None:
                values.append('{}={!r}'.format(field.name, val))
        res = '{}({})'.format(type(self).__name__, ', '.join(values))
        return res
