# agent_combat.py - 加强版（紧急躲避时也向反方向射击）
"""
战斗模块 - 快速规则反应
加强版：紧急躲避时也向反方向射击，确保任何时候都在输出
"""
import numpy as np
import time
from collections import deque

class CombatAgent:
    """战斗Agent - 快速规则反应"""
    
    def __init__(self, game_interface):
        self.game = game_interface
        self.mode = 'combat'
        
        # 战斗参数
        self.params = {
            'safe_distance': 250,        # 安全距离
            'danger_distance': 180,       # 危险距离
            'critical_distance': 100,     # 临界距离
            
            # 射击相关
            'shoot_cooldown': 0.05,        # 射击冷却
            'shoot_duration': 0.03,        # 短按持续时间
            'continuous_shoot': True,      # 是否连续射击
            'burst_count': 5,               # 连发次数阈值
            'burst_cooldown': 0.5,          # 连发后的冷却时间
            
            # 移动相关
            'move_duration': 0.1,           # 移动持续时间
            'evade_weight': 0.9,
            'attack_weight': 0.1,
            
            'last_shoot_time': 0,
            'current_target': None,
            'target_lifetime': 1.0,
            'tear_priority': 4.0,
            'enemy_priority': 1.5,
            'move_speed': 5,
            
            # 长按支持
            'hold_shoot': True,
            'hold_duration': 0.5,
            
            # 直线射击参数
            'line_align_threshold': 30,
            'prefer_horizontal': True,
        }
        
        # 目标跟踪
        self.target_history = {}
        self.next_target_id = 0
        
        # 上次决策结果
        self.last_action = 0
        self.last_decision_time = time.time()
        self.last_shoot_time = 0
        
        # 连续射击计数
        self.shoot_counter = 0
        self.last_shoot_direction = None
        self.burst_start_time = 0
        self.in_burst_cooldown = False
        
        # 直线射击状态
        self.aligning_mode = False
        self.current_align_target = None
        self.align_start_time = 0
        
        # 动作映射
        if hasattr(game_interface, 'action_mapper'):
            self.move_actions = {
                'up': game_interface.action_mapper.get_move_action('up'),
                'down': game_interface.action_mapper.get_move_action('down'),
                'left': game_interface.action_mapper.get_move_action('left'),
                'right': game_interface.action_mapper.get_move_action('right')
            }
            self.shoot_actions = {
                'up': game_interface.action_mapper.get_shoot_action('up'),
                'down': game_interface.action_mapper.get_shoot_action('down'),
                'left': game_interface.action_mapper.get_shoot_action('left'),
                'right': game_interface.action_mapper.get_shoot_action('right')
            }
            self.combined_actions = {
                ('up', 'up'): game_interface.action_mapper.get_combined_action('up'),
                ('down', 'down'): game_interface.action_mapper.get_combined_action('down'),
                ('left', 'left'): game_interface.action_mapper.get_combined_action('left'),
                ('right', 'right'): game_interface.action_mapper.get_combined_action('right')
            }
        else:
            self.move_actions = {'up': 1, 'down': 2, 'left': 3, 'right': 4}
            self.shoot_actions = {'up': 5, 'down': 6, 'left': 7, 'right': 8}
            self.combined_actions = {
                ('up', 'up'): 11,
                ('down', 'down'): 12,
                ('left', 'left'): 13,
                ('right', 'right'): 14
            }
        
        # 默认持续时间
        self.default_duration = 0.1
        
        # 统计信息
        self.stats = {
            'shots_fired': 0,
            'dodges': 0,
            'danger_frames': 0,
            'safe_frames': 0,
            'critical_frames': 0,
            'run_and_shoot': 0,
            'continuous_shots': 0,
            'bursts': 0,
            'holds': 0,
            'line_shots': 0,
            'align_moves': 0,
            'emergency_shots': 0,  # 【新增】紧急躲避时射击次数
        }
        
        print("✅ 战斗模块初始化完成（紧急射击版）")
        print(f"   - 安全距离: {self.params['safe_distance']}px")
        print(f"   - 危险距离: {self.params['danger_distance']}px")
        print(f"   - 临界距离: {self.params['critical_distance']}px")
        print(f"   - 射击冷却: {self.params['shoot_cooldown']}秒")
        print(f"   - 【新增】紧急躲避时也向反方向射击")
        print(f"   - 长按支持: {'开启' if self.params['hold_shoot'] else '关闭'}")
    
    def should_activate(self, game_state):
        """判断是否应该进入战斗模式"""
        if game_state is None:
            return False
        return len(game_state['enemies']['all']) > 0 or len(game_state['tears']['enemy']) > 0
    
    def on_room_enter(self, game_state):
        """进入新房间时的处理"""
        self.target_history = {}
        self.params['current_target'] = None
        self.shoot_counter = 0
        self.last_shoot_direction = None
        self.burst_start_time = 0
        self.in_burst_cooldown = False
        self.aligning_mode = False
        self.current_align_target = None
        print("🏠 进入新房间，重置战斗目标")
    
    def _get_opposite_direction(self, direction):
        """获取相反方向"""
        opposite_map = {
            'up': 'down',
            'down': 'up',
            'left': 'right',
            'right': 'left'
        }
        return opposite_map.get(direction)
    
    def _detailed_danger_check(self, game_state, player_center):
        """详细的危险检查"""
        threats = []
        critical = False
        max_urgency = 0
        
        # 检查子弹（最高优先级）
        for tear in game_state['tears']['enemy']:
            dx = tear['center'][0] - player_center[0]
            dy = tear['center'][1] - player_center[1]
            distance = np.sqrt(dx*dx + dy*dy)
            
            if distance < self.params['danger_distance'] * 1.5:
                if distance < self.params['critical_distance']:
                    urgency = 1.0
                    critical = True
                elif distance < self.params['danger_distance']:
                    urgency = 1.0 - (distance - self.params['critical_distance']) / (self.params['danger_distance'] - self.params['critical_distance'])
                else:
                    urgency = 0.3 * (1.0 - (distance - self.params['danger_distance']) / (self.params['danger_distance'] * 0.5))
                
                threats.append({
                    'dx': dx, 'dy': dy,
                    'distance': distance,
                    'urgency': urgency * self.params['tear_priority'],
                    'type': 'tear'
                })
                max_urgency = max(max_urgency, urgency)
        
        # 检查敌人
        for enemy in game_state['enemies']['all']:
            dx = enemy['center'][0] - player_center[0]
            dy = enemy['center'][1] - player_center[1]
            distance = np.sqrt(dx*dx + dy*dy)
            
            if distance < self.params['safe_distance']:
                if distance < self.params['danger_distance']:
                    urgency = 1.0 - (distance / self.params['danger_distance'])
                    if distance < self.params['critical_distance']:
                        critical = True
                else:
                    urgency = 0.2 * (1.0 - (distance - self.params['danger_distance']) / (self.params['safe_distance'] - self.params['danger_distance']))
                
                threats.append({
                    'dx': dx, 'dy': dy,
                    'distance': distance,
                    'urgency': urgency * self.params['enemy_priority'],
                    'type': 'enemy'
                })
                max_urgency = max(max_urgency, urgency)
        
        if not threats:
            return {'has_danger': False, 'critical': False}
        
        # 计算躲避方向
        total_dx = 0
        total_dy = 0
        total_weight = 0
        
        for t in threats:
            if t['dx'] != 0 or t['dy'] != 0:
                mag = np.sqrt(t['dx']*t['dx'] + t['dy']*t['dy'])
                if mag > 0:
                    away_dx = -t['dx'] / mag
                    away_dy = -t['dy'] / mag
                    
                    weight = t['urgency'] / max(t['distance'], 1)
                    
                    total_dx += away_dx * weight
                    total_dy += away_dy * weight
                    total_weight += weight
        
        if total_weight > 0:
            total_dx /= total_weight
            total_dy /= total_weight
            
            mag = np.sqrt(total_dx*total_dx + total_dy*total_dy)
            if mag > 0:
                total_dx /= mag
                total_dy /= mag
        
        return {
            'has_danger': True,
            'critical': critical,
            'safe_direction': (total_dx, total_dy),
            'urgency': max_urgency,
            'threat_count': len(threats),
            'threats': threats[:3]
        }
    
    def _get_evade_direction(self, danger):
        """根据安全方向获取具体的躲避方向"""
        safe_dx, safe_dy = danger['safe_direction']
        
        if abs(safe_dx) < 0.1 and abs(safe_dy) < 0.1:
            return 'right'
        
        if abs(safe_dx) > abs(safe_dy):
            return 'right' if safe_dx > 0 else 'left'
        else:
            return 'down' if safe_dy > 0 else 'up'
    
    def _get_nearest_enemy(self, game_state, player_center):
        """获取最近的敌人"""
        enemies = game_state['enemies']['all']
        if not enemies:
            return None
        
        nearest = None
        min_dist = float('inf')
        
        for enemy in enemies:
            dx = enemy['center'][0] - player_center[0]
            dy = enemy['center'][1] - player_center[1]
            dist = np.sqrt(dx*dx + dy*dy)
            if dist < min_dist:
                min_dist = dist
                nearest = {
                    'enemy': enemy,
                    'dx': dx,
                    'dy': dy,
                    'distance': dist
                }
        
        return nearest
    
    def _get_align_direction(self, player_center, enemy_info):
        """获取与敌人对齐需要的移动方向"""
        if enemy_info is None:
            return False, None, None
        
        dx = enemy_info['dx']
        dy = enemy_info['dy']
        
        abs_dx = abs(dx)
        abs_dy = abs(dy)
        
        # 检查是否已经在直线上
        if abs_dx < self.params['line_align_threshold']:
            return False, None, 'vertical'
        elif abs_dy < self.params['line_align_threshold']:
            return False, None, 'horizontal'
        
        # 需要移动对齐
        if self.params['prefer_horizontal']:
            if dx > 0:
                return True, 'right', 'horizontal'
            else:
                return True, 'left', 'horizontal'
        else:
            if dy > 0:
                return True, 'down', 'vertical'
            else:
                return True, 'up', 'vertical'
    
    def _get_attack_direction_from_enemy(self, enemy_info):
        """根据敌人位置获取射击方向"""
        if enemy_info is None:
            return None
        
        dx = enemy_info['dx']
        dy = enemy_info['dy']
        
        abs_dx = abs(dx)
        abs_dy = abs(dy)
        
        if abs_dx > abs_dy:
            return 'right' if dx > 0 else 'left'
        else:
            return 'down' if dy > 0 else 'up'
    
    def decide_action(self, game_state):
        """
        决策战斗动作 - 【关键修改】紧急躲避时也向反方向射击
        返回: 动作列表 [(action_id, duration), ...]
        """
        current_time = time.time()
        
        # 检查连发冷却
        if self.in_burst_cooldown:
            if current_time - self.burst_start_time > self.params['burst_cooldown']:
                self.in_burst_cooldown = False
                self.shoot_counter = 0
            else:
                # 冷却中只移动不射击
                pass
        
        if game_state is None or game_state['player'] is None:
            return [(0, self.default_duration)]
        
        player = game_state['player']
        player_center = player['center']
        
        # 获取最近的敌人
        nearest_enemy = self._get_nearest_enemy(game_state, player_center)
        
        # ===== 1. 详细威胁检测 =====
        danger = self._detailed_danger_check(game_state, player_center)
        
        # ===== 2. 有危险时躲避 =====
        if danger['has_danger']:
            self.stats['danger_frames'] += 1
            if danger['critical']:
                self.stats['critical_frames'] += 1
            
            # 获取躲避方向
            evade_dir = self._get_evade_direction(danger)
            if evade_dir:
                self.stats['dodges'] += 1
                
                # 计算反方向（射击方向）
                opposite_dir = self._get_opposite_direction(evade_dir)
                
                # 检查射击冷却
                can_shoot = (not self.in_burst_cooldown) and (current_time - self.last_shoot_time > self.params['shoot_cooldown'])
                
                actions = []
                
                # 第一行：移动
                actions.append((self.move_actions[evade_dir], self.params['move_duration']))
                
                # 【关键修改】紧急躲避时也尝试射击
                if can_shoot and opposite_dir:
                    self.last_shoot_time = current_time
                    self.stats['shots_fired'] += 1
                    
                    # 统计
                    if danger['critical']:
                        self.stats['emergency_shots'] += 1
                        shot_type = "紧急"
                    else:
                        self.stats['run_and_shoot'] += 1
                        shot_type = "常规"
                    
                    # 连发计数
                    if opposite_dir == self.last_shoot_direction:
                        self.shoot_counter += 1
                        self.stats['continuous_shots'] += 1
                    else:
                        self.shoot_counter = 1
                        self.last_shoot_direction = opposite_dir
                    
                    # 判断是否达到连发阈值，转成长按
                    if self.params['hold_shoot'] and self.shoot_counter >= self.params['burst_count']:
                        self.stats['bursts'] += 1
                        self.stats['holds'] += 1
                        self.in_burst_cooldown = True
                        self.burst_start_time = current_time
                        print(f"🏃‍♂️🔫🔫 {shot_type}长按射击: 逃跑方向 {evade_dir}, 射击方向 {opposite_dir}")
                        actions.append((self.shoot_actions[opposite_dir], self.params['hold_duration']))
                    else:
                        print(f"🏃‍♂️🔫 {shot_type}射击: 逃跑方向 {evade_dir}, 射击方向 {opposite_dir}")
                        actions.append((self.shoot_actions[opposite_dir], self.params['shoot_duration']))
                else:
                    # 不能射击时，只显示移动
                    if danger['critical']:
                        print(f"🏃 紧急躲避: {evade_dir} (射击冷却)")
                    else:
                        print(f"🏃 躲避: {evade_dir} (射击冷却)")
                
                self.aligning_mode = False
                return actions
        
        # ===== 3. 危险距离外，与最近的敌人保持直线 =====
        if nearest_enemy and nearest_enemy['distance'] > self.params['danger_distance']:
            
            # 检查是否需要移动对齐
            need_move, align_dir, align_type = self._get_align_direction(player_center, nearest_enemy)
            
            if need_move:
                # 需要移动来对齐
                self.stats['align_moves'] += 1
                self.aligning_mode = True
                self.current_align_target = nearest_enemy['enemy']
                
                print(f"📐 对齐移动: {align_dir} (与敌人{align_type}对齐)")
                return [(self.move_actions[align_dir], self.params['move_duration'])]
            
            else:
                # 已经在直线上，可以射击
                self.aligning_mode = False
                
                # 获取射击方向
                shoot_dir = self._get_attack_direction_from_enemy(nearest_enemy)
                
                if shoot_dir:
                    # 检查射击冷却
                    can_shoot = (not self.in_burst_cooldown) and (current_time - self.last_shoot_time > self.params['shoot_cooldown'])
                    
                    if can_shoot:
                        self.last_shoot_time = current_time
                        self.stats['shots_fired'] += 1
                        self.stats['line_shots'] += 1
                        
                        # 连发计数
                        if shoot_dir == self.last_shoot_direction:
                            self.shoot_counter += 1
                            self.stats['continuous_shots'] += 1
                        else:
                            self.shoot_counter = 1
                            self.last_shoot_direction = shoot_dir
                        
                        # 判断是否达到连发阈值，转成长按
                        if self.params['hold_shoot'] and self.shoot_counter >= self.params['burst_count']:
                            self.stats['bursts'] += 1
                            self.stats['holds'] += 1
                            self.in_burst_cooldown = True
                            self.burst_start_time = current_time
                            print(f"🎯📐 直线长按射击: {shoot_dir}")
                            return [(self.shoot_actions[shoot_dir], self.params['hold_duration'])]
                        else:
                            print(f"🎯📐 直线射击: {shoot_dir}")
                            return [(self.shoot_actions[shoot_dir], self.params['shoot_duration'])]
        
        # ===== 4. 没有危险时普通攻击 =====
        self.stats['safe_frames'] += 1
        attack_dir = self._get_attack_direction_from_enemy(nearest_enemy) if nearest_enemy else None
        
        if attack_dir:
            # 检查射击冷却
            can_shoot = (not self.in_burst_cooldown) and (current_time - self.last_shoot_time > self.params['shoot_cooldown'])
            
            if can_shoot:
                self.last_shoot_time = current_time
                self.stats['shots_fired'] += 1
                
                # 连发计数
                if attack_dir == self.last_shoot_direction:
                    self.shoot_counter += 1
                    self.stats['continuous_shots'] += 1
                else:
                    self.shoot_counter = 1
                    self.last_shoot_direction = attack_dir
                
                # 判断是否达到连发阈值，转成长按
                if self.params['hold_shoot'] and self.shoot_counter >= self.params['burst_count']:
                    self.stats['bursts'] += 1
                    self.stats['holds'] += 1
                    self.in_burst_cooldown = True
                    self.burst_start_time = current_time
                    print(f"🎯🔫🔫 长按射击: {attack_dir}")
                    return [(self.shoot_actions[attack_dir], self.params['hold_duration'])]
                else:
                    print(f"🎯 射击: {attack_dir}")
                    return [(self.shoot_actions[attack_dir], self.params['shoot_duration'])]
        
        # 没有动作时返回静止
        return [(0, self.default_duration)]
    
    def get_debug_info(self):
        """获取调试信息"""
        return {
            'mode': 'combat',
            'last_action': self.last_action,
            'shoot_counter': self.shoot_counter,
            'in_cooldown': self.in_burst_cooldown,
            'aligning_mode': self.aligning_mode,
            'stats': self.stats,
            'params': self.params
        }