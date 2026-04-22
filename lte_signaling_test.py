#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CMW500 LTE 信令自动化测试系统
用于测试功率、ACLR（邻道泄漏比）和灵敏度
测试标准: 3GPP

CMW500地址: TCPIP0::192.168.121.116::inst0::INSTR
"""

import socket
import time
import json
import csv
import logging
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from enum import Enum
import sys
import re

# 配置日志 - 使用UTF-8编码
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class BandType(Enum):
    """频段类型 - 3GPP标准"""
    # 常用LTE频段
    B1 = "1"      # 2100MHz
    B3 = "3"      # 1800MHz
    B5 = "5"      # 850MHz
    B7 = "7"      # 2600MHz
    B8 = "8"      # 900MHz
    B20 = "20"    # 800MHz
    B28 = "28"    # 700MHz
    B38 = "38"    # 2600MHz TDD
    B40 = "40"    # 2300MHz TDD
    B41 = "41"    # 2500MHz TDD
    
    @property
    def downlink_mhz(self) -> tuple:
        """获取下行频率范围 (MHz) - 3GPP TS 36.101"""
        band_freqs = {
            "1": (2110, 2170),
            "3": (1805, 1880),
            "5": (869, 894),
            "7": (2620, 2690),
            "8": (925, 960),
            "20": (791, 821),
            "28": (758, 803),
            "38": (2570, 2620),
            "40": (2300, 2400),
            "41": (2496, 2690),
        }
        return band_freqs.get(self.value, (0, 0))
    
    @property
    def uplink_mhz(self) -> tuple:
        """获取上行频率范围 (MHz) - 3GPP TS 36.101"""
        band_freqs = {
            "1": (1920, 1980),
            "3": (1710, 1785),
            "5": (824, 849),
            "7": (2500, 2570),
            "8": (880, 915),
            "20": (832, 862),
            "28": (703, 748),
            "38": (2570, 2620),
            "40": (2300, 2400),
            "41": (2496, 2690),
        }
        return band_freqs.get(self.value, (0, 0))


@dataclass
class TestConfig:
    """测试配置"""
    cmw_ip: str = "192.168.121.116"
    cmw_port: int = 5025
    band: str = "3"           # 频段
    bandwidth_mhz: int = 20   # 带宽 MHz
    dl_channel: int = 1850    # 下行信道
    ul_channel: int = 1950    # 上行信道
    
    # 功率设置
    target_power_dbm: int = 23  # 目标输出功率 dBm
    
    # ACLR设置 - 3GPP标准
    aclr_limit_db: float = -45.0  # ACLR限值 dBc
    
    # 灵敏度设置 - 3GPP标准
    sensitivity_target_bler: float = 1.0  # 目标BLER %
    sensitivity_max_power_dbm: float = -100.0  # 灵敏度最大功率限值


@dataclass
class PowerResult:
    """功率测试结果"""
    frequency_mhz: float
    channel: int
    power_dbm: float
    limit_dbm: float
    passed: bool
    timestamp: str


@dataclass
class ACLRResult:
    """ACLR测试结果 - 3GPP TS 36.101"""
    frequency_mhz: float = 0.0
    channel: int = 0
    lower_adj_power_dbm: float = 0.0
    lower_adj_power_dbch: float = 0.0
    upper_adj_power_dbm: float = 0.0
    upper_adj_power_dbch: float = 0.0
    lower_alt1_power_dbm: float = 0.0
    lower_alt1_power_dbch: float = 0.0
    upper_alt1_power_dbm: float = 0.0
    upper_alt1_power_dbch: float = 0.0
    limit_db: float = -45.0
    passed: bool = False
    timestamp: str = ""


@dataclass
class SensitivityResult:
    """灵敏度测试结果"""
    frequency_mhz: float = 0.0
    channel: int = 0
    sensitivity_power_dbm: float = 0.0
    bler_percent: float = 0.0
    passed: bool = False
    timestamp: str = ""


class CMW500_Signaling:
    """CMW500 信令测试控制类"""
    
    def __init__(self, ip: str, port: int = 5025):
        self.ip = ip
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.dut_connected = False
        
    def connect(self) -> bool:
        """连接CMW500"""
        try:
            logger.info(f"正在连接CMW500: {self.ip}:{self.port}")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(30)
            self.socket.connect((self.ip, self.port))
            
            # 测试连接
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
                except socket.timeout:
                    break
            
            idn = response.decode('utf-8').strip()
            logger.info(f"CMW500连接成功: {idn}")
            self.connected = True
            return True
        except Exception as e:
            logger.error(f"连接CMW500失败: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
            self.connected = False
            logger.info("CMW500已断开连接")
    
    def send_cmd(self, command: str, wait: float = 0.3) -> str:
        """发送SCPI命令"""
        if not self.connected:
            raise ConnectionError("未连接到CMW500")
        try:
            self.socket.sendall(f"{command}\n".encode('utf-8'))
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
                except socket.timeout:
                    break
            return response.decode('utf-8').strip()
        except Exception as e:
            logger.error(f"发送命令失败: {command}, 错误: {e}")
            return ""
    
    def write(self, command: str):
        """发送命令（无返回值）"""
        if not self.connected:
            raise ConnectionError("未连接到CMW500")
        self.socket.sendall(f"{command}\n".encode('utf-8'))
        time.sleep(0.2)
    
    def query(self, command: str) -> str:
        """查询命令"""
        return self.send_cmd(command, 0.5)
    
    def reset(self):
        """复位仪器"""
        logger.info("复位CMW500...")
        self.write("*RST")
        time.sleep(3)
        
    def setup_lte_signaling(self, band: str, bandwidth: int = 20, 
                           dl_channel: int = 1850, power_dbm: int = 23):
        """配置LTE信令（CMW500作为基站）"""
        logger.info(f"配置LTE信令: Band {band}, BW {bandwidth}MHz, 功率 {power_dbm}dBm")
        
        # 选择LTE信令测量场景
        self.write("ROUTe:LTE:MEAS:SCENario:SIGNing")
        time.sleep(1)
        
        # 检查错误
        err = self.query("SYSTem:ERRor?")
        logger.info(f"配置错误: {err}")
        
        # 设置频段
        self.write(f"SYSTem:BAND:INDex LTE,{band}")
        time.sleep(0.5)
        
        # 设置带宽
        self.write(f"CONF:LTE:DL:BANDwidth {bandwidth}")
        self.write(f"CONF:LTE:UL:BANDwidth {bandwidth}")
        
        # 设置下行频率/信道
        self.write(f"CONF:LTE:DL:FREQuency:CHANnel {dl_channel}")
        
        # 设置输出功率
        self.write(f"POW:RF:OUTP {power_dbm}")
        
        time.sleep(1)
        
        # 启用信令
        self.write("SOUR:LTE:MEAS:SCENario:SIGNing:STARt")
        time.sleep(2)
        
        # 检查连接状态
        self.check_connection_status()
        
        return self.dut_connected
    
    def check_connection_status(self):
        """检查DUT连接状态"""
        # 查询连接状态
        result = self.query("STATus:LTE:SIGN:PS?")
        logger.info(f"DUT连接状态: {result}")
        
        # 尝试解析状态
        if result and result != "0":
            self.dut_connected = True
            logger.info("DUT已连接")
        else:
            self.dut_connected = False
            logger.warning("DUT未连接")
    
    def wait_for_connection(self, timeout: int = 30) -> bool:
        """等待DUT连接"""
        logger.info(f"等待DUT连接 (超时 {timeout}秒)...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            self.check_connection_status()
            if self.dut_connected:
                return True
            time.sleep(2)
        
        return False
    
    def measure_power(self) -> float:
        """测量发射功率 - 3GPP LTE"""
        # 使用专用LTE功率测量
        self.write("INIT:LTE:MEAS:POW")
        time.sleep(1.5)
        
        result = self.query("FETCh:LTE:MEAS:POW:RF:RMS?")
        
        try:
            # 格式: "0,-75.24" 或直接是功率值
            if ',' in result:
                parts = result.split(',')
                if len(parts) >= 2:
                    status = int(parts[0])
                    if status == 0:
                        power = float(parts[1])
                        return power
            else:
                power = float(result.strip())
                return power
        except:
            pass
        
        # 备用方法
        result = self.query("FETCh:LTE:MEAS:POW:RF:AVER?")
        try:
            if ',' in result:
                parts = result.split(',')
                if len(parts) >= 2:
                    return float(parts[1])
            else:
                return float(result.strip())
        except:
            pass
            
        return -999.0
    
    def measure_aclr(self) -> ACLRResult:
        """测量ACLR - 3GPP LTE (TS 36.101)"""
        # 触发ACLR测量
        self.write("INIT:LTE:MEAS:ACLR")
        time.sleep(2)
        
        # 读取ACLR结果
        result = self.query("FETCh:LTE:MEAS:ACLR:REST?")
        
        aclr = ACLRResult(timestamp=datetime.now().isoformat())
        
        try:
            values = result.strip().split(',')
            if len(values) >= 4:
                aclr.lower_adj_power_dbch = float(values[1])
                aclr.upper_adj_power_dbch = float(values[3])
                
                if len(values) >= 8:
                    aclr.lower_alt1_power_dbch = float(values[5])
                    aclr.upper_alt1_power_dbch = float(values[7])
                
                # 3GPP ACLR限值: 主要邻信道 <-45dBc, 交替邻信道 <-50dBc
                aclr.passed = (aclr.lower_adj_power_dbch >= aclr.limit_db and 
                              aclr.upper_adj_power_dbch >= aclr.limit_db)
        except Exception as e:
            logger.error(f"ACLR测量解析失败: {e}")
        
        return aclr
    
    def measure_sensitivity(self, target_bler: float = 1.0) -> float:
        """测量灵敏度 - 3GPP LTE (TS 36.101)"""
        # 设置BLER测量
        self.write(f"CONF:LTE:MEAS:BLER:TARG {target_bler}")
        
        # 开始BLER测量
        self.write("INIT:LTE:MEAS:BLER")
        time.sleep(3)
        
        # 读取BLER结果
        result = self.query("FETCh:LTE:MEAS:BLER:STAT?")
        
        try:
            if ',' in result:
                bler = float(result.split(',')[1])
            else:
                bler = float(result.strip())
        except:
            bler = 100.0
        
        # 二分查找灵敏度
        return self.search_sensitivity(target_bler)
    
    def search_sensitivity(self, target_bler: float = 1.0, 
                          start_power: float = -80.0, 
                          min_power: float = -120.0) -> float:
        """搜索灵敏度"""
        logger.info(f"搜索灵敏度 (目标BLER: {target_bler}%)...")
        
        current_power = start_power
        step = 2.0
        
        while current_power >= min_power:
            # 设置输出功率
            self.write(f"POW:RF:OUTP {int(current_power)}")
            time.sleep(0.5)
            
            # 测量BLER
            self.write("INIT:LTE:MEAS:BLER")
            time.sleep(2)
            
            result = self.query("FETCh:LTE:MEAS:BLER:STAT?")
            try:
                if ',' in result:
                    bler = float(result.split(',')[1])
                else:
                    bler = float(result.strip())
                
                logger.info(f"功率: {current_power} dBm, BLER: {bler}%")
                
                if bler <= target_bler:
                    return current_power
            except:
                pass
            
            current_power -= step
        
        return min_power


class LTE_Signaling_Test_System:
    """LTE 信令测试系统"""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.cmw = CMW500_Signaling(config.cmw_ip, config.cmw_port)
        self.results: Dict[str, Any] = {
            "config": asdict(config),
            "power_results": [],
            "aclr_results": [],
            "sensitivity_results": [],
            "test_time": "",
            "dut_connected": False
        }
    
    def connect(self) -> bool:
        return self.cmw.connect()
    
    def disconnect(self):
        self.cmw.disconnect()
    
    def run_test(self, bands: List[str] = None) -> Dict:
        """运行测试"""
        if bands is None:
            bands = [self.config.band]
        
        self.results["test_time"] = datetime.now().isoformat()
        
        for band in bands:
            logger.info(f"\n{'='*50}")
            logger.info(f"测试频段: Band {band}")
            logger.info(f"{'='*50}")
            
            self.config.band = band
            
            # 配置LTE信令
            connected = self.cmw.setup_lte_signaling(
                band=band,
                bandwidth=self.config.bandwidth_mhz,
                dl_channel=self.config.dl_channel,
                power_dbm=self.config.target_power_dbm
            )
            
            if not connected:
                logger.warning("DUT未连接，尝试等待...")
                connected = self.cmw.wait_for_connection(timeout=30)
            
            self.results["dut_connected"] = connected
            
            if connected:
                time.sleep(2)
                
                # 功率测试
                power = self.cmw.measure_power()
                band_type = BandType(band)
                freq = (band_type.downlink_mhz[0] + band_type.downlink_mhz[1]) / 2
                
                power_result = PowerResult(
                    frequency_mhz=freq,
                    channel=self.config.dl_channel,
                    power_dbm=power,
                    limit_dbm=self.config.target_power_dbm - 3,
                    passed=abs(power - self.config.target_power_dbm) <= 3,
                    timestamp=datetime.now().isoformat()
                )
                logger.info(f"功率测试结果: {power:.2f} dBm, 通过: {power_result.passed}")
                self.results["power_results"].append(asdict(power_result))
                
                # ACLR测试
                logger.info("测试ACLR...")
                aclr_result = self.cmw.measure_aclr()
                aclr_result.frequency_mhz = freq
                aclr_result.channel = self.config.dl_channel
                aclr_result.limit_db = self.config.aclr_limit_db
                logger.info(f"ACLR测试结果: 下邻 {aclr_result.lower_adj_power_dbch:.2f} dBc, "
                           f"上邻 {aclr_result.upper_adj_power_dbch:.2f} dBc, "
                           f"通过: {aclr_result.passed}")
                self.results["aclr_results"].append(asdict(aclr_result))
                
                # 灵敏度测试
                logger.info("测试灵敏度...")
                sens_power = self.cmw.measure_sensitivity(self.config.sensitivity_target_bler)
                sens_result = SensitivityResult(
                    frequency_mhz=freq,
                    channel=self.config.dl_channel,
                    sensitivity_power_dbm=sens_power,
                    bler_percent=self.config.sensitivity_target_bler,
                    passed=sens_power <= self.config.sensitivity_max_power_dbm,
                    timestamp=datetime.now().isoformat()
                )
                logger.info(f"灵敏度测试结果: {sens_power:.2f} dBm, 通过: {sens_result.passed}")
                self.results["sensitivity_results"].append(asdict(sens_result))
            else:
                logger.error("DUT未连接，跳过测试")
            
            time.sleep(1)
        
        return self.results
    
    def save_results(self, filename: str = None):
        """保存测试结果"""
        if filename is None:
            filename = f"lte_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"测试结果已保存到: {filename}")
        
        # CSV格式
        csv_filename = filename.replace('.json', '.csv')
        self._save_csv(csv_filename)
        
        return filename
    
    def _save_csv(self, filename: str):
        """保存CSV"""
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['测试项目', '频率(MHz)', '信道', '结果', '限值', '通过/失败'])
            
            for r in self.results["power_results"]:
                writer.writerow([
                    '功率', r['frequency_mhz'], r['channel'],
                    f"{r['power_dbm']:.2f} dBm", f"{r['limit_dbm']:.2f} dBm",
                    'PASS' if r['passed'] else 'FAIL'
                ])
            
            for r in self.results["aclr_results"]:
                writer.writerow([
                    'ACLR', r['frequency_mhz'], r['channel'],
                    f"{r['lower_adj_power_dbch']:.2f} dBc", f"{r['limit_db']:.2f} dBc",
                    'PASS' if r['passed'] else 'FAIL'
                ])
            
            for r in self.results["sensitivity_results"]:
                writer.writerow([
                    '灵敏度', r['frequency_mhz'], r['channel'],
                    f"{r['sensitivity_power_dbm']:.2f} dBm", f"< {self.config.sensitivity_max_power_dbm} dBm",
                    'PASS' if r['passed'] else 'FAIL'
                ])
        
        logger.info(f"CSV结果已保存到: {filename}")


def main():
    """主函数"""
    # 创建测试配置
    config = TestConfig(
        cmw_ip="192.168.121.116",
        band="3",
        bandwidth_mhz=20,
        dl_channel=1850,
        target_power_dbm=23,
        aclr_limit_db=-45.0,
        sensitivity_target_bler=1.0,
        sensitivity_max_power_dbm=-100.0
    )
    
    # 创建测试系统
    test_system = LTE_Signaling_Test_System(config)
    
    try:
        # 连接
        if not test_system.connect():
            logger.error("连接失败")
            return
        
        # 测试频段
        test_bands = ["3", "7", "20"]
        
        # 运行测试
        results = test_system.run_test(bands=test_bands)
        
        # 保存结果
        test_system.save_results()
        
        logger.info("\n" + "="*50)
        logger.info("测试完成!")
        logger.info(f"DUT连接状态: {'已连接' if results['dut_connected'] else '未连接'}")
        logger.info("="*50)
        
    except Exception as e:
        logger.error(f"测试出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        test_system.disconnect()


if __name__ == "__main__":
    main()
