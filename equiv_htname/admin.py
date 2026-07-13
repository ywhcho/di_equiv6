from django.contrib import admin
from .models import MedInteractionMfname, MedicinesDruginfo, MedicinesMedicine

admin.site.register(MedicinesMedicine)
admin.site.register(MedInteractionMfname)
admin.site.register(MedicinesDruginfo)
