from rest_framework import serializers
from .models import ASN, Country, Delay,  Forwarding, Delay_alarms, Forwarding_alarms, Disco_events, Disco_probes, Hegemony, HegemonyCone, Atlas_location, Atlas_delay, Atlas_delay_alarms, Hegemony_alarms

class DelaySerializer(serializers.ModelSerializer):
    queryset = Delay.objects.all().prefetch_related("asn")
    asn_name = serializers.PrimaryKeyRelatedField(queryset=queryset, source='asn.name', help_text="Name of the Autonomous System corresponding to the reported IP address.")
    magnitude = serializers.FloatField(help_text="Amplitude of the delay change")

    class Meta:
        model = Delay
        fields = ('asn', 'timebin',  'magnitude', 'asn_name')

class DelayAlarmsSerializer(serializers.ModelSerializer):
    queryset = Delay_alarms.objects.all().prefetch_related('msmid', "asn")
    msmid = serializers.StringRelatedField(many=True)
    asn_name = serializers.PrimaryKeyRelatedField(queryset=queryset, source='asn.name', help_text="Name of the Autonomous System corresponding to the reported IP address.")

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
    asn_name = serializers.PrimaryKeyRelatedField(queryset=queryset, source='asn.name', help_text="Name of the Autonomous System corresponding to the reported IP address.")

    class Meta:
        model = Forwarding
        fields = ('asn', 'timebin', 'magnitude', 'asn_name')

class ForwardingAlarmsSerializer(serializers.ModelSerializer):
    queryset = Forwarding_alarms.objects.all().prefetch_related('msmid', 'asn')
    msmid = serializers.StringRelatedField(many=True)
    asn_name = serializers.PrimaryKeyRelatedField(queryset=queryset, source='asn.name', help_text="Name of the Autonomous System corresponding to the reported IP address.")

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

class DiscoEventsSerializer(serializers.ModelSerializer):
    discoprobes = DiscoProbesSerializer(many=True, read_only=True)

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
                'ongoing',
                'discoprobes')


class HegemonySerializer(serializers.ModelSerializer):
    queryset = Hegemony.objects.all().prefetch_related("asn","originasn")
    asn_name = serializers.PrimaryKeyRelatedField(queryset=queryset, source='asn.name', help_text="Autonomous System name of the dependency.")
    originasn_name = serializers.PrimaryKeyRelatedField(queryset=queryset, source='originasn.name', help_text="Autonomous System name of the dependent network.")

    class Meta:
        model = Hegemony
        fields = ('timebin',
                'originasn',
                'asn',
                'hege',
                'af',
                'asn_name',
                'originasn_name')

class HegemonyAlarmsSerializer(serializers.ModelSerializer):
    queryset = Hegemony_alarms.objects.all().prefetch_related("asn","originasn")
    asn_name = serializers.PrimaryKeyRelatedField(queryset=queryset, source='asn.name', help_text="Autonomous System name of the reported dependency.")
    originasn_name = serializers.PrimaryKeyRelatedField(queryset=queryset, source='originasn.name', help_text="Autonomous System name of the reported dependent network.")

    class Meta:
        model = Hegemony_alarms
        fields = ('timebin',
                'originasn',
                'asn',
                'deviation',
                'af',
                'asn_name',
                'originasn_name')


class HegemonyConeSerializer(serializers.ModelSerializer):
    class Meta:
        model = HegemonyCone
        fields = ('timebin', 'asn', 'conesize', 'af')

class NetworkDelaySerializer(serializers.ModelSerializer):
    queryset = Atlas_delay.objects.all().prefetch_related("startpoint", "endpoint")
    startpoint_type = serializers.CharField(source='startpoint.type')
    startpoint_name = serializers.CharField(source='startpoint.name')
    startpoint_af = serializers.IntegerField(source='startpoint.af')
    endpoint_type = serializers.CharField(source='endpoint.type')
    endpoint_name = serializers.CharField(source='endpoint.name')
    endpoint_af = serializers.IntegerField(source='endpoint.af')

    class Meta:
        model = Atlas_delay
        fields = ('timebin',
                'startpoint_type',
                'startpoint_name',
                'startpoint_af',
                'endpoint_type',
                'endpoint_name',
                'endpoint_af',
                'median',
                'nbtracks',
                'nbprobes',
                'entropy',
                'hop',
                'nbrealrtts')

class NetworkDelayLocationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Atlas_location
        fields = ('type', 'name', 'af')

class ASNSerializer(serializers.ModelSerializer):
    hegemony = serializers.BooleanField(source='ashash', help_text='True if participate in AS dependency analysis.')
    delay_forwarding = serializers.BooleanField(source='tartiflette', help_text='True if participate in link delay and forwarding anomaly analysis.')

    class Meta:
        model = ASN
        fields = ('number', 
                'name', 
                'hegemony',
                'delay_forwarding',
                'disco')

class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ('code', 'name')

class NetworkDelayAlarmsSerializer(serializers.ModelSerializer):
    queryset = Atlas_delay_alarms.objects.all().prefetch_related('startpoint', 'endpoint')
    startpoint_type = serializers.CharField(source='startpoint.type')
    startpoint_name = serializers.CharField(source='startpoint.name')
    startpoint_af = serializers.IntegerField(source='startpoint.af')
    endpoint_type = serializers.CharField(source='endpoint.type')
    endpoint_name = serializers.CharField(source='endpoint.name')
    endpoint_af = serializers.IntegerField(source='endpoint.af')

    class Meta:
        model = Atlas_delay_alarms
        fields = ('timebin',
                'startpoint_type',
                'startpoint_name',
                'startpoint_af',
                'endpoint_type',
                'endpoint_name',
                'endpoint_af',
                'deviation')
