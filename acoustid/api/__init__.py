# Copyright (C) 2011 Lukas Lalinsky
# Distributed under the MIT license, see the LICENSE file for details.

import six
import logging
import json
import xml.etree.cElementTree as etree
from werkzeug.wrappers import Response
from acoustid.utils import singular

logger = logging.getLogger(__name__)


def _serialize_xml_node(parent, data):
    if isinstance(data, dict):
        _serialize_xml_dict(parent, data)
    elif isinstance(data, list):
        _serialize_xml_list(parent, data)
    else:
        parent.text = six.text_type(data)


def _serialize_xml_dict(parent, data):
    for name, value in data.iteritems():
        if name.startswith('@'):
            parent.attrib[name[1:]] = six.text_type(value)
        else:
            elem = etree.SubElement(parent, name)
            _serialize_xml_node(elem, value)


def _serialize_xml_list(parent, data):
    name = singular(parent.tag)
    for item in data:
        elem = etree.SubElement(parent, name)
        _serialize_xml_node(elem, item)


def serialize_xml(data, **kwargs):
    root = etree.Element('response')
    _serialize_xml_node(root, data)
    res = etree.tostring(root, encoding="UTF-8")
    return Response(res, content_type='text/xml; charset=UTF-8', **kwargs)


def serialize_json(data, callback=None, **kwargs):
    res = json.dumps(data, sort_keys=True)
    if callback:
        res = '%s(%s)' % (callback, res)
        mime = 'application/javascript; charset=UTF-8'
    else:
        mime = 'application/json; charset=UTF-8'
    return Response(res, content_type=mime, **kwargs)


def serialize_response(data, format, **kwargs):
    if format == 'json':
        return serialize_json(data, **kwargs)
    elif format.startswith('jsonp:'):
        func = format.split(':', 1)[1]
        return serialize_json(data, callback=func, **kwargs)
    else:
        return serialize_xml(data, **kwargs)


def get_health_response(script, req, require_master=False):
    from acoustid.uwsgi_utils import is_shutting_down
    if require_master and script.config.cluster.role != 'master':
        return Response('not the master server', content_type='text/plain', status=503)
    if is_shutting_down(script.config.website.shutdown_file_path):
        return Response('shutdown in process', content_type='text/plain', status=503)
    return Response('ok', content_type='text/plain', status=200)


class ReadOnlyHealthHandler(object):

    def __init__(self, server):
        self.server = server

    @classmethod
    def create_from_server(cls, server):
        return cls(server)

    def handle(self, req):
        return get_health_response(self.server, req)


class HealthHandler(ReadOnlyHealthHandler):

    def handle(self, req):
        return get_health_response(self.server, req, require_master=True)
