# agent_explore_vlm.py (网格大小40px版本，强制朝门方向多走三步)
"""
智能探索模块 - 寻路版
- 代码规则选择门
- A*算法自动寻路
- 每个网格只走一步，网格大小40px
- 无论是否到达，都强制朝门方向多走三步
"""
import numpy as np
import time
import cv2
import heapq
import math
from collections import deque

class PathFinder:
    """寻路系统 - A*算法"""
    
    def __init__(self, grid_size=40):
        self.grid_size = grid_size
        
        # 移动参数
        self.move_params = {
            'step_duration': 0.075,
        }
        
        # 4方向移动
        self.directions = [
            (0, -1, 'up', 1.0),     # 上
            (0, 1, 'down', 1.0),     # 下
            (-1, 0, 'left', 1.0),    # 左
            (1, 0, 'right', 1.0),    # 右
        ]
        
        print(f"✅ 寻路系统初始化完成")
        print(f"   - 网格大小: {self.grid_size}px/格")
        print(f"   - 步长时间: {self.move_params['step_duration']}秒")
    
    def world_to_grid(self, x, y):
        """世界坐标转网格坐标"""
        return (int(x / self.grid_size), int(y / self.grid_size))
    
    def grid_to_world(self, gx, gy):
        """网格坐标转世界坐标（返回中心点）"""
        return (gx * self.grid_size + self.grid_size // 2, 
                gy * self.grid_size + self.grid_size // 2)
    
    def create_obstacle_map(self, game_state, player_pos, target_pos):
        """创建障碍物地图"""
        h, w = game_state['frame_shape'][:2]
        grid_h = h // self.grid_size + 2
        grid_w = w // self.grid_size + 2
        
        # 创建网格地图（0=可通行，1=障碍物）
        obstacle_map = np.zeros((grid_h, grid_w), dtype=int)
        
        # 添加墙壁边界
        for gy in range(grid_h):
            obstacle_map[gy, 0] = 1  # 左墙
            obstacle_map[gy, grid_w-1] = 1  # 右墙
        for gx in range(grid_w):
            obstacle_map[0, gx] = 1  # 上墙
            obstacle_map[grid_h-1, gx] = 1  # 下墙
        
        # 添加障碍物
        if 'obstacles' in game_state and game_state['obstacles']:
            for obstacle in game_state['obstacles']:
                try:
                    ox, oy = obstacle['center']
                    gx, gy = self.world_to_grid(ox, oy)
                    if 0 <= gy < grid_h and 0 <= gx < grid_w:
                        obstacle_map[gy, gx] = 1
                        # 扩大障碍物范围
                        for dy in [-1, 0, 1]:
                            for dx in [-1, 0, 1]:
                                ny, nx = gy + dy, gx + dx
                                if 0 <= ny < grid_h and 0 <= nx < grid_w:
                                    obstacle_map[ny, nx] = 1
                except Exception:
                    continue
        
        # 确保玩家和目标位置不是障碍物
        if player_pos:
            px, py = player_pos
            pgx, pgy = self.world_to_grid(px, py)
            if 0 <= pgy < grid_h and 0 <= pgx < grid_w:
                obstacle_map[pgy, pgx] = 0
        
        if target_pos:
            tx, ty = target_pos
            tgx, tgy = self.world_to_grid(tx, ty)
            if 0 <= tgy < grid_h and 0 <= tgx < grid_w:
                obstacle_map[tgy, tgx] = 0
        
        return obstacle_map
    
    def heuristic(self, a, b):
        """启发函数（曼哈顿距离）"""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
    
    def find_path(self, game_state, start_pos, target_pos):
        """A*寻路"""
        start_time = time.time()
        
        if start_pos is None or target_pos is None:
            print("❌ 寻路失败: 起点或目标为空")
            return None, None
        
        obstacle_map = self.create_obstacle_map(game_state, start_pos, target_pos)
        
        start = self.world_to_grid(start_pos[0], start_pos[1])
        goal = self.world_to_grid(target_pos[0], target_pos[1])
        
        print(f"🔍 A*寻路: 从{start}到{goal}")
        
        open_set = []
        heapq.heappush(open_set, (0, start))
        
        came_from = {}
        g_score = {start: 0}
        f_score = {start: self.heuristic(start, goal)}
        
        closed_set = set()
        
        while open_set:
            current = heapq.heappop(open_set)[1]
            
            if current in closed_set:
                continue
            
            if current == goal:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                path.reverse()
                
                world_path, directions = self.path_to_directions(path, start_pos, target_pos)
                
                elapsed = time.time() - start_time
                print(f"✅ 寻路成功: {len(path)}个网格点, {len(directions)}步, 耗时{elapsed:.3f}秒")
                
                return world_path, directions
            
            closed_set.add(current)
            
            for dx, dy, dir_name, cost_mult in self.directions:
                neighbor = (current[0] + dx, current[1] + dy)
                
                if (neighbor[1] < 0 or neighbor[1] >= obstacle_map.shape[0] or
                    neighbor[0] < 0 or neighbor[0] >= obstacle_map.shape[1]):
                    continue
                
                if obstacle_map[neighbor[1], neighbor[0]] == 1:
                    continue
                
                if neighbor in closed_set:
                    continue
                
                tentative_g = g_score[current] + cost_mult
                
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + self.heuristic(neighbor, goal)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
        
        print(f"❌ 寻路失败: 无法找到路径")
        return None, None
    
    def path_to_directions(self, grid_path, start_world, target_world):
        """将网格路径转换为移动方向（每格一步）"""
        if not grid_path:
            return [], []
        
        world_path = []
        directions = []
        
        world_path.append(start_world)
        
        for i in range(1, len(grid_path)):
            prev = grid_path[i-1]
            curr = grid_path[i]
            
            dx = curr[0] - prev[0]
            dy = curr[1] - prev[1]
            
            if dx > 0:
                dir_name = 'right'
            elif dx < 0:
                dir_name = 'left'
            elif dy > 0:
                dir_name = 'down'
            elif dy < 0:
                dir_name = 'up'
            else:
                continue
            
            steps = 1
            
            wx, wy = self.grid_to_world(curr[0], curr[1])
            world_path.append((wx, wy))
            
            directions.extend([dir_name] * steps)
        
        world_path[-1] = target_world
        
        return world_path, directions


class ExploreAgent:
    """探索Agent - 寻路版（强制朝门方向多走三步）"""
    
    def __init__(self, game_interface):
        self.game = game_interface
        
        # 寻路系统
        self.path_finder = PathFinder(grid_size=40)
        
        self.current_room = (6, 6)
        self.previous_room = None
        
        self.memory = {
            'steps_since_decision': 0,
            'rooms_visited': [(6, 6)],
            'last_decision_time': 0,
            'consecutive_failures': 0,
            'last_chosen_door': None,
            'last_chosen_door_coords': None,
            'last_player_position': None,
            'path_sequence': [],
            'current_path_index': 0,
            'path_finding_time': 0,
            'extra_step_done': 0,        # 【修改】从False改为整数计数器
            'door_direction': None,       # 记录门的方向
            'arrival_triggered': False,   # 标记是否触发了到达
        }
        
        # 移动记忆机制
        self.movement_memory = {
            'last_rooms': [],
            'last_directions': [],
            'max_memory': 3,
            'visited_from': {},
            'blocked_directions': set(),
        }
        
        # 门检测阈值
        self.door_threshold = 80
        
        # 探索策略参数
        self.explore_params = {
            'avoid_backtracking': True,
            'prefer_unexplored': True,
            'prefer_closest': True,
        }
        
        # 移动参数
        self.move_params = {
            'step_duration': 0.075,
        }
        
        self.params = {
            'decision_interval': 15,
            'min_decision_interval': 3.0,
            'max_path_length': 40,
            'max_consecutive_failures': 3,
            'arrival_threshold': 150,
            'extra_steps_count': 3,      # 【新增】强制多走三步
        }
        
        self.stats = {
            'decisions_made': 0,
            'actions_executed': 0,
            'rooms_explored': 1,
            'paths_found': 0,
            'paths_failed': 0,
            'avg_path_length': 0,
            'total_path_length': 0,
            'early_stops': 0,
            'extra_steps': 0,            # 多走一步的次数
            'arrivals': 0,                # 到达门的次数
        }
        
        # 方向映射
        self.dir_to_chinese = {'up': '上', 'down': '下', 'left': '左', 'right': '右'}
        self.chinese_to_dir = {'上': 'up', '下': 'down', '左': 'left', '右': 'right'}
        
        print(f"✅ 探索模块初始化完成（强制多走三步版）")
        print(f"   - 记忆机制: 记录最近{self.movement_memory['max_memory']}步移动")
        print(f"   - 寻路算法: A* (网格大小40px)")
        print(f"   - 移动模式: 每格一步，完成后强制朝门方向多走{self.params['extra_steps_count']}步")
        print(f"   - 到达阈值: {self.params['arrival_threshold']}px")
    
    def _get_action_name(self, action_id):
        if hasattr(self.game, 'action_mapper'):
            return self.game.action_mapper.get_action_name(action_id)
        names = {1: "上", 2: "下", 3: "左", 4: "右"}
        return names.get(action_id, f"未知{action_id}")
    
    def should_activate(self, game_state):
        if not game_state:
            return False
        return len(game_state['enemies']['all']) == 0 and len(game_state['tears']['enemy']) == 0
    
    def _detect_doors_from_state(self, game_state):
        """从YOLO检测结果中获取门的方向和位置"""
        doors = []
        if not game_state or not game_state.get('doors') or not game_state.get('player'):
            return doors
        
        player_center = game_state['player']['center']
        if not player_center:
            return doors
        
        frame_height, frame_width = game_state['frame_shape'][:2]
        
        doors_open = game_state['doors'].get('open', [])
        if not doors_open:
            return doors
        
        for door in doors_open:
            try:
                dx, dy = door['center']
                
                # 判断门的方向
                if dy < self.door_threshold:
                    direction = 'up'
                elif dy > frame_height - self.door_threshold:
                    direction = 'down'
                elif dx < self.door_threshold:
                    direction = 'left'
                elif dx > frame_width - self.door_threshold:
                    direction = 'right'
                else:
                    px, py = player_center
                    rel_x = dx - px
                    rel_y = dy - py
                    
                    if abs(rel_y) > abs(rel_x):
                        direction = 'up' if rel_y < -50 else 'down' if rel_y > 50 else None
                    else:
                        direction = 'left' if rel_x < -50 else 'right' if rel_x > 50 else None
                    
                    if direction is None:
                        continue
                
                distance = int(np.sqrt((dx - player_center[0])**2 + (dy - player_center[1])**2))
                
                doors.append({
                    'direction': direction,
                    'center': (int(dx), int(dy)),
                    'distance_to_player': distance,
                    'explored': self._is_direction_explored(direction),
                })
            except Exception:
                continue
        
        # 去重
        unique_doors = {}
        for door in doors:
            if door['direction'] not in unique_doors:
                unique_doors[door['direction']] = door
            elif door['distance_to_player'] < unique_doors[door['direction']]['distance_to_player']:
                unique_doors[door['direction']] = door
        
        result = list(unique_doors.values())
        if result:
            print(f"🚪 检测到门: {[(d['direction'], d['center'], '未探索' if not d['explored'] else '已探索') for d in result]}")
        
        return result
    
    def _is_direction_explored(self, direction):
        """判断某个方向是否已探索"""
        if not self.movement_memory['last_directions']:
            return False
        
        opposite_map = {'up': 'down', 'down': 'up', 'left': 'right', 'right': 'left'}
        opposite = opposite_map.get(direction)
        
        return opposite in self.movement_memory['last_directions']
    
    def _select_best_door(self, doors):
        """规则选择最好的门"""
        if not doors:
            return None
        
        unexplored = [d for d in doors if not d['explored']]
        explored = [d for d in doors if d['explored']]
        
        if unexplored and self.explore_params['prefer_unexplored']:
            return min(unexplored, key=lambda d: d['distance_to_player'])
        
        if explored:
            return min(explored, key=lambda d: d['distance_to_player'])
        
        return min(doors, key=lambda d: d['distance_to_player'])
    
    def update_room_info(self, game_state):
        """更新房间信息"""
        if not game_state or not game_state.get('analysis'):
            return
        
        new_room = game_state['analysis'].get('global_position')
        if new_room is None:
            return
        
        if new_room != self.current_room:
            old_x, old_y = self.current_room
            new_x, new_y = new_room
            direction = None
            
            if new_x > old_x:
                direction = 'right'
            elif new_x < old_x:
                direction = 'left'
            elif new_y > old_y:
                direction = 'down'
            elif new_y < old_y:
                direction = 'up'
            
            self.previous_room = self.current_room
            self.current_room = new_room
            
            if new_room not in self.memory['rooms_visited']:
                self.memory['rooms_visited'].append(new_room)
                self.stats['rooms_explored'] += 1
                print(f"🏠 进入新房间: {new_room}")
            
            if direction:
                self._update_movement_memory(new_room, direction)
                print(f"  移动记忆: {direction} -> {new_room}")
            
            # 进入新房间后，清空所有状态
            self.memory['path_sequence'] = []
            self.memory['current_path_index'] = 0
            self.memory['last_chosen_door'] = None
            self.memory['last_chosen_door_coords'] = None
            self.memory['extra_step_done'] = 0
            self.memory['door_direction'] = None
            self.memory['arrival_triggered'] = False
    
    def _update_movement_memory(self, new_room, direction):
        """更新移动记忆"""
        self.movement_memory['last_directions'].append(direction)
        if len(self.movement_memory['last_directions']) > self.movement_memory['max_memory']:
            self.movement_memory['last_directions'].pop(0)
        
        self.movement_memory['visited_from'][new_room] = direction
        self._update_blocked_directions()
    
    def _update_blocked_directions(self):
        """更新阻塞方向"""
        self.movement_memory['blocked_directions'].clear()
        
        opposite_map = {'up': 'down', 'down': 'up', 'left': 'right', 'right': 'left'}
        
        if len(self.movement_memory['last_directions']) >= 1:
            last_dir = self.movement_memory['last_directions'][-1]
            opposite = opposite_map.get(last_dir)
            if opposite:
                self.movement_memory['blocked_directions'].add(opposite)
    
    def need_new_decision(self):
        """判断是否需要新的路径规划"""
        if self.memory['current_path_index'] < len(self.memory['path_sequence']):
            return False
        
        if time.time() - self.memory.get('last_decision_time', 0) < self.params['min_decision_interval']:
            return False
        
        if self.memory['steps_since_decision'] >= self.params['decision_interval']:
            return True
        
        if self.previous_room != self.current_room:
            return True
        
        if self.memory['consecutive_failures'] >= self.params['max_consecutive_failures']:
            return True
        
        return False
    
    def _check_arrived_at_door(self, game_state):
        """检查是否已经到达目标门"""
        if not game_state or not game_state.get('player'):
            return False
        
        if not self.memory['last_chosen_door_coords']:
            return False
        
        player_pos = game_state['player']['center']
        if not player_pos:
            return False
        
        door_x, door_y = self.memory['last_chosen_door_coords']
        player_x, player_y = player_pos
        
        distance = np.sqrt((player_x - door_x)**2 + (player_y - door_y)**2)
        
        if distance < self.params['arrival_threshold']:
            return True
        
        return False
    
    def plan_path(self, game_state):
        """规划路径"""
        if not game_state or not game_state.get('player'):
            return False
        
        player_pos = game_state['player']['center']
        player_x, player_y = int(player_pos[0]), int(player_pos[1])
        
        doors = self._detect_doors_from_state(game_state)
        if not doors:
            print("🚪 没有检测到门，无法规划路径")
            return False
        
        target_door = self._select_best_door(doors)
        if not target_door:
            print("❌ 无法选择目标门")
            return False
        
        door_pos = target_door['center']
        door_dir = target_door['direction']
        
        print(f"\n🎯 选择目标门: {self.dir_to_chinese[door_dir]} 门, 坐标{door_pos}, 距离{target_door['distance_to_player']}px")
        
        self.memory['last_chosen_door'] = door_dir
        self.memory['last_chosen_door_coords'] = door_pos
        self.memory['last_player_position'] = (player_x, player_y)
        self.memory['extra_step_done'] = 0        # 【修改】初始化为0
        self.memory['door_direction'] = door_dir
        self.memory['arrival_triggered'] = False
        
        path_start_time = time.time()
        world_path, directions = self.path_finder.find_path(game_state, (player_x, player_y), door_pos)
        
        if not directions:
            print(f"❌ 寻路失败")
            self.stats['paths_failed'] += 1
            self.memory['consecutive_failures'] += 1
            return False
        
        if len(directions) > self.params['max_path_length']:
            print(f"⚠️ 路径过长 ({len(directions)}步)，截断到{self.params['max_path_length']}步")
            directions = directions[:self.params['max_path_length']]
        
        self.memory['path_sequence'] = directions
        self.memory['current_path_index'] = 0
        
        path_time = time.time() - path_start_time
        self.memory['path_finding_time'] = path_time
        self.stats['paths_found'] += 1
        self.stats['total_path_length'] += len(directions)
        self.stats['avg_path_length'] = self.stats['total_path_length'] / self.stats['paths_found']
        
        print(f"✅ 路径规划成功: {len(directions)}步, 耗时{path_time:.3f}秒")
        print(f"   路径: {''.join([self.dir_to_chinese[d] for d in directions[:20]])}...")
        
        self.memory['steps_since_decision'] = 0
        self.memory['last_decision_time'] = time.time()
        self.memory['consecutive_failures'] = 0
        self.stats['decisions_made'] += 1
        
        return True
    
    def decide_actions(self, game_state):
        """决策动作序列 - 【关键修改】强制朝门方向多走三步"""
        self.update_room_info(game_state)
        
        # ===== 1. 检查是否已经到达目标门（但不停止，只是标记） =====
        arrived = self._check_arrived_at_door(game_state)
        if arrived and not self.memory['arrival_triggered']:
            print(f"🚪 到达目标门附近！距离: 小于{self.params['arrival_threshold']}px")
            self.memory['arrival_triggered'] = True
            self.stats['arrivals'] += 1
        
        # ===== 2. 【修改】如果有门的方向，且还没多走完三步，强制多走 =====
        if (self.memory['door_direction'] and 
            self.memory['extra_step_done'] < self.params['extra_steps_count']):
            
            current_step = self.memory['extra_step_done'] + 1
            total_steps = self.params['extra_steps_count']
            
            print(f"🚶 强制朝门方向多走一步 ({current_step}/{total_steps}): {self.memory['door_direction']}")
            self.memory['extra_step_done'] += 1
            self.stats['extra_steps'] += 1
            
            # 朝门的方向多走一步
            if hasattr(self.game, 'action_mapper'):
                action_id = self.game.action_mapper.get_move_action(self.memory['door_direction'])
            else:
                action_map = {'up': 1, 'down': 2, 'left': 3, 'right': 4}
                action_id = action_map.get(self.memory['door_direction'], 4)
            
            return [(action_id, self.move_params['step_duration'])]
        
        # ===== 3. 执行路径中的下一步 =====
        if self.memory['current_path_index'] < len(self.memory['path_sequence']):
            
            direction = self.memory['path_sequence'][self.memory['current_path_index']]
            self.memory['current_path_index'] += 1
            
            # 转换方向为动作ID
            if hasattr(self.game, 'action_mapper'):
                action_id = self.game.action_mapper.get_move_action(direction)
            else:
                action_map = {'up': 1, 'down': 2, 'left': 3, 'right': 4}
                action_id = action_map.get(direction, 4)
            
            self.memory['steps_since_decision'] += 1
            self.stats['actions_executed'] += 1
            
            # 显示进度
            progress = f"{self.memory['current_path_index']}/{len(self.memory['path_sequence'])}"
            if self.memory['current_path_index'] == len(self.memory['path_sequence']):
                print(f"🏁 路径执行完成 [{progress}]，准备强制多走{self.params['extra_steps_count']}步")
            elif self.memory['current_path_index'] % 5 == 0:
                print(f"🚶 路径进度: {progress}")
            
            return [(action_id, self.move_params['step_duration'])]
        
        # ===== 4. 如果已经多走完三步，且到达门附近，清理状态 =====
        if (self.memory['extra_step_done'] >= self.params['extra_steps_count'] and 
            self.memory['arrival_triggered']):
            
            print(f"✅ 已完成强制多走{self.params['extra_steps_count']}步并到达门，准备下一目标")
            self.memory['path_sequence'] = []
            self.memory['current_path_index'] = 0
            self.memory['last_chosen_door'] = None
            self.memory['last_chosen_door_coords'] = None
            self.memory['door_direction'] = None
            self.memory['arrival_triggered'] = False
            self.memory['extra_step_done'] = 0
            return []
        
        # ===== 5. 需要新路径规划 =====
        if self.need_new_decision():
            if self.plan_path(game_state):
                return []
            else:
                self.memory['consecutive_failures'] += 1
                return []
        
        return []
    
    def on_room_change(self):
        """房间切换处理"""
        print("\n🚪 房间切换，清空路径")
        self.memory['path_sequence'] = []
        self.memory['current_path_index'] = 0
        self.memory['steps_since_decision'] = 0
        self.memory['consecutive_failures'] = 0
        self.memory['last_chosen_door'] = None
        self.memory['last_chosen_door_coords'] = None
        self.memory['extra_step_done'] = 0
        self.memory['door_direction'] = None
        self.memory['arrival_triggered'] = False
    
    def get_debug_info(self):
        """获取调试信息"""
        path_str = ""
        if self.memory['path_sequence']:
            path_str = ''.join([self.dir_to_chinese.get(d, d) for d in self.memory['path_sequence']])
        
        remaining = len(self.memory['path_sequence']) - self.memory['current_path_index']
        
        return {
            'mode': 'explore',
            'current_room': self.current_room,
            'steps_since_decision': self.memory['steps_since_decision'],
            'path': path_str[:50] + "..." if len(path_str) > 50 else path_str,
            'path_progress': f"{self.memory['current_path_index']}/{len(self.memory['path_sequence'])}",
            'remaining_steps': remaining,
            'last_chosen_door': self.memory['last_chosen_door'],
            'last_chosen_door_coords': self.memory['last_chosen_door_coords'],
            'path_finding_time': f"{self.memory['path_finding_time']:.3f}秒",
            'door_direction': self.memory['door_direction'],
            'extra_step_done': f"{self.memory['extra_step_done']}/{self.params['extra_steps_count']}",
            'arrival_triggered': self.memory['arrival_triggered'],
            'stats': self.stats,
        }