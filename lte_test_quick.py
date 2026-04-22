#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CMW500 LTE 自动化测试系统 - 优化版
支持功率和ACLR测试
测试标准: 3GPP
"""

import socket
import time
import json
import csv
import logging
import sys
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class BandType:
    BANDS = {
        "3": (1805, 1880), "7": (2620, 2690), "20": (791, 821),
        "1": (2110, 2170), "5": (869, 894), "8": (925, 960)
    }
    
    @staticmethod
    def get_freq(band: str) -> float:
        dl, _ = BandType.BANDS.get(band, (0, 0))
        return dl


@dataclass
class TestConfig:
    cmw_ip: str = "192.168.121.116"
    cmw_port: int = 5025
    band: str = "3"
    bandwidth_mhz: int = 20
    dl_channel: int = 1850
    target_power_dbm: int = 23
    aclr_limit_db: float = -45.0


class CMW500:
    def __init__(self, ip: str, port: int = 5025):
        self.ip = ip
        self.port = port
        self.socket = None
        self.connected = False
        
    def connect(self) -> bool:
        try:
            logger.info(f"连接CMW500: {self.ip}")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.ip, self.port))
            
            self.socket.sendall(b"*IDN?\n")
            resp = self._recv()
            logger.info(f"CMW500: {resp.strip()}")
            self.connected = True
            return True
        except Exception as e:
            logger.error(f"连接失败: {e}")
            return False
    
    def _recv(self, timeout: int = 3) -> str:
        self.socket.settimeout(timeout)
        try:
            data = b""
            while True:
                chunk = self.socket.recv(4096)
                if not chunk:
                    break
                data += chunk
                if data.endswith(b'\n'):
                    break
            return data.decode('utf-8').strip()
        except:
            return ""
    
    def send_cmd(self, cmd: str, wait: float = 0.2) -> str:
        if not self.connected:
            return ""
        try:
            self.socket.sendall(f"{cmd}\n".encode('utf-8'))
            time.sleep(wait)
            return self._recv()
        except:
            return ""
    
    def measure_power_gprf(self) -> float:
        """使用GPRF测量功率"""
        self.send_cmd("CONFigure:GPRf:MEAS:POW:AVG:SCOunt 10")
        self.send_cmd("INIT:GPRf:MEAS:POW")
        time.sleep(1)
        
        result = self.send_cmd("FETCh:GPRf:MEAS:POW:AVER?")
        
        try:
            if ',' in result:
                parts = result.split(',')
                if int(parts[0]) == 0:
                    return float(parts[1])
        except:
            pass
        return -999.0
    
    def measure_aclr_gprf(self) -> tuple:
        """使用GPRF测量ACLR"""
        self.send_cmd("INIT:GPRf:MEAS:ACLR")
        time.sleep(2)
        
        result = self.send_cmd("FETCh:GPRf:MEAS:ACLR?", wait=1)
        
        try:
            # 格式: status,power,adj1,adj2,...
            values = [float(x) for x in result.split(',') if x.replace('.','').replace('-','').isdigit()]
            if len(values) >= 3:
                return values[1], values[2]  # lower, upper
        except:
            pass
        return 0.0, 0.0
    
    def disconnect(self):
        if self.socket:
            self.socket.close()


def run_test(bands: List[str] = None):
    """运行测试"""
    if bands is None:
        bands = ["3", "7", "20"]
    
    config = TestConfig()
    cmw = CMW500(config.cmw_ip, config.cmw_port)
    
    if not cmw.connect():
        return
    
    results = {
        "config": asdict(config),
        "mode": "GPRF",
        "power_results": [],
        "aclr_results": [],
        "test_time": datetime.now().isoformat()
    }
    
    logger.info("使用GPRF模式测试")
    
    for band in bands:
        logger.info(f"\n=== Band {band} ===")
        
        freq = BandType.get_freq(band)
        
        # 功率测试
        power = cmw.measure_power_gprf()
        logger.info(f"功率: {power:.2f} dBm")
        
        results["power_results"].append({
            "band": band,
            "frequency_mhz": freq,
            "power_dbm": round(power, 2),
            "limit_dbm": config.target_power_dbm - 3,
            "passed": abs(power - config.target_power_dbm) <= 3
        })
        
        # ACLR测试
        lower, upper = cmw.measure_aclr_gprf()
        logger.info(f"ACLR: 下邻 {lower:.2f} dBc, 上邻 {upper:.2f} dBc")
        
        results["aclr_results"].append({
            "band": band,
            "frequency_mhz": freq,
            "lower_adj_dbch": round(lower, 2),
            "upper_adj_dbch": round(upper, 2),
            "limit_db": config.aclr_limit_db,
            "passed": lower >= config.aclr_limit_db and upper >= config.aclr_limit_db
        })
    
    cmw.disconnect()
    
    # 保存结果
    filename = f"lte_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\n结果已保存: {filename}")
    
    # 打印摘要
    logger.info("\n=== 测试摘要 ===")
    for pr in results["power_results"]:
        status = "PASS" if pr["passed"] else "FAIL"
        logger.info(f"Band {pr['band']} 功率: {pr['power_dbm']:.2f} dBm [{status}]")
    
    for ar in results["aclr_results"]:
        status = "PASS" if ar["passed"] else "FAIL"
        logger.info(f"Band {ar['band']} ACLR: {ar['lower_adj_dbch']:.2f} dBc [{status}]")


if __name__ == "__main__":
    run_test(bands=["3", "7", "20"])
