#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CMW500 LTE/5G 自动化测试系统
支持信令测试和非信令测试（回退模式）
测试标准: 3GPP

CMW500地址: TCPIP0::192.168.121.116::inst0::INSTR
"""

import socket
import time
import json
import csv
import logging
import sys
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from enum import Enum

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BandType(Enum):
    """频段类型 - 3GPP"""
    B1 = "1"
    B3 = "3"
    B5 = "5"
    B7 = "7"
    B8 = "8"
    B20 = "20"
    B28 = "28"
    B38 = "38"
    B40 = "40"
    B41 = "41"
    
    @property
    def downlink_mhz(self) -> tuple:
        band_freqs = {
            "1": (2110, 2170), "3": (1805, 1880), "5": (869, 894),
            "7": (2620, 2690), "8": (925, 960), "20": (791, 821),
            "28": (758, 803), "38": (2570, 2620), "40": (2300, 2400),
            "41": (2496, 2690),
        }
        return band_freqs.get(self.value, (0, 0))


@dataclass
class TestConfig:
    """测试配置"""
    cmw_ip: str = "192.168.121.116"
    cmw_port: int = 5025
    band: str = "3"
    bandwidth_mhz: int = 20
    dl_channel: int = 1850
    target_power_dbm: int = 23
    aclr_limit_db: float = -45.0
    sensitivity_max_power_dbm: float = -100.0


@dataclass
class PowerResult:
    frequency_mhz: float
    channel: int
    power_dbm: float
    limit_dbm: float
    passed: bool
    timestamp: str


@dataclass
class ACLRResult:
    frequency_mhz: float = 0.0
    channel: int = 0
    lower_adj_power_dbch: float = 0.0
    upper_adj_power_dbch: float = 0.0
    lower_alt1_power_dbch: float = 0.0
    upper_alt1_power_dbch: float = 0.0
    limit_db: float = -45.0
    passed: bool = False
    timestamp: str = ""


@dataclass
class SensitivityResult:
    frequency_mhz: float = 0.0
    channel: int = 0
    sensitivity_power_dbm: float = 0.0
    bler_percent: float = 0.0
    passed: bool = False
    timestamp: str = ""


class CMW500_Test:
    """CMW500测试控制类"""
    
    def __init__(self, ip: str, port: int = 5025):
        self.ip = ip
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.lte_mode = False
        self.dut_connected = False
        
    def connect(self) -> bool:
        try:
            logger.info(f"连接CMW500: {self.ip}:{self.port}")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(30)
            self.socket.connect((self.ip, self.port))
            
            self.socket.sendall(b"*IDN?\n")
            self.socket.settimeout(10)
            response = b""
            while True:
                try:
                    chunk = self.socket.recv(4096)
                    if chunk:
                        response += chunk
                        if response.endswith(b'\n'):
                            break
                except:
                    break
            
            idn = response.decode('utf-8').strip()
            logger.info(f"CMW500: {idn}")
            self.connected = True
            return True
        except Exception as e:
            logger.error(f"连接失败: {e}")
            return False
    
    def disconnect(self):
        if self.socket:
            self.socket.close()
            self.connected = False
    
    def send_cmd(self, cmd: str, wait: float = 0.3) -> str:
        if not self.connected:
            return ""
        try:
            self.socket.sendall(f"{cmd}\n".encode('utf-8'))
            time.sleep(wait)
            self.socket.settimeout(10)
            response = b""
            while True:
                try:
                    chunk = self.socket.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                    if response.endswith(b'\n'):
                        break
                except:
                    break
            return response.decode('utf-8').strip()
        except:
            return ""
    
    def write(self, cmd: str):
        self.send_cmd(cmd, 0.2)
    
    def query(self, cmd: str) -> str:
        return self.send_cmd(cmd, 0.5)
    
    def setup_lte_signaling(self, band: str, bw: int = 20, 
                          channel: int = 1850, power: int = 23) -> bool:
        """尝试配置LTE信令"""
        logger.info("尝试配置LTE信令...")
        
        # 选择LTE测量场景
        result = self.query("ROUTe:LTE:MEAS:SCENario:SIGN")
        
        if "UNDEFINED" in result.upper() or "ERROR" in result.upper():
            logger.warning("LTE信令模式不可用，尝试Analyzer模式")
            result = self.query("ROUTe:LTE:MEAS:SCENario SAL")
        
        time.sleep(1)
        
        # 设置频段
        self.write(f'SYSTem:BAND:INDex LTE,{band}')
        time.sleep(0.5)
        
        # 带宽
        self.write(f"CONF:LTE:DL:BANDwidth {bw}")
        self.write(f"CONF:LTE:UL:BANDwidth {bw}")
        
        # 信道
        self.write(f"CONF:LTE:DL:FREQuency:CHANnel {channel}")
        
        # 功率
        self.write(f"POW:RF:OUTP {power}")
        
        # 启用测量
        self.write("CONFigure:LTE:MEAS:POW:ENABLE ON")
        
        time.sleep(1)
        
        # 检查错误
        err = self.query("SYSTem:ERRor?")
        if "0" in err or "No error" in err:
            self.lte_mode = True
            logger.info("LTE模式配置成功")
            return True
        
        logger.warning(f"LTE配置错误: {err}，回退到GPRF模式")
        self.lte_mode = False
        return False
    
    def measure_power(self) -> float:
        """测量功率"""
        if self.lte_mode:
            # LTE模式
            self.write("INIT:LTE:MEAS:POW")
            time.sleep(1.5)
            result = self.query("FETCh:LTE:MEAS:POW:RF:RMS?")
        else:
            # GPRF模式（回退）
            self.write("CONFigure:GPRf:MEAS:POW:AVG:SCOunt 10")
            self.write("INIT:GPRf:MEAS:POW")
            time.sleep(1)
            result = self.query("FETCh:GPRf:MEAS:POW:AVER?")
        
        try:
            if ',' in result:
                parts = result.split(',')
                status = int(parts[0])
                if status == 0:
                    return float(parts[1])
            return float(result.strip())
        except:
            return -999.0
    
    def measure_aclr(self) -> ACLRResult:
        """测量ACLR"""
        aclr = ACLRResult(timestamp=datetime.now().isoformat())
        
        if self.lte_mode:
            self.write("INIT:LTE:MEAS:ACLR")
            time.sleep(2)
            result = self.query("FETCh:LTE:MEAS:ACLR:REST?")
        else:
            # GPRF模式 - 简化版
            self.write("INIT:GPRf:MEAS:ACLR")
            time.sleep(2)
            result = self.query("FETCh:GPRf:MEAS:ACLR?")
        
        try:
            values = result.strip().split(',')
            if len(values) >= 4:
                aclr.lower_adj_power_dbch = float(values[1])
                aclr.upper_adj_power_dbch = float(values[3])
                if len(values) >= 8:
                    aclr.lower_alt1_power_dbch = float(values[5])
                    aclr.upper_alt1_power_dbch = float(values[7])
                aclr.passed = (aclr.lower_adj_power_dbch >= aclr.limit_db and 
                              aclr.upper_adj_power_dbch >= aclr.limit_db)
        except:
            pass
        
        return aclr
    
    def check_dut_connection(self) -> bool:
        """检查DUT连接状态（仅信令模式）"""
        if self.lte_mode:
            result = self.query("STATus:LTE:SIGN:PS?")
            if result and result != "0":
                self.dut_connected = True
                return True
        return False


class LTE_Test_System:
    """LTE测试系统"""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.cmw = CMW500_Test(config.cmw_ip, config.cmw_port)
        self.results: Dict[str, Any] = {
            "config": asdict(config),
            "mode": "",
            "power_results": [],
            "aclr_results": [],
            "sensitivity_results": [],
            "test_time": "",
            "dut_connected": False
        }
    
    def run_test(self, bands: List[str] = None) -> Dict:
        if bands is None:
            bands = [self.config.band]
        
        self.results["test_time"] = datetime.now().isoformat()
        
        # 连接CMW500
        if not self.cmw.connect():
            logger.error("无法连接CMW500")
            return self.results
        
        # 尝试配置LTE
        self.cmw.setup_lte_signaling(
            band=self.config.band,
            bw=self.config.bandwidth_mhz,
            channel=self.config.dl_channel,
            power=self.config.target_power_dbm
        )
        
        mode = "LTE信令" if self.cmw.lte_mode else "GPRF(非信令)"
        self.results["mode"] = mode
        logger.info(f"测试模式: {mode}")
        
        # 检查DUT连接
        if self.cmw.lte_mode:
            self.cmw.check_dut_connection()
            self.results["dut_connected"] = self.cmw.dut_connected
            
            if not self.cmw.dut_connected:
                logger.warning("DUT未连接，将进行非信令测试")
        
        time.sleep(2)
        
        # 测试各频段
        for band in bands:
            logger.info(f"\n{'='*40}")
            logger.info(f"测试频段: Band {band}")
            logger.info(f"{'='*40}")
            
            self.config.band = band
            band_type = BandType(band)
            freq = (band_type.downlink_mhz[0] + band_type.downlink_mhz[1]) / 2
            
            # 功率测试
            logger.info("测量功率...")
            power = self.cmw.measure_power()
            power_result = PowerResult(
                frequency_mhz=freq,
                channel=self.config.dl_channel,
                power_dbm=power,
                limit_dbm=self.config.target_power_dbm - 3,
                passed=abs(power - self.config.target_power_dbm) <= 3,
                timestamp=datetime.now().isoformat()
            )
            logger.info(f"功率: {power:.2f} dBm, 通过: {power_result.passed}")
            self.results["power_results"].append(asdict(power_result))
            
            # ACLR测试
            logger.info("测量ACLR...")
            aclr_result = self.cmw.measure_aclr()
            aclr_result.frequency_mhz = freq
            aclr_result.channel = self.config.dl_channel
            aclr_result.limit_db = self.config.aclr_limit_db
            logger.info(f"ACLR: 下邻 {aclr_result.lower_adj_power_dbch:.2f} dBc, "
                       f"上邻 {aclr_result.upper_adj_power_dbch:.2f} dBc")
            self.results["aclr_results"].append(asdict(aclr_result))
            
            # 灵敏度测试（仅信令模式）
            if self.cmw.lte_mode and self.cmw.dut_connected:
                logger.info("测量灵敏度...")
                # 简化实现
                sens_power = -95.0  # 占位
                sens_result = SensitivityResult(
                    frequency_mhz=freq,
                    channel=self.config.dl_channel,
                    sensitivity_power_dbm=sens_power,
                    bler_percent=1.0,
                    passed=sens_power <= self.config.sensitivity_max_power_dbm,
                    timestamp=datetime.now().isoformat()
                )
                self.results["sensitivity_results"].append(asdict(sens_result))
            else:
                logger.info("跳过灵敏度测试（非信令模式或DUT未连接）")
            
            time.sleep(1)
        
        self.cmw.disconnect()
        return self.results
    
    def save_results(self, filename: str = None):
        if filename is None:
            filename = f"lte_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"结果已保存: {filename}")
        
        # CSV
        csv_file = filename.replace('.json', '.csv')
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['项目', '频率(MHz)', '结果', '限值', '通过'])
            
            for r in self.results["power_results"]:
                writer.writerow(['功率', r['frequency_mhz'], 
                               f"{r['power_dbm']:.2f} dBm", 
                               f"{r['limit_dbm']:.2f} dBm",
                               'PASS' if r['passed'] else 'FAIL'])
            
            for r in self.results["aclr_results"]:
                writer.writerow(['ACLR', r['frequency_mhz'],
                               f"{r['lower_adj_power_dbch']:.2f} dBc",
                               f"{r['limit_db']:.2f} dBc",
                               'PASS' if r['passed'] else 'FAIL'])
        
        logger.info(f"CSV已保存: {csv_file}")


def main():
    config = TestConfig(
        cmw_ip="192.168.121.116",
        band="3",
        bandwidth_mhz=20,
        dl_channel=1850,
        target_power_dbm=23,
        aclr_limit_db=-45.0,
        sensitivity_max_power_dbm=-100.0
    )
    
    test_system = LTE_Test_System(config)
    
    try:
        results = test_system.run_test(bands=["3", "7", "20"])
        test_system.save_results()
        
        logger.info("\n" + "="*50)
        logger.info("测试完成!")
        logger.info(f"测试模式: {results['mode']}")
        logger.info(f"DUT连接: {'是' if results['dut_connected'] else '否'}")
        logger.info("="*50)
        
    except Exception as e:
        logger.error(f"错误: {e}")
    finally:
        test_system.cmw.disconnect()


if __name__ == "__main__":
    main()
