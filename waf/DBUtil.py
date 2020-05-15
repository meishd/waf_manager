from . import db
from sqlalchemy.orm import sessionmaker,scoped_session

class DBUtil:
    def get_session(self):
        engine = db.get_engine(app=db.get_app())
        Session = scoped_session(sessionmaker(bind=engine))
        return Session()