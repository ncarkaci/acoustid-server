import pytest
from webtest import TestApp, AppError
from tests.data import TEST_2_FP, TEST_2_LENGTH


def test_lookup_invalid_client(server):
    client = TestApp(server)
    with pytest.raises(AppError, match=r".* 400 BAD REQUEST .*") as ex:
        client.post('/v2/lookup', {
            'client': 'xxx',
        })
    ex.match(r'.*"invalid API key\b.*')


def test_lookup_missing_fingerprint(server):
    client = TestApp(server)
    with pytest.raises(AppError, match=r".* 400 BAD REQUEST .*") as ex:
        client.post('/v2/lookup', {
            'client': 'app1_api_key',
        })
    ex.match(r'.*"missing required parameter.*fingerprint')


def test_lookup_missing_duration(server):
    client = TestApp(server)
    with pytest.raises(AppError, match=r".* 400 BAD REQUEST .*") as ex:
        client.post('/v2/lookup', {
            'client': 'app1_api_key',
            'fingerprint': TEST_2_FP,
        })
    ex.match(r'.*"missing required parameter.*duration')


def test_lookup_by_fingerprint(server):
    client = TestApp(server)
    resp = client.post('/v2/lookup', {
        'client': 'app1_api_key',
        'fingerprint': TEST_2_FP,
        'duration': str(TEST_2_LENGTH),
        'meta': 'recordings usermeta',
    })
    assert resp.status_int == 200
    assert resp.json == {
        'status': 'ok',
        'results': [
            {
                'id': 'eb31d1c3-950e-468b-9e36-e46fa75b1291',
                'score': 1.0,
                'recordings': [
                    {
                        'artists': ['Custom Artist'],
                        'title': 'Custom Track',
                    }
                ],
            },
        ],
    }


def test_lookup_by_track_id(server):
    client = TestApp(server)
    resp = client.post('/v2/lookup', {
        'client': 'app1_api_key',
        'trackid': 'eb31d1c3-950e-468b-9e36-e46fa75b1291',
        'meta': 'recordings usermeta',
    })
    assert resp.status_int == 200
    assert resp.json == {
        'status': 'ok',
        'results': [
            {
                'id': 'eb31d1c3-950e-468b-9e36-e46fa75b1291',
                'score': 1.0,
                'recordings': [
                    {
                        'artists': ['Custom Artist'],
                        'title': 'Custom Track',
                    }
                ],
            },
        ],
    }
