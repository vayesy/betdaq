from datetime import datetime
from betdaq.aapi.structures.commands import Ping


class TestCommandDump:

    @classmethod
    def setup_class(cls):
        cls.cmd = Ping(
            correlation_id=1, current_client_time=datetime(2020, 12, 31, 15, 59)
        )

    def test_dump_header(self):
        assert self.cmd.dump_header() == '\u000222'

    def test_dump_value(self):
        assert self.cmd.dump_body() == '\u00010\u00021\u00011\u00022020-12-31T15:59:00.000000Z\u0001'

    def test_dump(self):
        assert self.cmd.dump() == '\u000222\u00010\u00021\u00011\u00022020-12-31T15:59:00.000000Z\u0001'
