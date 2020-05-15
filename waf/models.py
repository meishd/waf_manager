from . import db
from sqlalchemy import Column,Integer,String,DateTime,ForeignKey
from datetime import datetime
import json
from werkzeug.security import generate_password_hash,check_password_hash
from flask_login import UserMixin

class Ipblacklist(db.Model):
    __tablename__ = 'ip_blacklist'
    id = Column(Integer,primary_key=True)
    ip_addr = Column(String())
    status = Column(Integer)
    effective_time = Column(Integer)
    create_time = Column(DateTime,default=datetime.now)
    modify_time = Column(DateTime,default=datetime.now)
    source_type = Column(String(30))
    source = Column(String(255))
    remark = Column(String(255))

    def to_dict(self):
        return {c.name: getattr(self, c.name, None) for c in self.__table__.columns}


class Rule(db.Model):
    __tablename__ = 'rule'
    id = Column(Integer,primary_key=True)
    domain = Column(String())
    url = Column(String())
    match_type = Column(String())
    win_duration = Column(Integer)
    slide_duration = Column(Integer)
    req_threshold = Column(Integer)
    active_status = Column(Integer)
    block_duration = Column(Integer)
    create_time = Column(DateTime,default=datetime.now)
    user_name = Column(String())

class Ipwhite(db.Model):
    __tablename__ = 'ip_white'
    id = Column(Integer, primary_key=True)
    ip_addr = Column(String())
    create_time = Column(DateTime,default=datetime.now)
    user_name = Column(String())
    remark = Column(String(255))

class Matchrecord(db.Model):
    __tablename__ = 'match_record'
    id = Column(Integer,primary_key=True)
    rule_id = Column(Integer)
    ip_addr = Column(String())
    win_begin = Column(DateTime)
    win_end = Column(DateTime)
    request_cnt = Column(Integer)
    create_time = Column(DateTime)

    def to_dict(self):
        return {c.name: getattr(self, c.name, None) for c in self.__table__.columns}


class User(UserMixin, db.Model):
    __tablename__ = 'user_base'
    id = Column(Integer,primary_key=True)
    user_name = Column(String())
    password = Column(String())
    active = Column(Integer)
    priv_rule = Column(Integer)
    login_cnt = Column(Integer)

    def check_password(self,password):
        return check_password_hash(self.password,password)


class Userpriv(db.Model):
    __tablename__ = 'user_priv'
    id = Column(Integer,primary_key=True)
    user_name = Column(String())
    user_priv = Column(String())