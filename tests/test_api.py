import pytest
from webtest import TestApp, AppError


def test_server(server):
    client = TestApp(server)
    with pytest.raises(AppError, match=r".* 404 NOT FOUND .*"):
        client.get('/')
