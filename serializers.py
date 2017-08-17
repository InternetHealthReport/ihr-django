from rest_framework import serializers
from .models import Delay,  Forwarding, Delay_alarms, Forwarding_alarms, Disco_events, Disco_probes


class DelaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Delay
        fields = ('asn', 'timebin',  'magnitude', 'deviation', 'label')

class DelayAlarmsSerializer(serializers.ModelSerializer):
    msmid = serializers.StringRelatedField(many=True)
    probeid = serializers.StringRelatedField(many=True)

    class Meta:
        model = Delay_alarms
        fields = ('asn', 'timebin',  'link', 'medianrtt', 'diffmedian', 'deviation', 'nbprobes', 'msmid', 'probeid')

class ForwardingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Forwarding
        fields = ('asn', 'timebin', 'magnitude', 'resp', 'label')

class ForwardingAlarmsSerializer(serializers.ModelSerializer):
    msmid = serializers.StringRelatedField(many=True)
    probeid = serializers.StringRelatedField(many=True)

    class Meta:
        model = Forwarding_alarms
        fields = ('asn', 'timebin', 'ip', 'correlation', 'pktdiff', 'previoushop', 'responsibility', 'msmid', 'probeid')

class DiscoEventsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disco_events
        fields = ('id', 'streamtype', 'streamname', 'starttime', 'endtime', 'avglevel', 'nbdiscoprobes', 'totalprobes', 'ongoing')

class DiscoProbesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disco_probes
        fields = ('probe_id', 'ipv4', 'prefixv4', 'event', 'starttime', 'endtime', 'level')
