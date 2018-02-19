# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from datetime import datetime

# Create your models here.

class User(models.Model):
    name = models.CharField(max_length=100, unique=True)
    credit = models.IntegerField(default=0)
    password_plain = models.CharField(max_length=20)
    is_free_user = models.BooleanField(default=True)
    is_ban = models.BooleanField(default=False)
    def __str__(self):
        return self.name

class PhysicalMachine(models.Model):
    name = models.CharField(max_length=200, unique=True)
    mem = models.IntegerField(default=0)
    mem_gpu = models.IntegerField(default=0)
    gpu_name = models.CharField(max_length=200)
    cpu_name =  models.CharField(max_length=200)
    cpu_cores = models.IntegerField(default=2)
    description = models.CharField(max_length=200)
    disk_size = models.IntegerField(default=0) ## G

    def __str__(self):
        return self.name

class VirtualMachines(models.Model):
    name = models.CharField(max_length=200, unique=True)
    physical_machine = models.ForeignKey(PhysicalMachine, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    creation_time = models.DateTimeField(default=datetime.now, blank=True)
    gpu_mem = models.IntegerField(default=0) ## M
    mem = models.IntegerField(default=0) ## M
    disk_size = models.IntegerField(default=0) ## G
    hdd_disk_size = models.IntegerField(default=0) ## G
    cpu_cores = models.IntegerField(default=2)
    #expiration_time = models.DateTimeField(default=datetime.now, blank=True)
    connection_info = models.CharField(max_length=200, default="")
    connection_host = models.CharField(max_length=200, default="")
    connection_port = models.IntegerField(default=8)
    connection_password = models.CharField(max_length=20, default="root")
    cost_money_per_day = models.IntegerField(default=8)

    def __str__(self):
        return self.name + " " +  self.created_by.name


 
class UserLog(models.Model):
    creation_time = models.DateTimeField(default=datetime.now, blank=True)
    #physical_machine_name = models.ForeignKey(PhysicalMachine, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField(max_length=1000, )
    short_description = models.CharField(max_length=200,)
