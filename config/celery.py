
import os

from celery import Celery
from internetHealthReport.tasks import kafka_alert

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "internetHealthReport.settings")

app = Celery("internetHealthReport")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

