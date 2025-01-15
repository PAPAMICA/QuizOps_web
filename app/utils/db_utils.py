from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError, TimeoutError, OperationalError
from flask import current_app
from app import db
import time

@contextmanager
def session_manager():
    """Gestionnaire de contexte optimisé pour les sessions DB"""
    session = db.session()  # Créer une nouvelle session
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()
        if not session.bind.pool.checkedin() > session.bind.pool.size * 0.9:
            # Si plus de 90% des connexions sont utilisées, forcer le nettoyage
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