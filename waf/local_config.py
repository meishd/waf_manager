from datetime import timedelta

class Config(object):
    SECRET_KEY='\xb9\xe8\xc8v\xf5\x18\x90\xcc\x9eb\x89\x9f\x1cq\x90\x89\x1f\x8d\xe4f\x97\xd0B'
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    REMEMBER_COOKIE_DURATION = timedelta(days=7)


class Prod(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = 'mysql://user:password@prod_ip:3306/waf'

class Dev(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'mysql://user:password@dev_ip:3306/waf'

