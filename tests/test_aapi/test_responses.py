from betdaq.aapi.structures import responses as r
from betdaq.aapi.structures.enums import MessageType


class TestResponseLoad:

    @classmethod
    def setup_class(cls):

        class TestResponse(r.Response):
            test1 = r.f.Int(order=2)

        cls.response_cls = TestResponse
        cls.head = r.Head(topic_name='Test', message_identifier=1, message_type=MessageType.TopicLoad)

    def test_load_ok(self):
        response = self.response_cls.load(self.head, {2: '2'})
        assert response.test1 == 2

    def test_load_missing_field(self):
        response = self.response_cls.load(self.head, {})
        assert response.test1 is None

    def test_load_invalid_field_type(self):
        response = self.response_cls.load(self.head, {2: 'invalid'})
        assert response.test1 is None

    def test_load_extra_field(self):
        body_fields = {2: '15', 3: 'invalid'}
        response = self.response_cls.load(self.head, body_fields)
        assert response.test1 == 15
