from __future__ import absolute_import, unicode_literals

# This makes sure Celery app is always imported when Django starts
from .celery import app as celery_app

__all__ = ('celery_app',)
import os
default_app_config = 'jobapp.apps.JobappConfig'
