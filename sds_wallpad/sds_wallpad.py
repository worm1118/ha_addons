# first written by nandflash("저장장치") <github@printk.info> since 2020-06-25

import socket
import serial
import paho.mqtt.client as paho_mqtt
import json

import sys
import time
import logging
from logging.handlers import TimedRotatingFileHandler
import os.path
import re

import os
import urllib.request
import subprocess

####################
VIRTUAL_DEVICE = {
    # 현관스위치: 엘리베이터 호출, 가스밸브 잠금 지원
    "entrance": {
        "header0": 0xAD,
        "resp_size": 4,
        "default": {
            "init":  { "header1": 0x5A, "resp": 0xB05A006A, }, # 처음 전기가 들어왔거나 한동안 응답을 안했을 때, 이것부터 해야 함
            "query": { "header1": 0x41, "resp": 0xB0560066, }, # 여기에 0xB0410071로 응답하면 gas valve 상태는 전달받지 않음
            "gas":   { "header1": 0x56, "resp": 0xB0410071, }, # 0xAD41에 항상 0xB041로 응답하면 이게 실행될 일은 없음
            "light": { "header1": 0x52, "resp": 0xB0520163, },

            # 성공 시 ack들, 무시해도 상관 없지만...
            "gasa":  { "header1": 0x55, "resp": 0xB0410071, },
            "eva":   { "header1": 0x2F, "resp": 0xB0410071, },
        },

        # 0xAD41에 다르게 응답하는 방법들, 이 경우 월패드가 다시 ack를 보내준다
        "trigger": {
            "gas":   { "ack": 0x55, "ON": 0xB0550164, "next": None, },
            "ev":    { "ack": 0x2F, "ON": 0xB02F011E, "next": None, },
        },
    },

    # 신형 현관스위치
    "entrance2": {
        "header0": 0xCC,
        "resp_size": 5,
        "default": {
            "init":  { "header1": 0x5A, "resp": 0xB05A01006B, }, # 처음 전기가 들어왔거나 한동안 응답을 안했을 때, 이것부터 해야 함
            "query": { "header1": 0x41, "resp": 0xB041010070, }, # keepalive
            "date":  { "header1": 0x01, "resp": 0xB001010030, }, # 스위치로 현재 날짜, 시각 전달
            "broad": { "header1": 0x0B, "resp": 0xB00B01003A, }, # 다른 기기 상태 전달받음
            "ukn12": { "header1": 0x12, "resp": 0xB041010070, }, # 엘리베이터 호출 결과?
            "ukn09": { "header1": 0x09, "resp": 0xB009010038, },
            "ukn07": { "header1": 0x07, "resp": 0xB007010137, },
            "ukn02": { "header1": 0x02, "resp": 0xB041010070, },

            # 성공 시 ack들, 무시해도 상관 없...으려나?
            "eva":   { "header1": 0x10, "resp": 0xB041010070, },
            "gasa":  { "header1": 0x13, "resp": 0xB041010070, },
        },

        # 0xCC41에 다르게 응답하는 방법들, 이 경우 월패드가 다시 ack를 보내준다
        "trigger": {
            "ev":    { "ack": 0x10, "ON": 0xB010010120, "next": None, },
            "gas":   { "ack": 0x13, "ON": 0xB01301015F, "next": None, },
        },
    },

    # 인터폰: 공동현관 문열림 기능 지원
    "intercom": {
        "header0": 0xA4,
        "resp_size": 4,
        "default": {
            "init":    { "header1": 0x5A, "resp": 0xB05A006A, }, # 처음 전기가 들어왔거나 한동안 응답을 안했을 때, 이것부터 해야 함
            "query":   { "header1": 0x41, "resp": 0xB0410071, }, # 평상시
            "block":   { "header1": 0x42, "resp": 0xB0410071, }, # 다른 인터폰이 통화중이라던지 해서 조작 거부중인 상태
            "public":  { "header1": 0x32, "resp": 0xB0320002, }, # 공동현관 초인종 눌림
            "private": { "header1": 0x31, "resp": 0xB0310001, }, # 현관 초인종 눌림
            "opena":   { "header1": 0x36, "resp": 0xB0420072, }, # 통화 시작 요청 성공, 통화중이라고 ack 보내기
            "vopena":  { "header1": 0x38, "resp": 0xB0420072, }, # 영상통화 시작 요청 성공, 통화중이라고 ack 보내기
            "vconna":  { "header1": 0x35, "resp": 0xB0350005, }, # 영상 전송 시작됨
            "open2a":  { "header1": 0x3B, "resp": 0xB0410071, }, # 문열림 요청 성공, 통화 종료
            "end":     { "header1": 0x3E, "resp": 0xB03EFFFF, }, # 상황 종료, Byte[2] 가 반드시 일치해야 함
        },

        "trigger": {
            "public":  { "ack": 0x36, "ON": 0xB0360204, "next": ("public0", "ON"), }, # 통화 시작
            "public0": { "ack": 0x3B, "ON": 0xB03B010A, "next": None, }, # 문열림
            "priv_a":  { "ack": 0x36, "ON": 0xB0360107, "next": ("privat2", "ON"), }, # 현관 통화 시작 (초인종 울렸을 때)
            "priv_b":  { "ack": 0x35, "ON": 0xB0380008, "next": ("privat2", "ON"), }, # 현관 통화 시작 (평상시)
            "private": { "ack": 0x35, "ON": 0xB0380008, "next": ("privat2", "ON"), }, # 현관 통화 시작 (평상시)
            "privat2": { "ack": 0x3B, "ON": 0xB03B000B, "next": None, }, # 현관 문열림
            #"end":     { "ack": 0x41, "ON": 0xB0420072, "next": None, }, # 문열림 후, 통화 종료

            # 딜레이 모드 사용 시 통화 유지 대충 구현
            "pubdelay1": { "ack": 0x41, "ON": 0xB0420072, "next": ("pubdelay2", "ON"), },
            "pubdelay2": { "ack": 0x41, "ON": 0xB0420072, "next": ("pubdelay3", "ON"), },
            "pubdelay3": { "ack": 0x41, "ON": 0xB0420072, "next": ("pubdelay4", "ON"), },
            "pubdelay4": { "ack": 0x41, "ON": 0xB0420072, "next": ("pubdelay5", "ON"), },
            "pubdelay5": { "ack": 0x41, "ON": 0xB0420072, "next": ("public0", "ON"), },
        },
    },
}

####################
# 기존 월패드 애드온의 역할하는 부분
RS485_DEVICE = {
    # 전등 스위치
    "light": {
        "query":    { "header": 0xAC79, "length":  5, "id": 2, },
        "state":    { "header": 0xB079, "length":  5, "id": 2, "parse": {("power", 3, "bitmap")} },
        "last":     { },

        "power":    { "header": 0xAC7A, "length":  5, "id": 2, "pos": 3, },
    },

    # 환기장치 (전열교환기)
    "fan": {
        "query":    { "header": 0xC24E, "length":  6, },
        "state":    { "header": 0xB04E, "length":  6, "parse": {("power", 4, "fan_toggle"), ("preset", 2, "fan_speed")} },
        "last":     { },

        "power":    { "header": 0xC24F, "length":  6, "pos": 2, },
        "preset":   { "header": 0xC24F, "length":  6, "pos": 2, },
    },

    # 각방 난방 제어
    "thermostat": {
        "query":    { "header": 0xAE7C, "length":  8, "id": 2, },
        "state":    { "header": 0xB07C, "length":  8, "id": 2, "parse": {("power", 3, "heat_toggle"), ("target", 4, "value"), ("current", 5, "value")} },
        "last":     { },

        "power":    { "header": 0xAE7D, "length":  8, "id": 2, "pos": 3, },
        "target":   { "header": 0xAE7F, "length":  8, "id": 2, "pos": 3, },
    },

    # 대기전력차단 스위치 (전력사용량 확인)
    "plug": {
        "query":    { "header": 0xC64A, "length": 10, "id": 2, },
        "state":    { "header": 0xB04A, "length": 10, "id": 2, "parse": {("power", 3, "toggle"), ("idlecut", 3, "toggle2"), ("current", 5, "2Byte")} },
        "last":     { },

        "power":    { "header": 0xC66E, "length": 10, "id": 2, "pos": 3, },
        "idlecut":  { "header": 0xC64B, "length": 10, "id": 2, "pos": 3, },
    },

    # 일괄조명: 현관 스위치 살아있으면...
    "cutoff": {
        "query":    { "header": 0xAD52, "length":  4, },
        "state":    { "header": 0xB052, "length":  4, "parse": {("power", 2, "toggle")} }, # 1: 정상, 0: 일괄소등
        "last":     { },

        "power":    { "header": 0xAD53, "length":  4, "pos": 2, },
    },

    # 부엌 가스 밸브
    "gas_valve": {
        "query":    { "header": 0xAB41, "length":  4, },
        #"state":    { "header": 0xB041, "length":  4, "parse": {("power", 2, "invert")} }, # 0: 정상, 1: 차단; 0xB041은 공용 ack이므로 처리하기 복잡함
        #"state":    { "header": 0xAD56, "length":  4, "parse": {("power", 2, "invert")} }, # 0: 정상, 1: 차단; 월패드가 현관 스위치에 보내주는 정보로 확인 가능
        "state":    { "header": 0xAB41, "length":  8, "parse": {("power", 6, "invert")} }, # 0: 정상, 1: 차단; 0xB041은 공용 ack이므로 query에서부터 읽어서 처리
        "last":     { },

        "power":    { "header": 0xAB78, "length":  4, }, # 0 으로 잠그기만 가능
    },

    # 실시간에너지 0:전기, 1:가스, 2:수도
    "energy": {
        "query":    { "header": 0xAA6F, "length":  4, "id": 2, },
        "state":    { "header": 0xB06F, "length":  7, "id": 2, "parse": {("current", 3, "6decimal")} },
        "last":     { },
    },
}

DISCOVERY_DEVICE = {
    "ids": ["sds_wallpad",],
    "name": "SDS월패드",
    "mf": "Samsung SDS",
    "mdl": "Samsung SDS Wallpad",
    "sw": "n-andflash/ha_addons/sds_wallpad",
}

DISCOVERY_VIRTUAL = {
    "entrance": [
        {
            "_intg": "switch",
            "~": "{prefix}/virtual/entrance/ev",
            "name": "엘리베이터",
            "obj_id": "{prefix}_elevator",
            "stat_t": "~/state",
            "cmd_t": "~/command",
            "icon": "mdi:elevator",
        },
        {
            "_intg": "switch",
            "~": "{prefix}/virtual/entrance/gas",
            "name": "가스차단",
            "obj_id": "{prefix}_gas_cutoff",
            "stat_t": "~/state",
            "cmd_t": "~/command",
            "icon": "mdi:valve",
        },
    ],
    "entrance2": [
        {
            "_intg": "switch",
            "~": "{prefix}/virtual/entrance2/ev",
            "name": "엘리베이터",
            "obj_id": "{prefix}_new_elevator",
            "stat_t": "~/state",
            "cmd_t": "~/command",
            "icon": "mdi:elevator",
        },
        {
            "_intg": "switch",
            "~": "{prefix}/virtual/entrance2/gas",
            "name": "가스차단",
            "obj_id": "{prefix}_new_gas_cutoff",
            "stat_t": "~/state",
            "cmd_t": "~/command",
            "icon": "mdi:valve",
        },
    ],
    "intercom": [
        {
            "_intg": "switch",
            "~": "{prefix}/virtual/intercom/public",
            "name": "공동현관",
            "obj_id": "{prefix}_intercom_public",
            "avty_t": "~/available",
            "stat_t": "~/state",
            "cmd_t": "~/command",
            "icon": "mdi:door-closed",
        },
        {
            "_intg": "switch",
            "~": "{prefix}/virtual/intercom/private",
            "name": "현관",
            "obj_id": "{prefix}_intercom_private",
            "stat_t": "~/state",
            "cmd_t": "~/command",
            "icon": "mdi:door-closed",
        },
        {
            "_intg": "binary_sensor",
            "~": "{prefix}/virtual/intercom/public",
            "name": "공동현관 초인종",
            "obj_id": "{prefix}_intercom_public",
            "dev_cla": "sound",
            "stat_t": "~/available",
            "pl_on": "online",
            "pl_off": "offline",
        },
        {
            "_intg": "binary_sensor",
            "~": "{prefix}/virtual/intercom/private",
            "name": "현관 초인종",
            "obj_id": "{prefix}_intercom_private",
            "dev_cla": "sound",
            "stat_t": "~/available",
            "pl_on": "online",
            "pl_off": "offline",
        },
    ],
}

DISCOVERY_PAYLOAD = {
    "light": [ {
        "_intg": "light",
        "~": "{prefix}/light",
        "name": "조명 {id2}",
        "obj_id": "{prefix}_light_{id2}",
        "opt": True,
        "stat_t": "~/{idn}/power{bit}/state",
        "cmd_t": "~/{id2}/power/command",
    } ],
    "fan": [ {
        "_intg": "fan",
        "~": "{prefix}/fan/{idn}",
        "name": "환기",
        "obj_id": "{prefix}_fan_{idn}",
        "opt": True,
        "stat_t": "~/power/state",
        "cmd_t": "~/power/command",
        "pr_mode_stat_t": "~/preset/state",
        "pr_mode_cmd_t": "~/preset/command",
        "pl_on": 5,
        "pl_off": 6,
        "pr_modes": ["low", "medium", "high", "auto"],
        "spd_rng_min": 1,
        "spd_rng_max": 3,
    } ],
    "thermostat": [ {
        "_intg": "climate",
        "~": "{prefix}/thermostat/{idn}",
        "name": "난방 {idn}",
        "obj_id": "{prefix}_thermostat_{idn}",
        "mode_stat_t": "~/power/state",
        "mode_cmd_t": "~/power/command",
        "temp_stat_t": "~/target/state",
        "temp_cmd_t": "~/target/command",
        "curr_temp_t": "~/current/state",
        "modes": [ "off", "heat" ],
        "min_temp": 10,
        "max_temp": 30,
    } ],
    "plug": [ {
        "_intg": "switch",
        "~": "{prefix}/plug/{idn}/power",
        "name": "콘센트 {idn} 전원",
        "obj_id": "{prefix}_plug_{idn}",
        "stat_t": "~/state",
        "cmd_t": "~/command",
        "icon": "mdi:power-plug",
    },
    {
        "_intg": "switch",
        "~": "{prefix}/plug/{idn}/idlecut",
        "name": "콘센트 {idn} 대기전력차단",
        "obj_id": "{prefix}_plug_{idn}_standby_cutoff",
        "stat_t": "~/state",
        "cmd_t": "~/command",
        "icon": "mdi:leaf",
    },
    {
        "_intg": "sensor",
        "~": "{prefix}/plug/{idn}",
        "name": "콘센트 {idn} 전력사용량",
        "obj_id": "{prefix}_plug_{idn}_power_usage",
        "dev_cla": "power",
        "stat_t": "~/current/state",
        "unit_of_meas": "W",
    } ],
    "cutoff": [ {
        "_intg": "switch",
        "~": "{prefix}/cutoff/{idn}/power",
        "name": "일괄소등",
        "obj_id": "{prefix}_light_cutoff_{idn}",
        "stat_t": "~/state",
        "cmd_t": "~/command",
    } ],
    "gas_valve": [ {
        "_intg": "switch",
        "~": "{prefix}/gas_valve/{idn}/power",
        "name": "가스밸브",
        "obj_id": "{prefix}_gas_valve_{idn}",
        "stat_t": "~/state",
        "cmd_t": "~/command",
        "icon": "mdi:valve",
    } ],
    "energy": [ {
        "_intg": "sensor",
        "~": "{prefix}/energy/{idn}",
        "name": "{kor} 사용량",
        "obj_id": "{prefix}_{eng}_consumption",
        "stat_t": "~/current/state",
        "unit_of_meas": "_",
        "val_tpl": "_",
    } ],
}

STATE_HEADER = {
    prop["state"]["header"]: (device, prop["state"]["length"] - 2)
    for device, prop in RS485_DEVICE.items()
    if "state" in prop
}
QUERY_HEADER = {
    prop["query"]["header"]: (device, prop["query"]["length"] - 2)
    for device, prop in RS485_DEVICE.items()
    if "query" in prop
}

HEADER_0_STATE = 0xB0
HEADER_0_FIRST = 0xA1
header_0_virtual = {}
HEADER_1_SCAN = 0x5A
header_0_first_candidate = [ 0xAB, 0xAC, 0xAD, 0xAE, 0xC2, 0xA5 ]


# human error를 로그로 찍기 위해서 그냥 전부 구독하자
#SUB_LIST = { "{}/{}/+/+/command".format(Options["mqtt"]["prefix"], device) for device in RS485_DEVICE } |\
#           { "{}/virtual/{}/+/command".format(Options["mqtt"]["prefix"], device) for device in VIRTUAL_DEVICE }

virtual_watch = {}
virtual_trigger = {}
virtual_ack = {}
virtual_avail = []

serial_queue = {}
serial_ack = {}

last_query = int(0).to_bytes(2, "big")
last_topic_list = {}

try:
    from paho.mqtt.enums import CallbackAPIVersion
    mqtt = paho_mqtt.Client(CallbackAPIVersion.VERSION1, client_id="sds_wallpad-{}".format(time.time()))
except Exception as e:
    mqtt = paho_mqtt.Client(client_id="sds_wallpad-{}".format(time.time()))

mqtt_connected = False

logger = logging.getLogger(__name__)


class SDSSerial:
    def __init__(self):
        self._ser = serial.Serial()
        self._ser.port = Options["serial"]["port"]
        self._ser.baudrate = Options["serial"]["baudrate"]
        self._ser.bytesize = Options["serial"]["bytesize"]
        self._ser.parity = Options["serial"]["parity"]
        self._ser.stopbits = Options["serial"]["stopbits"]

        self._ser.close()
        self._ser.open()

        self._pending_recv = 0

        # 시리얼에 뭐가 떠다니는지 확인
        self.set_timeout(5)
        data = self._recv_raw(1)
        self.set_timeout(10)
        if not data:
            raise RuntimeError("no active packet at this serial port!")

    def _recv_raw(self, count=1):
        try:
            return self._ser.read(count)
        except serial.SerialTimeoutException:
            return None
        except Exception as e:
            logger.warning("unhandled exception {}".format(e))

    def recv(self, count=1):
        # serial은 pending count만 업데이트
        self._pending_recv = max(self._pending_recv - count, 0)
        data = self._recv_raw(count)
        if not data or len(data) < count:
            # raise RuntimeError("serial connection lost!")
            logger.info("original: serial connection lost!, but CONTINUE;")
            send_discord_message_with_curl(Options["webhook_url"], "original: serial connection lost!, but CONTINUE;")
            return None
        return data

    def send(self, a):
        self._ser.write(a)

    def set_pending_recv(self):
        self._pending_recv = self._ser.in_waiting

    def check_pending_recv(self):
        return self._pending_recv

    def check_in_waiting(self):
        return self._ser.in_waiting

    def set_timeout(self, a):
        self._ser.timeout = a


class SDSSocket:
    def __init__(self):
        addr = Options["socket"]["address"]
        port = Options["socket"]["port"]

        self._soc = socket.socket()
        self._soc.connect((addr, port))

        self._recv_buf = bytearray()
        self._pending_recv = 0

        # 소켓에 뭐가 떠다니는지 확인
        self.set_timeout(5)
        data = self._recv_raw(1)
        self.set_timeout(10)
        if not data:
            raise RuntimeError("no active packet at this socket!")

    def _recv_raw(self, count=1):
        try:
            return self._soc.recv(count)
        except socket.timeout:
            return None
        except Exception as e:
            logger.warning("unhandled exception {}".format(e))

    def recv(self, count=1):
        # socket은 버퍼와 in_waiting 직접 관리
        while len(self._recv_buf) < count:
            new_data = self._recv_raw(256)
            if not new_data:
                raise RuntimeError("socket connection lost!")
            self._recv_buf.extend(new_data)

        self._pending_recv = max(self._pending_recv - count, 0)

        res = self._recv_buf[0:count]
        del self._recv_buf[0:count]
        return res

    def send(self, a):
        self._soc.sendall(a)

    def set_pending_recv(self):
        self._pending_recv = len(self._recv_buf)

    def check_pending_recv(self):
        return self._pending_recv

    def check_in_waiting(self):
        if len(self._recv_buf) == 0:
            new_data = self._recv_raw(256)
            self._recv_buf.extend(new_data)
        return len(self._recv_buf)

    def set_timeout(self, a):
        self._soc.settimeout(a)


def init_logger():
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(fmt="%(asctime)s %(levelname)-8s %(message)s", datefmt="%H:%M:%S")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def init_logger_file():
    if Options["log"]["to_file"]:
        filename = Options["log"]["filename"]
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        formatter = logging.Formatter(fmt="%(asctime)s %(levelname)-8s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        handler = TimedRotatingFileHandler(os.path.abspath(Options["log"]["filename"]), when="midnight", backupCount=7)
        handler.setFormatter(formatter)
        handler.suffix = '%Y%m%d'
        logger.addHandler(handler)


def init_option(argv):
    # option 파일 선택
    if len(argv) == 1:
        option_file = "./options_standalone.json"
    else:
        option_file = argv[1]

    # configuration이 예전 버전이어도 최대한 동작 가능하도록,
    # 기본값에 해당하는 파일을 먼저 읽고나서 설정 파일로 업데이트 한다.
    global Options

    # 기본값 파일은 .py 와 같은 경로에 있음
    default_file = os.path.join(os.path.dirname(os.path.abspath(argv[0])), "config.json")

    with open(default_file) as f:
        config = json.load(f)
        logger.info("addon version {}".format(config["version"]))
        Options = config["options"]
    with open(option_file) as f:
        Options2 = json.load(f)

    # 업데이트
    for k, v in Options.items():
        if type(v) is dict and k in Options2:
            Options[k].update(Options2[k])
            for k2 in Options[k].keys():
                if k2 not in Options2[k].keys():
                    logger.warning("no configuration value for '{}:{}'! try default value ({})...".format(k, k2, Options[k][k2]))
        else:
            if k not in Options2:
                logger.warning("no configuration value for '{}'! try default value ({})...".format(k, Options[k]))
            else:
                Options[k] = Options2[k]

    # 관용성 확보
    Options["mqtt"]["server"] = re.sub("[a-z]*://", "", Options["mqtt"]["server"])
    if Options["mqtt"]["server"] == "127.0.0.1":
        logger.warning("MQTT server address should be changed!")

    # internal options
    Options["mqtt"]["_discovery"] = Options["mqtt"]["discovery"]


def init_virtual_device():
    global virtual_watch

    if Options["entrance_mode"] != "off":
        if Options["entrance_mode"] == "new":
            ent = "entrance2"
        else:
            ent = "entrance"

        header_0_virtual[VIRTUAL_DEVICE[ent]["header0"]] = ent
        virtual_trigger[ent] = {}

        # 평상시 응답할 항목 등록
        virtual_watch.update({
            (VIRTUAL_DEVICE[ent]["header0"] << 8) + prop["header1"]: prop["resp"].to_bytes(VIRTUAL_DEVICE[ent]["resp_size"], "big")
            for prop in VIRTUAL_DEVICE[ent]["default"].values()
        })

    if Options["entrance_mode"] == "full" or Options["entrance_mode"] == "new":
        # full 모드에서 일괄소등 지원 안함
        STATE_HEADER.pop(RS485_DEVICE["cutoff"]["state"]["header"])
        RS485_DEVICE.pop("cutoff")

    if Options["intercom_mode"] == "on":
        VIRTUAL_DEVICE["intercom"]["header0"] = int(Options["rs485"]["intercom_header"][:2], 16)

        header_0_virtual[VIRTUAL_DEVICE["intercom"]["header0"]] = "intercom"
        virtual_trigger["intercom"] = {}

        # 평상시 응답할 항목 등록
        virtual_watch.update({
            (VIRTUAL_DEVICE["intercom"]["header0"] << 8) + prop["header1"]: prop["resp"].to_bytes(4, "big")
            for prop in VIRTUAL_DEVICE["intercom"]["default"].values()
        })

        # availability 관련
        for header_1 in (0x31, 0x32, 0x36, 0x3E):
            virtual_avail.append((VIRTUAL_DEVICE["intercom"]["header0"] << 8) + header_1)

        # delay 옵션 적용
        if Options["rs485"]["intercom_delay"]:
            VIRTUAL_DEVICE["intercom"]["trigger"]["public"]["next"] = ("pubdelay1", "ON")


def mqtt_discovery(payload):
    intg = payload.pop("_intg")

    # MQTT 통합구성요소에 등록되기 위한 추가 내용
    payload["device"] = DISCOVERY_DEVICE
    payload["uniq_id"] = payload["obj_id"]

    # discovery에 등록
    topic = "homeassistant/{}/sds_wallpad/{}/config".format(intg, payload["uniq_id"])
    logger.info("Add new device:  {}".format(topic))
    mqtt.publish(topic, json.dumps(payload))


def mqtt_add_virtual():
    # 현관스위치 장치 등록
    if Options["entrance_mode"] != "off":
        if Options["entrance_mode"] == "new":
            ent = "entrance2"
        else:
            ent = "entrance"

        prefix = Options["mqtt"]["prefix"]
        for payloads in DISCOVERY_VIRTUAL[ent]:
            payload = payloads.copy()
            payload["~"] = payload["~"].format(prefix=prefix)
            payload["obj_id"] = payload["obj_id"].format(prefix=prefix)

            mqtt_discovery(payload)

    # 인터폰 장치 등록
    if Options["intercom_mode"] != "off":
        prefix = Options["mqtt"]["prefix"]
        for payloads in DISCOVERY_VIRTUAL["intercom"]:
            payload = payloads.copy()
            payload["~"] = payload["~"].format(prefix=prefix)
            payload["obj_id"] = payload["obj_id"].format(prefix=prefix)

            mqtt_discovery(payload)


def mqtt_init_virtual():
    # 현관스위치 초기 상태 설정
    if Options["entrance_mode"] != "off":
        if Options["entrance_mode"] == "new":
            ent = "entrance2"
        else:
            ent = "entrance"

        prefix = Options["mqtt"]["prefix"]
        for payloads in DISCOVERY_VIRTUAL[ent]:
            payload = payloads.copy()
            payload["~"] = payload["~"].format(prefix=prefix)
            topic = payload["~"] + "/state"
            logger.info("initial state:   {} = OFF".format(topic))
            mqtt.publish(topic, "OFF")

    # 인터폰 초기 상태 설정
    if Options["intercom_mode"] != "off":
        prefix = Options["mqtt"]["prefix"]

        for payloads in DISCOVERY_VIRTUAL["intercom"]:
            payload = payloads.copy()
            payload["~"] = payload["~"].format(prefix=prefix)
            topic = payload["~"] + "/state"
            logger.info("initial state:   {} = OFF".format(topic))
            mqtt.publish(topic, "OFF")

        # 초인종 울리기 전까지 문열림 스위치 offline으로 설정
        payload = "offline"
        topic = "{}/virtual/intercom/public/available".format(prefix)
        logger.info("doorlock state:  {} = {}".format(topic, payload))
        mqtt.publish(topic, payload)
        topic = "{}/virtual/intercom/private/available".format(prefix)
        logger.info("doorlock state:  {} = {}".format(topic, payload))
        mqtt.publish(topic, payload)


def mqtt_virtual(topics, payload):
    device = topics[2]
    trigger = topics[3]
    triggers = VIRTUAL_DEVICE[device]["trigger"]

    # HA에서 잘못 보내는 경우 체크
    if len(topics) != 5:
        logger.error("    invalid topic length!"); return
    if trigger not in triggers:
        logger.error("    invalid trigger!"); return

    # OFF가 없는데(ev, gas) OFF가 오면, 이전 ON 명령의 시도 중지
    if payload not in triggers[trigger]:
        virtual_pop(device, trigger, "ON")
        return

    # 오류 체크 끝났으면 queue 에 넣어둠
    virtual_trigger[device][(trigger, payload)] = time.time()

    # ON만 있는 명령은, 명령이 queue에 있는 동안 switch를 ON으로 표시
    prefix = Options["mqtt"]["prefix"]
    if "OFF" not in triggers[trigger]:
        topic = "{}/virtual/{}/{}/state".format(prefix, device, trigger)
        logger.info("publish to HA:   {} = {}".format(topic, "ON"))
        mqtt.publish(topic, "ON")

    # ON/OFF 있는 명령은, 마지막으로 받은 명령대로 표시
    else:
        topic = "{}/virtual/{}/{}/state".format(prefix, device, trigger)
        logger.info("publish to HA:   {} = {}".format(topic, payload))
        mqtt.publish(topic, payload)

    # 그동안 조용히 있었어도, 이젠 가로채서 응답해야 함
    if device == "entrance" and Options["entrance_mode"] == "minimal":
        query = VIRTUAL_DEVICE["entrance"]["default"]["query"]
        virtual_watch[query["header"]] = query["resp"]


def mqtt_debug(topics, payload):
    group = topics[2]
    command = topics[3]

    if (group == "packet"):
        if (command == "send"):
            try:
                packet = bytearray.fromhex(payload)
            except Exception as e:
                logger.warning("    failed to convert: {}".format(payload))
                return

            # parity는 여기서 재생성
            packet[-1] = serial_generate_checksum(packet)
            packet = bytes(packet)

            logger.info("prepare packet:  {}".format(packet.hex()))
            serial_queue[packet] = time.time()
            return

    logger.warning("    unknown debug topic: {}".format(topics))


def mqtt_device(topics, payload):
    device = topics[1]
    idn = topics[2]
    cmd = topics[3]

    # HA에서 잘못 보내는 경우 체크
    if device not in RS485_DEVICE:
        logger.error("    unknown device!"); return
    if cmd not in RS485_DEVICE[device]:
        logger.error("    unknown command!"); return
    if payload == "":
        logger.error("    no payload!"); return
    if device == "gas_valve" and payload == "ON":
        logger.error("    gas valves cannot be opened remotely!"); return

    # 문자열 payload를 패킷으로 변환
    payloads = {
        "ON": 1, "OFF": 0,
        "heat": 1, "off": 0, # 난방
        "low": 3, "medium": 2, "high": 1, "auto": 4, # 환기
    }

    if payload in payloads:
        payload = payloads[payload]

    # 오류 체크 끝났으면 serial 메시지 생성
    cmd = RS485_DEVICE[device][cmd]

    packet = bytearray(cmd["length"])
    packet[0] = cmd["header"] >> 8
    packet[1] = cmd["header"] & 0xFF

    if "pos" in cmd: packet[cmd["pos"]] = int(float(payload))
    if "id" in cmd: packet[cmd["id"]] = int(idn)

    # parity 생성 후 queue 에 넣어둠
    packet[-1] = serial_generate_checksum(packet)
    packet = bytes(packet)

    serial_queue[packet] = time.time()


def mqtt_init_discovery():
    # HA가 재시작됐을 때 모든 discovery를 다시 수행한다
    Options["mqtt"]["_discovery"] = Options["mqtt"]["discovery"]
    mqtt_add_virtual()

    mqtt_init_state()


def mqtt_init_state():
    for device in RS485_DEVICE:
        RS485_DEVICE[device]["last"] = {}

    global last_topic_list
    last_topic_list = {}

    mqtt_init_virtual()


def mqtt_on_message(mqtt, userdata, msg):
    topics = msg.topic.split("/")
    payload = msg.payload.decode()

    logger.info("recv. from HA:   {} = {}".format(msg.topic, payload))

    device = topics[1]
    if device == "status":
        if payload == "online":
            mqtt_init_discovery()
    elif device == "virtual":
        mqtt_virtual(topics, payload)
    elif device == "debug":
        mqtt_debug(topics, payload)
    else:
        mqtt_device(topics, payload)


def mqtt_on_connect(mqtt, userdata, flags, rc):
    if rc == 0:
        logger.info("MQTT connect successful!")
        global mqtt_connected
        mqtt_connected = True
    else:
        logger.error("MQTT connection return with:  {}".format(paho_mqtt.connack_string(rc)))

    mqtt_init_discovery()

    topic = "homeassistant/status"
    logger.info("subscribe {}".format(topic))
    mqtt.subscribe(topic, 0)

    prefix = Options["mqtt"]["prefix"]

    topic = "{}/debug/#".format(prefix)
    logger.info("subscribe {}".format(topic))
    mqtt.subscribe(topic, 0)

    if Options["entrance_mode"] != "off" or Options["intercom_mode"] != "off":
        topic = "{}/virtual/+/+/command".format(prefix)
        logger.info("subscribe {}".format(topic))
        mqtt.subscribe(topic, 0)

    if Options["wallpad_mode"] != "off":
        topic = "{}/+/+/+/command".format(prefix)
        logger.info("subscribe {}".format(topic))
        mqtt.subscribe(topic, 0)


def mqtt_on_disconnect(mqtt, userdata, rc):
    logger.warning("MQTT disconnected! ({})".format(rc))
    global mqtt_connected
    mqtt_connected = False


def start_mqtt_loop():
    logger.info("initialize mqtt...")

    mqtt.on_message = mqtt_on_message
    mqtt.on_connect = mqtt_on_connect
    mqtt.on_disconnect = mqtt_on_disconnect

    if Options["mqtt"]["need_login"]:
        mqtt.username_pw_set(Options["mqtt"]["user"], Options["mqtt"]["passwd"])

    try:
        mqtt.connect(Options["mqtt"]["server"], Options["mqtt"]["port"])
    except Exception as e:
        raise AssertionError("MQTT server address/port may be incorrect! ({})".format(str(e)))

    mqtt.loop_start()

    delay = 1
    while not mqtt_connected:
        logger.info("waiting MQTT connected ...")
        time.sleep(delay)
        delay = min(delay * 2, 10)


def virtual_enable(header_0, header_1):
    prefix = Options["mqtt"]["prefix"]

    # 마무리만 하드코딩으로 좀 하자... 슬슬 귀찮다
    if header_1 == 0x32:
        payload = "online"
        topic = "{}/virtual/intercom/public/available".format(prefix)
        logger.info("doorlock status: {} = {}".format(topic, payload))
        mqtt.publish(topic, payload)

    elif header_1 == 0x31:
        payload = "online"
        topic = "{}/virtual/intercom/private/available".format(prefix)
        logger.info("doorlock status: {} = {}".format(topic, payload))
        mqtt.publish(topic, payload)

        VIRTUAL_DEVICE["intercom"]["trigger"]["private"] = VIRTUAL_DEVICE["intercom"]["trigger"]["priv_a"]

    elif header_1 == 0x36 or header_1 == 0x3E:
        payload = "offline"
        topic = "{}/virtual/intercom/public/available".format(prefix)
        logger.info("doorlock status: {} = {}".format(topic, payload))
        mqtt.publish(topic, payload)
        topic = "{}/virtual/intercom/private/available".format(prefix)
        logger.info("doorlock status: {} = {}".format(topic, payload))
        mqtt.publish(topic, payload)
        VIRTUAL_DEVICE["intercom"]["trigger"]["private"] = VIRTUAL_DEVICE["intercom"]["trigger"]["priv_b"]


def virtual_pop(device, trigger, cmd):
    query = VIRTUAL_DEVICE[device]["default"]["query"]
    triggers = VIRTUAL_DEVICE[device]["trigger"]

    virtual_trigger[device].pop((trigger, cmd), None)
    virtual_ack.pop((VIRTUAL_DEVICE[device]["header0"] << 8) + triggers[trigger]["ack"], None)

    # 명령이 queue에서 빠지면 OFF로 표시
    prefix = Options["mqtt"]["prefix"]
    topic = "{}/virtual/{}/{}/state".format(prefix, device, trigger)
    logger.info("publish to HA:   {} = {}".format(topic, "OFF"))
    mqtt.publish(topic, "OFF")

    # minimal 모드일 때, 조용해질지 여부
    if not virtual_trigger[device] and Options["entrance_mode"] == "minimal":
        entrance_watch.pop(query["header"], None)


def virtual_query(header_0, header_1):
    device = header_0_virtual[header_0]
    query = VIRTUAL_DEVICE[device]["default"]["query"]["header1"]
    triggers = VIRTUAL_DEVICE[device]["trigger"]
    resp_size = VIRTUAL_DEVICE[device]["resp_size"]

    # pending이 남은 상태면 지금 시도해봐야 가망이 없음
    if conn.check_pending_recv():
        return

    # 아직 4~5Byte 중 2Byte만 받았으므로 다 올때까지 기다리는게 정석 같지만,
    # 조금 일찍 시작하는게 성공률이 더 높은거 같기도 하다.
    length = resp_size - 2 - int(Options["rs485"]["early_response"])
    if length > 0:
        while conn.check_in_waiting() < length: pass

    if virtual_trigger[device] and header_1 == query:
        # 하나 뽑아서 보내봄
        trigger, cmd = next(iter(virtual_trigger[device]))
        resp = triggers[trigger][cmd].to_bytes(resp_size, "big")
        conn.send(resp)

        # retry time 관리, 초과했으면 제거
        elapsed = time.time() - virtual_trigger[device][trigger, cmd]
        if elapsed > Options["rs485"]["max_retry"]:
            logger.error("send to wallpad: {} max retry time exceeded!".format(resp.hex()))
            virtual_pop(device, trigger, cmd)
        elif elapsed > 3:
            logger.warning("send to wallpad: {}, try another {:.01f} seconds...".format(resp.hex(), Options["rs485"]["max_retry"] - elapsed))
            virtual_ack[(header_0 << 8) + triggers[trigger]["ack"]] = (device, trigger, cmd)
        else:
            logger.info("send to wallpad: {}".format(resp.hex()))
            virtual_ack[(header_0 << 8) + triggers[trigger]["ack"]] = (device, trigger, cmd)

    # full 모드일 때, 일상 응답
    else:
        header = (header_0 << 8) | header_1
        if header in virtual_watch:
            resp = virtual_watch[header]

            # Byte[2] 가 wallpad를 따라가야 하는 경우
            if resp[2] == 0xFF:
                ba = bytearray(resp)
                ba[2] = conn.recv(1)[0]
                ba[3] = serial_generate_checksum(ba)
                resp = bytes(ba)

            conn.send(resp)


def virtual_clear(header):
    logger.info("ack frm wallpad: {}".format(hex(header)))

    device, trigger, cmd = virtual_ack[header]
    triggers = VIRTUAL_DEVICE[device]["trigger"]

    # 성공한 명령을 지움
    virtual_pop(*virtual_ack[header])
    virtual_ack.pop(header, None)

    # 다음 트리거로 이어지면 추가
    if triggers[trigger]["next"] != None:
        next_trigger = triggers[trigger]["next"]
        virtual_trigger[device][next_trigger] = time.time()


def serial_verify_checksum(packet):
    # 모든 byte를 XOR
    checksum = 0
    for b in packet:
        checksum ^= b

    # parity의 최상위 bit는 항상 0
    if checksum >= 0x80: checksum -= 0x80

    # checksum이 안맞으면 로그만 찍고 무시
    if checksum:
        # logger.warning("checksum fail! {}, {:02x}".format(packet.hex(), checksum))
        return False

    # 정상
    return True


def serial_generate_checksum(packet):
    # 마지막 제외하고 모든 byte를 XOR
    checksum = 0
    for b in packet[:-1]:
        checksum ^= b

    # parity의 최상위 bit는 항상 0
    if checksum >= 0x80: checksum -= 0x80

    return checksum


def serial_peek_value(parse, packet):
    attr, pos, pattern = parse
    value = packet[pos]

    if pattern == "bitmap":
        res = []
        for i in range(1, 8+1):
            res += [("{}{}".format(attr, i), "ON" if value & 1 else "OFF")]
            value >>= 1
        return res
    elif pattern == "toggle":
        value = "ON" if value & 1 else "OFF"
    elif pattern == "invert":
        value = "OFF" if value & 1 else "ON"
    elif pattern == "toggle2":
        value = "ON" if value & 0x10 else "OFF"
    elif pattern == "fan_toggle":
        value = 5 if value == 0 else 6
    elif pattern == "fan_speed":
        value = ["", "high", "medium", "low", "auto"][value] if 0 <= value <= 4 else ""
    elif pattern == "heat_toggle":
        value = "heat" if value & 1 else "off"
    elif pattern == "value":
        pass
    elif pattern == "2Byte":
        value += packet[pos-1] << 8
    elif pattern == "6decimal":
        value = packet[pos : pos+3].hex()

    return [(attr, value)]


def serial_new_device(device, idn, packet):
    prefix = Options["mqtt"]["prefix"]

    # 조명은 두 id를 조합해서 개수와 번호를 정해야 함
    if device == "light":
        id2 = last_query[3]
        num = idn >> 4
        try:
            idn = int("{:x}".format(idn))
        except:
            logger.warning("invalid packet, light room number {} is not decimal".format(idn))

        for bit in range(0, num):
            payload = DISCOVERY_PAYLOAD[device][0].copy()
            payload["~"] = payload["~"].format(prefix=prefix, idn=idn)
            payload["name"] = payload["name"].format(id2=id2)
            payload["obj_id"] = payload["obj_id"].format(prefix=prefix, id2=id2+bit)
            payload["stat_t"] = payload["stat_t"].format(idn=idn, bit=bit+1)
            payload["cmd_t"] = payload["cmd_t"].format(id2=id2+bit)

            mqtt_discovery(payload)

    elif device in DISCOVERY_PAYLOAD:
        for payloads in DISCOVERY_PAYLOAD[device]:
            payload = payloads.copy()
            payload["~"] = payload["~"].format(prefix=prefix, idn=idn)

            if device != "energy":
                payload["name"] = payload["name"].format(idn=idn)
                payload["obj_id"] = payload["obj_id"].format(prefix=prefix, idn=idn)
            else:
                # 실시간 에너지 사용량에는 적절한 이름과 단위를 붙여준다 (단위가 없으면 그래프로 출력이 안됨)
                eng = ("power", "gas", "water")[idn]
                kor = ("전기", "가스", "수도")[idn]
                payload["name"] = payload["name"].format(kor=kor)
                payload["obj_id"] = payload["obj_id"].format(prefix=prefix, eng=eng)
                payload["unit_of_meas"] = ("W", "m³/h", "m³/h")[idn]
                payload["val_tpl"] = "{{{{ value | float / {} }}}}".format(10 ** Options["rs485"]["{}_decimal".format(eng)])
                if idn == 0:
                    payload["dev_cla"] = "power"

            mqtt_discovery(payload)


def serial_receive_state(device, packet):
    form = RS485_DEVICE[device]["state"]
    last = RS485_DEVICE[device]["last"]

    if form.get("id") != None:
        idn = packet[form["id"]]
    else:
        idn = 1

    # 해당 ID의 이전 상태와 같은 경우 바로 무시
    if last.get(idn) == packet:
        return

    # 처음 받은 상태인 경우, discovery 용도로 등록한다.
    if Options["mqtt"]["_discovery"] and not last.get(idn):
        # 전등 때문에 last query도 필요... 지금 패킷과 일치하는지 검증
        # gas valve는 일치하지 않는다
        if last_query[1] == packet[1] or device == "gas_valve":
            serial_new_device(device, idn, packet)
            last[idn] = True

        # 장치 등록 먼저 하고, 상태 등록은 그 다음 턴에 한다. (난방 상태 등록 무시되는 현상 방지)
        return

    else:
        last[idn] = packet

    # device 종류에 따라 전송할 데이터 정리
    value_list = []
    for parse in form["parse"]:
        value_list += serial_peek_value(parse, packet)

    # MQTT topic 형태로 변환, 이전 상태와 같은지 한번 더 확인해서 무시하거나 publish
    for attr, value in value_list:
        prefix = Options["mqtt"]["prefix"]
        topic = "{}/{}/{:x}/{}/state".format(prefix, device, idn, attr)
        if value == "" or last_topic_list.get(topic) == value: continue

        if attr != "current":  # 전력사용량이나 현재온도는 너무 자주 바뀌어서 로그 제외
            logger.info("publish to HA:   {} = {} ({})".format(topic, value, packet.hex()))
        mqtt.publish(topic, value)
        last_topic_list[topic] = value


def serial_get_header():
    try:
        # 0x80보다 큰 byte가 나올 때까지 대기
        while 1:
            header_0 = conn.recv(1)[0]
            if header_0 >= 0x80: break

        # 중간에 corrupt되는 data가 있으므로 연속으로 0x80보다 큰 byte가 나오면 먼젓번은 무시한다
        while 1:
            header_1 = conn.recv(1)[0]
            if header_1 < 0x80: break
            header_0 = header_1

    except (OSError, serial.SerialException):
        logger.warning("ignore exception {}".format(e))
        header_0 = header_1 = 0

    # 헤더 반환
    return header_0, header_1


def serial_ack_command(packet):
    logger.info("ack from device: {} ({:x})".format(serial_ack[packet].hex(), packet))

    # 성공한 명령을 지움
    serial_queue.pop(serial_ack[packet], None)
    serial_ack.pop(packet)


def serial_send_command():
    # 한번에 여러개 보내면 응답이랑 꼬여서 망함
    cmd = next(iter(serial_queue))
    conn.send(cmd)

    ack = bytearray(cmd[0:3])
    ack[0] = 0xB0
    ack = int.from_bytes(ack, "big")

    # retry time 관리, 초과했으면 제거
    elapsed = time.time() - serial_queue[cmd]
    if elapsed > Options["rs485"]["max_retry"]:
        logger.error("send to device:  {} max retry time exceeded!".format(cmd.hex()))
        serial_queue.pop(cmd)
        serial_ack.pop(ack, None)
    elif elapsed > 3:
        logger.warning("send to device:  {}, try another {:.01f} seconds...".format(cmd.hex(), Options["rs485"]["max_retry"] - elapsed))
        serial_ack[ack] = cmd
    else:
        logger.info("send to device:  {}".format(cmd.hex()))
        serial_ack[ack] = cmd


def serial_loop():
    logger.info("start loop ...")
    loop_count = 0
    scan_count = 0
    send_aggressive = False

    start_time = time.time()
    while True:
        # 로그 출력
        sys.stdout.flush()

        # 첫 Byte만 0x80보다 큰 두 Byte를 찾음
        header_0, header_1 = serial_get_header()
        header = (header_0 << 8) | header_1

        # 요청했던 동작의 ack 왔는지 확인
        if header in virtual_ack:
            virtual_clear(header)

        # 인터폰 availability 관련 헤더인지 확인
        if header in virtual_avail:
            virtual_enable(header_0, header_1)

        # 가상 장치로써 응답해야 할 header인지 확인
        if header_0 in header_0_virtual:
            virtual_query(header_0, header_1)

        # device로부터의 state 응답이면 확인해서 필요시 HA로 전송해야 함
        if header in STATE_HEADER:
            packet = bytes([header_0, header_1])

            # 몇 Byte짜리 패킷인지 확인
            device, remain = STATE_HEADER[header]

            # 해당 길이만큼 읽음
            packet += conn.recv(remain)

            # checksum 오류 없는지 확인
            if not serial_verify_checksum(packet):
                continue

            # 디바이스 응답 뒤에도 명령 보내봄
            if serial_queue and not conn.check_pending_recv():
                serial_send_command()
                conn.set_pending_recv()

            # 적절히 처리한다
            serial_receive_state(device, packet)

        elif header_0 == HEADER_0_STATE:
            # 한 byte 더 뽑아서, 보냈던 명령의 ack인지 확인
            header_2 = conn.recv(1)[0]
            header = (header << 8) | header_2

            if header in serial_ack:
                serial_ack_command(header)

        # 마지막으로 받은 query를 저장해둔다 (조명 discovery에 필요)
        elif header in QUERY_HEADER:
            # 나머지 더 뽑아서 저장
            global last_query
            packet = conn.recv(QUERY_HEADER[header][1])
            packet = header.to_bytes(2, "big") + packet
            last_query = packet

        # 명령을 보낼 타이밍인지 확인: 0xXX5A 는 장치가 있는지 찾는 동작이므로,
        # 아직도 이러고 있다는건 아무도 응답을 안할걸로 예상, 그 타이밍에 끼어든다.
        if header_1 == HEADER_1_SCAN or send_aggressive:
            scan_count += 1
            if serial_queue and not conn.check_pending_recv():
                serial_send_command()
                conn.set_pending_recv()

        # 전체 루프 수 카운트
        global HEADER_0_FIRST
        if header_0 == HEADER_0_FIRST:
            loop_count += 1

            # 돌만큼 돌았으면 상황 판단
            if loop_count == 30:
                # discovery: 가끔 비트가 튈때 이상한 장치가 등록되는걸 막기 위해, 시간제한을 둠
                if Options["mqtt"]["_discovery"]:
                    logger.info("Add new device:  All done.")
                    Options["mqtt"]["_discovery"] = False

                    # discovery 속도 문제로 HA에 초기 상태 등록 안되는 경우 있어서, 한번 재등록
                    mqtt_init_state()

                else:
                    logger.info("running stable...")

                # 스캔이 없거나 적으면, 명령을 내릴 타이밍을 못잡는걸로 판단, 아무때나 닥치는대로 보내봐야한다.
                if Options["serial_mode"] == "serial" and scan_count < 30:
                    logger.warning("initiate aggressive send mode!", scan_count)
                    send_aggressive = True

            # HA 재시작한 경우
            elif loop_count > 30 and Options["mqtt"]["_discovery"]:
                loop_count = 1

        # 루프 카운트 세는데 실패하면 다른 걸로 시도해봄
        if loop_count == 0 and time.time() - start_time > 6:
            logger.warning("check loop count fail: there are no {:X}! try {:X}...".format(HEADER_0_FIRST, header_0_first_candidate[-1]))
            HEADER_0_FIRST = header_0_first_candidate.pop()
            start_time = time.time()
            scan_count = 0


def dump_loop():
    dump_time = Options["rs485"]["dump_time"]

    if dump_time > 0:
        if dump_time < 10:
            logger.warning("dump_time is too short! automatically changed to 10 seconds...")
            dump_time = 10

        start_time = time.time()
        logger.warning("packet dump for {} seconds!".format(dump_time))

        conn.set_timeout(2)
        logs = []
        while time.time() - start_time < dump_time:
            try:
                data = conn.recv(256)
            except:
                continue

            if data:
                for b in data:
                    if b == 0xA1 or len(logs) > 500:
                        logger.info("".join(logs))
                        logs = ["{:02X}".format(b)]
                    elif b <= 0xA0: logs.append(   "{:02X}".format(b))
                    elif b == 0xFF: logs.append(   "{:02X}".format(b))
                    elif b == 0xB0: logs.append( ": {:02X}".format(b))
                    else:           logs.append(",  {:02X}".format(b))
        logger.info("".join(logs))
        logger.warning("dump done.")
        conn.set_timeout(10)

def restart_addon():
    supervisor_token = os.getenv("SUPERVISOR_TOKEN")
    url = "http://supervisor/addons/self/restart"
    headers = {"Authorization": f"Bearer {supervisor_token}"}

    req = urllib.request.Request(url, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                print("Addon restart triggered successfully.")
            else:
                print(f"Failed to restart addon: {response.status}")
    except Exception as e:
        print(f"Error occurred: {e}")

def send_discord_message_with_curl(webhook_url, message):
    # curl 명령어 구성
    curl_command = [
        "curl", "-X", "POST",
        "-H", "Content-Type: application/json",
        "-d", f'{{"content":"{message}"}}',
        webhook_url
    ]
    
    try:
        # curl 명령 실행
        result = subprocess.run(curl_command, capture_output=True, text=True, check=True)
        logger.info("Message sent successfully via curl!")
    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to send message via curl: {e.stderr}")
    except Exception as e:
        logger.warning(f"Unexpected error while sending message via curl: {e}")

def conn_init():
    global conn

    if Options["serial_mode"] == "socket":
        logger.info("initialize socket...")
        conn = SDSSocket()
    else:
        logger.info("initialize serial...")
        conn = SDSSerial()

if __name__ == "__main__":
    # configuration 로드 및 로거 설정
    init_logger()
    init_option(sys.argv)
    init_logger_file()

    init_virtual_device()

    send_discord_message_with_curl(Options["webhook_url"], "Addon started.")
    
    while True:
        try:
            conn_init()
            dump_loop()
            start_mqtt_loop()

            # 무한 루프
            serial_loop()

        except RuntimeError as e:
            error_msg = f"RuntimeError occurred: {e} - Restarting addon."
            logger.warning(error_msg)
            send_discord_message_with_curl(Options["webhook_url"], error_msg)
            restart_addon()
            # time.sleep(2)
        except Exception as e:
            logger.exception("addon exception! ({})".format(str(e)))
            sys.exit(1)
