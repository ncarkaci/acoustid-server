import os
import pytest
from webtest import TestApp, AppError


def test_health(server):
    client = TestApp(server)
    resp = client.get('/_health')
    assert resp.status_int == 200


def test_health_on_slave(server):
    server.config.cluster.role = 'slave'
    try:
        client = TestApp(server)
        with pytest.raises(AppError, match=r".* 503 SERVICE UNAVAILABLE .*"):
            client.get('/_health')
    finally:
        server.config.cluster.role = 'master'


def test_health_ro(server):
    client = TestApp(server)
    resp = client.get('/_health_ro')
    assert resp.status_int == 200


def test_health_ro_on_slave(server):
    server.config.cluster.role = 'slave'
    try:
        client = TestApp(server)
        resp = client.get('/_health_ro')
        assert resp.status_int == 200
    finally:
        server.config.cluster.role = 'master'


def test_health_docker(server):
    client = TestApp(server)
    resp = client.get('/_health_docker')
    assert resp.status_int == 200


def test_health_docker_on_slave(server):
    server.config.cluster.role = 'slave'
    try:
        client = TestApp(server)
        resp = client.get('/_health_docker')
        assert resp.status_int == 200
    finally:
        server.config.cluster.role = 'master'


@pytest.mark.parametrize('endpoint', ['health', 'health_ro', 'health_docker'])
def test_health_while_shutdown(server, endpoint):
    with open(server.config.website.shutdown_file_path, 'wt') as shutdown_file:
        shutdown_file.write('shutdown')
    try:
        client = TestApp(server)
        with pytest.raises(AppError, match=r".* 503 SERVICE UNAVAILABLE .*"):
            client.get('/_' + endpoint)
    finally:
        os.remove(server.config.website.shutdown_file_path)
