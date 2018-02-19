import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cmachines.settings")
django.setup()

from users.models import User as UserLocal
from users.models import VirtualMachines
from users.controllers import daily_update_user_credit
from users.controllers import daily_notify_user

if __name__ == "__main__":
    print("daily_update_user_credit.....")
    daily_update_user_credit()
    daily_notify_user()
