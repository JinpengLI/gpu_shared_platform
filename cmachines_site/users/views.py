# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from cmachines.settings import ALLOW_EMAILS
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.core import serializers
from django.shortcuts import redirect
from django.shortcuts import render
from django.contrib.auth.models import User
from users.controllers import add_new_user
from django.contrib.auth import authenticate
from django.contrib.auth import logout
from django.contrib.auth import login
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import PhysicalMachine
from .controllers import estimate_price as api_estimate_price
from .controllers import add_new_virtual_machine
from .controllers import remove_virtual_machine
from .controllers import modify_virtual_machine
from .controllers import write_log
from .controllers import get_sum_attr
from .models import PhysicalMachine
from .models import VirtualMachines
from .models import User as UserLocal
from .models import UserLog
from cmachines.settings import MAX_GPU_MEM_PER_USER
# Create your views here.


@login_required
def ws_virtual_machines(request):
    current_user = request.user
    print current_user.username    
    groups = request.user.groups.values_list('name', flat=True)
    if "physical_machines" not in groups:
        return HttpResponse('Unauthorized', status=401)
    physical_machine = current_user.username
    physical_machine_id = PhysicalMachine.objects.get(name=physical_machine)
    print("physical_machine=", physical_machine)
    q = VirtualMachines.objects.all().filter(physical_machine=physical_machine_id)
    serialized_obj = serializers.serialize('json', q)
    #data = []
    #for vm in q:
    #    print(vm.to_json())
    #    data.append(vm.to_json())
    return JsonResponse(serialized_obj, safe=False)

@login_required
@csrf_exempt
def ws_virtual_machines_set(request):
    print("request.POST=", request.POST)
    update_data = request.POST
    update_vm_name = update_data["name"]

    current_user = request.user
    print current_user.username    
    groups = request.user.groups.values_list('name', flat=True)
    if "physical_machines" not in groups:
        return HttpResponse('Unauthorized', status=401)
    physical_machine = current_user.username
    physical_machine_id = PhysicalMachine.objects.get(name=physical_machine)
    q = VirtualMachines.objects.all().filter(physical_machine=physical_machine_id, name=update_vm_name)
    if q.count() != 1:
        return HttpResponse('Unauthorized', status=401)
    vm_obj = q.first()
    if "host" in update_data:
        vm_obj.connection_host = update_data["host"]
    if "port" in update_data:
        vm_obj.connection_port = update_data["port"]
    if "connection_info" in update_data:
        vm_obj.connection_info = update_data["connection_info"]
    if "is_ban" in update_data:
        if int(update_data["is_ban"]) == 1:
           user_local = vm_obj.created_by
           print("%s is banded.." % user_local.name) 
           user_local.is_ban = True
           user_local.save()
    vm_obj.save()
    #serialized_obj = serializers.serialize('json', q)
    #data = []
    #for vm in q:
    #    print(vm.to_json())
    #    data.append(vm.to_json())
    ret_obj = {}
    ret_obj["is_success"] = True
    ret_obj["message"] = ""
    return JsonResponse(ret_obj, safe=False)

@csrf_exempt
def ws_login(request):
    if request.POST:
        #print(request.POST)
        user = None
        username = request.POST.get("username", None)
        password = request.POST.get("password", None)
        if username is not None and password is not None:
            user = authenticate(request, username=username, password=password)
            request.session.set_expiry(0)
            login(request, user)
            return HttpResponse('OK')
    return HttpResponse('Unauthorized', status=401)

@login_required
def log(request):
    user_local = UserLocal.objects.get(name=request.user.email)    
    user_logs = UserLog.objects.filter(created_by=user_local).extra(order_by = ['-creation_time'])
    page_data = {}
    page_data["user_logs"] = user_logs
    return render(request, 'users/log.html', page_data)

@login_required
def machines(request):
    is_success = True
    error_message = ""
    if request.POST and request.user.is_authenticated():
        # print("request.POST=", request.POST)
        ## check if remove a machine
        rm_vm_name = request.POST.get("del_vm", None)
        if rm_vm_name is not None:
            print("remove virtual machine ", rm_vm_name)
            remove_virtual_machine(request, rm_vm_name)
        elif request.POST.get("cpu_cores", None) is not None:
            # check machine
            print("request.POST=", request.POST)
            if request.POST["machine_created_type"] == "new":    
                cpu_cores = int(request.POST["cpu_cores"])
                mem = int(request.POST["mem"])
                gpu_mem = int(request.POST["gpu_mem"])
                disk_size = int(request.POST["disk_size"])
                hdd_disk_size = int(request.POST["hdd_disk_size"])
                cost_money_per_day = api_estimate_price(
                    int(cpu_cores),
                    int(mem),
                    int(gpu_mem),
                    int(disk_size),
                    int(hdd_disk_size),
                )
                physical_machine_name = request.POST["machine_type"]
                user_email = request.user.email
                is_success, error_message = add_new_virtual_machine(
                    request=request,
                    user_email=user_email,
                    physical_machine_name=physical_machine_name,
                    cpu_cores=cpu_cores,
                    mem=mem,
                    gpu_mem=gpu_mem,
                    disk_size=disk_size,
                    hdd_disk_size=hdd_disk_size,
                    cost_money_per_day=cost_money_per_day,
                )
                if is_success:
                    print("success machine creation...")
                else:
                    print("fail to create machine..")
            elif request.POST["machine_created_type"] == "modified":
                cpu_cores = int(request.POST["cpu_cores"])
                mem = int(request.POST["mem"])
                gpu_mem = int(request.POST["gpu_mem"])
                physical_machine_name = request.POST["machine_type"]
                user_email = request.user.email
                user_local = UserLocal.objects.get(name=user_email)
                physical_machine = PhysicalMachine.objects.get(name=physical_machine_name)
                virtual_machine = VirtualMachines.objects.get(physical_machine=physical_machine, created_by=user_local)
                disk_size = virtual_machine.disk_size
                ## disk_size = int(request.POST["disk_size"]) cannot be modified
                hdd_disk_size = int(request.POST["hdd_disk_size"])
                cost_money_per_day = api_estimate_price(
                    int(cpu_cores),
                    int(mem),
                    int(gpu_mem),
                    int(disk_size),
                    int(hdd_disk_size),
                )
                user_email = request.user.email
                is_success, error_message = modify_virtual_machine(
                    request=request,
                    physical_machine_name=physical_machine_name,
                    cpu_cores=cpu_cores,
                    mem=mem,
                    gpu_mem=gpu_mem,
                    hdd_disk_size=hdd_disk_size,
                    cost_money_per_day=cost_money_per_day,
                )
                if is_success:
                    print("success machine modification...")
                else:
                    print("fail to modify machine..")

    machine_configs = {}
    user_local = UserLocal.objects.get(name=request.user.email)
    if user_local.is_ban:
        request.session.set_expiry(1)
        return HttpResponse('Unauthorized', status=401)
    if user_local.is_free_user:
        machine_configs["cpu_cores"] = [
            {"key": key, "selected": False}
            for key in range(1, 3)
        ]
        machine_configs["mem"] = [
            {"key": key, "selected": False}
             for key in range(1000, 4001, 1000)
        ]
        machine_configs["gpu_mem"] = [
            {"key": key, "selected": False}
            for key in range(0, 1001, 1000)
        ]
        machine_configs["disk_size"] = [
            {"key": key, "selected": False}
            for key in range(30, 51, 5)
        ]
        machine_configs["hdd_disk_size"] = [
            {"key": key, "selected": False}
            for key in range(25, 51, 25)
        ]
    else:
        machine_configs["cpu_cores"] = [
            {"key": key, "selected": False}
            for key in range(1, 5)
        ]
        machine_configs["mem"] = [
            {"key": key, "selected": False}
             for key in range(1000, 10001, 1000)
        ]
        machine_configs["gpu_mem"] = [
            {"key": key, "selected": False}
            for key in range(0, 4001, 1000)
        ]
        machine_configs["disk_size"] = [
            {"key": key, "selected": False}
            for key in range(30, 51, 5)
        ]
        machine_configs["hdd_disk_size"] = [
            {"key": key, "selected": False}
            for key in range(25, 151, 25)
        ]

    #print("physical_machines....")
    physical_machines = PhysicalMachine.objects.all()
    virtual_machines = VirtualMachines.objects.filter(created_by=user_local)
    page_physical_machines = []
    for physical_machine in physical_machines:
        dict_physical_machine = {}
        dict_physical_machine["name"] = physical_machine.name
        dict_physical_machine["already_created_vm"] = False
        dict_physical_machine["remaining_gpu_mem"] = min(
                                                           max(1000, 
                                                             physical_machine.mem_gpu - get_sum_attr(physical_machine, "gpu_mem", 1001)
                                                           ),
                                                           MAX_GPU_MEM_PER_USER
                                                        )
        vm_objs = VirtualMachines.objects.filter(
            created_by=user_local, physical_machine=physical_machine)
        if vm_objs.count() > 0:
            dict_physical_machine["already_created_vm"] = True
            vm_obj = vm_objs[0]
            config_names = machine_configs.keys()
            for config_name in config_names:
                #print("config_name=", config_name)
                #print("getattr(vm_obj, config_name)=", getattr(vm_obj, config_name))
                for i, item in enumerate(machine_configs[config_name]):
                    #print("config_name=", config_name)
                    #print("getattr(vm_obj, config_name)=", getattr(vm_obj, config_name))
                    if item["key"] == getattr(vm_obj, config_name):
                        item["selected"] = True
                        break
        page_physical_machines.append(dict_physical_machine)
    #print("machine_configs=", machine_configs)
    page_data = {}
    page_data["is_free_user"] = user_local.is_free_user
    page_data["user_credit"] = user_local.credit
    page_data["physical_machines"] = page_physical_machines
    page_data["virtual_machines"] = virtual_machines
    page_data["machine_configs"] = machine_configs
    page_data["error_message"] = error_message
    page_data["is_success"] = is_success
    #print("virtual_machines.count()=", virtual_machines.count())
    return render(request, 'users/machines.html', page_data)


def root_index(request):
    return redirect('/users')

@login_required
def index(request):
    page_data = {}
    if request.user.is_authenticated():
        print("user already login %s" % request.user.username)
    else:
        print("user not login")
    page_data["credit_page"] = False
    page_data["error_message"] = ""
    if request.user.is_superuser:
        page_data["credit_page"] = True
        print("request.POST=", request.POST)
        if "email" in request.POST:
            user_email = request.POST["email"]
            money = int(request.POST["money"])
            long_description = request.POST["description"]
            user_local = UserLocal.objects.get(name=user_email)
            if (user_local.is_free_user and int(money) >= 20) or\
                    (not user_local.is_free_user):
                user_local.credit += int(money)
                user_local.is_free_user = False
                user_local.save()
                short_description = "credit %d rmb" % money
                description = short_description + " " + long_description
                write_log(user_local, short_description, description)
            else:
                page_data["error_message"] = u"免费用户充值低于20元"
    return render(request, 'users/index.html', page_data)
    #return HttpResponse("Hello, world. You're at the polls index.")

@login_required
def estimate_price(request):
    try:
        cpu_cores = request.GET["cpu_cores"]
        mem = request.GET["mem"]
        gpu_mem = request.GET["gpu_mem"]
        disk_size = request.GET["disk_size"]
        hdd_disk_size = request.GET["hdd_disk_size"]
        price = api_estimate_price(int(cpu_cores), int(mem), int(gpu_mem), int(disk_size), int(hdd_disk_size))
    except:
        price = None
    return JsonResponse({"price": price})

def register(request):
    page_data = {}
    if request.POST:
        input_email = request.POST.get("inputEmail", "")
        is_success, error_message = add_new_user(input_email, request)
        if not is_success:
            page_data["error_message"] = error_message
        else:
            page_data["error_message"] = u"发送成功，请查收邮件"
    return render(request, 'users/register.html', page_data)

def signin(request):
    page_data = {}
    if request.POST:
        print(request.POST)
        print(request.GET)
        next_url = request.GET.get("next", None)
        input_email = request.POST.get("inputEmail", "")
        password = request.POST.get("password", "")
        remember_me = request.POST.get("remember_me", "")
        user = authenticate(username=input_email, password=password)
        if user is not None:
            user_local = UserLocal.objects.get(name=input_email)
            if user_local.is_ban:
                print("%s is band" % input_email)
                page_data["error_message"] = u"用户验证失败"
                return render(request, 'users/signin.html', page_data)
            login(request, user)
            if len(remember_me) > 0:
                request.session.set_expiry(0)
            login(request, user)
            if next_url is None:
                return redirect('./')
            else:
                return redirect(next_url)
            #page_data["error_message"] = u"success"
        else:
            page_data["error_message"] = u"用户验证失败"
    return render(request, 'users/signin.html', page_data)

def signout(request):
    logout(request)
    return redirect('./')    

def example(request):
    return render(request, 'users/example.html', {})
