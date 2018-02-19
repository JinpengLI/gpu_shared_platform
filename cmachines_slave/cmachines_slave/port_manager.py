# -*- coding: utf-8 -*-
from cmachines_slave.utils import exe_cmd_on_local 
from cmachines_slave.utils import get_default_settings 
from cmachines_slave.persistent_object import PersistentObject 
from datetime import datetime 
import uuid 
import os 
import json 
import numpy as np

class PortManager(PersistentObject):

    def __init__(self, allow_ports, mem_file): 
        super(PortManager, self).__init__(mem_file)
        self.allow_ports = allow_ports
        self.avoid_ports = [40020, ]

    def allocate_port(self,):
        self.load()
        used_ports = self.data.get("used_ports", [])
        allocated_port = None
        len_allow_ports = len(self.allow_ports)
        for port_i in np.random.permutation(range(len_allow_ports)):
            port = self.allow_ports[port_i]
            if port not in used_ports and port not in self.avoid_ports:
                allocated_port = port
                break
        if allocated_port is not None:
            used_ports.append(allocated_port)
            self.data["used_ports"] = used_ports
            self.save()
        return allocated_port

    def release_port(self, port):
        self.load()
        used_ports = self.data.get("used_ports", [])
        if port in used_ports:
            port_index = used_ports.index(port)
        else:
            port_index = -1
        #if port_index == -1:
        #    raise ValueError("%d is not used." % port)
        if port_index != -1:
            del used_ports[port_index]
        self.data["used_ports"] = used_ports
        self.save()
