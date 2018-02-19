# -*- coding: utf-8 -*-

import requests
import json

class Client(object):

    def __init__(self, base_url, login, password):
        if not base_url.endswith("/"):
            base_url += "/"
        self.base_url = base_url
        self.login_url = base_url + "login"
        self.login = login
        self.password = password
        self.session = requests.Session()
        r = self.session.post(self.login_url, 
            {'username': login, 'password': password},
        )
        self.cookies = r.cookies
        if r.status_code != 200:
            raise ValueError("fail to auth")

    def get_virtual_machines(self,):
        url = self.base_url + "virtual_machines"
        r = self.session.get(url)
        return json.loads(r.json())

    def set_virtual_machine_connection_info(self, vm_name, connection_info):
        url = self.base_url + "virtual_machines/set"
        data = {}
        data["name"] = vm_name
        data["connection_info"] = connection_info
        r = self.session.post(url, data=data)
        return r.json()

    def set_virtual_machine_ban(self, vm_name, is_ban):
        url = self.base_url + "virtual_machines/set"
        data = {}
        data["name"] = vm_name
        data["is_ban"] = int(is_ban)
        r = self.session.post(url, data=data)
        return r.json()

    def set_virtual_machine(self, vm_name, host, port, connection_info, is_ban=0):      
        print("call set_virtual_machine")
        url = self.base_url + "virtual_machines/set"
        print("url ", url)
        data = {}
        data["name"] = vm_name
        data["host"] = host
        data["port"] = port
        data["connection_info"] = connection_info
        data["is_ban"] = 0
        r = self.session.post(url, data=data)
        return r.json()

if __name__ == '__main__':
    base_url = "http://45.79.137.136/users/ws"
    login = "gtx1080"
    password = "cithJedUtit2"
    client = Client(base_url, login, password)
    #vm_json = client.get_virtual_machines()
    #print vm_json
    ret = client.set_virtual_machine(vm_name="gtx1080_813900bc",
                               host="45.79.137.136",
                               port=4000,
                               connection_info="Ready",
                              )
    print ret
