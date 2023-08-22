from betdaq.common.enums import ReturnCode

from betdaq.aapi.structures.topics import Event1
from betdaq.aapi.structures.responses import Unsubscribe
from betdaq.aapi.message_parser import parse_response_str, parse_response


class TestParseResponseStr:
    def test_all_fields_present(self):
        s = 'AAPI/6/D\u000210\u0002F\u00010\u00021\u00011\u00020\u00012\u00021\u00014\u0002499\u0001'
        headers, fields = parse_response_str(s)
        assert headers == ['AAPI/6/D', '10', 'F']
        assert fields == {0: '1', 1: '0', 2: '1', 4: '499'}

    def test_header_field_empty(self):
        s = "AAPI/1/E/E_1/E/E_100003/E/E_45645645/M/E_151515/S/E_565656/SEI/SEL/en" \
            "\u0002\u0002T\u00011\u0002en name\u00012\u0002test blurb\u0001"
        headers, fields = parse_response_str(s)
        assert headers == ['AAPI/1/E/E_1/E/E_100003/E/E_45645645/M/E_151515/S/E_565656/SEI/SEL/en', '', 'T']
        assert fields == {1: 'en name', 2: 'test blurb'}

    def test_body_field_list(self):
        s = "AAPI/6/E/E_1/E/E_100003\u0002\u0002T\u00011\u00021\u00012V1-1\u00022018-06-20T18:00:00.000Z" \
            "\u00012V1-2\u00022-3\u00013V1-1\u0002MatchStarted\u00013V1-2\u00022018-06-20T18:00:00.000Z\u0001"
        _, fields = parse_response_str(s)
        assert fields == {
            1: '1',
            2: [{
                1: '2018-06-20T18:00:00.000Z',
                2: '2-3'
            }],
            3: [{
                1: 'MatchStarted',
                2: '2018-06-20T18:00:00.000Z'
            }]
        }

    def test_body_field_nested_list(self):
        s = "AAPI/6/E/E_1/E/E_100004/E/E_190538/E/E_4100115/E/E_4100118/M/E_333542/MEI/MDP/3_3_100_EUR_1" \
            "\u0002\u0002T\u00011V1-1\u00022030974\u00011V1-2V1-1\u00022.72\u00011V1-2V1-2\u0002865.53" \
            "\u00011V1-3V1-1\u00022.76\u00011V1-3V1-2\u0002600.60\u00011V2-1\u00022030975\u00011V2-2V1-1" \
            "\u00021.98\u00011V2-2V1-2\u0002474.16\u00011V2-3V1-1\u00022\u00011V2-3V1-2\u0002643.50\u0001"
        _, fields = parse_response_str(s)
        assert fields == {
            1: [{
                1: '2030974',
                2: [{
                    1: '2.72',
                    2: '865.53'
                }],
                3: [{
                    1: '2.76',
                    2: '600.60'
                }]
            }, {
                1: '2030975',
                2: [{
                    1: '1.98',
                    2: '474.16'
                }],
                3: [{
                    1: '2',
                    2: '643.50'
                }]
            }]
        }


class TestParseResponse:
    def test_parse_response(self):
        s = 'AAPI/6/D\u000220\u0002F\u00010\u00021984840034\u00011\u00020\u00013\u00022~3\u0001'
        resp = parse_response(s)
        assert resp.head.topic_name == 'AAPI/6/D'
        assert type(resp) is Unsubscribe
        assert resp.correlation_id == 1984840034
        assert resp.return_code == ReturnCode.Success
        assert resp.subscription_ids == [2, 3]

    def test_parse_data_message(self):
        s = 'AAPI/6/E/E_1/E/E_100003\u0002\u0002T\u00011\u00021\u0001'
        resp = parse_response(s)
        assert resp.head.topic_name == 'AAPI/6/E/E_1/E/E_100003'
        assert type(resp) is Event1
        assert resp.display_order == 1
