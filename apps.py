from django.apps import AppConfig
from django.db import ProgrammingError
from django.db.models.signals import post_migrate
from django_filters import rest_framework as filters 

class NoMarkupDjangoFilterBackend(filters.DjangoFilterBackend):
    def to_html(self, request, queryset, view):
        # We want this, but currently it incurs a huge performance penality on ChoiceFields with 1000+ choices
        return ''


class IHRConfig(AppConfig):
    name = 'ihr'

    def ready(self):
        super(IHRConfig, self).ready()
