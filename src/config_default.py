import os
from dotenv import load_dotenv
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY='verysecretkey12345'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_recycle': 1800}
    MAX_CONTENT_LENGTH=512 * 1024 * 1024
    SESSION_COOKIE_SECURE = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=31)
    REMEMBER_COOKIE_SECURE = True
    S3_ACCESS_KEY = 'your s3 access key'
    S3_SECRET_KEY = 'your s3 secret key'
    S3_BUCKET_NAME = 'https://your_bucket_name.s3.your_bucket_location.amazonaws.com/'
    CELERY_BROKER_URL = f'sqs://{S3_ACCESS_KEY}:{S3_SECRET_KEY}@'
    BROKER_TRANSPORT_OPTIONS = {'region': 'your bucket location'}
    INFERFILES_PATH = 'your path' # you can use your desktop to watch what's happening
    PROD = False
    LANGUAGES = ['tr', 'en']