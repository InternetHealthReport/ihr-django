from rest_framework import serializers
from .models import Congestion,  Forwarding


class CongestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Congestion
        fields = ('asn', 'timebin',  'magnitude', 'deviation', 'label')


class ForwardingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Forwarding
        fields = ('asn', 'timebin', 'magnitude', 'resp', 'label')
