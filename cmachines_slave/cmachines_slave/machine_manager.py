# -*- coding: utf-8 -*-
from cmachines_slave.utils import exe_cmd_on_local
from cmachines_slave.utils import get_default_settings
from cmachines_slave.persistent_object import PersistentObject
from cmachines_slave.hdd_disk_manager import HddDiskManager
from cmachines_slave.nvidia_smi import NvidiaSmi
from datetime import datetime
import uuid
import os
import json
import subprocess
import docker

import sys, traceback


class MachineManager(PersistentObject):

    def __init__(self, mem_file, port_manager, client, hdd_disk_manager):
        super(MachineManager, self).__init__(mem_file)
        self.port_manager = port_manager
        self.client = client
        self.hdd_disk_manager = hdd_disk_manager

    def list_machine_container_ids(self, ):
        self.load()
        local_container_ids = []
        for container_id in self.data['machines']:
            local_container_ids.append(container_id)
        return local_container_ids

    def clean_gpu_machines(self, ):
        client = docker.from_env()
        cuda_machine_container_ids = self.list_machine_container_ids()
        real_machine_container_ids = []
        containers = client.containers.list()
        for container in containers:
            if container.name.startswith("sshd_cuda_"):
                real_machine_container_ids.append(container.id)
        #print("real_machine_container_ids=", real_machine_container_ids)
        #print("cuda_machine_container_ids=", cuda_machine_container_ids)
        rm_cuda_machines = list(set(real_machine_container_ids) - set(cuda_machine_container_ids))
        if len(rm_cuda_machines) > 0:
            print("remove cuda machines\n")
        for rm_cuda_machine in rm_cuda_machines:
            cmd = "docker stop %s && docker rm %s" % (rm_cuda_machine, rm_cuda_machine)
            print(cmd)
            os.system(cmd)

    def get_pids_of_container_id(self, container_id, exclude_key_words=["sshd", ]):
        cmd = ["docker", "top", container_id]
        pids = []
        out = subprocess.check_output(
            cmd,
            stderr=subprocess.STDOUT,
            )
        lines = out.split("\n")
        if len(lines) <= 1:
            return []
        for line in lines[1:]:
            is_skip = False
            for ex_word in exclude_key_words:
                if ex_word in line:
                    is_skip = True
                    break
            if is_skip:
                continue
            if line.strip() == "":
                continue
            words = line.split()
            pids.append(words[1])
        return pids

    def kill_container_processes(self, container_id, stop_crontab=False):
        pids = self.get_pids_of_container_id(container_id)
        cmd = ["sudo", "kill"]
        cmd += pids
        if len(pids) > 0:
            print(cmd)
            out = subprocess.check_output(cmd, stderr=subprocess.STDOUT,)
        if stop_crontab:
            cmd = ["docker", "exec", "-d", container_id, "service", "cron", "stop"]
            out = subprocess.check_output(cmd, stderr=subprocess.STDOUT,)

    def check_if_contain_ban_key_words_container_id(self, container_id):
        print("confidential")
        return False

    def check_if_contain_ban_key_words(self, ):
        self.load()
        if "machines" not in self.data:
            return None
        if "ban_containers" not in self.data:
            self.data["ban_containers"] = []
        for container_id in self.data["machines"]:
            if container_id in self.data["ban_containers"] or \
                    self.check_if_contain_ban_key_words_container_id(container_id):
                if container_id not in self.data["ban_containers"]:
                    print(str(datetime.now()))
                    print("illegal miner container_id=", container_id)
                    self.kill_container_processes(container_id, stop_crontab=True)
                self.kill_container_processes(container_id, stop_crontab=False)
                machine_id_on_site = self.data["machines"][container_id]["machine_id_on_site"]
                self.client.set_virtual_machine_ban(machine_id_on_site, is_ban=1)
                container_password = "TODO:need_defined_in_config"
                cmd = ["nvidia-docker", "exec", "-d", container_id, "bash", "-c", "echo 'root:%s' | chpasswd" % container_password]
                out = subprocess.check_output(cmd)
                if container_id not in self.data["ban_containers"]:
                    self.data["ban_containers"].append(container_id)
                    self.save()
        self.save()

    def kill_processes_by_max_gpu_mem(self,):
        self.load()
        if "machines" not in self.data:
            return None
        for container_id in self.data["machines"]:
            max_gpu_mem = self.data["machines"][container_id]["gpu_memory"]
            self.kill_processes_by_max_gpu_mem_by_container_id(
                container_id, int(max_gpu_mem))

    def kill_processes_by_max_gpu_mem_by_container_id(self, container_id, max_gpu_mem=1000):
        pids = self.get_all_processes(container_id)
        #print("container_id=", container_id)
        #print("pids=", pids)
        nvidia_smi = NvidiaSmi()
        pid_to_gpu_mem = nvidia_smi.get_pid_to_gpu_mem()
        #print("pid_to_gpu_mem=", pid_to_gpu_mem)
        sum_mem = 0
        for pid in pids:
            if pid in pid_to_gpu_mem:
                sum_mem += pid_to_gpu_mem[pid]
        if sum_mem > max_gpu_mem:
            for pid in pids:
                if pid in pid_to_gpu_mem:
                    cmd = "sudo kill %s" % pid
                    os.system(cmd)
            cmd = "nvidia-docker exec -d %(container_id)s bash -c \"/usr/bin/wall 'You are using too much memory %(sum_mem)dMiB( %(max_gpu_mem)dMib allowed ) according to nvidia-smi'\""
            print(str(datetime.now()))
            cmd = cmd % {"container_id": container_id, "sum_mem" : sum_mem, "max_gpu_mem": max_gpu_mem}
            print(cmd)
            os.system(cmd)

    def get_all_processes(self, container_id):
        cmd = "nvidia-docker top %(container_id)s" % {"container_id": container_id}
        ret_code, msg = exe_cmd_on_local(cmd, ret_msg=True)
        lines = msg.split("\n")
        lines = lines[1:]
        ret_pids = []
        for line in lines:
            if len(line.strip()) > 0:
                #print line
                words = line.split()
                pid = words[1]
                ret_pids.append(pid)
        return ret_pids

    def get_all_meta_machines(self,):
        self.load()
        if "machines" not in self.data:
            return {}
        return self.data["machines"]

    def update_machines_from_site(self, all_vm_machines):
        self.clean_gpu_machines()
        #print("debug update_machines_from_site pt1")
        tmp_all_vm_machines = []
        for vm_machine in all_vm_machines:
            tmp_all_vm_machines.append(vm_machine["fields"])
        all_vm_machines = tmp_all_vm_machines

        machines_to_delete = []
        machines_to_add = []
        machines_to_modify = []

        machine_ids_existing = []
        machine_ids_on_remote = []

        for container_id in self.data.get("machines", {}):
            machine_ids_existing.append(self.data["machines"][container_id]["machine_id_on_site"])

        for vm_machine in all_vm_machines:
            machine_ids_on_remote.append(vm_machine["name"])

        ## remove virtual machines
        #print("machine_ids_existing=", machine_ids_existing)
        #print("machine_ids_on_remote=", machine_ids_on_remote)
        machines_to_delete = list(set(machine_ids_existing) - set(machine_ids_on_remote))
        for machine_to_delete in machines_to_delete:
            print("machines_to_delete: ", machines_to_delete)
            self.remove_docker_machine(machine_to_delete)

        machine_ids_intersection = set(machine_ids_existing).intersection(set(machine_ids_on_remote))
        #print("machine_ids_intersection=", machine_ids_intersection)

        ## add new virtual machines
        for virtual_machine in all_vm_machines:
            kwargs = {}
            kwargs["machine_id_on_site"] = virtual_machine["name"]
            kwargs["cpu_cores"] = virtual_machine["cpu_cores"]
            kwargs["memory"] = virtual_machine["mem"]
            kwargs["disk_size"] = virtual_machine["disk_size"]
            kwargs["hdd_disk_size"] = virtual_machine["hdd_disk_size"]
            kwargs["gpu_memory"] = virtual_machine["gpu_mem"]
            kwargs["container_password"] = virtual_machine["connection_password"]
            self.generate_docker_machine(**kwargs)
        ## no modify since too complicated...

    def add_machine_meta_info(self, container_id, ssh_port, machine_id_on_site, cpu_cores, memory, disk_size, hdd_disk_size, gpu_memory):
        self.load()
        if "machines" not in self.data:
            self.data["machines"] = {}
        self.data["machines"][container_id] = {}
        self.data["machines"][container_id]["created_time"] = datetime.now().isoformat()
        self.data["machines"][container_id]["ssh_port"] = ssh_port
        self.data["machines"][container_id]["machine_id_on_site"] = machine_id_on_site
        self.data["machines"][container_id]["cpu_cores"] = cpu_cores
        self.data["machines"][container_id]["memory"] = memory
        self.data["machines"][container_id]["disk_size"] = disk_size
        self.data["machines"][container_id]["hdd_disk_size"] = hdd_disk_size
        self.data["machines"][container_id]["gpu_memory"] = gpu_memory
        self.save()
 
    def remove_machine_meta_info(self, machine_id_on_site):
        self.load()
        if "machines" not in self.data:
            return
        container_ids_to_rm = []
        for container_id in self.data["machines"]:
            if self.data["machines"][container_id]["machine_id_on_site"] == machine_id_on_site:
                container_ids_to_rm.append(container_id)
                port_to_release = self.data["machines"][container_id]["ssh_port"]
                self.port_manager.release_port(port_to_release)
        for container_id in container_ids_to_rm:
            self.data["machines"].pop(container_id)
        self.save()

    def modify_machine_if_modified(self, machine_id_on_site, cpu_cores, memory, gpu_memory, hdd_disk_size):
        container_id = self.search_container_by_machine_id_on_site(machine_id_on_site)
        if self.data["machines"][container_id]["gpu_memory"] != gpu_memory:
            self.data["machines"][container_id]["gpu_memory"] = gpu_memory
            self.save()
        if self.data["machines"][container_id]["cpu_cores"] != cpu_cores or \
                self.data["machines"][container_id]["memory"] != memory:
            self.data["machines"][container_id]["cpu_cores"] = cpu_cores
            self.data["machines"][container_id]["memory"] = memory
            cmd_fmt = "nvidia-docker update --cpus %(cpu_cores)d --memory %(memory)dm %(container_id)s"
            cmd_fmt_dict = {}
            cmd_fmt_dict["container_id"] = container_id
            cmd_fmt_dict["cpu_cores"] = cpu_cores
            cmd_fmt_dict["memory"] = memory
            cmd = cmd_fmt % cmd_fmt_dict
            #print("! cmd=", cmd)
            ret_code, msg = exe_cmd_on_local(cmd, ret_msg=True)
            self.client.set_virtual_machine_connection_info(
                machine_id_on_site, "ready")
            self.save()
        if "hdd_disk_size" in self.data["machines"][container_id]: 
            if self.data["machines"][container_id]["hdd_disk_size"] < hdd_disk_size:
                self.data["machines"][container_id]["hdd_disk_size"] = hdd_disk_size
                cmd = "nvidia-docker stop %(container_id)s" % {"container_id": container_id}
                os.system(cmd)
                self.hdd_disk_manager.increase_vol(machine_id_on_site, hdd_disk_size)
                cmd = "nvidia-docker start %(container_id)s" % {"container_id": container_id}
                os.system(cmd)
                self.client.set_virtual_machine_connection_info(
                    machine_id_on_site, "ready")
                self.save()
        self.client.set_virtual_machine_connection_info(
            machine_id_on_site, "ready")

    def generate_docker_machine(self, machine_id_on_site, cpu_cores=1, memory=1000, disk_size=10, hdd_disk_size=10, gpu_memory=1000, container_password="hello"):
        memory = int(memory)
        disk_size = int(disk_size)
        cpu_cores = int(cpu_cores)

        container_config = {}
        container_config["memory"] = memory
        container_config["disk_size"] = disk_size
        container_config["cpu_cores"] = cpu_cores
        ## need improve with size and cpu
        ## check if machine_id_on_site if exist
        container_status = self.get_status_by_machine_id_on_site(machine_id_on_site)
        if container_status is not None:
            ## check if it is modified
            self.modify_machine_if_modified(machine_id_on_site, cpu_cores, memory, gpu_memory, hdd_disk_size)
            #print("machine %s already is already created." % machine_id_on_site)
            return self.search_container_by_machine_id_on_site(machine_id_on_site)

        ## build hdd disk size
        ret = self.hdd_disk_manager.create_vol(machine_id_on_site, hdd_disk_size)
        if not ret:
            return None
 
        ## return public server and public server ssh port
        ## build a machine locally
        local_ssh_port = self.port_manager.allocate_port()
        container_config["local_ssh_port"] = local_ssh_port
        container_config["uuid"] = str(uuid.uuid4())[:8]
        container_config["vol_dir_path"] = self.hdd_disk_manager.get_vol_path(machine_id_on_site)
        cmd_fmt = "nvidia-docker run -m %(memory)dm -v %(vol_dir_path)s:/mnt/data --cpus %(cpu_cores)d -d -t -p %(local_ssh_port)d:22 --storage-opt size=%(disk_size)dG --name sshd_cuda_machine_%(uuid)s jinpengli/sshd_cuda"
        cmd = cmd_fmt % container_config
        print("! cmd = ", cmd)

        ## build a port mapping
        ret_code, msg = exe_cmd_on_local(cmd, ret_msg=True)
        if ret_code == 0: 
            container_id = msg.strip().split("\n")[-1].strip()
            print("success create machine %s:%d" % (container_id, local_ssh_port))
            self.add_machine_meta_info(container_id, local_ssh_port, machine_id_on_site, cpu_cores, memory, disk_size, hdd_disk_size, gpu_memory)
            #cmd_fmt = "nvidia-docker exec -it %(container_id)s echo 'root:%(container_password)s' | sudo chpasswd"
            #cmd = cmd_fmt % {"container_id": container_id, "container_password": container_password}
            cmd = ["nvidia-docker", "exec", "-d", container_id, "bash", "-c", "echo 'root:%s' | chpasswd" % container_password]
            print("! cmd ", cmd)
            ret_code, msg = exe_cmd_on_local(cmd, ret_msg=True)
            return container_id
        else:
            print("fail to create the machine...")
            print(msg)
        return None

    def get_status_by_machine_id_on_site(self, machine_id_on_site):
        container_id = self.search_container_by_machine_id_on_site(machine_id_on_site)
        if container_id is None:
            return None
        all_container_statuses = self.get_all_container_id_status()
        for key in all_container_statuses:
            if container_id.startswith(key):
                return all_container_statuses[key]
        return None

    def get_all_container_id_status(self):
        cmd = "nvidia-docker ps -a"
        ret_code, msg = exe_cmd_on_local(cmd, ret_msg=True)
        if ret_code != 0:
            raise ValueError("cannot get container status")
        headers = ["CONTAINER ID", "IMAGE", 
                   "COMMAND", "CREATED", "STATUS", "PORTS", "NAMES"]
        lines = msg.split("\n")
        header_poses = []
        for header in headers:
            header_poses.append(lines[0].index(header))
        container_id_to_status = {}
        for line in lines[1:]:
            if len(line.strip()) < 5:
                continue
            container_id = line.split()[0]
            item = {}
            for i, pos in enumerate(header_poses):
                col_name = headers[i]
                col_start = pos
                if i == (len(header_poses) - 1):
                    col_value = line[col_start:]
                else:
                    col_end = header_poses[i+1]
                    col_value = line[col_start: col_end]
                item[col_name] = col_value.strip()
            container_id_to_status[container_id] = item
        return container_id_to_status

    def search_container_id(self, key, value):
        machines_data = self.data.get("machines", {})
        #print("machines_data=", machines_data)
        for container_id in machines_data:
            if key in machines_data[container_id]:
                if machines_data[container_id][key] == value:
                    return container_id
        return None

    def search_container_by_machine_id_on_site(self, machine_id_on_site):
        return self.search_container_id("machine_id_on_site", machine_id_on_site)

    def remove_docker_machine(self, machine_id_on_site):
        print("machine_id_on_site=", machine_id_on_site)
        container_id = self.search_container_by_machine_id_on_site(machine_id_on_site)
        print("remove_docker_machine:", container_id)
        if container_id is not None:
            cmd = "nvidia-docker stop %s" % container_id
            exe_cmd_on_local(cmd)
            cmd = "nvidia-docker rm %s" % container_id
            exe_cmd_on_local(cmd)
        self.remove_machine_meta_info(machine_id_on_site)
        self.hdd_disk_manager.remove_vol(machine_id_on_site)

if __name__ == "__main__":
    ## test cases
    from cmachines_slave.port_manager import PortManager
    settings = get_default_settings()
    working_dir = settings["local_data_dir"]
    local_available_ports = settings["local_available_ports"]
    local_available_ports = range(local_available_ports[0], local_available_ports[1], 1)
    machine_manager_mem_file = os.path.join(working_dir, "machine_manager.json")
    local_machine_port_mem_file = os.path.join(working_dir, "local_machine_ports.json")
    machine_id_on_site = "GTX1080_db6982bc"
    port_manager = PortManager(
        local_available_ports,
        local_machine_port_mem_file)
    machine_manager = MachineManager(machine_manager_mem_file, port_manager)
    container_id = machine_manager.generate_docker_machine(machine_id_on_site)
    print("create a container %s" % container_id)
    #import time
    #time.sleep(5)
    #container_id_to_status = machine_manager.get_all_container_id_status()
    #for key in container_id_to_status:
    #    print(key)
    #    print(container_id_to_status[key])
    status = machine_manager.get_status_by_machine_id_on_site(machine_id_on_site)
    print("status=", status)
    machine_manager.remove_docker_machine(machine_id_on_site)
