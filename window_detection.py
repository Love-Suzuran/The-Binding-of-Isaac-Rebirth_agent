# window_detection.py
"""
以撒游戏调整阈值位置跟踪程序
调整检测阈值：横向1000像素，纵向600像素
"""

import cv2
import numpy as np
import win32gui
import mss
import time
from ultralytics import YOLO

class IsaacWindowCapture:
    def __init__(self, window_title_part='Binding of Isaac: Rebirth'):
        self.window_title_part = window_title_part
        self.hwnd = None
        self.capture_region = None
        self.find_window()
        
        if not self.hwnd:
            raise Exception(f"未找到窗口")
        
        self.setup_capture_region()
        
    def find_window(self):
        def enum_callback(hwnd, results):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if self.window_title_part.lower() in title.lower():
                    results.append(hwnd)
            return True
        
        windows = []
        win32gui.EnumWindows(enum_callback, windows)
        
        if windows:
            self.hwnd = windows[0]
        else:
            self.list_all_visible_windows()
    
    def list_all_visible_windows(self):
        def enum_all(hwnd, results):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    results.append((hwnd, title))
            return True
        
        all_windows = []
        win32gui.EnumWindows(enum_all, all_windows)
        
        if all_windows:
            self.hwnd = all_windows[0][0]
    
    def setup_capture_region(self):
        window_rect = win32gui.GetWindowRect(self.hwnd)
        left, top, right, bottom = window_rect
        
        client_rect = win32gui.GetClientRect(self.hwnd)
        client_left_top = win32gui.ClientToScreen(self.hwnd, (0, 0))
        
        self.capture_region = {
            "left": client_left_top[0],
            "top": client_left_top[1],
            "width": client_rect[2],
            "height": client_rect[3]
        }
        
        if (self.capture_region["width"] <= 0 or 
            self.capture_region["height"] <= 0):
            
            self.capture_region = {
                "left": left + 8,
                "top": top + 31,
                "width": (right - left) - 16,
                "height": (bottom - top) - 39
            }
    
    def capture_frame(self):
        if not self.capture_region:
            return None
        
        try:
            with mss.mss() as sct:
                monitor = {
                    "top": self.capture_region["top"],
                    "left": self.capture_region["left"],
                    "width": self.capture_region["width"],
                    "height": self.capture_region["height"]
                }
                
                screenshot = sct.grab(monitor)
                frame = np.array(screenshot)
                return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        except:
            return None
    
    def is_window_active(self):
        return self.hwnd and win32gui.IsWindow(self.hwnd)

class AdjustedPositionTracker:
    def __init__(self):
        # 全局地图 - 0=未探索, 1=已探索, 2=当前
        self.global_grid = np.zeros((13, 13), dtype=int)
        self.global_position = (6, 6)  # 初始位置
        self.global_grid[6, 6] = 2  # 初始房间为当前房间
        
        # 记录上一帧的玩家位置和时间
        self.prev_player_pos = None
        self.prev_player_time = None
        
        # 调整后的检测阈值
        self.horizontal_threshold = 200  # 横向1000像素
        self.vertical_threshold = 200     # 纵向600像素
        self.min_time_threshold = 0.2     # 位移必须在0.2秒内完成
        self.cooldown_time = 0.5          # 房间切换后0.5秒冷却
        
        # 移动状态记录
        self.last_move_time = 0  # 上次房间切换时间
        self.move_count = 0      # 房间切换次数
        
        # ===== 新增：玩家死亡标记 =====
        self.player_dead = False
        self.death_position = None
        
        # 调试信息
        self.last_detection_info = ""
        self.window_width = 0
        self.window_height = 0
        
        # ===== 新增：保存最近的分析结果 =====
        self.last_analysis = None
        
        print(f"初始化: 全局位置({self.global_position}), 状态: 2")
        print(f"调整检测阈值: 横向{self.horizontal_threshold}px, 纵向{self.vertical_threshold}px")
        print(f"时间要求: 位移<{self.min_time_threshold}s, 冷却{self.cooldown_time}s")
    
    def update_window_size(self, width, height):
        """更新窗口尺寸"""
        self.window_width = width
        self.window_height = height
    
    def get_player_position(self, detections):
        """从YOLO检测结果中获取玩家位置"""
        player_pos = None
        
        if detections is not None and detections.boxes is not None:
            for i, box in enumerate(detections.boxes):
                if int(box.cls[0]) == 15:  # 玩家class_id=15
                    x_center = (box.xyxy[0][0] + box.xyxy[0][2]) / 2
                    y_center = (box.xyxy[0][1] + box.xyxy[0][3]) / 2
                    player_pos = (float(x_center), float(y_center))
                    break
        
        return player_pos
    
    def detect_movement_by_player(self, current_player_pos, current_time):
        """通过玩家位置变化检测移动方向（调整阈值版）"""
        if current_player_pos is None or self.prev_player_pos is None:
            return None, None
        
        # 检查冷却时间
        if current_time - self.last_move_time < self.cooldown_time:
            return None, None
        
        curr_x, curr_y = current_player_pos
        prev_x, prev_y = self.prev_player_pos
        prev_time = self.prev_player_time
        
        if prev_time is None:
            return None, None
        
        # 计算位移时间和距离
        time_diff = current_time - prev_time
        dx = curr_x - prev_x
        dy = curr_y - prev_y
        abs_dx = abs(dx)
        abs_dy = abs(dy)
        
        # 重置检测信息
        self.last_detection_info = ""
        
        # 检查是否满足阈值条件
        direction = None
        new_position = None
        
        # 1. 检测向下移动
        if (abs_dy >= self.vertical_threshold and
            time_diff < self.min_time_threshold and
            dy > 0):
            
            direction = "down"
            new_position = (self.global_position[0], self.global_position[1] + 1)
            self.last_detection_info = f"向下移动 {abs_dy:.0f}px, 时间:{time_diff:.2f}s"
        
        # 2. 检测向上移动
        elif (abs_dy >= self.vertical_threshold and
              time_diff < self.min_time_threshold and
              dy < 0):
            
            direction = "up"
            new_position = (self.global_position[0], self.global_position[1] - 1)
            self.last_detection_info = f"向上移动 {abs_dy:.0f}px, 时间:{time_diff:.2f}s"
        
        # 3. 检测向右移动
        elif (abs_dx >= self.horizontal_threshold and
              time_diff < self.min_time_threshold and
              dx > 0):
            
            direction = "right"
            new_position = (self.global_position[0] + 1, self.global_position[1])
            self.last_detection_info = f"向右移动 {abs_dx:.0f}px, 时间:{time_diff:.2f}s"
        
        # 4. 检测向左移动
        elif (abs_dx >= self.horizontal_threshold and
              time_diff < self.min_time_threshold and
              dx < 0):
            
            direction = "left"
            new_position = (self.global_position[0] - 1, self.global_position[1])
            self.last_detection_info = f"向左移动 {abs_dx:.0f}px, 时间:{time_diff:.2f}s"
        
        if direction is not None:
            self.last_move_time = current_time
            self.move_count += 1
        
        return direction, new_position
    
    def update_position(self, new_position):
        """更新位置：旧位置2→1，新位置?→2"""
        if new_position is None:
            return
        
        new_x, new_y = new_position
        old_x, old_y = self.global_position
        
        # 1. 将原来的当前房间(2)改为已探索(1)
        if 0 <= old_x < 13 and 0 <= old_y < 13:
            self.global_grid[old_y, old_x] = 1
        
        # 2. 将新位置改为当前房间(2)
        if 0 <= new_x < 13 and 0 <= new_y < 13:
            old_status = self.global_grid[new_y, new_x]
            self.global_grid[new_y, new_x] = 2
            self.global_position = (new_x, new_y)
            
            status_text = {
                0: "未探索→当前",
                1: "已探索→当前",
                2: "当前→当前(错误)"
            }.get(old_status, f"{old_status}→2")
            
            print(f"房间切换: ({old_x},{old_y})→({new_x},{new_y}) {status_text}")
    
    def set_player_dead(self, is_dead):
        """设置玩家死亡状态 - 死亡时完全重置地图"""
        if is_dead and not self.player_dead:
            # 刚死亡，记录死亡时的位置
            self.death_position = self.global_position
            self.player_dead = True
            print(f"💀 玩家在房间 {self.death_position} 死亡")
            
        elif not is_dead and self.player_dead:
            # 复活，完全重置地图到初始状态
            print(f"✨ 玩家复活，完全重置地图到初始状态")
            
            # 完全重置地图网格
            self.global_grid = np.zeros((13, 13), dtype=int)
            self.global_grid[6, 6] = 2  # 只有当前房间是2
            self.global_position = (6, 6)
            
            # 重置所有相关状态
            self.prev_player_pos = None
            self.prev_player_time = None
            self.last_move_time = 0
            self.move_count = 0
            self.death_position = None
            
            print(f"  重置完成: 当前位置({6},{6})，其他所有房间未探索")
            
        self.player_dead = is_dead
    
    def analyze_frame(self, detections, frame_shape):
        """分析当前帧并更新位置"""
        current_time = time.time()
        
        # 更新窗口尺寸
        if frame_shape is not None:
            height, width = frame_shape[:2]
            self.update_window_size(width, height)
        
        # 1. 获取当前玩家位置
        current_player_pos = self.get_player_position(detections)
        
        # 2. 检测移动并更新
        updated = False
        direction = None
        new_position = None
        
        # 只有在玩家未死亡时才更新位置
        if not self.player_dead:
            if self.prev_player_pos is not None and current_player_pos is not None:
                direction, new_position = self.detect_movement_by_player(current_player_pos, current_time)
                
                if direction is not None and new_position is not None:
                    print(f"\n检测到房间切换: {self.last_detection_info}")
                    self.update_position(new_position)
                    updated = True
            elif current_player_pos is not None:
                # 第一帧：初始化
                print("第一帧: 玩家位置初始化")
                updated = True
        
        # 3. 保存当前玩家位置和时间作为参考
        if current_player_pos is not None:
            self.prev_player_pos = current_player_pos
            self.prev_player_time = current_time
        
        # 计算冷却剩余时间
        cooldown_remaining = max(0, self.cooldown_time - (current_time - self.last_move_time))
        
        # ===== 构建分析结果 =====
        self.last_analysis = {
            'global_position': self.global_position,
            'global_grid': self.global_grid.copy(),
            'stats': {
                'current': np.sum(self.global_grid == 2),
                'visited': np.sum(self.global_grid == 1),
                'total_moves': self.move_count
            },
            'updated': updated,
            'player_position': current_player_pos,
            'direction': direction,
            'move_count': self.move_count,
            'cooldown_remaining': cooldown_remaining,
            'detection_info': self.last_detection_info,
            'window_size': (self.window_width, self.window_height),
            'player_dead': self.player_dead,
            'room_just_changed': direction is not None  # 【新增】房间刚刚切换标记
        }
        
        return self.last_analysis
    
    def draw_display(self, frame, analysis):
        """绘制显示信息到帧上"""
        display = frame.copy()
        
        # 显示全局位置
        gx, gy = analysis['global_position']
        cv2.putText(display, f"Position: ({gx}, {gy})", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # 显示统计信息
        stats = analysis['stats']
        cv2.putText(display, f"Current: {stats['current']}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
        cv2.putText(display, f"Visited: {stats['visited']}", (10, 80),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
        cv2.putText(display, f"Moves: {stats['total_moves']}", (10, 100),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        # 显示窗口尺寸
        win_width, win_height = analysis['window_size']
        cv2.putText(display, f"Window: {win_width}x{win_height}", (10, 125),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        # 显示玩家位置
        if analysis['player_position']:
            px, py = analysis['player_position']
            cv2.putText(display, f"Player: ({px:.0f}, {py:.0f})", (10, 150),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 1)
        
        # 显示移动方向
        if analysis['direction']:
            cv2.putText(display, f"Last Move: {analysis['direction']}", (10, 175),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # 显示检测信息
        if analysis['detection_info']:
            cv2.putText(display, f"Switch: {analysis['detection_info']}", (10, 200),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # 显示阈值信息
        cv2.putText(display, f"Thresholds: H={self.horizontal_threshold}px, V={self.vertical_threshold}px", 
                   (10, 225), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        
        # 显示冷却时间
        cooldown = analysis['cooldown_remaining']
        if cooldown > 0:
            cv2.putText(display, f"Cooldown: {cooldown:.2f}s", (10, 250),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 100, 0), 1)
        else:
            cv2.putText(display, "Cooldown: Ready", (10, 250),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # 显示死亡状态
        if analysis['player_dead']:
            cv2.putText(display, "💀 PLAYER DEAD", (10, 280),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # 显示房间切换标记
        if analysis.get('room_just_changed'):
            cv2.putText(display, "🏠 ROOM CHANGED!", (10, 310),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # 显示二维数组
        cv2.putText(display, "Memory Map (13x13):", (10, 345),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # 显示列号
        start_y = 365
        col_text = "   "
        for col in range(13):
            col_text += f"{col:2} "
        cv2.putText(display, col_text, (10, start_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 255), 1)
        
        # 显示网格内容（只显示中心区域）
        grid_display = analysis['global_grid']
        display_rows = 7
        display_cols = 7
        
        center_x, center_y = self.global_position
        start_row = max(0, center_y - 3)
        start_col = max(0, center_x - 3)
        
        for row_offset in range(display_rows):
            actual_row = start_row + row_offset
            if actual_row >= 13:
                break
                
            row_text = f"{actual_row:2}: "
            for col_offset in range(display_cols):
                actual_col = start_col + col_offset
                if actual_col >= 13:
                    break
                    
                status = grid_display[actual_row, actual_col]
                if status == 2:
                    row_text += " C "
                elif status == 1:
                    row_text += " V "
                else:
                    row_text += " . "
            
            y_pos = start_y + 15 + row_offset * 15
            cv2.putText(display, row_text, (10, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 255), 1)
        
        # 显示图例
        legend_y = start_y + 15 * display_rows + 10
        cv2.putText(display, "图例: C=当前(2) V=已探索(1) .=未探索(0)", (10, legend_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        
        return display