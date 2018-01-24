from architect.commands import partition

from django.apps import AppConfig
from django.db import ProgrammingError
from django.db.models.signals import post_migrate
from django_filters import rest_framework as filters 

class NoMarkupDjangoFilterBackend(filters.DjangoFilterBackend):
    def to_html(self, request, queryset, view):
        # We want this, but currently it incurs a huge performance penality on ChoiceFields with 1000+ choices
        return ''


def create_partitions(sender, **kwargs):
    """
    After running migrations, go through each of the models
    in the app and ensure the partitions have been setup
    """
    paths = {model.__module__ for model in sender.get_models()}
    for path in paths:
        try:
            partition.run(dict(module=path))
        except ProgrammingError:
            # Possibly because models were just un-migrated or
            # fields have been changed that effect Architect
            print("Unable to apply partitions for module '{}'".format(path))
        else:
            print("Applied partitions for module '{}'".format(path))


class IHRConfig(AppConfig):
    name = 'ihr'

    def ready(self):
        super(IHRConfig, self).ready()
        # Hook up Architect to the post migrations signal
        post_migrate.connect(create_partitions, sender=self)
