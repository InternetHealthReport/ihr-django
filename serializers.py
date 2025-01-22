from rest_framework import serializers
from django.core.validators import validate_email  # For better email validation
from django.contrib.auth.hashers import make_password
from .models import ASN, Country, Delay,  Forwarding, Delay_alarms, Forwarding_alarms, Disco_events, Disco_probes, Hegemony, HegemonyCone, Atlas_location, Atlas_delay, Atlas_delay_alarms, Hegemony_alarms, Hegemony_country, Hegemony_prefix, Metis_atlas_selection, Metis_atlas_deployment, TR_hegemony, IHRUser 

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8) # Minimum password length
    code = serializers.CharField(required=True, min_length=6, max_length=6) # Exact code length

     # Enhanced email validation
    class Meta:
        model = IHRUser
        fields = ('email', 'password', 'code')  # List fields explicitly
        extra_kwargs = {
            'email': {'validators': [validate_email]},
        }

    def validate_email(self, value):
        if IHRUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        user = IHRUser.objects.create(**validated_data)  # Or use create_user
        return user

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, min_length=8)

    class Meta:
        model = IHRUser
        fields = ('email', 'password')
        extra_kwargs = {
            'email': {'validators': [validate_email]},
        }

class UserEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, validators=[validate_email])


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, validators=[validate_email])
    password = serializers.CharField(required=True)
    
class UserChangePasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, validators=[validate_email])
    password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)

    def validate(self, data):
        #Prevent users from reusing the same password.
        if data['password'] == data['new_password']:
            raise serializers.ValidationError("New password cannot be the same as the old password.")
        return data

class UserForgetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, validators=[validate_email])
    new_password = serializers.CharField(required=True, min_length=8)
    code = serializers.CharField(required=True, min_length=6, max_length=6)
    
    def validate(self, data):
        return data

class DelaySerializer(serializers.ModelSerializer):
    queryset = Delay.objects.select_related("asn")
    asn_name = serializers.StringRelatedField(source='asn', read_only=True) 

    class Meta:
        model = Delay
        fields = ('asn', 'timebin',  'magnitude', 'asn_name')

class DelayAlarmsSerializer(serializers.ModelSerializer):
    queryset = Delay_alarms.objects.prefetch_related('msmid', "asn").all()
    msmid = serializers.StringRelatedField(many=True)
    asn_name = serializers.StringRelatedField(source='asn', read_only=True)

    class Meta:
        model = Delay_alarms
        fields = '__all__'

class ForwardingSerializer(serializers.ModelSerializer):
    asn_name = serializers.StringRelatedField(source='asn', read_only=True)
    class Meta:
        model = Forwarding
        fields = '__all__'  

class ForwardingAlarmsSerializer(serializers.ModelSerializer):
    asn_name = serializers.StringRelatedField(source='asn', read_only=True)
    class Meta:
        model = Forwarding_alarms
        fields = '__all__'

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
    asn_name = serializers.CharField(source='asn.name', 
            help_text="Autonomous System name of the dependency.")
    originasn_name = serializers.CharField(
            source='originasn.name', help_text="Autonomous System name of the dependent network.")

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
    queryset = Hegemony_alarms.objects.prefetch_related("asn","originasn").all()
    asn_name = serializers.CharField(source='asn.name', 
            help_text="Autonomous System name of the reported dependency.")
    originasn_name = serializers.CharField(source='originasn.name', 
            help_text="Autonomous System name of the reported dependent network.")

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

class HegemonyCountrySerializer(serializers.ModelSerializer):
    asn_name = serializers.CharField(source='asn.name', 
            help_text="Autonomous System name of the dependency.")

    class Meta:
        model = Hegemony_country
        fields = ('timebin',
                'country',
                'asn',
                'hege',
                'af',
                'asn_name',
                'weight',
                'weightscheme',
                'transitonly')

class HegemonyPrefixSerializer(serializers.ModelSerializer):
    originasn_name = serializers.CharField(source='originasn.name', 
            help_text="Autonomous System name of the ASN originating the prefix.")
    asn_name = serializers.CharField(source='asn.name', 
            help_text="Autonomous System name of the dependency.")

    class Meta:
        model = Hegemony_prefix
        fields = ('timebin',
                'prefix',
                'originasn',
                'country',
                'asn',
                'hege',
                'af',
                'visibility',
                'rpki_status',
                'irr_status',
                'delegated_prefix_status',
                'delegated_asn_status',
                'descr',
                'moas',
                'originasn_name',
                'asn_name')



class NetworkDelaySerializer(serializers.ModelSerializer):
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
    hegemony = serializers.BooleanField(source='ashash', 
            help_text='True if participate in AS dependency analysis.')
    delay_forwarding = serializers.BooleanField(source='tartiflette', 
            help_text='True if participate in link delay and forwarding anomaly analysis.')

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

class MetisAtlasSelectionSerializer(serializers.ModelSerializer):
    asn_name = serializers.CharField(source='asn.name', 
            help_text="Autonomous System name.")

    class Meta:
        model = Metis_atlas_selection
        fields = ('timebin',
                'metric',
                'rank',
                'asn',
                'af',
                'asn_name')

class MetisAtlasDeploymentSerializer(serializers.ModelSerializer):
    asn_name = serializers.CharField(source='asn.name', 
            help_text="Autonomous System name.")

    class Meta:
        model = Metis_atlas_deployment
        fields = ('timebin',
                'metric',
                'rank',
                'asn',
                'af',
                'nbsamples',
                'asn_name')

class TRHegemonySerializer(serializers.ModelSerializer):
    origin_type = serializers.CharField(source='origin.type')
    origin_name = serializers.CharField(source='origin.name')
    origin_af = serializers.IntegerField(source='origin.af')
    dependency_type = serializers.CharField(source='dependency.type')
    dependency_name = serializers.CharField(source='dependency.name')
    dependency_af = serializers.IntegerField(source='dependency.af')

    class Meta:
        model = TR_hegemony
        fields = ('timebin',
                'origin_type',
                'origin_name',
                'origin_af',
                'dependency_type',
                'dependency_name',
                'dependency_af',
                'hege',
                'af',
                'nbsamples')
