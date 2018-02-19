# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from cmachines.settings import ALLOW_EMAILS
from cmachines.settings import DEFAULT_USER_CREDIT
from users.utils import send_email
from users.utils import generate_password
from users.utils import get_client_ip
from users.utils import get_ip_send_emails_file
from users.utils import get_ip_send_emails
from users.utils import save_ip_send_emails
from users.models import User as UserLocal
from users.models import PhysicalMachine
from users.models import VirtualMachines
from users.models import UserLog 
from django.contrib.auth.models import User
from dateutil import parser
from datetime import datetime
from datetime import timedelta
import base64
import uuid
import math
import sys, traceback

def write_log(user_id, short_description, description):
    user_log = UserLog.objects.create(
        created_by=user_id,
        short_description=short_description,
        description=description,
    )
    user_log.save()

def write_log_request(request, short_description, description):
    if request.user.is_authenticated():
        user_email = request.user.email
        user_id = UserLocal.objects.get(name=user_email)
        write_log(user_id, short_description, description)

def consume_user_credit(request, cost_money):
    if request.user.is_authenticated():
        user_email = request.user.email
        user_id = UserLocal.objects.get(name=user_email)
        user_id.credit -= cost_money
        user_id.save()
        short_description = "consume %d RMB" % cost_money
        description = short_description
        write_log_request(request, short_description, description)

def refund_user_credit(request, refund_money):
    if request.user.is_authenticated():
        user_email = request.user.email
        user_id = UserLocal.objects.get(name=user_email)
        user_id.credit += refund_money
        user_id.save()
        short_description = "refund %d RMB" % refund_money
        description = short_description
        write_log_request(request, short_description, description)

def refund_user_credit_by_ratio_day(request, cost_money_per_day):
    if request.user.is_authenticated():
        print("refund_user_credit_by_ratio_day")
        cur_date = datetime.now()
        tomorrow_date = cur_date + timedelta(days=1)
        tomorrow_date = datetime(year=tomorrow_date.year, month=tomorrow_date.month, day=tomorrow_date.day)
        diff_time = tomorrow_date - cur_date
        print("refund=", (diff_time.seconds / float(3600*24)) * cost_money_per_day)
        refund_money = int((diff_time.seconds / float(3600*24)) * cost_money_per_day)
        refund_user_credit(request, refund_money)

def check_if_enough_credit_by_ratio_day(request, cost_money_per_day):
    cur_date = datetime.now()
    tomorrow_date = cur_date + timedelta(days=1)
    tomorrow_date = datetime(year=tomorrow_date.year, month=tomorrow_date.month, day=tomorrow_date.day)
    diff_time = tomorrow_date - cur_date
    #print("cost_money_per_day=", cost_money_per_day)
    #print("diff_time hours=", diff_time.seconds/3600.0)
    cost_money = math.ceil((diff_time.seconds / float(3600*24)) * cost_money_per_day)
    user_email = request.user.email
    user_id = UserLocal.objects.get(name=user_email)
    if user_id.credit >= cost_money:
        return True
    return False

def consume_credit_by_ratio_day(request, cost_money_per_day):
    cur_date = datetime.now()
    tomorrow_date = cur_date + timedelta(days=1)
    tomorrow_date = datetime(year=tomorrow_date.year, month=tomorrow_date.month, day=tomorrow_date.day)
    diff_time = tomorrow_date - cur_date
    #print("cost_money_per_day=", cost_money_per_day)
    #print("diff_time hours=", diff_time.seconds/3600.0)
    cost_money = math.ceil((diff_time.seconds / float(3600*24)) * cost_money_per_day)
    consume_user_credit(request, cost_money)

def estimate_price(cpu_cores, mem, gpu_mem, disk_size, hdd_disk_size):
    price = 0
    price += cpu_cores * 1 ## 1
    price += (mem / 1000) * 2 ## 2
    price += (gpu_mem / 1000) * 5 ## 5
    if disk_size > 30:
        price += int((disk_size - 30) / 10.0 * 4)
    if hdd_disk_size > 25:
        price += (hdd_disk_size - 25) / 10.0 * 0.5
    price = math.ceil(price)
    return price

def remove_virtual_machine(request, virtual_machine_name):
    entity_del = VirtualMachines.objects.filter(name=virtual_machine_name)
    write_log_request(
        request,
        short_description="remove machine %s" % virtual_machine_name,
        description="remove machine %s" % virtual_machine_name,
    )
    refund_user_credit_by_ratio_day(request, entity_del[0].cost_money_per_day)
    entity_del.delete()

def get_sum_attr(physical_machine, attr_name, min_val=0):
    sum_val = 0
    vms = VirtualMachines.objects.filter(physical_machine=physical_machine)
    for vm in vms:
        #print("get_sum_attr vm=", vm)
        #print(getattr(vm, attr_name))
        if getattr(vm, attr_name) > min_val:
            #print("debug vm.name=", vm.name)
            #print(getattr(vm, attr_name))
            sum_val += getattr(vm, attr_name)
    return sum_val

def check_if_enough_resource(physical_machine, **kwargs):
    if "gpu_mem" in kwargs:
        gpu_mem = kwargs.get("gpu_mem", 0)
        if gpu_mem <= 1000:
            gpu_mem = 0
        #print("gpu_mem=", gpu_mem)
        cur_sum = get_sum_attr(physical_machine, "gpu_mem", 1001)
        if gpu_mem + cur_sum > physical_machine.mem_gpu:
            return False, "not enough gpu memory"
    return True, ""

def modify_virtual_machine(request,
                           physical_machine_name,
                           cpu_cores, mem,
                           gpu_mem,
                           hdd_disk_size,
                           cost_money_per_day=10,
                           connection_info = u"updating",
                          ):
    is_success = True
    error_message = ""
    try:
        virtual_machine_name = physical_machine_name + "_" + str(uuid.uuid4())[:8]
        user_email = request.user.email
        user_local = UserLocal.objects.get(name=user_email)
        physical_machine = PhysicalMachine.objects.get(name=physical_machine_name)
        virtual_machine = VirtualMachines.objects.get(physical_machine=physical_machine, created_by=user_local)

        if gpu_mem > virtual_machine.gpu_mem:
            is_success, error_message = check_if_enough_resource(
                physical_machine, gpu_mem=(gpu_mem - virtual_machine.gpu_mem))
            if not is_success:
                return is_success, error_message

        virtual_machine.gpu_mem = gpu_mem
        virtual_machine.mem = mem
        if virtual_machine.hdd_disk_size <= hdd_disk_size:
            virtual_machine.hdd_disk_size = hdd_disk_size
        else:
            is_success = False
            error_message = "hdd disk can only be increased: %dG is less than %dG" % (hdd_disk_size, virtual_machine.hdd_disk_size)
            return is_success, error_message
        virtual_machine.cpu_cores = cpu_cores
        previous_cost_money_per_day = virtual_machine.cost_money_per_day
        if cost_money_per_day > previous_cost_money_per_day:
            if not check_if_enough_credit_by_ratio_day(request, cost_money_per_day - previous_cost_money_per_day):
                is_success = False
                error_message = "not enough credit"
                return is_success, error_message

        virtual_machine.cost_money_per_day=cost_money_per_day
        virtual_machine.connection_info = connection_info
        virtual_machine.save()
        virtual_machine_name=virtual_machine.name
        description = "Update a new machine %(virtual_machine_name)s/(Physical machine %(physical_machine)s). "\
                      "GPU memory %(gpu_mem)d MiB. "\
                      "Memory %(mem)d mb. "\
                      "HDD Disk size %(hdd_disk_size)d G. "\
                      "CPU cores %(cpu_cores)d. "\
                      "Cost %(cost_money_per_day)d RMB per day. "
        description = description % {
            "virtual_machine_name": virtual_machine_name,
            "physical_machine": physical_machine,
            "gpu_mem": int(gpu_mem),
            "mem": int(mem),
            "hdd_disk_size": int(hdd_disk_size),
            "cpu_cores": int(cpu_cores),
            "cost_money_per_day": int(cost_money_per_day),
        }
        print("modify_virtual_machine")
        write_log(user_local,
            short_description="modify a new machine %s" % virtual_machine_name,
            description=description,
        )
        if previous_cost_money_per_day > cost_money_per_day:
            refund_user_credit_by_ratio_day(
                request, previous_cost_money_per_day - cost_money_per_day)
        else:
            consume_credit_by_ratio_day(request,
                cost_money_per_day - previous_cost_money_per_day)

        ## calculate the cost        
    except:
        print("Exception in user code:")
        print('-'*60)
        traceback.print_exc(file=sys.stdout)
        print('-'*60)
        is_success = False
    return is_success, error_message

def add_new_virtual_machine(request,
                            user_email, 
                            physical_machine_name,
                            cpu_cores, mem,
                            gpu_mem,
                            disk_size,
                            hdd_disk_size,
                            cost_money_per_day=10,
                            connection_info = u"creating",
                            connection_host = u"0.0.0.0",
                            connection_port = -1,
                            connection_password = "",
                            ):
    is_success = True
    error_message = ""
    try:
        ## check if enough money
        user_local = UserLocal.objects.get(name=user_email)
        if user_local.credit < cost_money_per_day:
            is_success = False
            error_message = "not enough money for one day"
            return is_success, error_message

        virtual_machine_name = physical_machine_name + "_" + str(uuid.uuid4())[:8]
        physical_machine = PhysicalMachine.objects.get(name=physical_machine_name)
        print("....")
        ## check if we have enough resource to create a machine
        is_success, error_message = check_if_enough_resource(physical_machine, gpu_mem=gpu_mem)
        if not is_success:
            return is_success, error_message

        virtual_machine = VirtualMachines.objects.create(
            name=virtual_machine_name,
            physical_machine=physical_machine,
            created_by=user_local,
            gpu_mem=gpu_mem,
            mem=mem,
            disk_size=disk_size,
            hdd_disk_size=hdd_disk_size,
            cpu_cores=cpu_cores,
            connection_info=connection_info,
            connection_host=connection_host,
            connection_port=connection_port,
            connection_password=generate_password(),
            cost_money_per_day=cost_money_per_day
            )
        virtual_machine.save()
        description = "Create a new machine %(virtual_machine_name)s/(Physical machine %(physical_machine)s). "\
                      "GPU memory %(gpu_mem)d MiB. "\
                      "Memory %(mem)d mb. "\
                      "Disk size %(disk_size)d G. "\
                      "CPU cores %(cpu_cores)d. "\
                      "Cost %(cost_money_per_day)d RMB per day. "
        description = description % {
            "virtual_machine_name": virtual_machine_name,
            "physical_machine": physical_machine,
            "gpu_mem": int(gpu_mem),
            "mem": int(mem),
            "disk_size": int(disk_size),
            "cpu_cores": int(cpu_cores),
            "cost_money_per_day": int(cost_money_per_day),
        }
        write_log(user_local,
            short_description="create a new machine %s" % virtual_machine_name,
            description=description,
        )
        consume_credit_by_ratio_day(request, cost_money_per_day)
        ## calculate the cost        
    except:
        print("Exception in user code:")
        print('-'*60)
        traceback.print_exc(file=sys.stdout)
        print('-'*60)
        is_success = False
    return is_success, error_message
    
def add_new_user(user_email, request):
    is_success = True
    error_message = ""
    is_allow = False
    for allow_email in ALLOW_EMAILS:
        if user_email.endswith(allow_email):
            is_allow = True
            break
    if not is_allow:
        error_message = u"%s不在允许的emails列表中" % user_email
        is_success = False
        return is_success, error_message
    try:
        is_new_account = False
        one_user = UserLocal.objects.get(name=user_email)
        user_password = base64.b64decode(one_user.password_plain)
        subject = u"虫数据 GPU 主机 密码忘记"
        print("Password forgot: ", user_email, ":", user_password)
    except:
        is_new_account = True
        user_password = generate_password()
        subject = u"虫数据 GPU 主机 用户创建"
        print("User creation: ", user_email, ":", user_password)
    content = u"用户帐号: %s\n用户密码: %s" % (user_email, user_password)
    ip_address = get_client_ip(request)
    print("%s ask for a new account." % ip_address)
    ip_send_emails = get_ip_send_emails()
    ip_address_data = ip_send_emails.get(ip_address, {})
    is_allow_email = True
    max_re_send_email = 5*60
    if "send_email" in ip_address_data:
        last_sent_time = parser.parse(ip_address_data["send_email"])
        if (datetime.now() - last_sent_time).seconds < max_re_send_email:
            is_allow_email = False
            error_message = "%d 分钟内只能申请一次" % int(max_re_send_email/60)
    if not is_allow_email:
        is_success = False
        return is_success, error_message 
    send_email(subject, content, [user_email, ])
    ip_address_data["send_email"] = datetime.now().isoformat()
    ip_send_emails[ip_address] = ip_address_data
    save_ip_send_emails(ip_send_emails)
    if is_new_account:
        u = User.objects.create_user(user_email, user_email, user_password)
        u.save()
        u_local = UserLocal(name=user_email, credit=DEFAULT_USER_CREDIT,
                            password_plain=base64.b64encode(user_password))
        u_local.save()
    return is_success, error_message


def compuate_total_cost(user_local, ):
    sum_cost = 0
    vms = VirtualMachines.objects.filter(created_by=user_local)
    for vm in vms:
        sum_cost += vm.cost_money_per_day
    return sum_cost

def daily_update_user_credit():
    for user in UserLocal.objects.filter():
        user_total_cost = compuate_total_cost(user)
        if user.credit >= user_total_cost:
            user.credit -= user_total_cost
            description = "daily consume %d RMB" % user_total_cost
            write_log(user, description, description)
            user.save()
        else:
            vms = VirtualMachines.objects.filter(created_by=user)
            vms.delete()
            short_description = "remove virtual machines"
            description = "remove virtual machines because of insuffic insufficient money"
            write_log(user, short_description, description)

def daily_notify_user():
    subject = u"虫数据主机将在24小时后删除"
    content = u"由于余额不足，您的虫数据主机将会在下一个凌晨12点被删除, 如果需要保存数据请及时充值或者降低主机配置。"
    for user in UserLocal.objects.filter():
        user_total_cost = compuate_total_cost(user)
        if user.credit < user_total_cost and (not user.is_ban):
            #if not user.is_free_user:
            print("virtual machines of %s will be deleted." % user.name)
            send_email(subject, content, [user.name, ])

