sudo kill -9 $(ps ax | grep "python manage.py runserver " | fgrep -v grep | awk '{ print $1 }')
unbuffer python manage.py runserver your.ip.address:6570 --insecure >> ./var/log/cmachines.log &
