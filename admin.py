from django.contrib import admin

from .models import ASN
from .models import Congestion  
from .models import Forwarding  

admin.site.register(ASN)
admin.site.register(Congestion)
admin.site.register(Forwarding)

