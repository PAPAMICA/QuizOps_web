from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError, TimeoutError, OperationalError
from flask import current_app, request
from app import db
import time
from functools import wraps

@contextmanager
def session_manager():
    """Optimized context manager for DB sessions"""
    session = None
    session_id = id(db.session())
    print(f"[DB] Opening session {session_id} for route: {request.endpoint}")
    try:
        session = db.session()
        yield session
        session.commit()
        print(f"[DB] Session {session_id} committed successfully")
    except Exception as e:
        if session:
            session.rollback()
            print(f"[DB] Session {session_id} rolled back due to error: {str(e)}")
        raise
    finally:
        if session:
            session.close()
            db.engine.dispose()
            print(f"[DB] Session {session_id} closed and connections disposed")

def retry_on_db_lock(max_retries=3, delay=0.1):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return f(*args, **kwargs)
                except (TimeoutError, OperationalError) as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        time.sleep(delay * (2 ** attempt))
                        continue
                    raise last_error
            raise last_error
        return wrapper
    return decorator