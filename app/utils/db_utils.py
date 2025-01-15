from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError, TimeoutError, OperationalError
from flask import current_app
from app import db
import time
from functools import wraps

@contextmanager
def session_manager():
    """Optimized context manager for DB sessions"""
    session = db.session()  # Create a new session
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()
        # Check the number of active connections
        checkedin = session.bind.pool.checkedin()
        pool_size = session.bind.pool.size()
        if checkedin >= int(pool_size * 0.9):
            # If more than 90% of connections are used, force cleanup
            db.engine.dispose()

def retry_on_db_lock(max_retries=3, delay=0.1):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    with session_manager() as session:
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