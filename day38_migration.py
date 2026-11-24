"""Explicit offline upgrades from synthetic Day 38 SQLite fixtures."""
from contextlib import closing
from pathlib import Path
import sqlite3

from day30_outbox import SCHEMA as OUTBOX_SCHEMA
from day31_receiver import SCHEMAS as RECEIVER_SCHEMAS


SYNTHETIC_OUTBOX_SCHEMA = OUTBOX_SCHEMA.replace(', text TEXT', ', rendered_text TEXT')
SYNTHETIC_RECEIVER_SCHEMAS = (
    RECEIVER_SCHEMAS[0],
    RECEIVER_SCHEMAS[1].replace(', payload TEXT', ', effect_payload TEXT'),
)


def _validate(db, schemas):
    actual = db.execute(
        'SELECT sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY sql COLLATE BINARY'
    ).fetchall()
    if actual != [(schema,) for schema in sorted(schemas)]:
        raise sqlite3.DatabaseError('unexpected migration schema')
    if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
        raise sqlite3.DatabaseError('migration integrity check failed')
    if db.execute('PRAGMA foreign_key_check').fetchall():
        raise sqlite3.DatabaseError('migration foreign key check failed')


def _migrate(path, *, source_version, source, target_version, target, rename):
    uri = Path(path).resolve().as_uri() + '?mode=rw'
    with closing(sqlite3.connect(uri, uri=True, timeout=0.2)) as db:
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA synchronous=FULL')
        with db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('PRAGMA journal_mode').fetchone() != ('delete',):
                raise sqlite3.DatabaseError('migration requires DELETE journal mode')
            version, = db.execute('PRAGMA user_version').fetchone()
            if version == target_version:
                _validate(db, target)
                return False
            if version != source_version:
                raise sqlite3.DatabaseError(f'unsupported migration version: {version}')
            _validate(db, source)
            db.execute(rename)
            db.execute(f'PRAGMA user_version={target_version}')
            _validate(db, target)
        return True


def migrate_outbox(path):
    """Upgrade a synthetic version 1 outbox to 30; return False if already current."""
    return _migrate(
        path, source_version=1, source=(SYNTHETIC_OUTBOX_SCHEMA,),
        target_version=30, target=(OUTBOX_SCHEMA,),
        rename='ALTER TABLE outbox RENAME COLUMN rendered_text TO text',
    )


def migrate_receiver(path):
    """Upgrade a synthetic version 2 receiver to 31; return False if already current."""
    return _migrate(
        path, source_version=2, source=SYNTHETIC_RECEIVER_SCHEMAS,
        target_version=31, target=RECEIVER_SCHEMAS,
        rename='ALTER TABLE effects RENAME COLUMN effect_payload TO payload',
    )
