import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cmachines.settings")
django.setup()

from users.models import User as UserLocal
from users.models import VirtualMachines
from users.controllers import daily_update_user_credit
from users.controllers import daily_notify_user

import sys, paramiko
import sys, traceback


if __name__ == "__main__":
    fail_vm = []
    for vm in VirtualMachines.objects.all():
        try:
            port = int(vm.connection_port)
            client = paramiko.SSHClient()
            #client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.WarningPolicy)
            client.connect(vm.connection_host, port=int(vm.connection_port), username="root", password=vm.connection_password)
            client.close()
        except:
            #fail_vm.append((vm.name, vm.connection_host, vm.connection_port, vm.connection_password))
            var = traceback.format_exc()
            if "AuthenticationException: Authentication failed." not in var:
                fail_vm.append((vm.name, vm.connection_host, vm.connection_port, vm.connection_password)) 
            print("cannot connect to ", vm.name)
            print "Exception in user code:"
            print '-'*60
            traceback.print_exc(file=sys.stdout)
            print '-'*60
    print("\n\n")
    print("machines to debug:")
    for vm in fail_vm:
        print("cannot connect to ", vm)
