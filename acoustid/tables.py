from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, DateTime

metadata = MetaData()

track = Table('track', metadata,
    Column('id', Integer, primary_key=True),
    Column('created', DateTime),
)

track_mbid = Table('track_mbid', metadata,
    Column('track_id', Integer, ForeignKey('track.id'), primary_key=True),
    Column('mbid', String, primary_key=True),
    Column('created', DateTime),
)

mb_artist = Table('artist', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String),
    Column('gid', String),
    schema='musicbrainz',
)

mb_track = Table('track', metadata,
    Column('id', Integer, primary_key=True),
    Column('artist', Integer, ForeignKey('musicbrainz.artist.id')),
    Column('name', String),
    Column('gid', String),
    Column('length', Integer),
    schema='musicbrainz',
)

