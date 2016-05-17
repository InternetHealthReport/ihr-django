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
