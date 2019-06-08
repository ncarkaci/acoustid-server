from webtest import TestApp


def test_index(web_app):
    client = TestApp(web_app)
    resp = client.get('/')
    resp.mustcontain(
        'Welcome to AcoustID!',
        'Applications',
        'Statistics',
        'Documentation',
        'Donate',
        'Sign in',
    )


def test_applications(web_app):
    client = TestApp(web_app)
    resp = client.get('/applications')
    resp.mustcontain('MusicBrainz Picard')


def test_stats(web_app):
    client = TestApp(web_app)
    resp = client.get('/stats')
    resp.mustcontain(
        'Basic statistics',
        'Daily additions',
        'Searches',
        'AcoustIDs per the number of linked recordings',
        'Recordings per the number of linked AcoustIDs',
    )


def test_docs(web_app):
    client = TestApp(web_app)
    resp = client.get('/docs')
    resp.mustcontain(
        'Documentation',
        'Frequently Asked Questions',
        'Web Service',
        'Server',
        'Chromaprint',
        'Fingerprinter',
    )


def test_faq(web_app):
    client = TestApp(web_app)
    resp = client.get('/faq')
    resp.mustcontain('Frequently Asked Questions')


def test_webservice(web_app):
    client = TestApp(web_app)
    resp = client.get('/webservice')
    resp.mustcontain(
        'Web Service',
        'Usage Guidelines',
        'Overview',
        'Compression',
        'API Keys',
        'Methods',
        'Lookup by fingerprint',
        'Lookup by track ID',
        'Submit',
        'Get submission status',
        'List AcoustIDs by MBID',
    )


def test_server(web_app):
    client = TestApp(web_app)
    resp = client.get('/server')
    resp.mustcontain('Server')


def test_chromaprint(web_app):
    client = TestApp(web_app)
    resp = client.get('/chromaprint')
    resp.mustcontain('Chromaprint', 'Download', 'Usage')


def test_donate(web_app):
    client = TestApp(web_app)
    resp = client.get('/donate')
    resp.mustcontain('Donate Money')


def test_login(web_app):
    client = TestApp(web_app)
    resp = client.get('/login')
    resp.mustcontain('Sign in')


def test_contact(web_app):
    client = TestApp(web_app)
    resp = client.get('/contact')
    resp.mustcontain(
        'Contact us',
        'acoustid@googlegroups.com',
        'info@acoustid.org',
        '#acoustid',
    )


def test_track(web_app):
    client = TestApp(web_app)

    resp = client.get('/track/eb31d1c3-950e-468b-9e36-e46fa75b1291')
    resp.mustcontain(
        'eb31d1c3-950e-468b-9e36-e46fa75b1291',
        'Track',
        'Custom Track',
        'Custom Artist',
    )


def test_fingerprint(web_app):
    client = TestApp(web_app)

    resp = client.get('/fingerprint/1')
    resp.mustcontain(
        'Fingerprint #1',
        'eb31d1c3-950e-468b-9e36-e46fa75b1291',
    )
