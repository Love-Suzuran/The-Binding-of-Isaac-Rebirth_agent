# config.py
"""
以撒结合RL环境配置文件
"""
from dataclasses import dataclass
from typing import Dict, List
import numpy as np

@dataclass
class IsaacConfig:
    # YOLO模型路径
    yolo_model_path: str = "icon.pt"
    
    # 游戏窗口标题
    window_title: str = "Binding of Isaac: Rebirth"
    
    # 帧率控制
    target_fps: int = 60
    frame_time: float = 1/60  # 16.67ms
    
    # YOLO检测阈值
    yolo_conf_threshold: float = 0.3
    
    # 动作空间大小 (0-14)
    action_space: int = 15
    
    # 归一化参数
    max_distance: float = 400.0
    
    # ============ 类别分组（基于你的实际数据） ============
    @property
    def CLASS_GROUPS(self):
        return {
            # 玩家
            'player': [15],
            
            # 敌人 - 【修改】移除了44（地刺）
            'enemies_flying': [28, 41, 42, 49, 50, 61],  # 苍蝇、幽灵、火蝇、地蛇、火怪、小蜘蛛
            'enemies_walking': [56, 57, 58, 59],         # 僵尸、大僵尸、身体怪、SB怪
            'enemies_spiders': [51, 55],                 # 大蜘蛛、超大蜘蛛
            'enemies_boss': [45, 46, 47, 52, 60, 63, 64],  # 【修改】移除了44
            'enemies_other': [44],  # 【新增】单独的地刺类别（用于调试）
            
            # 弹幕
            'tears_enemy': [54],      # 敌人红色子弹
            'tears_player': [24],     # 玩家蓝色眼泪
            
            # 掉落物
            'pickups_heart': [23],    # 红心
            'pickups_key': [35],      # 钥匙
            'pickups_coin': [39],     # 金币
            'pickups_card': [53],     # 卡片
            'pickups_bomb': [29],     # 炸弹
            
            # 障碍物 - 【修改】加入44（地刺）
            'obstacles': [25, 32, 36, 37, 44],  # 火堆、石头、可破坏障碍、可通行障碍、地刺
            
            # 门
            'doors': [16, 17, 19, 26, 34],  # 上/右/左/好门/下
            'doors_closed': [18, 27, 30, 31, 33, 40, 43, 48],  # 各种关闭的门
            
            # UI元素
            'ui': [20, 21, 22],  # 血量条、状态栏、地图
            
            # 无效类别
            'invalid': [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,62]
        }
    
    # ============ 每个分组最大检测数量 ============
    @property
    def MAX_PER_GROUP(self):
        return {
            'player': 1,
            
            # 敌人
            'enemies_flying': 12,
            'enemies_walking': 8,
            'enemies_spiders': 4,
            'enemies_boss': 2,
            'enemies_other': 2,  # 【新增】地刺最多2个
            
            # 弹幕
            'tears_enemy': 20,
            'tears_player': 10,
            
            # 掉落物
            'pickups_heart': 2,
            'pickups_key': 1,
            'pickups_coin': 4,
            'pickups_card': 2,
            'pickups_bomb': 3,
            
            # 障碍物 - 30个（包含地刺）
            'obstacles': 30,
            
            # 门
            'doors': 4,
            'doors_closed': 4,
        }
    
    # ============ 状态维度计算 ============
    @property
    def STATE_DIM(self):
        """计算总状态维度"""
        dim = 0
        for group, count in self.MAX_PER_GROUP.items():
            dim += count * 2  # 每个物体用[距离,角度]表示
        dim += 4  # 玩家特征（血量、敌数、钥匙、炸弹）
        return dim

config = IsaacConfig()
print(f"状态维度: {config.STATE_DIM}")
print(f"动作空间: {config.action_space}")