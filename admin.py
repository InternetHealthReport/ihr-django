from django.contrib import admin

from .models import ASN
from .models import Delay  
from .models import Forwarding  

admin.site.register(ASN)
admin.site.register(Delay)
admin.site.register(Forwarding)

