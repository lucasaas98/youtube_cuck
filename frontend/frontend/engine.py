from contextlib import contextmanager

from sqlalchemy.future.engine import create_engine
from sqlalchemy.orm.session import sessionmaker

from frontend.env_vars import DB_HOST, DB_NAME, DB_PASS, DB_USER

engine = create_engine(
    f"mysql+mysqlconnector://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}",
    pool_size=100,
    max_overflow=-1,
)


def close_engine():
    engine.dispose()


def create_session():
    Session = sessionmaker(bind=engine)
    session = Session()
    return session


@contextmanager
def session_scope():
    session = create_session()
    try:
        yield session
    finally:
        session.close()
