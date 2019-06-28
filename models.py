from django.db import models
from django.contrib.postgres.fields import JSONField

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
            related_name='startpoint', db_index=True)
    endpoint = models.ForeignKey(Atlas_location, on_delete=models.CASCADE, 
            related_name='endopint', db_index=True)
    median = models.FloatField(default=0.0)
    nbtracks = models.IntegerField(default=0)
    nbprobes = models.IntegerField(default=0)
    entropy = models.FloatField(default=0.0)
    hop = models.IntegerField(default=0)
    nbrealrtts = models.IntegerField(default=0)

    def __str__(self):
        return "%s -> %s: %s" % (
                self.startpoint.name, self.endpoint.name, self.median)


