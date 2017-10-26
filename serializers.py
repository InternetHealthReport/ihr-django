from rest_framework import serializers
from .models import Delay,  Forwarding, Delay_alarms, Forwarding_alarms, Disco_events, Disco_probes, Hegemony


class DelaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Delay
        fields = ('asn', 'timebin',  'magnitude')

class DelayAlarmsSerializer(serializers.ModelSerializer):
    queryset = Delay_alarms.objects.all().prefetch_related('msmid')
    msmid = serializers.StringRelatedField(many=True)

    class Meta:
        model = Delay_alarms
        fields = ('asn', 'timebin',  'link', 'medianrtt', 'diffmedian', 'deviation', 'nbprobes', 'msmid')

class ForwardingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Forwarding
        fields = ('asn', 'timebin', 'magnitude')

class ForwardingAlarmsSerializer(serializers.ModelSerializer):
    queryset = Forwarding_alarms.objects.all().prefetch_related('msmid')
    msmid = serializers.StringRelatedField(many=True)

    class Meta:
        model = Forwarding_alarms
        fields = ('asn', 'timebin', 'ip', 'correlation', 'pktdiff', 'previoushop', 'responsibility', 'msmid')

class DiscoEventsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disco_events
        fields = ('id', 'streamtype', 'streamname', 'starttime', 'endtime', 'avglevel', 'nbdiscoprobes', 'totalprobes', 'ongoing')

class DiscoProbesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disco_probes
        fields = ('probe_id', 'ipv4', 'prefixv4', 'event', 'starttime', 'endtime', 'level')

class HegemonySerializer(serializers.ModelSerializer):
    queryset = Hegemony.objects.all().prefetch_related("asn","originasn")
    class Meta:
        model = Hegemony
        fields = ('timebin', 'originasn', 'asn', 'hege', 'af')

