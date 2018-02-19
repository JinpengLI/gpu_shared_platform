# -*- coding: utf-8 -*-

import requests
import json
import subprocess

class NvidiaSmi(object):

    def __init__(self, ):
        pass

    def get_pid_to_gpu_mem(self, ):
        cmd = "nvidia-smi"
        out = subprocess.check_output(
            cmd,
            stderr=subprocess.STDOUT,
            shell=True)
        lines = \
        [
        "+-----------------------------------------------------------------------------+",
        "| Processes:                                                       GPU Memory |",
        "|  GPU       PID  Type  Process name                               Usage      |",
        "|=============================================================================|",
        "|    0     14630    C   /usr/bin/python                               7833MiB |",
        "+-----------------------------------------------------------------------------+",
        ]
        lines = out.split("\n")
        ret = {}
        pass_line_processes = False
        pass_line_double_dash = False
        for i, line in enumerate(lines):
            if "Processes:" in line:
                pass_line_processes = True
                continue
            if pass_line_processes:
                if "==============================================" in line:
                    pass_line_double_dash = True
                    continue
            if pass_line_processes and pass_line_double_dash:
                if ("+-------------------------------" not in line) and ("No running processes found" not in line):
                    words = line.split()
                    pid = words[2]
                    mem = words[5].replace("MiB", "")
                    ret[pid] = float(mem)
                    continue
                else:
                    break
        return ret

if __name__ == "__main__":
    nvidia_smi = NvidiaSmi()
    print nvidia_smi.get_pid_to_gpu_mem()
