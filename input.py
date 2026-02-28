# input_winapi_simple.py
"""
Input Manager using Windows API - Simplified version
Only supports WSADQE and arrow keys and space
"""

import time
import logging
import ctypes
import ctypes.wintypes
from typing import Optional

logger = logging.getLogger(__name__)

# Windows API 结构体定义
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.wintypes.WORD),
        ("wScan", ctypes.wintypes.WORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
    ]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.wintypes.LONG),
        ("dy", ctypes.wintypes.LONG),
        ("mouseData", ctypes.wintypes.DWORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.wintypes.DWORD),
        ("wParamL", ctypes.wintypes.WORD),
        ("wParamH", ctypes.wintypes.WORD)
    ]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki", KEYBDINPUT),
        ("mi", MOUSEINPUT),
        ("hi", HARDWAREINPUT)
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.wintypes.DWORD),
        ("union", _INPUT_UNION)
    ]

# Windows API 常量
INPUT_KEYBOARD = 1
KEYEVENTF_KEYDOWN = 0x0000
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

# 虚拟键码映射（添加空格键）
VK_MAP = {
    # WASD
    'w': 0x57,  # VK_W
    'a': 0x41,  # VK_A
    's': 0x53,  # VK_S
    'd': 0x44,  # VK_D
    
    # QE
    'q': 0x51,  # VK_Q
    'e': 0x45,  # VK_E
    
    # 方向键
    'up': 0x26,     # VK_UP
    'down': 0x28,   # VK_DOWN
    'left': 0x25,   # VK_LEFT
    'right': 0x27,  # VK_RIGHT
    
    # 【新增】空格键
    'space': 0x20,  # VK_SPACE
}

class InputManager:
    """键盘输入管理器 - 使用 Windows API"""
    
    def __init__(self):
        """初始化输入管理器"""
        # 键盘键映射
        self.key_mapping = {
            # WASD 移动
            'MOVE_LEFT': 'a',
            'MOVE_RIGHT': 'd', 
            'MOVE_UP': 'w',
            'MOVE_DOWN': 's',
            
            # QE 旋转/特殊
            'Q': 'q',
            'E': 'e',
            
            # 方向键
            'ARROW_UP': 'up',
            'ARROW_DOWN': 'down',
            'ARROW_LEFT': 'left',
            'ARROW_RIGHT': 'right',
            
            # 【新增】空格键
            'SPACE': 'space',
        }
        
        # 加载 Windows API
        self.user32 = ctypes.WinDLL('user32', use_last_error=True)
        
        # 设置 SendInput 函数原型
        self.user32.SendInput.argtypes = [
            ctypes.wintypes.UINT,  # nInputs
            ctypes.POINTER(INPUT), # pInputs  
            ctypes.c_int           # cbSize
        ]
        self.user32.SendInput.restype = ctypes.wintypes.UINT
        
        logger.info("Windows API 输入管理器已初始化")
    
    def _send_key(self, vk_code: int, key_down: bool = True):
        """发送单个键盘事件"""
        # 创建输入结构
        extra = ctypes.c_ulong(0)
        ii = INPUT()
        
        ii.type = INPUT_KEYBOARD
        ii.union.ki = KEYBDINPUT()
        ii.union.ki.wVk = vk_code
        ii.union.ki.wScan = 0
        ii.union.ki.dwFlags = KEYEVENTF_KEYDOWN if key_down else KEYEVENTF_KEYUP
        ii.union.ki.time = 0
        ii.union.ki.dwExtraInfo = ctypes.pointer(extra)
        
        # 发送输入
        result = self.user32.SendInput(1, ctypes.pointer(ii), ctypes.sizeof(ii))
        
        if result != 1:
            logger.error(f"发送按键事件失败: 虚拟键码 {vk_code:02X}, 状态 {'按下' if key_down else '释放'}")
            return False
        return True
    
    def press_key(self, key: str, duration: Optional[float] = 0.1):
        """按下并释放一个键"""
        try:
            if key not in VK_MAP:
                logger.error(f"不支持的键: {key}")
                return False
            
            vk_code = VK_MAP[key]
            logger.debug(f"按下键: {key} (虚拟键码: {vk_code:02X}), 持续时间: {duration}s")
            
            # 按下键
            if not self._send_key(vk_code, True):
                return False
            
            # 保持按下状态
            time.sleep(duration)
            
            # 释放键
            if not self._send_key(vk_code, False):
                return False
            
            logger.debug(f"按键完成: {key}")
            return True
            
        except Exception as e:
            logger.error(f"按键失败 {key}: {e}")
            return False
    
    def execute_action(self, action_name: str, duration: Optional[float] = 0.1):
        """执行命名的动作"""
        if action_name in self.key_mapping:
            key = self.key_mapping[action_name]
            return self.press_key(key, duration)
        else:
            logger.warning(f"未知动作: {action_name}")
            return False
    
    def press_multiple(self, keys: list, duration: Optional[float] = 0.1):
        """同时按下多个键"""
        try:
            # 按下所有键
            for key in keys:
                if key in VK_MAP:
                    vk_code = VK_MAP[key]
                    self._send_key(vk_code, True)
            
            # 保持状态
            time.sleep(duration)
            
            # 释放所有键
            for key in reversed(keys):
                if key in VK_MAP:
                    vk_code = VK_MAP[key]
                    self._send_key(vk_code, False)
            
            return True
        except Exception as e:
            logger.error(f"多键按下失败: {e}")
            return False