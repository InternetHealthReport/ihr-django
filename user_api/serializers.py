from ..models import IHRUser, MonitoredASN, ASN
from rest_framework import serializers
from ..serializers import ASNSerializer

class MonitoredASNSerializer(serializers.ModelSerializer):
    asnumber = serializers.IntegerField(source="asn.number", read_only=True)
    asname = serializers.CharField(source="asn.name", read_only=True)
    class Meta:
        model = MonitoredASN
        fields = ('notifylevel', 'asnumber', 'asname')

class IHRUserSerializer(serializers.ModelSerializer):
    monitoredasn = MonitoredASNSerializer(source="monitoredasn_set", required=False, read_only=True, many=True)

    class Meta:
        model = IHRUser
        fields = ('email', 'monitoredasn')