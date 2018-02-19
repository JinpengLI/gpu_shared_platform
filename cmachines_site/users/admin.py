# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from .models import User
from .models import PhysicalMachine
from .models import VirtualMachines

# Register your models here.
admin.site.register(User)
admin.site.register(PhysicalMachine)
admin.site.register(VirtualMachines)
