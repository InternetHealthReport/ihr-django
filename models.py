from django.db import models
from django.contrib.postgres.fields import JSONField
from model_utils import Choices
from django.contrib.auth.models import PermissionsMixin 
from django.contrib.auth.models import Group, Permission 
from django.contrib.auth.base_user import AbstractBaseUser 
from django.contrib.auth.models import BaseUserManager

from caching.base import CachingManager, CachingMixin

class ASN(CachingMixin, models.Model):
    number = models.BigIntegerField(primary_key=True, help_text='Autonomous System Number (ASN) or IXP ID. Note that IXP ID are negative to avoid colision.')
    name   = models.CharField(max_length=255, help_text='Name registered for the network.')
    tartiflette = models.BooleanField(default=False, help_text='True if participate in link delay and forwarding anomaly analysis.')
    disco = models.BooleanField(default=False, help_text='True if participate in network disconnection analysis.')
    ashash = models.BooleanField(default=False, help_text='True if participate in AS dependency analysis.')

    objects = CachingManager()

    class Meta:
        base_manager_name = 'objects'  # Attribute name of CachingManager(), above

    def __str__(self):
        return "ASN%s %s" % (self.number, self.name)

class Country(CachingMixin, models.Model):
    code = models.CharField(max_length=4, primary_key=True)
    name   = models.CharField(max_length=255)
    tartiflette = models.BooleanField(default=False)
    disco = models.BooleanField(default=False)

    objects = CachingManager()

    class Meta:
        base_manager_name = 'objects'  # Attribute name of CachingManager(), above

    def __str__(self):
        return "%s (%s)" % (self.name, self.code)


# Tartiflette
class Delay(CachingMixin, models.Model):
    timebin = models.DateTimeField(db_index=True, help_text="Timestamp of reported value.")
    asn = models.ForeignKey(ASN, on_delete=models.CASCADE, help_text="ASN or IXP ID of the monitored network (see number in /network/).")
    magnitude = models.FloatField(default=0.0, help_text="Cumulated link delay deviation. Values close to zero represent usual delays for the network, whereas higher values stand for significant links congestion in the monitored network.  ")

    objects = CachingManager()

    class Meta:
        base_manager_name = 'objects'  # Attribute name of CachingManager(), above

    def __str__(self):
        return "%s AS%s" % (self.timebin, self.asn.number)


class Delay_alarms(CachingMixin, models.Model):
    asn = models.ForeignKey(ASN, on_delete=models.CASCADE, db_index=True, help_text="ASN or IXPID of the reported network.")
    timebin = models.DateTimeField(db_index=True, help_text="Timestamp of reported alarm.")
    ip = models.CharField(max_length=64, db_index=True)
    link = models.CharField(max_length=128, db_index=True, help_text="Pair of IP addresses corresponding to the reported link.")
    medianrtt = models.FloatField(default=0.0, help_text="Median differential RTT observed during the alarm.")
    diffmedian = models.FloatField(default=0.0, help_text="Difference between the link usual median RTT and the median RTT observed during the alarm.")
    deviation = models.FloatField(default=0.0, help_text="Distance between observed delays and the past usual values normalized by median absolute deviation.")
    nbprobes = models.IntegerField(default=0, help_text="Number of Atlas probes monitoring this link at the reported time window.")
    msm_prb_ids = JSONField(default=None, null=True, help_text="List of Atlas measurement IDs and probe IDs used to compute this alarm.")

    objects = CachingManager()

    class Meta:
        base_manager_name = 'objects'  # Attribute name of CachingManager(), above

    def __str__(self):
        return "%s AS%s" % (self.timebin, self.asn.number)



class Forwarding_alarms(CachingMixin, models.Model):
    asn = models.ForeignKey(ASN, on_delete=models.CASCADE, db_index=True, help_text="ASN or IXPID of the reported network.")
    timebin = models.DateTimeField(db_index=True, help_text="Timestamp of reported alarm.")
    ip = models.CharField(max_length=64, db_index=True, help_text="Reported IP address, this IP address is seen an unusually high or low number of times in Atlas traceroutes.")
    correlation = models.FloatField(default=0.0, help_text="Correlation coefficient between the usual forwarding pattern and the forwarding pattern observed during the alarm. Values range between 0 and -1. Lowest values represent the most anomalous patterns.")
    responsibility = models.FloatField(default=0.0, help_text="Responsability score of the reported IP in the forwarding pattern change.")
    pktdiff = models.FloatField(default=0.0, help_text="The difference between the number of times the reported IP is seen in traceroutes compare to its usual appearance.")
    previoushop   = models.CharField(max_length=64, help_text="Last observed IP hop on the usual path.")
    msm_prb_ids = JSONField(default=None, null=True, help_text="List of Atlas measurement IDs and probe IDs used to compute this alarm.")

    objects = CachingManager()

    class Meta:
        base_manager_name = 'objects'  # Attribute name of CachingManager(), above

    def __str__(self):
        return "%s AS%s %s" % (self.timebin, self.asn.number, self.ip)


class Forwarding(CachingMixin, models.Model):
    timebin = models.DateTimeField(db_index=True, help_text="Timestamp of reported value.")
    asn = models.ForeignKey(ASN, on_delete=models.CASCADE, help_text="ASN or IXP ID of the monitored network (see number in /network/).")
    magnitude = models.FloatField(default=0.0, help_text="Cumulated link delay deviation. Values close to zero represent usual delays for the network, whereas higher values stand for significant links congestion in the monitored network.  ")

    objects = CachingManager()

    class Meta:
        base_manager_name = 'objects'  # Attribute name of CachingManager(), above

    def __str__(self):
        return "%s AS%s" % (self.timebin, self.asn.number)



# Disco
class Disco_events(CachingMixin, models.Model):
    mongoid = models.CharField(max_length=24, default="000000000000000000000000", db_index=True)
    streamtype = models.CharField(max_length=10, help_text="Granularity of the detected event. The possible values are asn, country, admin1, and admin2. Admin1 represents a wider area than admin2, the exact definition might change from one country to another. For example 'California, US' is an admin1 stream and 'San Francisco County, California, US' is an admin2 stream.")
    streamname = models.CharField(max_length=128, help_text="Name of the topological (ASN) or geographical area where the network disconnection happened.")
    starttime = models.DateTimeField(help_text="Estimated start time of the network disconnection.")
    endtime = models.DateTimeField(help_text="Estimated end time of the network disconnection. Equal to starttime if the end of the event is unknown.")
    avglevel = models.FloatField(default=0.0, help_text="Score representing the coordination of disconnected probes. Higher values stand for a large number of Atlas probes that disconnected in a very short time frame. Events with an avglevel lower than 10 are likely to be false positives detection.")
    nbdiscoprobes = models.IntegerField(default=0, help_text="Number of Atlas probes that disconnected around the reported start time.")
    totalprobes = models.IntegerField(default=0, help_text="Total number of Atlas probes active in the reported stream (ASN, Country, or geographical area).")
    ongoing = models.BooleanField(default=False, help_text="Deprecated, this value is unused")

    objects = CachingManager()

    class Meta:
        index_together = ("streamtype", "streamname", "starttime", "endtime")
        base_manager_name = 'objects'  # Attribute name of CachingManager(), above

class Disco_probes(CachingMixin, models.Model):
    probe_id = models.IntegerField(help_text="Atlas probe ID of disconnected probe." )
    event = models.ForeignKey(Disco_events, on_delete=models.CASCADE, db_index=True, related_name="discoprobes", help_text="ID of the network disconnection event where this probe is reported.")
    starttime = models.DateTimeField(help_text="Probe disconnection time.")
    endtime = models.DateTimeField(help_text="Reconnection time of the probe, this may not be reported if other probes have reconnected earlier.")
    level = models.FloatField(default=0.0, help_text="Disconnection level when the probe disconnected.")
    ipv4 = models.CharField(max_length=64, default="None", help_text="Public IP address of the Atlas probe.")
    prefixv4 = models.CharField(max_length=70, default="None", help_text="IP prefix corresponding the probe.")
    lat = models.FloatField(default=0.0, help_text="Latitude of the probe during the network detection as reported by RIPE Altas.")
    lon = models.FloatField(default=0.0, help_text="Longitude of the probe during the network detection as reported by RIPE Altas.")

    objects = CachingManager()

    class Meta:
        base_manager_name = 'objects'  # Attribute name of CachingManager(), above


class Hegemony(CachingMixin, models.Model):
    timebin = models.DateTimeField(db_index=True, help_text="Timestamp of reported value.")
    originasn = models.ForeignKey(ASN, on_delete=models.CASCADE, related_name="local_graph", db_index=True, help_text="Dependent network, it can be any public ASN. Retrieve all dependencies of a network by setting only this parameter and a timebin.")
    asn = models.ForeignKey(ASN, on_delete=models.CASCADE, db_index=True, help_text="Dependency. Transit network commonly seen in BGP paths towards originasn.")
    hege = models.FloatField(default=0.0, help_text="AS Hegemony is the estimated fraction of paths towards the originasn. The values range between 0 and 1, low values represent a small number of path (low dependency) and values close to 1 represent strong dependencies.")
    af = models.IntegerField(default=0, help_text="Address Family (IP version), values are either 4 or 6.")

    objects = CachingManager()

    class Meta:
        base_manager_name = 'objects'  # Attribute name of CachingManager(), above

    def __str__(self):
        return "%s originAS%s AS%s %s" % (self.timebin, self.originasn.number, self.asn.number, self.hege)

class HegemonyCone(CachingMixin, models.Model):
    timebin = models.DateTimeField(db_index=True, help_text="Timestamp of reported value.")
    asn = models.ForeignKey(ASN, on_delete=models.CASCADE, db_index=True, help_text="Autonomous System Number (ASN).")
    conesize = models.IntegerField(default=0, help_text="Number of dependent networks, namely, networks that are reached through the asn, this is similar to CAIDA's customer cone size. The detailed list of all dependent networks is obtained by querying /hegemony/ with parameter asn (e.g /hegemony/?asn=2497&timebin=2020-03-01 gives IIJ's customer networks).")
    af = models.IntegerField(default=0, help_text="Address Family (IP version), values are either 4 or 6.")

    objects = CachingManager()

    class Meta:
        index_together = ("timebin", "asn", "af")
        base_manager_name = 'objects'  # Attribute name of CachingManager(), above

class Hegemony_country(CachingMixin, models.Model):
    timebin = models.DateTimeField(db_index=True, help_text="Timestamp of reported value.")
    country = models.ForeignKey(Country, on_delete=models.CASCADE, db_index=True, help_text="Monitored country. Retrieve all dependencies of a country by setting only this parameter and a timebin.")
    asn = models.ForeignKey(ASN, on_delete=models.CASCADE, db_index=True, help_text="Dependency. Network commonly seen in BGP paths towards monitored country.")
    hege = models.FloatField(default=0.0, help_text="AS Hegemony is the estimated fraction of paths towards the originasn. The values range between 0 and 1, low values represent a small number of path (low dependency) and values close to 1 represent strong dependencies.")
    af = models.IntegerField(default=0, help_text="Address Family (IP version), values are either 4 or 6.")
    weight = models.FloatField(default=0.0, help_text="Absolute weight given to the ASN for the AS Hegemony calculation.")
    weightscheme = models.CharField(max_length=16, default="None", help_text="Weighting scheme used for the AS Hegemony calculation.")
    transitonly = models.BooleanField(default=False, help_text="If True, then origin ASNs of BGP path are ignored (focus only on transit networks).")

    objects = CachingManager()

    class Meta:
        base_manager_name = 'objects'  # Attribute name of CachingManager(), above

    def __str__(self):
        return "%s %s AS%s %s" % (self.timebin, self.country.name, self.asn.number, self.hege)


class Atlas_location(CachingMixin, models.Model):
    name = models.CharField(max_length=255, help_text="Location identifier. The meaning of values dependend on the location type: <ul><li>type=AS: ASN</li><li>type=CT: city name, region name, country code</li><li>type=PB: Atlas Probe ID</li><li>type=IP: IP version (4 or 6)</li></ul> ")
    type = models.CharField(max_length=4, help_text="Type of location. Possible values are: <ul><li>AS: Autonomous System</li><li>CT: City</li><li>PB: Atlas Probe</li><li>IP: Whole IP space</li></ul>")
    af = models.IntegerField(help_text="Address Family (IP version), values are either 4 or 6.")

    objects = CachingManager()

    class Meta:
        base_manager_name = 'objects'  # Attribute name of CachingManager(), above

    def __str__(self):
        return "(%s) %s %s" % (self.type, self.name, self.af)


class Atlas_delay(CachingMixin, models.Model):
    timebin = models.DateTimeField(db_index=True, help_text="Timestamp of reported value.")
    startpoint = models.ForeignKey(Atlas_location, on_delete=models.CASCADE,
             db_index=True, related_name='location_startpoint', help_text="Starting location for the delay estimation.")
    endpoint = models.ForeignKey(Atlas_location, on_delete=models.CASCADE,
             db_index=True, related_name='location_endpoint', help_text="Ending location for the delay estimation.")
    median = models.FloatField(default=0.0, help_text="Estimated median RTT. RTT values are directly extracted from traceroute (a.k.a. realrtts) and estimated via differential RTTs.")
    nbtracks = models.IntegerField(default=0, help_text="Number of RTT samples used to compute median RTT (either real or differential RTT).")
    nbprobes = models.IntegerField(default=0, help_text="Number of Atlas probes used to compute median RTT.")
    entropy = models.FloatField(default=0.0, help_text="Entropy of RTT samples with regards to probes' ASN. Values close to zero mean that Atlas probes used for these measures are located in the same AS, values close to one means that preobes are equally spread out accross multiple ASes.")
    hop = models.IntegerField(default=0, help_text="Median number of AS hops between the start and end locations.")
    nbrealrtts = models.IntegerField(default=0, help_text="Number of RTT samples directly obtained from traceroutes (as opposed to differential RTTs).")

    objects = CachingManager()

    class Meta:
        base_manager_name = 'objects'  # Attribute name of CachingManager(), above

    def __str__(self):
        return "%s -> %s: %s" % (
                self.startpoint.name, self.endpoint.name, self.median)

class Hegemony_alarms(CachingMixin, models.Model):
    timebin = models.DateTimeField(db_index=True, help_text="Timestamp of reported alarm.")
    originasn = models.ForeignKey(ASN, on_delete=models.CASCADE, related_name="anomalous_originasn", db_index=True, help_text="ASN of the reported dependent network.")
    asn = models.ForeignKey(ASN, on_delete=models.CASCADE, related_name="anomalous_asn", db_index=True, help_text="ASN of the anomalous dependency (transit network).")
    deviation = models.FloatField(default=0.0, help_text="Significance of the AS Hegemony change.")
    af = models.IntegerField(help_text="Address Family (IP version), values are either 4 or 6.")

    objects = CachingManager()

    class Meta:
        base_manager_name = 'objects'  # Attribute name of CachingManager(), above

    def __str__(self):
        return "(%s, %s, v%s) %s" % (self.originasn, self.asn, self.af, self.deviation)

class Atlas_delay_alarms(CachingMixin, models.Model):
    timebin = models.DateTimeField(db_index=True, help_text="Timestamp of reported alarm.")
    startpoint = models.ForeignKey(Atlas_location, on_delete=models.CASCADE,
             db_index=True, related_name='anomalous_startpoint', help_text="Starting location reported as anomalous.")
    endpoint = models.ForeignKey(Atlas_location, on_delete=models.CASCADE,
             db_index=True, related_name='anomalous_endpoint', help_text="Ending location reported as anomalous.")
    deviation = models.FloatField(default=0.0, help_text="Significance of the AS Hegemony change.")

    objects = CachingManager()

    class Meta:
        base_manager_name = 'objects'  # Attribute name of CachingManager(), above

    def __str__(self):
        return "(%s, %s) %s" % (self.startpoint, self.endpoint, self.deviation)

#user
class UserManager(BaseUserManager):
    def _create_user(self, email, password):
        if not email or not password:
            raise ValueError('The email and password must be set')
        email = self.normalize_email(email)
        user = self.model(email=email)
        user.set_password(password)
        user.is_active = False
        user.save()
        return user

    def create_user(self, email, password, **extra_fields):
        """
        Create a User.
        """
        if not email:
            raise ValueError('The Email must be set')

        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password)

    def create_superuser(self, email, password, **extra_fields):
        """
        Create a super User.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password)


class IHRUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, help_text='Email of the user, also used a the login ID.')
    groups = models.ManyToManyField(
        Group,
        blank=True,
        related_name="ihruser_set",
        related_query_name="ihruser",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name="ihruser_set",
        related_query_name="ihruser",
    )
    is_active = models.BooleanField(default=False)
    # last time requested for password
    objects = UserManager()
    monitoringasn = models.ManyToManyField(
        'ASN', through='MonitoredASN')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []


class EmailChangeRequest(models.Model):
    """
    This model permit to change the email leaving the IHRUser model DRY.
    store change requests so can be verified by the change entrypoint
    """
    user = models.ForeignKey(IHRUser, on_delete=models.CASCADE)
    new_email = models.EmailField(unique=True)
    request_time = models.DateTimeField(auto_now_add=True)

    VALIDITY = 60 * 24 #expressed in minutes


class MonitoredASN(models.Model):
    NOTIFY_LEVEL = Choices((0, 'LOW', 'low'), (5, 'MODERATE', 'moderate'), (10, 'HIGH', 'high'))
    user = models.ForeignKey(IHRUser, on_delete=models.CASCADE)
    asn = models.ForeignKey(ASN, on_delete=models.CASCADE)

    notifylevel = models.SmallIntegerField(
        choices=NOTIFY_LEVEL,
        default=NOTIFY_LEVEL.HIGH
    )

# TODO Remove this?

class Delay_alarms_msms(models.Model):
    alarm = models.ForeignKey(Delay_alarms, related_name="msmid",
            on_delete=models.CASCADE)
    msmid = models.BigIntegerField(default=0)
    probeid = models.IntegerField(default=0)

    def __str__(self):
        return "%s %s" % (self.msmid, self.probeid)


class Forwarding_alarms_msms(models.Model):
    alarm = models.ForeignKey(Forwarding_alarms, related_name="msmid",
            on_delete=models.CASCADE)
    msmid = models.BigIntegerField(default=0)
    probeid = models.IntegerField(default=0)

    def __str__(self):
        return "%s %s" % (self.msmid, self.probeid)

