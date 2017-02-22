from django.db import models

class ASN(models.Model):
    number = models.IntegerField(primary_key=True)
    name   = models.CharField(max_length=255)

    def __str__(self):
        return "ASN%s %s" % (self.number, self.name)


class Congestion(models.Model):
    timebin = models.DateTimeField(db_index=True)
    asn = models.ForeignKey(ASN, on_delete=models.CASCADE)
    magnitude = models.FloatField(default=0.0)
    deviation = models.FloatField(default=0.0)
    # TODO add a table for tfidf results
    label     = models.CharField(max_length=255)

    def __str__(self):
        return "%s AS%s" % (self.timebin, self.asn.number)


class Congestion_alarms(models.Model):
    asn = models.ForeignKey(ASN, on_delete=models.CASCADE, db_index=True)
    timebin = models.DateTimeField(db_index=True)
    ip = models.CharField(max_length=64, db_index=True)
    link = models.CharField(max_length=128, db_index=True)
    medianrtt = models.FloatField(default=0.0)
    diffmedian = models.FloatField(default=0.0)
    deviation = models.FloatField(default=0.0)
    nbprobes = models.IntegerField(default=0)

    def __str__(self):
        return "%s AS%s" % (self.timebin, self.asn.number)

    
class Forwarding_alarms(models.Model):
    asn = models.ForeignKey(ASN, on_delete=models.CASCADE, db_index=True)
    timebin = models.DateTimeField(db_index=True)
    ip = models.CharField(max_length=64, db_index=True)
    correlation = models.FloatField(default=0.0)
    responsibility = models.FloatField(default=0.0)
    pktdiff = models.FloatField(default=0.0)
    previoushop   = models.CharField(max_length=64)

    def __str__(self):
        return "%s AS%s %s" % (self.timebin, self.asn.number, self.ip)
    

class Forwarding(models.Model):
    timebin = models.DateTimeField(db_index=True)
    asn = models.ForeignKey(ASN, on_delete=models.CASCADE)
    magnitude = models.FloatField(default=0.0)
    resp = models.FloatField(default=0.0)
    # TODO add a table for tfidf results
    label     = models.CharField(max_length=255, default="")

    def __str__(self):
        return "%s AS%s" % (self.timebin, self.asn.number)

class CongestionRanking(models.Model):
    asn = models.ForeignKey(ASN, on_delete=models.CASCADE)
    score = models.FloatField(default=0.0)
    timebin = models.DateTimeField()

    def __str__(self):
        return "%s AS%s" % (self.timebin, self.asn.number)


class ForwardingRanking(models.Model):
    asn = models.ForeignKey(ASN, on_delete=models.CASCADE)
    score = models.FloatField(default=0.0)
    timebin = models.DateTimeField()

    def __str__(self):
        return "%s AS%s" % (self.timebin, self.asn.number)
