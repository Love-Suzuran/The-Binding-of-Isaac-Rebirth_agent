# main.py - 修复版（正确处理战斗模块返回的列表）
"""
以撒的结合 规则Agent主程序
修复版：正确处理战斗模块返回的动作列表
"""
import cv2
import time
import numpy as np
import argparse
import sys
from collections import deque

# 导入自定义模块
from isaac_game_interface import IsaacGameInterface
from agent_combat import CombatAgent
from agent_explore_vlm import ExploreAgent
from agent_controller import IsaacAgentController

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='以撒的结合规则Agent')
    
    # 窗口参数
    parser.add_argument('--window', type=str, default='Binding of Isaac: Rebirth',
                       help='游戏窗口标题')
    parser.add_argument('--render', action='store_true', help='显示调试窗口')
    parser.add_argument('--fps', type=int, default=30, help='目标FPS')
    
    # 死亡检测参数
    parser.add_argument('--missing-threshold', type=int, default=30,
                       help='玩家消失多少帧判定死亡')
    
    return parser.parse_args()

class IsaacAgent:
    """主Agent类"""
    
    def __init__(self, args):
        # 保存参数
        self.args = args
        self.last_action = 0  # 记录上一次执行的动作
        
        # 创建游戏接口
        self.game = IsaacGameInterface(window_title=args.window)
        
        # 创建探索Agent
        print("\n🤖 使用寻路探索模式")
        self.explore = ExploreAgent(game_interface=self.game)
        
        # 创建战斗Agent
        self.combat = CombatAgent(self.game)
        
        # 创建控制器
        self.controller = IsaacAgentController(self.game, self.combat, self.explore)
        
        # 设置死亡检测阈值
        self.controller.player_missing_threshold = args.missing_threshold
        
        # 运行状态
        self.running = True
        self.paused = False
        self.step_count = 0
        self.start_time = time.time()
        
        # FPS控制
        self.target_fps = args.fps
        self.frame_time = 1.0 / self.target_fps
        
        # 性能统计
        self.fps_history = deque(maxlen=60)
        self.latency_history = deque(maxlen=60)
        
        # 渲染标志
        self._render_enabled = args.render
        
        # 创建预览窗口
        if self._render_enabled:
            cv2.namedWindow("Isaac Agent", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Isaac Agent", 800, 600)
        
        # 打印启动信息
        self._print_startup_info()
    
    def _print_startup_info(self):
        """打印启动信息"""
        print("\n" + "="*60)
        print("🎮 以撒的结合 规则Agent (修复版)")
        print("="*60)
        print(f"📊 目标FPS: {self.target_fps}")
        print(f"🤖 探索模式: 寻路版 (A*算法)")
        print(f"💀 死亡检测: 玩家消失{self.args.missing_threshold}帧")
        print(f"🎮 游戏窗口: {self.args.window}")
        print(f"🖥️  渲染: {'开启' if self.args.render else '关闭'}")
        print("="*60)
        print("快捷键: Q - 退出")
        print("="*60)
    
    def run(self):
        """主循环"""
        print("\n🚀 开始运行...\n")
        
        frame_count = 0
        last_status_time = time.time()
        last_fps_time = time.time()
        fps_counter = 0
        
        while self.running:
            loop_start = time.time()
            
            # 处理键盘输入
            self._handle_keyboard()
            
            if not self.paused:
                # 1. 获取游戏状态
                game_state = self.game.get_game_state()
                
                if game_state is None:
                    time.sleep(0.5)
                    continue
                
                # 2. 决策动作
                actions = self.controller.decide_actions(game_state)
                
                # 3. 执行动作 - 【修复】正确处理各种返回格式
                if actions:
                    # 【修复】确保actions是列表
                    if not isinstance(actions, list):
                        actions = [actions]
                    
                    for action in actions:
                        # 【修复】处理特殊指令
                        if isinstance(action, str):
                            if action == 'wait':
                                time.sleep(0.1)
                            continue
                        
                        # 【修复】确保action是元组且有两个元素
                        if isinstance(action, tuple) and len(action) == 2:
                            action_id, duration = action
                            # 【关键修复】确保action_id是整数
                            if isinstance(action_id, int):
                                self.game.execute_action(action_id, duration)
                                self.last_action = action_id
                            else:
                                print(f"⚠️ 无效动作ID类型: {type(action_id)}")
                        else:
                            print(f"⚠️ 无效动作格式: {action}")
                    
                    frame_count += len(actions)
                else:
                    # 没有动作时，短时间休眠
                    time.sleep(0.01)
                    frame_count += 1
                
                # 4. 更新统计
                self.step_count += 1
                fps_counter += 1
                
                # 5. 渲染调试窗口
                if self._render_enabled:
                    self._render_debug(game_state)
                    cv2.waitKey(1)
                
                # 6. FPS控制
                elapsed = time.time() - loop_start
                if elapsed < self.frame_time:
                    time.sleep(self.frame_time - elapsed)
                
                # 7. 计算实时FPS
                current_time = time.time()
                if current_time - last_fps_time >= 1.0:
                    real_fps = fps_counter / (current_time - last_fps_time)
                    self.fps_history.append(real_fps)
                    latency = (current_time - last_fps_time) * 1000 / fps_counter
                    self.latency_history.append(latency)
                    fps_counter = 0
                    last_fps_time = current_time
                
                # 8. 定期显示简单状态（每30秒）
                if current_time - last_status_time >= 30.0:
                    mode = self.controller.current_mode
                    print(f"📊 运行中... 步数: {self.step_count}, 模式: {mode}")
                    last_status_time = current_time
            
            else:
                # 暂停时
                time.sleep(0.1)
    
    def _handle_keyboard(self):
        """处理键盘输入"""
        key = cv2.waitKey(1) & 0xFF if self._render_enabled else -1
        
        if key == ord('q'):
            print("\n👋 用户退出")
            self.running = False
    
    def _render_debug(self, game_state):
        """渲染调试信息"""
        if game_state is None or game_state.get('frame') is None:
            return
        
        frame = game_state['frame'].copy()
        h, w = frame.shape[:2]
        
        # 获取控制器调试信息
        ctrl_info = self.controller.get_debug_info()
        
        # 显示当前模式
        mode = ctrl_info.get('mode', 'unknown')
        mode_color = (0, 255, 0) if mode == 'explore' else (0, 0, 255)
        cv2.putText(frame, f"Mode: {mode}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, mode_color, 2)
        
        # 显示房间位置
        room = ctrl_info.get('last_room', (6, 6))
        cv2.putText(frame, f"Room: {room}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        # 显示死亡状态
        if ctrl_info.get('death_detected', False):
            cv2.putText(frame, "💀 DEAD", (10, 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 3)
        
        # 显示敌人数量
        enemies = game_state.get('enemies', {})
        enemy_count = len(enemies.get('all', []))
        cv2.putText(frame, f"Enemies: {enemy_count}", (10, 120),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 1)
        
        # 显示地刺数量
        spike_count = len(enemies.get('other', []))
        cv2.putText(frame, f"Spikes: {spike_count}", (10, 145),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 1)
        
        # 显示子弹数量
        tears = game_state.get('tears', {})
        tear_count = len(tears.get('enemy', []))
        cv2.putText(frame, f"Tears: {tear_count}", (10, 170),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 100, 255), 1)
        
        # 如果探索模块有路径信息，显示路径进度
        if hasattr(self.explore, 'get_debug_info'):
            explore_info = self.explore.get_debug_info()
            path_progress = explore_info.get('path_progress', '0/0')
            cv2.putText(frame, f"Path: {path_progress}", (10, 195),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        # 显示战斗模块的连发状态
        if mode == 'combat' and hasattr(self.combat, 'shoot_counter'):
            cv2.putText(frame, f"Burst: {self.combat.shoot_counter}/5", (10, 220),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 165, 0), 1)
            if self.combat.in_burst_cooldown:
                cv2.putText(frame, "Cooldown", (10, 240),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
        
        cv2.imshow("Isaac Agent", frame)
    
    def close(self):
        """关闭接口"""
        if self._render_enabled:
            cv2.destroyAllWindows()
        self.game.close()
        print(f"\n📊 统计: 步数={self.step_count}")

def main():
    """主函数"""
    args = parse_args()
    
    # 打印参数
    print("\n" + "="*60)
    print("🎮 以撒的结合 规则Agent (修复版)")
    print("="*60)
    print(f"📊 运行参数:")
    print(f"   - 目标FPS: {args.fps}")
    print(f"   - 死亡检测阈值: {args.missing_threshold}帧")
    print(f"   - 渲染: {'开启' if args.render else '关闭'}")
    print("="*60)
    
    agent = None
    try:
        # 创建Agent
        agent = IsaacAgent(args)
        
        # 运行
        agent.run()
        
    except KeyboardInterrupt:
        print("\n\n👋 用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理
        if agent:
            agent.close()
        cv2.destroyAllWindows()
        print("\n✅ 程序退出")

if __name__ == "__main__":
    main()