from functools import wraps
from flask import g, current_app
from sqlalchemy import event
from app import db
import time

def setup_db_connection_handling(app):
    @app.before_request
    def before_request():
        g.db_session = db.session()

    @app.teardown_request
    def teardown_request(exception=None):
        if hasattr(g, 'db_session'):
            g.db_session.close()
            del g.db_session

    @event.listens_for(db.engine, 'checkout')
    def receive_checkout(dbapi_connection, connection_record, connection_proxy):
        if connection_record.info.get('checked_out_time') is not None:
            connection_record.info['checked_out_time'] = time.time()