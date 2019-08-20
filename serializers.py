from rest_framework import serializers
from .models import ASN, Country, Delay,  Forwarding, Delay_alarms, Forwarding_alarms, Disco_events, Disco_probes, Hegemony, HegemonyCone
from django.forms import widgets


class DelaySerializer(serializers.ModelSerializer):
    queryset = Delay.objects.all().prefetch_related("asn")
    asn_name = serializers.PrimaryKeyRelatedField(queryset=queryset, source='asn.name')

    class Meta:
        model = Delay
        fields = ('asn', 'timebin',  'magnitude', 'asn_name')

class DelayAlarmsSerializer(serializers.ModelSerializer):
    queryset = Delay_alarms.objects.all().prefetch_related('msmid', "asn")
    msmid = serializers.StringRelatedField(many=True)
    asn_name = serializers.PrimaryKeyRelatedField(queryset=queryset, source='asn.name')

    class Meta:
        model = Delay_alarms
        fields = ('asn', 
                'asn_name',
                'timebin',
                'link',
                'medianrtt',
                'diffmedian',
                'deviation',
                'nbprobes',
                'msm_prb_ids',
                'msmid')

class ForwardingSerializer(serializers.ModelSerializer):
    queryset = Forwarding.objects.all().prefetch_related("asn")
    asn_name = serializers.PrimaryKeyRelatedField(queryset=queryset, source='asn.name')

    class Meta:
        model = Forwarding
        fields = ('asn', 'timebin', 'magnitude', 'asn_name')

class ForwardingAlarmsSerializer(serializers.ModelSerializer):
    queryset = Forwarding_alarms.objects.all().prefetch_related('msmid', 'asn')
    msmid = serializers.StringRelatedField(many=True)
    asn_name = serializers.PrimaryKeyRelatedField(queryset=queryset, source='asn.name')

    class Meta:
        model = Forwarding_alarms
        fields = ('asn',
                'asn_name',
                'timebin',
                'ip',
                'correlation',
                'pktdiff',
                'previoushop',
                'responsibility',
                'msm_prb_ids',
                'msmid')

class DiscoEventsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disco_events
        fields = ('id',
                'streamtype',
                'streamname',
                'starttime',
                'endtime',
                'avglevel',
                'nbdiscoprobes',
                'totalprobes',
                'ongoing')

class DiscoProbesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disco_probes
        fields = ('probe_id',
                'ipv4',
                'prefixv4',
                'event',
                'starttime',
                'endtime',
                'level',
                'lat',
                'lon')

class HegemonySerializer(serializers.ModelSerializer):
    queryset = Hegemony.objects.all().prefetch_related("asn","originasn")
    asn_name = serializers.PrimaryKeyRelatedField(queryset=queryset, source='asn.name')
    originasn_name = serializers.PrimaryKeyRelatedField(queryset=queryset, source='originasn.name')
    # originasn = serializers.PrimaryKeyRelatedField( widget=widgets.TextInput)

    class Meta:
        model = Hegemony
        fields = ('timebin',
                'originasn',
                'asn',
                'hege',
                'af',
                'asn_name',
                'originasn_name')

class HegemonyConeSerializer(serializers.ModelSerializer):
    class Meta:
        model = HegemonyCone
        fields = ('timebin', 'asn', 'conesize', 'af')

class ASNSerializer(serializers.ModelSerializer):
    class Meta:
        model = ASN
        fields = ('number', 'name')

class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ('code', 'name')
