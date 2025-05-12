#!/usr/bin/env python
import os
import redis

r_server = redis.Redis()

f = open('./ids.txt')
data = f.read()
f.close()

lines = data.split("\n")
for line in lines:
    if line:
      r_server.rpush('sites', line)

