# action_mapper.py (修正版本)
"""
动作映射器 - 将RL动作ID转换为Windows API按键
修正：完整支持移动(WASD)和射击(方向键)
增强版：支持更多组合动作 (0-14)
"""
import sys
import os
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from input import InputManager

class ActionMapper:
    def __init__(self):
        self.input = InputManager()
        
        # ============ 按键映射定义 ============
        # 移动键映射 (WASD)
        self.move_keys = {
            'up': 'w',
            'down': 's',
            'left': 'a',
            'right': 'd'
        }
        
        # 射击键映射 (方向键)
        self.shoot_keys = {
            'up': 'up',
            'down': 'down',
            'left': 'left',
            'right': 'right'
        }
        
        # ============ 扩展动作空间 (0-14) ============
        self.actions = {
            # 动作0: 静止
            0: {'move': None, 'shoot': None, 'special': None},
            
            # 动作1-4: 纯移动 (WASD)
            1: {'move': 'up', 'shoot': None},      # 向上移动 (W)
            2: {'move': 'down', 'shoot': None},    # 向下移动 (S)
            3: {'move': 'left', 'shoot': None},    # 向左移动 (A)
            4: {'move': 'right', 'shoot': None},   # 向右移动 (D)
            
            # 动作5-8: 纯射击 (方向键)
            5: {'move': None, 'shoot': 'up'},      # 向上射击 (↑)
            6: {'move': None, 'shoot': 'down'},    # 向下射击 (↓)
            7: {'move': None, 'shoot': 'left'},    # 向左射击 (←)
            8: {'move': None, 'shoot': 'right'},   # 向右射击 (→)
            
            # 动作9-10: 特殊动作
            9: {'special': 'q'},   # 使用主动道具
            10: {'special': 'e'},  # 放置炸弹
            
            # 动作11-14: 组合动作（移动+射击同方向）
            11: {'move': 'up', 'shoot': 'up'},     # W + ↑
            12: {'move': 'down', 'shoot': 'down'}, # S + ↓
            13: {'move': 'left', 'shoot': 'left'}, # A + ←
            14: {'move': 'right', 'shoot': 'right'}, # D + →
        }
        
        # 动作名称映射（用于调试）
        self.action_names = {
            0: "静止",
            1: "向上移动 (W)",
            2: "向下移动 (S)",
            3: "向左移动 (A)",
            4: "向右移动 (D)",
            5: "向上射击 (↑)",
            6: "向下射击 (↓)",
            7: "向左射击 (←)",
            8: "向右射击 (→)",
            9: "使用道具 (Q)",
            10: "放置炸弹 (E)",
            11: "上移+上射 (W+↑)",
            12: "下移+下射 (S+↓)",
            13: "左移+左射 (A+←)",
            14: "右移+右射 (D+→)",
        }
        
        print("✅ 动作映射器初始化完成")
        print(f"   - 动作空间大小: {len(self.actions)}")
        print(f"   - 支持组合动作: 11-14 (移动+射击)")
    
    def execute(self, action_id, duration=1/60):
        """
        执行动作
        
        Args:
            action_id: 0-14 (动作ID)
            duration: 按键持续时间（默认1帧=16.67ms）
        
        Returns:
            bool: 是否执行成功
        """
        if action_id not in self.actions:
            print(f"⚠️ 警告: 未知动作ID {action_id}")
            return False
        
        action = self.actions[action_id]
        
        try:
            # ============ 情况1: 特殊动作 ============
            if action.get('special'):
                key = action['special']  # 'q' 或 'e'
                print(f"🔹 执行特殊动作 {action_id}: {key}")
                return self.input.press_key(key, duration)
            
            # ============ 情况2: 移动 + 射击组合 ============
            move_dir = action.get('move')
            shoot_dir = action.get('shoot')
            
            if move_dir and shoot_dir:
                # 从方向转换为实际键名
                move_key = self.move_keys[move_dir]      # 'up' → 'w'
                shoot_key = self.shoot_keys[shoot_dir]   # 'up' → 'up'
                print(f"🔹 执行组合动作 {action_id}: 移动({move_key}) + 射击({shoot_key})")
                return self.input.press_multiple([move_key, shoot_key], duration)
            
            # ============ 情况3: 纯移动 ============
            elif move_dir:
                move_key = self.move_keys[move_dir]
                print(f"🔹 执行移动动作 {action_id}: {move_key}")
                return self.input.press_key(move_key, duration)
            
            # ============ 情况4: 纯射击 ============
            elif shoot_dir:
                shoot_key = self.shoot_keys[shoot_dir]
                print(f"🔹 执行射击动作 {action_id}: {shoot_key}")
                return self.input.press_key(shoot_key, duration)
            
            # ============ 情况5: 静止 ============
            else:
                # 【修改】删除打印，只静默等待
                time.sleep(duration)
                return True
                
        except Exception as e:
            print(f"❌ 动作执行失败 {action_id}: {e}")
            return False
    
    def get_action_name(self, action_id):
        """获取单个动作的文字描述"""
        return self.action_names.get(action_id, f"未知动作{action_id}")
    
    def get_action_names(self):
        """获取所有动作的文字描述"""
        return self.action_names.copy()
    
    def get_move_action(self, direction):
        """
        根据方向获取移动动作ID
        
        Args:
            direction: 'up', 'down', 'left', 'right'
        
        Returns:
            int: 动作ID (1-4)
        """
        mapping = {'up': 1, 'down': 2, 'left': 3, 'right': 4}
        return mapping.get(direction, 0)
    
    def get_shoot_action(self, direction):
        """
        根据方向获取射击动作ID
        
        Args:
            direction: 'up', 'down', 'left', 'right'
        
        Returns:
            int: 动作ID (5-8)
        """
        mapping = {'up': 5, 'down': 6, 'left': 7, 'right': 8}
        return mapping.get(direction, 0)
    
    def get_combined_action(self, direction):
        """
        根据方向获取组合动作ID（移动+射击）
        
        Args:
            direction: 'up', 'down', 'left', 'right'
        
        Returns:
            int: 动作ID (11-14)
        """
        mapping = {'up': 11, 'down': 12, 'left': 13, 'right': 14}
        return mapping.get(direction, 0)
    
    def is_movement_action(self, action_id):
        """判断是否是移动动作"""
        return 1 <= action_id <= 4
    
    def is_shoot_action(self, action_id):
        """判断是否是射击动作"""
        return 5 <= action_id <= 8
    
    def is_special_action(self, action_id):
        """判断是否是特殊动作"""
        return action_id in [9, 10]
    
    def is_combined_action(self, action_id):
        """判断是否是组合动作"""
        return 11 <= action_id <= 14
    
    def get_action_type(self, action_id):
        """获取动作类型"""
        if action_id == 0:
            return "静止"
        elif 1 <= action_id <= 4:
            return "移动"
        elif 5 <= action_id <= 8:
            return "射击"
        elif 9 <= action_id <= 10:
            return "特殊"
        elif 11 <= action_id <= 14:
            return "组合"
        else:
            return "未知"
    
    def get_action_direction(self, action_id):
        """
        获取动作的方向
        
        Returns:
            str: 'up'/'down'/'left'/'right' 或 None
        """
        if action_id == 0:
            return None
        
        action = self.actions.get(action_id)
        if not action:
            return None
        
        # 优先返回移动方向，没有则返回射击方向
        return action.get('move') or action.get('shoot')