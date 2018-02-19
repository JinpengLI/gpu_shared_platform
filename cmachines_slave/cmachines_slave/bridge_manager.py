# -*- coding: utf-8 -*-
from cmachines_slave.utils import exe_cmd_on_local
from cmachines_slave.utils import exe_cmd_on_remote
from cmachines_slave.utils import get_default_settings
from cmachines_slave.persistent_object import PersistentObject
from datetime import datetime
import uuid
import os
import json

class BridgeManager(PersistentObject):

    def __init__(self,
                 mem_file, 
                 remote_port_manager,
                 local_port_manager,
                 machine_manager,
                 client,
                 remote_login,
                 remote_host,
                 bridge_password,
                 ):
        super(BridgeManager, self).__init__(mem_file)

        self.remote_port_manager = remote_port_manager
        self.local_port_manager = local_port_manager
        self.machine_manager = machine_manager
        self.client = client

        self.remote_login = remote_login
        self.remote_host = remote_host
        self.bridge_password = bridge_password

    def list_bridge_local_containers(self,):
        self.load()
        local_container_ids = []
        bridges = self.data.get("bridges", {})
        for key in bridges:
            bridge = bridges[key]
            local_container_id = bridge["local_container_id"]
            local_container_ids.append(local_container_id)
        return local_container_ids

    def list_bridge_remote_containers(self,):
        self.load()
        remote_container_ids = []
        bridges = self.data.get("bridges", {})
        for key in bridges:
            bridge = bridges[key]
            remote_container_id = bridge["remote_container_id"]
            remote_container_ids.append(remote_container_id)
        return remote_container_ids

    def add_machine(self, machine_id_on_site, local_ssh_port):
        self.load()
        if "machines" not in self.data:
            self.data["machines"] = {}
        self.data["machines"][machine_id_on_site] = {}
        self.data["machines"][machine_id_on_site]["local_ssh_port"] = local_ssh_port
        self.save()
        self.build_bridge(local_ssh_port)
        new_bridge = self.search_bridge(local_ssh_port)
        if new_bridge is not None:
            self.client.set_virtual_machine(
                vm_name=machine_id_on_site,
                host=self.remote_host,
                port=new_bridge["forwarding_port"],
                connection_info="Ready",
            )
        else:
            raise ValueError("cannot build bridge for " + str(local_ssh_port))

    def remove_machine(self, machine_id_on_site,):
        self.load()
        if "machines" not in self.data:
            return
        if machine_id_on_site not in self.data["machines"]:
            raise ValueError("cannod find the machine")
        local_service_port = self.data["machines"][machine_id_on_site]["local_ssh_port"]
        if machine_id_on_site in self.data["machines"]:
            self.data["machines"].pop(machine_id_on_site)
            self.save()
        self.remove_bridge(local_service_port)
        self.save()

    def clean_bridge(self, ):
        self.load()
        all_machine_ids_on_site = {}
        local_machines = self.machine_manager.get_all_meta_machines()
        for container_id in local_machines:
            machine_id_on_site = local_machines[container_id]["machine_id_on_site"]
            ssh_port = local_machines[container_id]["ssh_port"]
            all_machine_ids_on_site[machine_id_on_site] = ssh_port

        ports_to_rm = []
        bridge_machines = []
        machines_data = self.data.get("machines", {})
        for machine_id_on_site in machines_data:
            if machine_id_on_site in all_machine_ids_on_site:
                if all_machine_ids_on_site[machine_id_on_site] != machines_data[machine_id_on_site]["local_ssh_port"]:
                    ports_to_rm.append(machines_data[machine_id_on_site]["local_ssh_port"])
        if len(ports_to_rm) > 0:
            for service_port in ports_to_rm:
                print("remove bridge with service port ", service_port)
                self.remove_bridge(service_port)

    def update(self, ):
        self.clean_bridge()
        self.load()
        ## scan all the local machines
        all_machine_ids_on_site = {}
        local_machines = self.machine_manager.get_all_meta_machines()
        for container_id in local_machines:
            machine_id_on_site = local_machines[container_id]["machine_id_on_site"]
            ssh_port = local_machines[container_id]["ssh_port"]
            all_machine_ids_on_site[machine_id_on_site] = ssh_port

        bridge_machines = []
        machines_data = self.data.get("machines", {})
        for machine_id_on_site in machines_data:
            local_ssh_port = machines_data[machine_id_on_site]["local_ssh_port"]
            #print("machine_id_on_site=", machine_id_on_site)
            #print("local_ssh_port=", local_ssh_port)
            if self.check_bridge_if_exist(local_ssh_port):
                bridge_machines.append(machine_id_on_site)

        ## remove bridges
        machines_to_rm = list(set(bridge_machines) - set(all_machine_ids_on_site.keys()))
        if len(machines_to_rm) > 0:
            print("BridgeManager machines_to_rm:", machines_to_rm)
        ## add bridge machine
        machines_to_add = list(set(all_machine_ids_on_site.keys()) - set(bridge_machines))
        if len(machines_to_add) > 0:
            print("BridgeManager machines_to_add:", machines_to_add)

        for machine_to_rm in machines_to_rm:
            self.remove_machine(machine_to_rm)

        for machine_to_add in machines_to_add:
            self.add_machine(machine_to_add, all_machine_ids_on_site[machine_to_add])

    def search_bridge(self, local_service_port):
        self.load()
        #cmd_fmt_stop = "docker stop %(container_id)s"
        #cmd_fmt_rm = "docker rm %(container_id)s"
        bridges = self.data.get("bridges", {})
        keys_to_remove = []
        for bridge_key in bridges:
            if bridges[bridge_key]["local_service_port"] == local_service_port:
                return bridges[bridge_key]
        return None

    def remove_bridge(self, local_service_port):
        self.load()
        cmd_fmt_stop = "docker stop %(container_id)s"
        cmd_fmt_rm = "docker rm %(container_id)s"
        bridges = self.data.get("bridges", {})
        keys_to_remove = []
        for bridge_key in bridges:
            if bridges[bridge_key]["local_service_port"] == local_service_port:
                local_containder_id = bridges[bridge_key]["local_container_id"]
                remote_container_id = bridges[bridge_key]["remote_container_id"]
                forwarding_port = bridges[bridge_key]["forwarding_port"]
                your_sshd_port = bridges[bridge_key]["your_sshd_port"]

                cmd = cmd_fmt_stop % {"container_id": local_containder_id}
                ret, msg = exe_cmd_on_local(cmd, ret_msg=True)
                cmd = cmd_fmt_rm % {"container_id": local_containder_id}
                ret, msg = exe_cmd_on_local(cmd, ret_msg=True)

                cmd = cmd_fmt_stop % {"container_id": remote_container_id}
                ret, msg = exe_cmd_on_remote(self.remote_login, self.remote_host, cmd, ret_msg=True)
                cmd = cmd_fmt_rm % {"container_id": remote_container_id}
                ret, msg = exe_cmd_on_remote(self.remote_login, self.remote_host, cmd, ret_msg=True)

                self.remote_port_manager.release_port(forwarding_port)
                self.remote_port_manager.release_port(your_sshd_port)

                keys_to_remove.append(bridge_key)
        for key_to_remove in keys_to_remove:
            bridges.pop(key_to_remove)
        self.data["bridges"] = bridges
        self.save()

    def check_bridge_if_exist(self, local_service_port):
        bridges = self.data.get("bridges", {})
        #print("bridges=", bridges)
        #print("local_service_port=", local_service_port)
        for key in bridges:
            bridge = bridges[key]
            if bridge["local_service_port"] == local_service_port:
                return True
        return False

    def start_bridge_if_exist(self, local_service_port):
        self.load()
        bridges = self.data.get("bridges", {})
        for key in bridges:
            bridge = bridges[key]
            if bridge["local_service_port"] == local_service_port:
                local_container_id = bridge["local_container_id"]
                remote_container_id = bridge["remote_container_id"]
                cmd_remote = "docker start %s" % remote_container_id
                ret, msg = exe_cmd_on_remote(self.remote_login,
                                             self.remote_host,
                                             cmd_remote,
                                             ret_msg=True)
                if ret != 0:
                    print("fail to execute ", cmd_remote)
                cmd_local = "docker start %s" % local_container_id
                ret, msg = exe_cmd_on_local(cmd_local, ret_msg=True)
                if ret != 0:
                    print("fail to execute ", cmd_local)
                return True
        return False

    def build_bridge(self, local_service_port):
        '''
            see https://github.com/JinpengLI/docker-image-reverse-ssh-tunnel
            return remote port
        '''
        if self.start_bridge_if_exist(local_service_port):
            #print("debug build_bridge already exist")
            return
        self.load()
        forwarding_port = self.remote_port_manager.allocate_port() ## open service so it is called forwarding port
        your_sshd_port = self.remote_port_manager.allocate_port() ## ssh server listening
        data = {}
        data["remote_login"] = self.remote_login
        data["remote_host"] = self.remote_host
        data["your_sshd_port"] = your_sshd_port
        data["forwarding_port"] = forwarding_port
        data["bridge_password"] = self.bridge_password
        data["local_service_port"] = local_service_port

        cmd = "docker run -d -e ROOT_PASS=%(bridge_password)s -p %(your_sshd_port)d:22 -p %(forwarding_port)d:1080 jinpengli/docker-image-reverse-ssh-tunnel"
        cmd = cmd % data
        ret, msg = exe_cmd_on_remote(self.remote_login, self.remote_host, cmd, ret_msg=True)
        if ret != 0:
            print("fail cmd:", cmd)
            return None
        remote_container_id = msg.strip()
        cmd = "docker run -d -e PUBLIC_HOST_ADDR=%(remote_host)s -e PUBLIC_HOST_PORT=%(your_sshd_port)d -e ROOT_PASS=%(bridge_password)s -e PROXY_PORT=%(local_service_port)d --net=host jinpengli/docker-image-reverse-ssh-tunnel"
        cmd = cmd % data
        ret, msg = exe_cmd_on_local(cmd, ret_msg=True)
        if ret != 0:
            print("fail cmd:", cmd)
            return None
        local_container_id = msg.strip()
        bridges = self.data.get("bridges", {})
        bridge_key = (str(local_container_id) + '_' + str(remote_container_id))
        bridges[bridge_key] = {}
        bridges[bridge_key]["created_time"] = datetime.now().isoformat()
        bridges[bridge_key]["your_sshd_port"] = your_sshd_port
        bridges[bridge_key]["forwarding_port"] = forwarding_port
        bridges[bridge_key]["local_service_port"] = local_service_port
        bridges[bridge_key]["local_container_id"] = local_container_id
        bridges[bridge_key]["remote_container_id"] = remote_container_id
        self.data["bridges"] = bridges
        self.save()


if __name__ == "__main__":
    from cmachines_slave.port_manager import PortManager
    settings = get_default_settings()
    working_dir = settings["local_data_dir"]
    local_available_ports = settings["local_available_ports"]
    local_available_ports = range(local_available_ports[0], local_available_ports[1], 1)
    machine_manager_mem_file = os.path.join(working_dir, "machine_manager.json")
    local_machine_port_mem_file = os.path.join(working_dir, "local_machine_ports.json")
    port_manager = PortManager(
        local_available_ports,
        local_machine_port_mem_file)
    bridge_manager = BridgeManager()
    
