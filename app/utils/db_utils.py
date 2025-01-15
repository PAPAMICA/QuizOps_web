from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError, TimeoutError, OperationalError
from flask import current_app
from app import db
import time

@contextmanager
def session_manager():
    """Gestionnaire de contexte pour les sessions DB"""
    try:
        yield db.session
        db.session.commit()
    except (TimeoutError, OperationalError) as e:
        current_app.logger.error(f"Database connection error: {e}")
        db.session.rollback()
        db.session.remove()
        raise
    except Exception as e:
        current_app.logger.error(f"Database error: {e}")
        db.session.rollback()
        raise
    finally:
        db.session.remove()

def retry_on_db_lock(max_retries=3, delay=0.1):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    with session_manager():
                        return f(*args, **kwargs)
                except (TimeoutError, OperationalError) as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        time.sleep(delay * (2 ** attempt))  # exponential backoff
                        db.session.remove()  # Force la libération de la session
                        continue
                    raise last_error
            raise last_error
        return wrapper
    return decorator 