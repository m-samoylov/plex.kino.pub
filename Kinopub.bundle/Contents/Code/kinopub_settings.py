# -*- coding: utf-8 -*-

# @TODO: Realise storage type behaviour
class Settings():
    def __init__(self, storage, storage_type="dict"):
        self.storage = storage
        self.storage_type = storage_type

    def get(self, key):
        return self.storage[key]

    def set(self, key, value):
        self.storage[key] = value
