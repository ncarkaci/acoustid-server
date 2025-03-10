import logging
from flask import Blueprint, render_template, request, redirect, url_for, abort, session
from acoustid.web import db
from acoustid.web.utils import require_user
from acoustid.models import TrackMBIDChange, TrackMeta, Meta
from acoustid.data.track import resolve_track_gid
from acoustid.data.musicbrainz import lookup_recording_metadata
from acoustid.data.account import is_moderator
from acoustid.utils import is_uuid
from acoustid import tables as schema
from sqlalchemy import sql
from sqlalchemy.orm import joinedload

logger = logging.getLogger(__name__)

metadata_page = Blueprint('metadata', __name__)


@metadata_page.route('/track/<track_id>')
def track(track_id):
    conn = db.session.connection()

    if is_uuid(track_id):
        track_gid = track_id
        track_id = resolve_track_gid(conn, track_id)
    else:
        try:
            track_id = int(track_id)
        except ValueError:
            track_id = None
        query = sql.select([schema.track.c.gid], schema.track.c.id == track_id)
        track_gid = conn.execute(query).scalar()

    if track_id is None or track_gid is None:
        abort(404)

    title = 'Track "%s"' % (track_gid,)
    track = {
        'id': track_id
    }

    query = sql.select(
        [schema.fingerprint.c.id,
         schema.fingerprint.c.length,
         schema.fingerprint.c.submission_count],
        schema.fingerprint.c.track_id == track_id).order_by(schema.fingerprint.c.length)
    fingerprints = conn.execute(query).fetchall()

    query = sql.select(
        [schema.track_mbid.c.id,
         schema.track_mbid.c.mbid,
         schema.track_mbid.c.submission_count,
         schema.track_mbid.c.disabled],
        schema.track_mbid.c.track_id == track_id)
    mbids = conn.execute(query).fetchall()

    metadata = lookup_recording_metadata(conn, [r['mbid'] for r in mbids])

    recordings = []
    for mbid in mbids:
        recording = metadata.get(mbid['mbid'], {})
        recording['mbid'] = mbid['mbid']
        recording['submission_count'] = mbid['submission_count']
        recording['disabled'] = mbid['disabled']
        recordings.append(recording)
    recordings.sort(key=lambda r: r.get('name', r.get('mbid')))

    user_metadata = (
        db.session.query(Meta.track, Meta.artist, Meta.album, sql.func.sum(TrackMeta.submission_count))
        .select_from(TrackMeta).join(Meta)
        .filter(TrackMeta.track_id == track_id)
        .group_by(Meta.track, Meta.artist, Meta.album)
        .order_by(sql.func.min(TrackMeta.created))
        .all()
    )

    edits = db.session.query(TrackMBIDChange).\
        options(joinedload('account', innerjoin=True).load_only('mbuser', 'name')).\
        options(joinedload('track_mbid', innerjoin=True).load_only('mbid')).\
        filter(TrackMBIDChange.track_mbid_id.in_(m.id for m in mbids)).\
        order_by(TrackMBIDChange.created.desc()).all()

    moderator = is_moderator(conn, session.get('id'))

    return render_template('track.html', title=title,
        fingerprints=fingerprints, recordings=recordings,
        moderator=moderator, track=track,
        edits=edits,
        user_metadata=user_metadata)


@metadata_page.route('/fingerprint/<int:fingerprint_id>')
def fingerprint(fingerprint_id):
    conn = db.session.connection()
    title = 'Fingerprint #%s' % (fingerprint_id,)
    query = sql.select(
        [schema.fingerprint.c.id,
         schema.fingerprint.c.length,
         schema.fingerprint.c.fingerprint,
         schema.fingerprint.c.track_id,
         schema.fingerprint.c.submission_count],
        schema.fingerprint.c.id == fingerprint_id)
    fingerprint = conn.execute(query).first()
    query = sql.select([schema.track.c.gid], schema.track.c.id == fingerprint['track_id'])
    track_gid = conn.execute(query).scalar()
    return render_template('fingerprint.html', title=title,
        fingerprint=fingerprint, track_gid=track_gid)


@metadata_page.route('/fingerprint/<int:fingerprint_id_1>/compare/<int:fingerprint_id_2>')
def compare_fingerprints(fingerprint_id_1, fingerprint_id_2):
    conn = db.session.connection()
    title = 'Compare fingerprints #%s and #%s' % (fingerprint_id_1, fingerprint_id_2)
    query = sql.select(
        [schema.fingerprint.c.id,
         schema.fingerprint.c.length,
         schema.fingerprint.c.fingerprint,
         schema.fingerprint.c.track_id,
         schema.fingerprint.c.submission_count],
        schema.fingerprint.c.id.in_((fingerprint_id_1, fingerprint_id_2)))
    fingerprint_1 = None
    fingerprint_2 = None
    for fingerprint in conn.execute(query):
        if fingerprint['id'] == fingerprint_id_1:
            fingerprint_1 = fingerprint
        elif fingerprint['id'] == fingerprint_id_2:
            fingerprint_2 = fingerprint
    if not fingerprint_1 or not fingerprint_2:
        abort(404)
    return render_template('compare_fingerprints.html', title=title,
        fingerprint_1=fingerprint_1, fingerprint_2=fingerprint_2)


@metadata_page.route('/mbid/<mbid>')
def mbid(mbid):
    from acoustid.data.track import lookup_tracks
    from acoustid.data.musicbrainz import lookup_recording_metadata
    conn = db.session.connection()
    metadata = lookup_recording_metadata(conn, [mbid])
    if mbid not in metadata:
        title = 'Incorrect Recording'
        return render_template('mbid-not-found.html', title=title, mbid=mbid)
    metadata = metadata[mbid]
    title = 'Recording "%s" by %s' % (metadata['name'], metadata['artist_name'])
    tracks = lookup_tracks(conn, [mbid]).get(mbid, [])
    return render_template('mbid.html', title=title, tracks=tracks, mbid=mbid)


@metadata_page.route('/edit/toggle-track-mbid', methods=['GET', 'POST'])
def toggle_track_mbid():
    conn = db.session.connection()
    user = require_user()
    track_id = request.values.get('track_id', type=int)
    if track_id:
        query = sql.select([schema.track.c.gid], schema.track.c.id == track_id)
        track_gid = conn.execute(query).scalar()
    else:
        track_gid = request.values.get('track_gid')
        track_id = resolve_track_gid(conn, track_gid)
    state = bool(request.values.get('state', type=int))
    mbid = request.values.get('mbid')
    if not track_id or not mbid or not track_gid:
        return redirect(url_for('general.index'))
    if not is_moderator(conn, user.id):
        title = 'MusicBrainz account required'
        return render_template('toggle_track_mbid_login.html', title=title)
    query = sql.select([schema.track_mbid.c.id, schema.track_mbid.c.disabled],
        sql.and_(schema.track_mbid.c.track_id == track_id,
                 schema.track_mbid.c.mbid == mbid))
    rows = conn.execute(query).fetchall()
    if not rows:
        return redirect(url_for('general.index'))
    id, current_state = rows[0]
    if state == current_state:
        return redirect(url_for('.track', track_id=track_id))
    if request.form.get('submit'):
        note = request.values.get('note')
        update_stmt = schema.track_mbid.update().where(schema.track_mbid.c.id == id).values(disabled=state)
        conn.execute(update_stmt)
        insert_stmt = schema.track_mbid_change.insert().values(track_mbid_id=id, account_id=session['id'],
                                                               disabled=state, note=note)
        conn.execute(insert_stmt)
        db.session.commit()
        return redirect(url_for('.track', track_id=track_id))
    if state:
        title = 'Unlink MBID'
    else:
        title = 'Link MBID'
    return render_template('toggle_track_mbid.html', title=title, track_gid=track_gid, mbid=mbid, state=state, track_id=track_id)
