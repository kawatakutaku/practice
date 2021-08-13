import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

SECRET_KEY = '#qy1jkj-%&k_o(bfv)pdo)+5r55hn^vx0ls==(l_#t5ek2t==q'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

ALLOWED_HOSTS = []

DEBUG = True