"""
Parser of betdaq string messages, encoded with specific
protocol to dictionaries with nested fields
"""
from logging import getLogger
from typing import Union, Tuple

from .structures.head import Head
from .structures.base import MessageMeta
from .structures.responses import RESPONSE_TYPES
from .structures.topics import resolve_data_message
from .utils import BLOCK_DELIMITER, VALUE_DELIMITER


L = getLogger(__name__)


def parse_response_str(response: str) -> Tuple[list, dict]:
    """Parse response message string, get headers as list and body as dictionary"""
    head, body = response.split(BLOCK_DELIMITER, 1)
    headers = head.split(VALUE_DELIMITER)
    fields = dict()
    for field in body.split(BLOCK_DELIMITER):
        if not field:
            break
        k, v = field.split(VALUE_DELIMITER, 1)
        parse_field(fields, k, v)
    return headers, fields


def parse_field(data: dict, key: str, value: Union[str, int, list, dict]) -> None:
    """Recursively process data field"""
    list_field_delimiter = '-'
    if list_field_delimiter in key:
        list_identifier = 'V'
        key, sub_key = key.split(list_identifier, 1)
        sub_key_index, sub_key = sub_key.split(list_field_delimiter, 1)
        sub_key_index = int(sub_key_index)
        items_list = data.setdefault(int(key), [])
        if len(items_list) < sub_key_index:
            sub_data = {}
            items_list.insert(sub_key_index - 1, sub_data)
        else:
            sub_data = items_list[sub_key_index - 1]
        parse_field(sub_data, sub_key, value)
    else:
        data[int(key)] = value


def parse_response(response_str: str):
    try:
        headers, fields = parse_response_str(response_str)
    except ValueError:
        L.exception('Failed to parse AAPI response %s', response_str)
        return None
    head_fields = getattr(Head, MessageMeta.fields_key)
    head = Head()
    for f in head_fields.values():
        setattr(head, f.name, f.load(headers[f.order], head))
    if head.message_identifier:
        response_cls = RESPONSE_TYPES.get(head.message_identifier)
        response = response_cls.load(head=head, body=fields)
        return response
    else:
        topic_cls, topic_kwargs = resolve_data_message(head.topic_name)
        if topic_cls is not None:
            topic = topic_cls.load(fields, head=head, topic_kwargs=topic_kwargs)
        else:
            topic = None
        return topic
