import pytest
from webtest import TestApp, AppError
from acoustid.models import Submission
from tests.data import TEST_2_FP, TEST_2_FP_RAW, TEST_2_LENGTH


def test_submit_invalid_client(server):
    client = TestApp(server)
    with pytest.raises(AppError, match=r".* 400 BAD REQUEST .*") as ex:
        client.post('/v2/submit', {
            'client': 'xxx',
        })
    ex.match(r'.*"invalid API key\b.*')


def test_submit_invalid_user(server):
    client = TestApp(server)
    with pytest.raises(AppError, match=r".* 400 BAD REQUEST .*") as ex:
        client.post('/v2/submit', {
            'client': 'app1_api_key',
            'user': 'xxx',
        })
    ex.match(r'.*"invalid user API key\b.*')


@pytest.mark.usefixtures("cleanup")
def test_submit(server):
    client = TestApp(server)
    resp = client.post('/v2/submit', {
        'client': 'app1_api_key',
        'user': 'user1_api_key',
        'fingerprint': TEST_2_FP,
        'duration': str(TEST_2_LENGTH),
        'mbid': '7b924948-200e-4517-921f-5eaaa9300db2',
        'puid': 'b2325721-1584-4afb-ac84-f265d80650c4',
        'foreignid': 'youtube:dN44xpHjNxE',
    })
    assert resp.status_int == 200

    with server.context() as ctx:
        submissions = ctx.db.query(Submission).all()
        assert len(submissions) == 1
        s = submissions[0]
        assert s.fingerprint == TEST_2_FP_RAW
        assert s.duration == TEST_2_LENGTH
        assert s.mbid == '7b924948-200e-4517-921f-5eaaa9300db2'
        assert s.puid == 'b2325721-1584-4afb-ac84-f265d80650c4'
        assert s.foreignid == 'youtube:dN44xpHjNxE'

        assert resp.json == {
            'status': 'ok',
            'submissions': [
                {
                    'id': s.id,
                    'status': 'pending',
                },
            ],
        }

    resp = client.post('/v2/submission_status', {
        'client': 'app1_api_key',
        'id': str(s.id),
    })
    assert resp.status_int == 200
    assert resp.json == {
        'status': 'ok',
        'submissions': [
            {
                'id': s.id,
                'status': 'pending',
            },
        ],
    }
