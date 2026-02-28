# agent_controller.py - 修复版（正确处理动作返回格式）
"""
主控制器 - 管理战斗和探索模式的切换
修复版：统一处理战斗和探索模块的返回格式
"""
import time
from collections import deque

class IsaacAgentController:
    """以撒Agent主控制器"""
    
    def __init__(self, game_interface, combat_agent, explore_agent):
        self.game = game_interface
        self.combat = combat_agent
        self.explore = explore_agent
        
        # 当前模式
        self.current_mode = 'explore'  # 'combat' 或 'explore'
        self.mode_history = deque(maxlen=10)
        self.mode_switch_time = time.time()
        
        # 房间切换检测
        self.last_room = (6, 6)
        self.room_stable_counter = 0
        self.room_stable_threshold = 5
        
        # 无怪物计数器
        self.no_enemy_counter = 0
        self.no_enemy_threshold = 10
        
        # 门打开检测
        self.doors_open_counter = 0
        self.doors_open_threshold = 5
        
        # 死亡检测（简单规则版）
        self.death_detected = False
        self.respawn_phase = 0
        self.respawn_start_time = None
        
        # 玩家消失计数器
        self.player_missing_counter = 0
        self.player_missing_threshold = 30  # 连续30帧玩家消失认为死亡
        
        # 统计
        self.stats = {
            'mode_switches': 0,
            'combat_frames': 0,
            'explore_frames': 0,
            'room_changes': 0,
            'deaths_detected': 0,
            'revivals': 0,
        }
        
        print("✅ 主控制器初始化完成（修复版）")
        print("   - 死亡检测: 基于玩家消失（30帧）")
        print("   - 动作返回格式: 统一处理")
    
    def check_death_by_player_missing(self, game_state):
        """通过玩家是否消失检测死亡"""
        if game_state is None:
            return False
        
        # 检查玩家是否存在
        player_exists = game_state.get('player') is not None
        
        if not player_exists:
            self.player_missing_counter += 1
        else:
            self.player_missing_counter = 0
        
        # 连续多帧玩家消失，判定为死亡
        if self.player_missing_counter >= self.player_missing_threshold and not self.death_detected:
            print(f"💀 检测到玩家死亡（连续{self.player_missing_counter}帧消失）")
            self.death_detected = True
            self.stats['deaths_detected'] += 1
            self.respawn_phase = 0
            self.respawn_start_time = time.time()
            return True
        
        return False
    
    def _handle_respawn(self, game_state):
        """处理复活流程"""
        current_time = time.time()
        
        if self.respawn_phase == 0:
            self.respawn_phase = 1
            self.respawn_start_time = current_time
            print("💀 死亡，开始复活流程...")
            return True
        
        elif self.respawn_phase == 1:
            # 按空格键继续
            for i in range(3):
                self.game.press_key('space', 0.3)
                time.sleep(0.3)
            self.respawn_phase = 2
            self.respawn_start_time = current_time
            print("   - 按空格继续")
            return True
        
        elif self.respawn_phase == 2:
            # 等待复活动画
            elapsed = current_time - self.respawn_start_time
            if elapsed >= 5.0:
                self.respawn_phase = 3
                self.respawn_start_time = current_time
                print("   - 等待复活完成")
            return True
        
        elif self.respawn_phase == 3:
            # 重置探索模块状态
            if hasattr(self.explore, 'memory'):
                self.explore.memory['path_sequence'] = []
                self.explore.memory['current_path_index'] = 0
                self.explore.memory['rooms_visited'] = [(6, 6)]
                self.explore.memory['consecutive_failures'] = 0
                self.explore.memory['last_chosen_door'] = None
                self.explore.memory['last_chosen_door_coords'] = None
            
            # 重置探索模块的房间信息
            if hasattr(self.explore, 'current_room'):
                self.explore.current_room = (6, 6)
                self.explore.previous_room = None
            
            # 重置战斗模块状态
            if hasattr(self.combat, 'shoot_counter'):
                self.combat.shoot_counter = 0
                self.combat.last_shoot_direction = None
                self.combat.in_burst_cooldown = False
            
            # 重置控制器状态
            self.last_room = (6, 6)
            self.room_stable_counter = 0
            self.current_mode = 'explore'
            self.player_missing_counter = 0
            
            # 死亡状态清除
            self.death_detected = False
            self.respawn_phase = 0
            
            self.stats['revivals'] += 1
            print("✨ 复活完成，返回初始房间")
            
            return False
        
        return True
    
    def should_switch_to_combat(self, game_state):
        """判断是否应该切换到战斗模式"""
        if game_state is None or self.death_detected:
            return False
        
        enemies = game_state.get('enemies', {})
        tears = game_state.get('tears', {})
        
        has_enemies = len(enemies.get('all', [])) > 0
        if has_enemies:
            return True
        
        has_enemy_tears = len(tears.get('enemy', [])) > 0
        if has_enemy_tears:
            return True
        
        return False
    
    def should_switch_to_explore(self, game_state):
        """判断是否应该切换到探索模式"""
        if game_state is None or self.death_detected:
            return False
        
        enemies = game_state.get('enemies', {})
        tears = game_state.get('tears', {})
        
        has_enemies = len(enemies.get('all', [])) > 0
        if has_enemies:
            self.no_enemy_counter = 0
            return False
        
        self.no_enemy_counter += 1
        
        doors = game_state.get('doors', {})
        open_doors = len(doors.get('open', [])) if doors else 0
        
        if open_doors > 0:
            self.doors_open_counter += 1
        else:
            self.doors_open_counter = 0
        
        if (self.no_enemy_counter >= self.no_enemy_threshold and 
            self.doors_open_counter >= self.doors_open_threshold):
            return True
        
        return False
    
    def detect_room_change(self, game_state):
        """检测房间是否切换"""
        if game_state is None or game_state.get('analysis') is None or self.death_detected:
            return False
        
        current_room = game_state['analysis'].get('global_position')
        if current_room is None:
            return False
        
        if current_room != self.last_room:
            self.room_stable_counter = 0
            self.last_room = current_room
            self.stats['room_changes'] += 1
            return True
        
        return False
    
    def is_room_stable(self, game_state):
        """检查房间是否稳定"""
        if game_state is None or game_state.get('analysis') is None or self.death_detected:
            return False
        
        current_room = game_state['analysis'].get('global_position')
        if current_room is None:
            return False
        
        if current_room == self.last_room:
            self.room_stable_counter += 1
        else:
            self.room_stable_counter = 0
            self.last_room = current_room
        
        return self.room_stable_counter >= self.room_stable_threshold
    
    def _normalize_action_result(self, action_result):
        """
        【新增】统一规范化动作返回格式
        将各种可能的返回格式统一转换为列表
        """
        if action_result is None:
            return []
        
        # 已经是列表
        if isinstance(action_result, list):
            # 检查列表中的元素格式
            normalized = []
            for item in action_result:
                if isinstance(item, tuple) and len(item) == 2:
                    # 确保第一个元素是整数
                    if isinstance(item[0], int):
                        normalized.append(item)
                    else:
                        print(f"⚠️ 无效动作ID类型: {type(item[0])}")
                elif isinstance(item, int):
                    # 如果是纯整数，使用默认持续时间
                    normalized.append((item, 0.1))
                else:
                    print(f"⚠️ 忽略无效动作格式: {item}")
            return normalized
        
        # 单个元组 (action_id, duration)
        if isinstance(action_result, tuple) and len(action_result) == 2:
            if isinstance(action_result[0], int):
                return [action_result]
            else:
                print(f"⚠️ 无效动作ID类型: {type(action_result[0])}")
                return []
        
        # 单个整数
        if isinstance(action_result, int):
            return [(action_result, 0.1)]
        
        # 字符串指令
        if isinstance(action_result, str):
            if action_result in ['wait', 'just_processed', 'error']:
                return [action_result]
        
        print(f"⚠️ 未知返回格式: {type(action_result)}")
        return []
    
    def decide_actions(self, game_state):
        """
        主决策函数 - 修复版
        统一处理战斗和探索模块的返回格式
        返回: 统一格式的动作列表 [(action_id, duration), ...]
        """
        if game_state is None:
            return []
        
        # 死亡检测（基于玩家消失）
        self.check_death_by_player_missing(game_state)
        
        # 处理复活流程
        if self.death_detected:
            if self._handle_respawn(game_state):
                return []  # 复活流程中，不执行其他动作
        
        # 检测房间切换
        room_changed = self.detect_room_change(game_state)
        if room_changed:
            if self.current_mode != 'combat':
                self._switch_mode('combat', '房间切换')
            if hasattr(self.explore, 'on_room_change'):
                self.explore.on_room_change()
        
        # 模式切换判断
        if self.current_mode == 'explore':
            if self.should_switch_to_combat(game_state):
                self._switch_mode('combat', '发现敌人')
        
        elif self.current_mode == 'combat':
            if self.should_switch_to_explore(game_state) and self.is_room_stable(game_state):
                self._switch_mode('explore', '房间清空')
        
        # 根据当前模式获取动作
        actions = []
        
        if self.current_mode == 'combat':
            self.stats['combat_frames'] += 1
            
            # 获取战斗模块的决策结果
            combat_result = self.combat.decide_action(game_state)
            
            # 规范化战斗结果
            actions = self._normalize_action_result(combat_result)
            
            # 调试输出
            if actions and len(actions) > 0:
                if len(actions) == 1:
                    action_id, duration = actions[0]
                    if action_id != 0:
                        action_name = self.game.get_action_name(action_id) if hasattr(self.game, 'get_action_name') else str(action_id)
                        print(f"⚔️ 战斗动作: {action_name} ({duration:.3f}s)")
                else:
                    print(f"⚔️ 战斗动作序列: {len(actions)}个动作")
        
        elif self.current_mode == 'explore':
            self.stats['explore_frames'] += 1
            
            # 获取探索模块的决策结果
            explore_result = self.explore.decide_actions(game_state)
            
            # 处理探索模块的特殊返回值
            if explore_result == ['just_processed'] or explore_result == ['error']:
                return []
            
            # 规范化探索结果
            actions = self._normalize_action_result(explore_result)
        
        return actions
    
    def _switch_mode(self, new_mode, reason):
        """切换模式"""
        if new_mode == self.current_mode:
            return
        
        old_mode = self.current_mode
        self.current_mode = new_mode
        self.mode_switch_time = time.time()
        self.mode_history.append((old_mode, new_mode, reason))
        self.stats['mode_switches'] += 1
        
        if new_mode == 'combat':
            self.no_enemy_counter = 0
            self.doors_open_counter = 0
            print(f"⚔️ 切换到战斗模式 ({reason})")
        else:
            # 清空探索路径
            if hasattr(self.explore, 'memory'):
                self.explore.memory['path_sequence'] = []
                self.explore.memory['current_path_index'] = 0
                self.explore.memory['last_chosen_door'] = None
                self.explore.memory['last_chosen_door_coords'] = None
            print(f"🗺️ 切换到探索模式 ({reason})")
    
    def get_debug_info(self):
        """获取调试信息"""
        return {
            'mode': self.current_mode,
            'last_room': self.last_room,
            'death_detected': self.death_detected,
            'player_missing': self.player_missing_counter,
            'stats': self.stats,
            'mode_switches': self.stats['mode_switches'],
            'room_changes': self.stats['room_changes'],
        }