# -*- coding: utf-8 -*-

# @TODO: Realise storage type behaviour
class Settings():
    def __init__(self, storage, cid, storage_type="dict"):
        self.cid = cid
        self.storage = storage
        self.storage_type = storage_type

    def get(self, key):
        return self.storage[self.cid].get(key, None)

    def set(self, key, value):
        self.storage[self.cid][key] = value
