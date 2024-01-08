from celery import Celery

celery = Celery(
    __name__,
    broker='pyamqp://guest:guest@localhost//',
    backend='rpc://',
)
