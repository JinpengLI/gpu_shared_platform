# -*- coding: utf-8 -*-

import requests
import json
import os
from cmachines_slave.utils import exe_cmd_on_local

class HddDiskManager(object):

    def __init__(self, base_dir):
        self.base_dir = base_dir

    def get_vol_path(self, vol_name):
        vol_dir_path  = os.path.join(self.base_dir, vol_name)
        return vol_dir_path

    def create_vol(self, vol_name, size):
        vol_dir_path  = os.path.join(self.base_dir, vol_name)
        image_path = os.path.join(self.base_dir, vol_name + ".img")
        data = {
            "image_path": image_path,
            "size": size*1024,
            "vol_dir_path": vol_dir_path,
        }
        cmd = "sudo dd if=/dev/zero of=%(image_path)s bs=1M count=100"
        cmd = cmd % data
        ret_code, msg = exe_cmd_on_local(cmd, ret_msg=True)
        if ret_code != 0:
            print("fail ", cmd)
            return ret_code, msg

        cmd = "sudo mkfs.ext4 %(image_path)s" % data
        cmd = cmd % data
        ret_code, msg = exe_cmd_on_local(cmd, ret_msg=True)
        if ret_code != 0:
            print("fail ", cmd)
            return ret_code, msg

        cmd = "sudo e2fsck -y -f %(image_path)s"
        cmd = cmd % data
        ret_code, msg = exe_cmd_on_local(cmd, ret_msg=True)
        if ret_code != 0:
            print("fail ", cmd)
            return ret_code, msg

        cmd = "sudo resize2fs %(image_path)s %(size)dM"
        cmd = cmd % data
        ret_code, msg = exe_cmd_on_local(cmd, ret_msg=True)
        if ret_code != 0:
            print("fail ", cmd)
            return ret_code, msg

        cmd = "sudo mkdir %(vol_dir_path)s" % data
        ret_code, msg = exe_cmd_on_local(cmd, ret_msg=True)
        if ret_code != 0:
            print("fail ", cmd)
            return ret_code, msg

        cmd = "sudo mount -o loop %(image_path)s %(vol_dir_path)s" % data
        ret_code, msg = exe_cmd_on_local(cmd, ret_msg=True)
        if ret_code != 0:
            print("fail ", cmd)
            return ret_code, msg

        cmd = "echo '%(image_path)s %(vol_dir_path)s  ext4   loop    0    2' | sudo tee -a /etc/fstab" % data
        os.system(cmd)

        cmd = "sudo chmod -R o-r %(vol_dir_path)s" % data
        ret_code, msg = exe_cmd_on_local(cmd, ret_msg=True)
        if ret_code != 0:
            print("fail ", cmd)
            return ret_code, msg

        cmd = "sudo chmod -R o-r %(image_path)s" % data
        ret_code, msg = exe_cmd_on_local(cmd, ret_msg=True)
        if ret_code != 0:
            print("fail ", cmd)
            return ret_code, msg

        return True

    def remove_vol(self, vol_name):
        vol_dir_path  = os.path.join(self.base_dir, vol_name)
        image_path = os.path.join(self.base_dir, vol_name + ".img")
        data = {
            "image_path": image_path,
            "vol_name": vol_name,
            "vol_dir_path": vol_dir_path,
        }
        cmds = [
           "sudo umount -l %(vol_dir_path)s",
           "sudo rm -rf %(vol_dir_path)s",
           "sudo rm %(image_path)s",
           "sudo sed -i '/%(vol_name)s/d' /etc/fstab",
        ]
        for cmd in cmds:
            os.system(cmd % data)
        return True

    def increase_vol(self, vol_name, size):
        vol_dir_path  = os.path.join(self.base_dir, vol_name)
        image_path = os.path.join(self.base_dir, vol_name + ".img")
        data = {
            "image_path": image_path,
            "size": size*1024,
            "vol_dir_path": vol_dir_path,
        }
        cmds = [
            "sudo umount -l %(vol_dir_path)s",
            "sudo e2fsck -y -f %(image_path)s",
            "sudo resize2fs %(image_path)s %(size)dM",
            "sudo mount -o loop %(image_path)s %(vol_dir_path)s",
        ]
        for cmd in cmds:
            os.system(cmd % data)
        return True 
if __name__ == "__main__":
    hdd_disk_manager = HddDiskManager("/hdd/containers")
    vol_name = "gtx1080_a7c2e804"
    #hdd_disk_manager.create_vol(vol_name, 2)
    #hdd_disk_manager.increase_vol(vol_name, 4) 
    hdd_disk_manager.remove_vol(vol_name)
