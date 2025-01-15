from functools import wraps
from flask import g, current_app
from sqlalchemy import event
from app import db
import time

def setup_db_connection_handling(app):
    @app.before_request
    def before_request():
        session_id = id(db.session())
        g.db_session = db.session()
        print(f"[DB] Created request session {session_id} for {request.endpoint}")

    @app.teardown_appcontext
    def teardown_appcontext(exception=None):
        if hasattr(g, 'db_session'):
            session_id = id(g.db_session)
            g.db_session.close()
            print(f"[DB] Closed request session {session_id}")
            del g.db_session
        db.session.remove()
        if exception:
            print(f"[DB] Exception occurred, disposing engine: {str(exception)}")
            db.engine.dispose()

    @event.listens_for(db.engine, 'checkout')
    def receive_checkout(dbapi_connection, connection_record, connection_proxy):
        print(f"[DB] Connection checkout - Total active: {len(db.engine.pool._checked_out)}")
        if connection_record.info.get('checked_out_time') is not None:
            connection_record.info['checked_out_time'] = time.time()

    @event.listens_for(db.engine, 'checkin')
    def receive_checkin(dbapi_connection, connection_record):
        print(f"[DB] Connection checkin - Total active: {len(db.engine.pool._checked_out)}")