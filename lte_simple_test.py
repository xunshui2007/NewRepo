#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CMW500 简化版测试 - 只用GPRF
"""

import socket
import time
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CMW_IP = "192.168.121.116"
CMW_PORT = 5025

def cmd(s, c, wait=0.3):
    s.sendall(f"{c}\n".encode())
    time.sleep(wait)
    s.settimeout(3)
    try:
        return s.recv(4096).decode().strip()
    except:
        return ""

s = socket.socket()
s.settimeout(10)
s.connect((CMW_IP, CMW_PORT))

logger.info(f"CMW500: {cmd(s, '*IDN?')}")

results = {"time": datetime.now().isoformat()}

# 功率
logger.info("\n功率测试...")
cmd(s, "CONFigure:GPRf:MEAS:POW:AVG:SCOunt 10")
cmd(s, "INIT:GPRf:MEAS:POW")
time.sleep(1)
r = cmd(s, "FETCh:GPRf:MEAS:POW:AVER?")
logger.info(f"GPRF功率: {r}")

try:
    p = r.split(',')
    if int(p[0]) == 0:
        results["power_dbm"] = float(p[1])
        logger.info(f"功率: {results['power_dbm']:.2f} dBm")
except:
    results["power_dbm"] = -999
    logger.info("功率测量失败")

# ACLR
logger.info("\nACLR测试...")
cmd(s, "INIT:GPRf:MEAS:ACLR")
time.sleep(2)
r = cmd(s, "FETCh:GPRf:MEAS:ACLR?")
logger.info(f"ACLR: {r}")

try:
    v = [float(x) for x in r.split(',') if x.replace('.','').replace('-','').isdigit()]
    if len(v) >= 3:
        results["aclr_lower"] = v[1]
        results["aclr_upper"] = v[2]
        logger.info(f"ACLR: 下邻 {v[1]:.2f} dBc, 上邻 {v[2]:.2f} dBc")
except:
    results["aclr_lower"] = 0
    results["aclr_upper"] = 0

# BLER
logger.info("\nBLER测试...")
cmd(s, "INIT:GPRf:MEAS:BLER")
time.sleep(2)
r = cmd(s, "FETCh:GPRf:MEAS:BLER:STAT?")
logger.info(f"BLER: {r}")

try:
    b = r.split(',')
    results["bler"] = float(b[1])
    logger.info(f"BLER: {results['bler']:.2f}%")
except:
    results["bler"] = 100

s.close()

# 保存
fname = f"lte_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(fname, 'w') as f:
    json.dump(results, f, indent=2)

logger.info(f"\n结果: {fname}")
logger.info(f"\n=== 结果 ===")
logger.info(f"功率: {results.get('power_dbm', -999):.2f} dBm")
logger.info(f"ACLR: {results.get('aclr_lower', 0):.2f} / {results.get('aclr_upper', 0):.2f} dBc")
logger.info(f"BLER: {results.get('bler', 100):.2f}%")
