from .frame import Frame
from .enums import MessageType
from .fields import Str, Int, Enum


class Head(Frame):
    topic_name = Str(max_length=256, order=0)
    message_identifier = Int(order=1)
    message_type = Enum(enum_cls=MessageType, order=2)
