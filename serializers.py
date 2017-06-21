from rest_framework import serializers
from .models import Congestion,  Forwarding, Congestion_alarms, Forwarding_alarms, Disco_events, Disco_probes


class CongestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Congestion
        fields = ('asn', 'timebin',  'magnitude', 'deviation', 'label')

class CongestionAlarmsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Congestion_alarms
        fields = ('asn', 'timebin',  'link', 'medianrtt', 'diffmedian', 'deviation', 'nbprobes')

class ForwardingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Forwarding
        fields = ('asn', 'timebin', 'magnitude', 'resp', 'label')

class ForwardingAlarmsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Forwarding_alarms
        fields = ('asn', 'timebin', 'ip', 'correlation', 'pktdiff', 'previoushop', 'responsibility')

class DiscoEventsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disco_events
        fields = ('id', 'streamtype', 'streamname', 'starttime', 'endtime', 'avglevel', 'nbdiscoprobes', 'totalprobes', 'ongoing')

class DiscoProbesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disco_probes
        fields = ('probe_id', 'event', 'starttime', 'endtime', 'level')
