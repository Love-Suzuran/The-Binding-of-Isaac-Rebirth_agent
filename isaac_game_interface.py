# isaac_game_interface.py
"""
以撒游戏接口 - 简化版，只提供游戏状态获取和动作执行
修改：将class=44的地刺从敌人移到障碍物
"""
import cv2
import numpy as np
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ultralytics import YOLO
from window_detection import IsaacWindowCapture, AdjustedPositionTracker
from action_mapper import ActionMapper
from config import config

class IsaacGameInterface:
    """游戏接口：提供状态获取和动作执行功能"""
    
    def __init__(self, 
                 model_path=config.yolo_model_path,
                 window_title=config.window_title,
                 conf_threshold=config.yolo_conf_threshold):
        
        # YOLO模型
        self.yolo = YOLO(model_path)
        self.conf_threshold = conf_threshold
        
        # 窗口标题
        self.window_title = window_title
        self.window = None
        
        # ===== 先初始化统计信息 =====
        self.stats = {
            'capture_count': 0,
            'capture_failures': 0,
            'actions_executed': 0,
            'window_resets': 0
        }
        
        # ===== 窗口重置相关 =====
        self.frame_count = 0
        self.initial_frames = 5
        self.last_reset_time = time.time()
        self.reset_interval = 50.0
        
        # 初始化窗口
        self._init_window()
        
        # 位置跟踪器
        self.position_tracker = AdjustedPositionTracker()
        
        # 动作映射器
        self.action_mapper = ActionMapper()
        
        # 帧率控制
        self.frame_time = config.frame_time
        
        # 缓存
        self.last_frame = None
        self.last_detections = None
        self.last_analysis = None
        
        print(f"✅ 游戏接口初始化完成")
        print(f"   - 窗口: {window_title}")
        print(f"   - YOLO模型: {model_path}")
        print(f"   - 置信度阈值: {conf_threshold}")
        print(f"   - 动作空间: {config.action_space} (0-14)")
        print(f"   - 窗口重置: 前{self.initial_frames}帧强制重置，之后每{self.reset_interval}秒重置")
        print(f"   - 【修改】class=44地刺已移到障碍物")
    
    def _init_window(self):
        """初始化窗口捕获器"""
        try:
            self.window = IsaacWindowCapture(self.window_title)
            self.stats['window_resets'] += 1
            self.last_reset_time = time.time()
            print(f"📸 窗口捕获器初始化成功 (第{self.stats['window_resets']}次)")
            return True
        except Exception as e:
            print(f"❌ 窗口捕获器初始化失败: {e}")
            self.window = None
            return False
    
    def _check_window_reset_needed(self):
        """检查是否需要重置窗口"""
        self.frame_count += 1
        current_time = time.time()
        
        if self.frame_count <= self.initial_frames:
            print(f"📸 前{self.frame_count}/{self.initial_frames}帧，强制重置窗口")
            return True
        
        if self.window is None:
            return True
        
        if current_time - self.last_reset_time >= self.reset_interval:
            print(f"📸 超过{self.reset_interval}秒，重置窗口")
            return True
        
        return False
    
    def _capture_frame(self):
        """捕获一帧画面"""
        if self._check_window_reset_needed():
            self._init_window()
            if self.window is None:
                return None
        
        if not self.window.is_window_active():
            print("⚠️ 窗口不活跃，尝试重置...")
            self._init_window()
            if self.window is None:
                return None
        
        try:
            frame = self.window.capture_frame()
            if frame is None:
                self.stats['capture_failures'] += 1
                if self.stats['capture_failures'] >= 5:
                    print("⚠️ 连续5次捕获失败，强制重置窗口")
                    self._init_window()
                    self.stats['capture_failures'] = 0
                return None
            
            self.stats['capture_count'] += 1
            self.stats['capture_failures'] = 0
            return frame
            
        except Exception as e:
            print(f"❌ 捕获异常: {e}")
            self.stats['capture_failures'] += 1
            return None
    
    def _filter_detections_by_class(self, detections, class_ids):
        """按类别ID过滤检测结果"""
        if detections is None or detections.boxes is None:
            return []
        
        filtered = []
        for box in detections.boxes:
            cls_id = int(box.cls[0])
            if cls_id in class_ids:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                filtered.append({
                    'class_id': cls_id,
                    'bbox': [x1, y1, x2, y2],
                    'center': [(x1 + x2) / 2, (y1 + y2) / 2],
                    'confidence': conf
                })
        return filtered
    
    def get_game_state(self):
        """
        获取当前游戏状态
        返回: {
            'frame': 原始帧,
            'detections': YOLO检测结果,
            'analysis': 位置跟踪分析,
            'player': 玩家信息,
            'enemies': 敌人列表,
            'tears': 子弹列表,
            'pickups': 掉落物列表,
            'obstacles': 障碍物列表（包含地刺）,
            'doors': 门列表
        }
        """
        # 1. 捕获帧
        frame = self._capture_frame()
        if frame is None:
            return None
        
        self.last_frame = frame
        
        # 2. YOLO检测
        try:
            results = self.yolo(frame, conf=self.conf_threshold, verbose=False)
            detections = results[0]
            self.last_detections = detections
        except Exception as e:
            print(f"❌ YOLO检测失败: {e}")
            return None
        
        # 3. 位置跟踪分析
        try:
            analysis = self.position_tracker.analyze_frame(detections, frame.shape)
            self.last_analysis = analysis
        except Exception as e:
            print(f"❌ 位置跟踪失败: {e}")
            analysis = None
        
        # 4. 按类别分组过滤
        from config import config
        class_groups = config.CLASS_GROUPS
        
        # 玩家
        player = self._filter_detections_by_class(detections, class_groups['player'])
        
        # 敌人分组 - 【修改】移除了44
        enemies_flying = self._filter_detections_by_class(detections, class_groups['enemies_flying'])
        enemies_walking = self._filter_detections_by_class(detections, class_groups['enemies_walking'])
        enemies_spiders = self._filter_detections_by_class(detections, class_groups['enemies_spiders'])
        enemies_boss = self._filter_detections_by_class(detections, class_groups['enemies_boss'])
        enemies_other = self._filter_detections_by_class(detections, class_groups['enemies_other'])  # 【新增】地刺单独分组
        
        # 弹幕
        tears_enemy = self._filter_detections_by_class(detections, class_groups['tears_enemy'])
        tears_player = self._filter_detections_by_class(detections, class_groups['tears_player'])
        
        # 掉落物
        pickups_heart = self._filter_detections_by_class(detections, class_groups['pickups_heart'])
        pickups_key = self._filter_detections_by_class(detections, class_groups['pickups_key'])
        pickups_coin = self._filter_detections_by_class(detections, class_groups['pickups_coin'])
        pickups_card = self._filter_detections_by_class(detections, class_groups['pickups_card'])
        pickups_bomb = self._filter_detections_by_class(detections, class_groups['pickups_bomb'])
        
        # 障碍物 - 【修改】包含地刺(44)
        obstacles = self._filter_detections_by_class(detections, class_groups['obstacles'])
        
        # 门
        doors = self._filter_detections_by_class(detections, class_groups['doors'])
        doors_closed = self._filter_detections_by_class(detections, class_groups['doors_closed'])
        
        # 5. 组装状态
        game_state = {
            'frame': frame,
            'detections': detections,
            'analysis': analysis,
            'player': player[0] if player else None,
            'enemies': {
                'flying': enemies_flying,
                'walking': enemies_walking,
                'spiders': enemies_spiders,
                'boss': enemies_boss,
                'other': enemies_other,  # 【新增】地刺单独分组
                'all': enemies_flying + enemies_walking + enemies_spiders + enemies_boss  # 【修改】不包含地刺
            },
            'tears': {
                'enemy': tears_enemy,
                'player': tears_player,
                'all': tears_enemy + tears_player
            },
            'pickups': {
                'heart': pickups_heart,
                'key': pickups_key,
                'coin': pickups_coin,
                'card': pickups_card,
                'bomb': pickups_bomb,
                'all': pickups_heart + pickups_key + pickups_coin + pickups_card + pickups_bomb
            },
            'obstacles': obstacles,  # 【修改】包含地刺
            'doors': {
                'open': doors,
                'closed': doors_closed,
                'all': doors + doors_closed
            },
            'timestamp': time.time(),
            'frame_shape': frame.shape
        }
        
        return game_state
    
    def execute_action(self, action_id, duration=None):
        """
        执行动作
        action_id: 0-14 (动作ID)
        duration: 持续时间，None表示使用默认帧时间
        """
        if duration is None:
            duration = self.frame_time
        
        success = self.action_mapper.execute(action_id, duration)
        if success:
            self.stats['actions_executed'] += 1
        return success
    
    def execute_actions(self, action_sequence):
        """
        执行动作序列
        action_sequence: [(action_id, duration), ...] 或 [action_id, ...]
        """
        for action in action_sequence:
            if isinstance(action, tuple):
                action_id, duration = action
            else:
                action_id = action
                duration = self.frame_time
            
            self.execute_action(action_id, duration)
            time.sleep(duration * 0.5)
    
    def press_key(self, key_name, duration=0.1):
        """直接按键（用于重置等操作）"""
        return self.action_mapper.input.press_key(key_name, duration)
    
    def press_multiple(self, keys, duration=0.1):
        """同时按多个键"""
        return self.action_mapper.input.press_multiple(keys, duration)
    
    def is_player_alive(self, game_state=None):
        """检查玩家是否存活"""
        if game_state is None:
            game_state = self.get_game_state()
            if game_state is None:
                return False
        
        return game_state['player'] is not None
    
    def has_enemies(self, game_state=None):
        """检查是否有敌人"""
        if game_state is None:
            game_state = self.get_game_state()
            if game_state is None:
                return False
        
        return len(game_state['enemies']['all']) > 0
    
    def get_nearest_enemy(self, game_state):
        """获取最近的敌人"""
        if not game_state or not game_state['player']:
            return None
        
        player_center = game_state['player']['center']
        enemies = game_state['enemies']['all']
        
        if not enemies:
            return None
        
        for enemy in enemies:
            dx = enemy['center'][0] - player_center[0]
            dy = enemy['center'][1] - player_center[1]
            enemy['distance'] = np.sqrt(dx*dx + dy*dy)
            enemy['angle'] = np.arctan2(dy, dx)
        
        return min(enemies, key=lambda e: e['distance'])
    
    def get_nearest_pickup(self, game_state):
        """获取最近的掉落物"""
        if not game_state or not game_state['player']:
            return None
        
        player_center = game_state['player']['center']
        pickups = game_state['pickups']['all']
        
        if not pickups:
            return None
        
        for pickup in pickups:
            dx = pickup['center'][0] - player_center[0]
            dy = pickup['center'][1] - player_center[1]
            pickup['distance'] = np.sqrt(dx*dx + dy*dy)
        
        return min(pickups, key=lambda p: p['distance'])
    
    def get_danger_direction(self, game_state, danger_distance=100):
        """获取危险方向（用于躲避）"""
        if not game_state or not game_state['player']:
            return None
        
        player_center = game_state['player']['center']
        threats = []
        
        for enemy in game_state['enemies']['all']:
            dx = enemy['center'][0] - player_center[0]
            dy = enemy['center'][1] - player_center[1]
            distance = np.sqrt(dx*dx + dy*dy)
            if distance < danger_distance * 2:
                threats.append({
                    'dx': dx,
                    'dy': dy,
                    'distance': distance,
                    'weight': 1.0 / max(distance, 1)
                })
        
        for tear in game_state['tears']['enemy']:
            dx = tear['center'][0] - player_center[0]
            dy = tear['center'][1] - player_center[1]
            distance = np.sqrt(dx*dx + dy*dy)
            if distance < danger_distance:
                threats.append({
                    'dx': dx,
                    'dy': dy,
                    'distance': distance,
                    'weight': 2.0 / max(distance, 1)
                })
        
        if not threats:
            return None
        
        total_dx = sum(-t['dx'] * t['weight'] for t in threats)
        total_dy = sum(-t['dy'] * t['weight'] for t in threats)
        
        magnitude = np.sqrt(total_dx*total_dx + total_dy*total_dy)
        if magnitude > 0:
            total_dx /= magnitude
            total_dy /= magnitude
        
        return {
            'dx': total_dx,
            'dy': total_dy,
            'angle': np.arctan2(total_dy, total_dx)
        }
    
    def get_action_for_direction(self, direction, action_type='move'):
        """
        根据方向获取动作ID
        direction: 'up'/'down'/'left'/'right' 或角度
        action_type: 'move', 'shoot', 'both'
        """
        if isinstance(direction, (int, float)):
            angle = direction
            if -np.pi/4 <= angle < np.pi/4:
                dir_str = 'right'
            elif np.pi/4 <= angle < 3*np.pi/4:
                dir_str = 'down'
            elif angle >= 3*np.pi/4 or angle < -3*np.pi/4:
                dir_str = 'left'
            else:
                dir_str = 'up'
        else:
            dir_str = direction
        
        if action_type == 'move':
            return self.action_mapper.get_move_action(dir_str)
        elif action_type == 'shoot':
            return self.action_mapper.get_shoot_action(dir_str)
        elif action_type == 'both':
            return self.action_mapper.get_combined_action(dir_str)
        
        return 0
    
    def get_action_name(self, action_id):
        """获取动作名称"""
        return self.action_mapper.get_action_name(action_id)
    
    def render_debug(self, game_state=None, window_name="Isaac Debug"):
        """渲染调试信息"""
        if game_state is None:
            game_state = self.get_game_state()
        
        if game_state is None or game_state['frame'] is None:
            return
        
        frame = game_state['frame'].copy()
        
        if game_state['detections'] and game_state['detections'].boxes:
            for box in game_state['detections'].boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                
                if cls_id == 15:
                    color = (0, 255, 0)
                elif cls_id == 44:  # 【新增】地刺用紫色显示
                    color = (255, 0, 255)
                elif cls_id in [28,41,42,49,50,61,56,57,58,59,51,55,45,46,47,52,60,63,64]:
                    color = (0, 0, 255)
                elif cls_id == 54:
                    color = (0, 100, 255)
                elif cls_id == 24:
                    color = (255, 255, 0)
                elif cls_id in [23,35,39,53,29]:
                    color = (255, 0, 255)
                else:
                    color = (200, 200, 200)
                
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                
                if conf > 0.5:
                    label = f"{cls_id}"
                    cv2.putText(frame, label, (x1, y1-5),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        if game_state['analysis']:
            gx, gy = game_state['analysis']['global_position']
            cv2.putText(frame, f"Room: ({gx}, {gy})", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            
            if game_state['analysis']['player_dead']:
                cv2.putText(frame, "💀 DEAD", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 3)
        
        enemy_count = len(game_state['enemies']['all'])
        cv2.putText(frame, f"Enemies: {enemy_count}", (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 1)
        
        # 【新增】显示地刺数量
        spike_count = len(game_state['enemies'].get('other', []))
        cv2.putText(frame, f"Spikes: {spike_count}", (10, 115),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 1)
        
        tear_count = len(game_state['tears']['enemy'])
        cv2.putText(frame, f"Tears: {tear_count}", (10, 140),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 100, 255), 1)
        
        cv2.putText(frame, f"Resets: {self.stats['window_resets']}", (10, 165),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        cv2.imshow(window_name, frame)
        cv2.waitKey(1)
    
    def close(self):
        """关闭接口"""
        cv2.destroyAllWindows()
        print(f"\n📊 统计: 捕获={self.stats['capture_count']}, 动作={self.stats['actions_executed']}, 窗口重置={self.stats['window_resets']}")


if __name__ == "__main__":
    print("测试游戏接口...")
    
    game = IsaacGameInterface()
    
    try:
        for i in range(30):
            state = game.get_game_state()
            if state:
                print(f"\r帧 {i+1}: 敌人={len(state['enemies']['all'])}, "
                      f"地刺={len(state['enemies'].get('other', []))}, "
                      f"子弹={len(state['tears']['enemy'])}, "
                      f"掉落={len(state['pickups']['all'])}", end="")
                
                game.render_debug(state)
                time.sleep(1/30)
            else:
                print(f"\r帧 {i+1}: 获取失败", end="")
    
    except KeyboardInterrupt:
        print("\n测试中断")
    finally:
        game.close()