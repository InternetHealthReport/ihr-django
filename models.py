from django.db import models
from django.contrib.postgres.fields import JSONField
from model_utils import Choices
from django.contrib.auth.models import PermissionsMixin
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import BaseUserManager

class ASN(models.Model):
    number = models.BigIntegerField(primary_key=True)
    name   = models.CharField(max_length=255)
    tartiflette = models.BooleanField(default=False)
    disco = models.BooleanField(default=False)
    ashash = models.BooleanField(default=False)

    def __str__(self):
        return "ASN%s %s" % (self.number, self.name)

class Country(models.Model):
    code = models.CharField(max_length=4, primary_key=True)
    name   = models.CharField(max_length=255)
    tartiflette = models.BooleanField(default=False)
    disco = models.BooleanField(default=False)

    def __str__(self):
        return "%s (%s)" % (self.name, self.code)


# Tartiflette
class Delay(models.Model):
    timebin = models.DateTimeField(db_index=True)
    asn = models.ForeignKey(ASN, on_delete=models.CASCADE)
    magnitude = models.FloatField(default=0.0)

    def __str__(self):
        return "%s AS%s" % (self.timebin, self.asn.number)


class Delay_alarms(models.Model):
    asn = models.ForeignKey(ASN, on_delete=models.CASCADE, db_index=True)
    timebin = models.DateTimeField(db_index=True)
    ip = models.CharField(max_length=64, db_index=True)
    link = models.CharField(max_length=128, db_index=True)
    medianrtt = models.FloatField(default=0.0)
    diffmedian = models.FloatField(default=0.0)
    deviation = models.FloatField(default=0.0)
    nbprobes = models.IntegerField(default=0)
    msm_prb_ids = JSONField(default=None, null=True)

    def __str__(self):
        return "%s AS%s" % (self.timebin, self.asn.number)


class Delay_alarms_msms(models.Model):
    alarm = models.ForeignKey(Delay_alarms, related_name="msmid",
            on_delete=models.CASCADE)
    msmid = models.BigIntegerField(default=0)
    probeid = models.IntegerField(default=0)

    def __str__(self):
        return "%s %s" % (self.msmid, self.probeid)


# @architect.install('partition', type='range', subtype='date', constraint='day', column='timebin')
class Forwarding_alarms(models.Model):
    asn = models.ForeignKey(ASN, on_delete=models.CASCADE, db_index=True)
    timebin = models.DateTimeField(db_index=True)
    ip = models.CharField(max_length=64, db_index=True)
    correlation = models.FloatField(default=0.0)
    responsibility = models.FloatField(default=0.0)
    pktdiff = models.FloatField(default=0.0)
    previoushop   = models.CharField(max_length=64)
    msm_prb_ids = JSONField(default=None, null=True)

    def __str__(self):
        return "%s AS%s %s" % (self.timebin, self.asn.number, self.ip)


class Forwarding_alarms_msms(models.Model):
    alarm = models.ForeignKey(Forwarding_alarms, related_name="msmid",
            on_delete=models.CASCADE)
    msmid = models.BigIntegerField(default=0)
    probeid = models.IntegerField(default=0)

    def __str__(self):
        return "%s %s" % (self.msmid, self.probeid)


class Forwarding(models.Model):
    timebin = models.DateTimeField(db_index=True)
    asn = models.ForeignKey(ASN, on_delete=models.CASCADE)
    magnitude = models.FloatField(default=0.0)

    def __str__(self):
        return "%s AS%s" % (self.timebin, self.asn.number)



# Disco
class Disco_events(models.Model):
    mongoid = models.CharField(max_length=24, default="000000000000000000000000", db_index=True)
    streamtype = models.CharField(max_length=10)
    streamname = models.CharField(max_length=20)
    starttime = models.DateTimeField()
    endtime = models.DateTimeField()
    avglevel = models.FloatField(default=0.0)
    nbdiscoprobes = models.IntegerField(default=0)
    totalprobes = models.IntegerField(default=0)
    ongoing = models.BooleanField(default=False)

    class Meta:
        index_together = ("streamtype", "streamname", "starttime", "endtime")

class Disco_probes(models.Model):
    probe_id = models.IntegerField()
    event = models.ForeignKey(Disco_events, on_delete=models.CASCADE, db_index=True)
    starttime = models.DateTimeField()
    endtime = models.DateTimeField()
    level = models.FloatField(default=0.0)
    ipv4 = models.CharField(max_length=64, default="None")
    prefixv4 = models.CharField(max_length=70, default="None")
    lat = models.FloatField(default=0.0)
    lon = models.FloatField(default=0.0)


class Hegemony(models.Model):
    timebin = models.DateTimeField(db_index=True)
    originasn = models.ForeignKey(ASN, on_delete=models.CASCADE, related_name="local_graph", db_index=True)
    asn = models.ForeignKey(ASN, on_delete=models.CASCADE, db_index=True)
    hege = models.FloatField(default=0.0)
    af = models.IntegerField(default=0)

    def __str__(self):
        return "%s originAS%s AS%s %s" % (self.timebin, self.originasn.number, self.asn.number, self.hege)

class HegemonyCone(models.Model):
    timebin = models.DateTimeField(db_index=True)
    asn = models.ForeignKey(ASN, on_delete=models.CASCADE, db_index=True)
    conesize = models.IntegerField(default=0)
    af = models.IntegerField(default=0)

    class Meta:
        index_together = ("timebin", "asn", "af")


class Atlas_location(models.Model):
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=4)
    af = models.IntegerField()

    def __str__(self):
        return "(%s) %s %s" % (self.type, self.name, self.af)


class Atlas_delay(models.Model):
    timebin = models.DateTimeField(db_index=True)
    startpoint = models.ForeignKey(Atlas_location, on_delete=models.CASCADE,
             db_index=True)
    endpoint = models.ForeignKey(Atlas_location, on_delete=models.CASCADE,
             db_index=True)
    median = models.FloatField(default=0.0)
    nbtracks = models.IntegerField(default=0)
    nbprobes = models.IntegerField(default=0)
    entropy = models.FloatField(default=0.0)
    hop = models.IntegerField(default=0)
    nbrealrtts = models.IntegerField(default=0)

    def __str__(self):
        return "%s -> %s: %s" % (
                self.startpoint.name, self.endpoint.name, self.median)


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
    email = models.EmailField(unique=True)
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
