"""
房间树形结构 - 用于准确记录以撒的房间探索状态
包含智能推理功能：选择下一个要探索的未探索房间
"""

import numpy as np
from collections import deque
import time

class RoomNode:
    """房间节点"""
    def __init__(self, coords, parent=None, door_direction=None):
        self.coords = coords  # (x, y) 全局坐标
        self.parent = parent  # 父节点（从哪个房间来的）
        self.children = []    # 子节点（通往哪些房间）
        self.door_direction = door_direction  # 从父节点进入这个房间的方向
        self.status = "unexplored"  # "current"=正处于, "explored"=已探索, "unexplored"=未探索
        self.visit_time = None  # 进入时间（只有current/explored才有）
        
        # 从该房间出发的门状态
        self.doors = {
            'up': {'exists': False, 'leads_to': None},
            'down': {'exists': False, 'leads_to': None},
            'left': {'exists': False, 'leads_to': None},
            'right': {'exists': False, 'leads_to': None}
        }
        
    def __repr__(self):
        status_map = {"current": "🟢", "explored": "✅", "unexplored": "❓"}
        return f"{status_map.get(self.status, '⚪')}{self.coords}"


class RoomTree:
    """
    房间树形结构
    维护房间之间的连接关系，准确记录探索状态
    包含智能推理功能
    """
    
    def __init__(self):
        # 节点字典 {coords: RoomNode}
        self.nodes = {}
        
        # 根节点（初始房间）
        self.root_coords = (6, 6)
        self.root = RoomNode(self.root_coords)
        self.root.status = "current"
        self.root.visit_time = time.time()
        self.nodes[self.root_coords] = self.root
        
        # 当前房间
        self.current_coords = self.root_coords
        
        # 地图边界
        self.min_x = self.max_x = 6
        self.min_y = self.max_y = 6
        
        # 访问历史
        self.visit_history = [(6, 6, time.time())]
        
        # 统计信息
        self.stats = {
            'total_rooms': 1,
            'explored_rooms': 1,
            'unexplored_rooms': 0,
            'dead_ends': 0,
            'branches': 0,
            'max_depth': 0
        }
        
        print(f"🌳 房间树初始化完成")
        print(f"   - 根节点: {self.root_coords}")
        print(f"   - 初始状态: 1个房间")
    
    # ==================== 基础方法 ====================
    
    def get_node(self, coords):
        """获取节点"""
        return self.nodes.get(coords)
    
    def get_current_node(self):
        """获取当前房间节点"""
        return self.nodes.get(self.current_coords)
    
    def has_node(self, coords):
        """检查节点是否存在"""
        return coords in self.nodes
    
    def _get_opposite_direction(self, direction):
        """获取相反方向"""
        opposite = {
            'up': 'down',
            'down': 'up',
            'left': 'right',
            'right': 'left'
        }
        return opposite.get(direction, direction)
    
    def _get_child_coords(self, parent_coords, direction):
        """根据父节点坐标和方向计算子节点坐标"""
        x, y = parent_coords
        if direction == 'up':
            return (x, y - 1)
        elif direction == 'down':
            return (x, y + 1)
        elif direction == 'left':
            return (x - 1, y)
        elif direction == 'right':
            return (x + 1, y)
        return parent_coords
    
    def _update_bounds(self, coords):
        """更新地图边界"""
        x, y = coords
        updated = False
        
        if x < self.min_x:
            self.min_x = x
            updated = True
        if x > self.max_x:
            self.max_x = x
            updated = True
        if y < self.min_y:
            self.min_y = y
            updated = True
        if y > self.max_y:
            self.max_y = y
            updated = True
        
        if updated:
            print(f"📏 地图边界更新: ({self.min_x},{self.min_y})~({self.max_x},{self.max_y})")
    
    def _calculate_depth(self, node):
        """计算节点的深度"""
        depth = 0
        current = node
        while current.parent:
            depth += 1
            current = current.parent
        return depth
    
    def _update_stats(self):
        """更新统计信息"""
        explored = 0
        unexplored = 0
        dead_ends = 0
        branches = 0
        
        for node in self.nodes.values():
            if node.status == "explored" or node.status == "current":
                explored += 1
            elif node.status == "unexplored":
                unexplored += 1
            
            # 计算连接数
            connections = (1 if node.parent else 0) + len(node.children)
            if connections == 1:
                dead_ends += 1
            elif connections >= 3:
                branches += 1
        
        self.stats['explored_rooms'] = explored
        self.stats['unexplored_rooms'] = unexplored
        self.stats['total_rooms'] = explored + unexplored
        self.stats['dead_ends'] = dead_ends
        self.stats['branches'] = branches
    
    # ==================== 核心逻辑 ====================
    
    def enter_room(self, coords, from_direction=None):
        """
        进入房间
        
        Args:
            coords: 进入的房间坐标
            from_direction: 从哪个方向进入（None表示初始房间）
        """
        # 检查房间是否存在
        if coords not in self.nodes:
            print(f"❌ 错误: 尝试进入不存在的房间 {coords}")
            return False
        
        node = self.nodes[coords]
        old_coords = self.current_coords
        
        # 标记之前的当前房间为已探索
        if self.current_coords in self.nodes:
            old_node = self.nodes[self.current_coords]
            if old_node.status == "current":
                old_node.status = "explored"
        
        # 标记新房间为当前
        node.status = "current"
        node.visit_time = time.time()
        self.current_coords = coords
        
        # 记录访问历史
        self.visit_history.append((coords[0], coords[1], time.time()))
        
        # 更新统计
        self._update_stats()
        
        from_info = f"从{from_direction}方向" if from_direction else "初始房间"
        print(f"🚪 进入房间 {coords} {from_info}")
        
        return True
    
    def update_doors_from_detection(self, current_coords, detected_doors):
        """
        根据YOLO检测到的门更新房间信息
        
        Args:
            current_coords: 当前房间坐标
            detected_doors: ['up', 'down', 'left', 'right'] 检测到的门方向列表
        """
        if current_coords not in self.nodes:
            print(f"❌ 错误: 当前房间 {current_coords} 不存在")
            return
        
        current_node = self.nodes[current_coords]
        new_rooms_found = 0
        
        for direction in detected_doors:
            # 标记这个方向有门
            current_node.doors[direction]['exists'] = True
            
            # 计算子节点坐标
            child_coords = self._get_child_coords(current_coords, direction)
            
            # 检查节点是否已存在
            if child_coords in self.nodes:
                # 节点已存在 - 只更新连接
                child_node = self.nodes[child_coords]
                print(f"🔄 确认连接: {current_coords} {direction} → {child_coords}")
            else:
                # 节点不存在 - 创建新节点并标记为未探索
                child_node = RoomNode(child_coords)
                child_node.status = "unexplored"
                self.nodes[child_coords] = child_node
                new_rooms_found += 1
                
                # 更新地图边界
                self._update_bounds(child_coords)
                print(f"🆕 发现新房间: {child_coords} (来自{direction}方向)")
            
            # 建立双向连接
            opposite_dir = self._get_opposite_direction(direction)
            current_node.doors[direction]['leads_to'] = child_coords
            child_node.doors[opposite_dir]['exists'] = True
            child_node.doors[opposite_dir]['leads_to'] = current_coords
            
            # 维护父子关系（只记录一次，避免重复）
            if child_node not in current_node.children:
                current_node.children.append(child_node)
            if child_node.parent is None and child_coords != self.root_coords:
                child_node.parent = current_node
                child_node.door_direction = direction
        
        if new_rooms_found > 0:
            print(f"✨ 本次发现 {new_rooms_found} 个新房间")
        
        # 更新统计
        self._update_stats()
    
    # ==================== 查询方法 ====================
    
    def get_unexplored_doors(self, coords=None):
        """获取当前房间未探索的门方向（有门但没去过）"""
        if coords is None:
            coords = self.current_coords
        
        node = self.nodes.get(coords)
        if not node:
            return []
        
        unexplored = []
        for direction, info in node.doors.items():
            # 有门，且还没去过（leads_to为None或指向未探索房间）
            if info['exists']:
                if info['leads_to'] is None:
                    unexplored.append(direction)
                else:
                    target_node = self.nodes.get(info['leads_to'])
                    if target_node and target_node.status == "unexplored":
                        unexplored.append(direction)
        
        return unexplored
    
    def get_explored_doors(self, coords=None):
        """获取当前房间已探索的门方向"""
        if coords is None:
            coords = self.current_coords
        
        node = self.nodes.get(coords)
        if not node:
            return []
        
        explored = []
        for direction, info in node.doors.items():
            if info['exists'] and info['leads_to'] is not None:
                target_node = self.nodes.get(info['leads_to'])
                if target_node and target_node.status in ["explored", "current"]:
                    explored.append(direction)
        
        return explored
    
    def get_all_doors(self, coords=None):
        """获取所有门的状态"""
        if coords is None:
            coords = self.current_coords
        
        node = self.nodes.get(coords)
        if not node:
            return {}
        
        return node.doors.copy()
    
    # ==================== 推理方法 ====================
    
    def select_next_target(self, current_coords=None):
        """
        选择下一个要探索的未探索房间
        
        策略：
        1. 优先选择当前房间的未探索门（直接可达）
        2. 其次选择最近的未探索房间（BFS距离最短）
        3. 如果距离相同，优先选择分支少的路径（避免死胡同）
        4. 考虑地图边界方向（边缘更可能有新房间）
        
        Returns:
            tuple: (target_coords, path_directions, reason)
        """
        if current_coords is None:
            current_coords = self.current_coords
        
        current_node = self.nodes.get(current_coords)
        if not current_node:
            return None, [], "无效的当前房间"
        
        # === 策略1：检查当前房间是否有未探索的门 ===
        unexplored_doors = self.get_unexplored_doors(current_coords)
        if unexplored_doors:
            # 如果有多个未探索门，选择优先级最高的方向
            best_door = self._select_best_door_direction(unexplored_doors, current_coords)
            target_coords = self._get_child_coords(current_coords, best_door)
            return target_coords, [best_door], f"当前房间的{best_door}方向未探索"
        
        # === 策略2：BFS搜索最近的未探索房间 ===
        result = self._bfs_nearest_unexplored(current_coords)
        if result:
            target_coords, path = result
            # 获取目标房间的状态用于显示
            target_node = self.nodes.get(target_coords)
            status = "未探索" if target_node and target_node.status == "unexplored" else "未知"
            return target_coords, path, f"BFS找到最近{status}房间{target_coords}"
        
        # === 策略3：如果没有未探索房间，返回中心区域 ===
        return self._select_strategic_position(current_coords)
    
    def _select_best_door_direction(self, unexplored_doors, current_coords):
        """
        从多个未探索门中选择最佳方向
        
        考虑因素：
        - 朝向地图边界的方向优先（可能探索新区域）
        - 远离死胡同的方向优先
        """
        if len(unexplored_doors) == 1:
            return unexplored_doors[0]
        
        # 计算每个方向的得分
        scores = {}
        for direction in unexplored_doors:
            score = 0
            
            # 1. 朝向边界加分
            x, y = current_coords
            if direction == 'left' and x > self.min_x:
                score += 2
            elif direction == 'right' and x < self.max_x:
                score += 2
            elif direction == 'up' and y > self.min_y:
                score += 2
            elif direction == 'down' and y < self.max_y:
                score += 2
            
            # 2. 远离死胡同（检查这个方向通往的房间）
            target_coords = self._get_child_coords(current_coords, direction)
            if target_coords in self.nodes:
                target_node = self.nodes[target_coords]
                # 如果目标房间有多个未探索门，加分
                target_unexplored = self.get_unexplored_doors(target_coords)
                score += len(target_unexplored) * 3
            
            scores[direction] = score
        
        # 选择得分最高的方向
        return max(scores.items(), key=lambda x: x[1])[0]
    
    def _bfs_nearest_unexplored(self, start_coords, max_depth=15):
        """
        BFS搜索最近的未探索房间
        
        返回: (target_coords, path_directions) 或 None
        """
        # BFS队列: (当前坐标, 路径方向列表)
        queue = deque([(start_coords, [])])
        visited = {start_coords}
        
        while queue:
            coords, path = queue.popleft()
            
            # 如果已经搜索到一定深度还没找到，停止
            if len(path) > max_depth:
                continue
            
            node = self.nodes.get(coords)
            if not node:
                continue
            
            # 检查这个房间是否有未探索的门
            unexplored = self.get_unexplored_doors(coords)
            if unexplored:
                # 找到目标，计算完整路径
                target_coords = self._get_child_coords(coords, unexplored[0])
                full_path = path + [unexplored[0]]
                return (target_coords, full_path)
            
            # 继续BFS搜索已探索的方向
            for direction in self.get_explored_doors(coords):
                next_coords = node.doors[direction]['leads_to']
                if next_coords and next_coords not in visited:
                    visited.add(next_coords)
                    queue.append((next_coords, path + [direction]))
        
        return None
    
    def _select_strategic_position(self, current_coords):
        """
        没有未探索房间时，选择战略性位置（中心区域或分支点）
        """
        # 如果没有未探索房间，返回中心区域
        if (6, 6) in self.nodes:
            # 计算到中心区域的路径
            result = self._bfs_shortest_path(current_coords, (6, 6))
            if result:
                target_coords, path = result
                return target_coords, path, "返回中心区域"
        
        return None, [], "没有未探索房间"
    
    def _bfs_shortest_path(self, start_coords, target_coords):
        """BFS搜索最短路径"""
        if start_coords == target_coords:
            return (target_coords, [])
        
        queue = deque([(start_coords, [])])
        visited = {start_coords}
        
        while queue:
            coords, path = queue.popleft()
            
            node = self.nodes.get(coords)
            if not node:
                continue
            
            for direction in self.get_explored_doors(coords):
                next_coords = node.doors[direction]['leads_to']
                if next_coords and next_coords not in visited:
                    if next_coords == target_coords:
                        return (target_coords, path + [direction])
                    
                    visited.add(next_coords)
                    queue.append((next_coords, path + [direction]))
        
        return None
    
    # ==================== 调试方法 ====================
    
    def to_grid(self):
        """转换为网格表示（与 AdjustedPositionTracker 兼容）"""
        grid = np.zeros((13, 13), dtype=int)
        
        for coords, node in self.nodes.items():
            x, y = coords
            if 0 <= x < 13 and 0 <= y < 13:
                if node.status == "current":
                    grid[y, x] = 2
                elif node.status == "explored":
                    grid[y, x] = 1
                # unexplored 保持为 0
        
        return grid
    
    def print_tree(self, node=None, level=0, prefix="", is_last=True):
        """打印树形结构"""
        if node is None:
            node = self.root
            print("\n🌳 房间树结构:")
            print(f"   总房间: {self.stats['total_rooms']} (探索:{self.stats['explored_rooms']}, 未探索:{self.stats['unexplored_rooms']})")
        
        # 当前房间标记
        marker = " [当前]" if node.coords == self.current_coords else ""
        
        # 门状态
        doors_status = []
        for d, info in node.doors.items():
            if info['exists']:
                dest = info['leads_to']
                if dest:
                    doors_status.append(f"{d}→{dest}")
                else:
                    doors_status.append(f"{d}?")
        
        doors_str = f" 门: {', '.join(doors_status)}" if doors_status else " 无门"
        
        # 打印当前节点
        if level == 0:
            print(f"└── {node}{marker}{doors_str}")
        else:
            branch = "└── " if is_last else "├── "
            print(f"{prefix}{branch}{node}{marker}{doors_str}")
        
        # 打印子节点
        child_prefix = prefix + ("    " if is_last else "│   ")
        for i, child in enumerate(node.children):
            # 避免重复打印（双向连接）
            if child.parent == node:
                self.print_tree(child, level+1, child_prefix, i == len(node.children)-1)
    
    def get_debug_info(self):
        """获取调试信息"""
        current_node = self.get_current_node()
        unexplored_doors = self.get_unexplored_doors()
        
        return {
            'current_room': self.current_coords,
            'current_status': current_node.status if current_node else "unknown",
            'total_rooms': self.stats['total_rooms'],
            'explored_rooms': self.stats['explored_rooms'],
            'unexplored_rooms': self.stats['unexplored_rooms'],
            'dead_ends': self.stats['dead_ends'],
            'branches': self.stats['branches'],
            'max_depth': self.stats['max_depth'],
            'bounds': ((self.min_x, self.min_y), (self.max_x, self.max_y)),
            'unexplored_doors': unexplored_doors,
            'visit_history': self.visit_history[-5:]  # 最近5次
        }


# ==================== 测试代码 ====================
if __name__ == "__main__":
    print("测试房间树结构...")
    
    tree = RoomTree()
    
    # 模拟初始房间检测到门
    print("\n--- 初始房间(6,6)检测到门 ---")
    tree.update_doors_from_detection((6, 6), ['up', 'right'])
    
    # 进入上方房间
    print("\n--- 进入上方房间(6,5) ---")
    tree.enter_room((6, 5), 'up')
    
    # (6,5)检测到门
    print("\n--- 房间(6,5)检测到门 ---")
    tree.update_doors_from_detection((6, 5), ['left', 'right'])
    
    # 推理下一个目标
    print("\n--- 推理下一个目标 ---")
    target, path, reason = tree.select_next_target()
    print(f"推理结果: {target}, 路径:{path}, 原因:{reason}")
    
    # 打印树结构
    tree.print_tree()
    
    print(f"\n调试信息: {tree.get_debug_info()}")