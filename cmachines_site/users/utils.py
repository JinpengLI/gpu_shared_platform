# -*- coding: utf-8 -*-

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email import Encoders
import smtplib
import socket
import time
import os
from cmachines.settings import ALLOW_EMAILS
from cmachines.settings import EMAIL_SENDER
from cmachines.settings import SMTP_SERVER
from cmachines.settings import SMTP_SERVER_PORT
from cmachines.settings import SMTP_LOGIN
from cmachines.settings import SMTP_PASSWORD_FILE
from cmachines.settings import DATA_DIR
import random
import string
import base64
import json
class EmailManager:

    def __init__(self,
                 smtp_host,
                 smtp_port,
                 smtp_user=None,
                 smtp_user_password=None,
                 ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_user_password = smtp_user_password

    def send_email(self,
                   subject,
                   cont,
                   email_sender,
                   email_receivers,
                   attached_files=None,
                   ):
        # Need to encode
        msg = MIMEMultipart()
        msg['Subject'] =subject
        msg.attach(MIMEText(cont.encode('utf-8'), 'plain', 'utf-8'))
        if attached_files:
            for f in attached_files:
                part = MIMEBase('application', "octet-stream")
                part.set_payload(open(f, "rb").read())
                Encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment',
                                filename="%s" % os.path.basename(f))
                msg.attach(part)
        msg['From'] = email_sender
        msg['To'] = ", ".join(email_receivers)
        s = smtplib.SMTP(host=self.smtp_host,
                         port=int(self.smtp_port))
        if int(self.smtp_port) == 587:
            s.ehlo()
            s.starttls()
        if self.smtp_user is not None and\
                self.smtp_user_password is not None:
            user_name = self.smtp_user.strip()
            pwd = self.smtp_user_password.strip()
            if user_name != "" and pwd != "":
                s.login(user_name, pwd)
        s.sendmail(email_sender,
                   email_receivers,
                   msg.as_string())
        s.close()

def get_project_base_dir():
    dir_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')
    return dir_path

def get_customer_dir():
    dir_path = get_project_base_dir()
    customer_dir = os.path.join(dir_path, DATA_DIR)
    if not os.path.isdir(customer_dir):
        os.makedirs(customer_dir)
    return customer_dir

def generate_password(N=5):
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(N))

def get_ip_send_emails_file():
    customer_dir = get_customer_dir()
    return os.path.join(customer_dir, "ip_send_emails.json") 

def get_ip_send_emails():
    path = get_ip_send_emails_file()
    if not os.path.isfile(path):
        return {}
    else:
        return json.load(open(path, "r"))

def save_ip_send_emails(data):
    path = get_ip_send_emails_file()
    json.dump(data, open(path, "w+"))

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def send_email(subject, cont, email_receivers):
    password_real_path = os.path.join(get_project_base_dir(), SMTP_PASSWORD_FILE)
    password_val = open(password_real_path, 'r').read().strip()
    password_val = base64.b64decode(password_val)
    email_manager = EmailManager(SMTP_SERVER, SMTP_SERVER_PORT,
                                 SMTP_LOGIN, password_val)
    email_manager.send_email(subject, cont, EMAIL_SENDER, email_receivers)
