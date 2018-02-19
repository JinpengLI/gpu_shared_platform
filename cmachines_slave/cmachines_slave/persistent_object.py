# -*- coding: utf-8 -*-
from datetime import datetime
import uuid
import os
import json

class PersistentObject(object):
    def __init__(self, mem_file):
        self.mem_file = mem_file
        self.data = {}
        self.load()

    def load(self,):
        if os.path.isfile(self.mem_file):
            self.data = json.load(open(self.mem_file, 'r'))

    def save(self, ):
        json.dump(self.data, open(self.mem_file, 'w+'), indent=4)




