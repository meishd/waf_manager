import os

if os.path.exists('/root/.flaskenv'):
    for line in open('/root/.flaskenv'):
        var = line.strip().split('=')
        if len(var) == 2:
            os.environ[var[0].strip()] = var[1].strip()

from waf import create_app
from flask_script import Manager

app = create_app()

manager = Manager(app)

if __name__ == '__main__':
    manager.run()