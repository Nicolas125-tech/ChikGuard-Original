import os
from celery import Celery

def make_celery():
    redis_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    celery = Celery(
        'chikguard',
        broker=redis_url,
        backend=redis_url,
        include=['src.tasks.vision_tasks']
    )
    celery.conf.update(
        task_serializer='json',
        result_serializer='json',
        accept_content=['json'],
    )
    return celery

celery_app = make_celery()
