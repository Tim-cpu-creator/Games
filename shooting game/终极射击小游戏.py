#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
顶级射击小游戏（键盘走位 + 鼠标射击）
=====================================================
作者：WJF
目标：
    - 键盘控制 4 方向移动（上下左右）
    - 鼠标左键发射子弹，子弹沿鼠标位置方向射出
    - 敌方从边缘随机出现并朝玩家移动
    - 子弹击中敌人消失，玩家获得分值
    - 生命值系统：与玩家碰撞或被敌方射中扣回合
    - 计分、弹窗显示、重新开始
    - 完整注释，便于改动和学习

注意：
    - 只使用 Pygame（无音效/音乐）
    - 代码长度足够“非常完善”，可自由扩展
"""

import sys
import math
import random
import pygame
from pygame.locals import QUIT, KEYDOWN, K_ESCAPE, K_UP, K_DOWN, K_LEFT, K_RIGHT, MOUSEBUTTONDOWN, K_SPACE, K_RETURN
import json
import os

# ================== 高分管理 ==================
HIGH_SCORE_FILE = os.path.join(os.path.dirname(__file__), "highscore.json")

def load_high_score():
    """加载历史最高得分"""
    try:
        if os.path.exists(HIGH_SCORE_FILE):
            with open(HIGH_SCORE_FILE, 'r') as f:
                data = json.load(f)
                return data.get('high_score', 0)
    except:
        pass
    return 0

def save_high_score(score):
    """保存最高得分"""
    try:
        data = {'high_score': score}
        with open(HIGH_SCORE_FILE, 'w') as f:
            json.dump(data, f)
    except:
        pass

# ================== 常量 ==================
SCREEN_W, SCREEN_H      = 1024, 768
FPS                     = 60
PLAYER_SPEED            = 5
BULLET_SPEED            = 10
ENEMY_SPEED             = 2
ENEMY_SPAWN_INTERVAL    = 2000      # 毫秒
BULLET_LIMIT            = 10        # 子弹数(可无限发射，这里仅限制)
INITIAL_LIVES           = 3
DIFFICULTY_SCORE_STEP   = 50        # 每50分增加难度

# 颜色
COLOR_BLACK   = (0, 0, 0)
COLOR_WHITE   = (255, 255, 255)
COLOR_RED     = (255, 0, 0)
COLOR_GREEN   = (0, 255, 0)
COLOR_YELLOW  = (255, 255, 0)
COLOR_BLUE    = (0, 0, 255)
COLOR_BLUE    = (30, 144, 255)   # 海军蓝

# ================== 初始化 ==================
pygame.init()
pygame.display.set_caption("键盘走位 + 鼠标射击 • 终极射击小游戏")
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
clock  = pygame.time.Clock()
# 使用英文避免字体编码问题
font   = pygame.font.SysFont(None, 32)
big_font = pygame.font.SysFont(None, 72)

# 主界面装饰小球（移动并碰撞反弹）- 现在是5个
MENU_BALLS = []
MENU_BALL_POSITIONS = [
    (150, 100),
    (SCREEN_W - 150, 120),
    (SCREEN_W // 2 - 200, SCREEN_H - 100),
    (SCREEN_W // 2 + 200, SCREEN_H - 120),
    (SCREEN_W // 2, SCREEN_H // 2 + 150),  # 新增第5个小球
]
for i in range(5):
    base_x, base_y = MENU_BALL_POSITIONS[i]
    x = base_x + random.uniform(-40, 40)
    y = base_y + random.uniform(-40, 40)
    # 随机方向与速度（稍微更快），速度范围 1.8 - 3.0
    angle = random.uniform(0, 2 * math.pi)
    speed = random.uniform(1.8, 3.0)
    vx = math.cos(angle) * speed
    vy = math.sin(angle) * speed
    MENU_BALLS.append({'x': float(x), 'y': float(y), 'vx': vx, 'vy': vy, 'r': 18, 'alive': True})

# 主界面子弹系统（中央三角形发射）
MENU_BULLETS = []
MENU_BULLET_FIRE_TIMER = 0
MENU_BULLET_FIRE_INTERVAL = 30  # 每30帧发射一次
    
# 主界面暂停标志（右键切换）
MENU_PAUSED = False

def spawn_menu_ball():
    """在主菜单中生成一个新的小球（在原球死亡后）"""
    base_x, base_y = random.choice(MENU_BALL_POSITIONS)
    x = base_x + random.uniform(-40, 40)
    y = base_y + random.uniform(-40, 40)
    angle = random.uniform(0, 2 * math.pi)
    speed = random.uniform(1.8, 3.0)
    vx = math.cos(angle) * speed
    vy = math.sin(angle) * speed
    MENU_BALLS.append({'x': float(x), 'y': float(y), 'vx': vx, 'vy': vy, 'r': 18, 'alive': True})
# ================== 定义类 ==================
class Player(pygame.sprite.Sprite):
    """玩家角色"""

    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((48, 48), pygame.SRCALPHA)
        pygame.draw.polygon(
            self.image,
            COLOR_BLUE,
            [(24, 0), (48, 48), (24, 64), (0, 48)]
        )
        self.rect    = self.image.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2))
        self.lives   = INITIAL_LIVES
        self.score   = 0
        self.dead    = False
        self.color = COLOR_BLUE  # 玩家颜色
        # 运动加速参数：连续移动时速度逐渐增加，停止后重置
        self.base_speed = PLAYER_SPEED
        self.current_speed = PLAYER_SPEED
        self.max_speed = PLAYER_SPEED * 2.0  # 最大为基础速度的两倍
        self.accel_per_frame = 0.08  # 每帧增加的速度值
        # 小跟班跟随所需属性
        self.angle = 0  # 玩家移动方向角度
        self.velocity = (0, 0)  # 玩家速度向量

    def darken(self):
        """死亡时变为深蓝色"""
        self.color = (0, 0, 100)  # 深蓝色
        # 重绘玩家形状
        self.image = pygame.Surface((48, 48), pygame.SRCALPHA)
        pygame.draw.polygon(
            self.image,
            self.color,
            [(24, 0), (48, 48), (24, 64), (0, 48)]
        )

    def lose_life(self, state=None):
        """减少一条生命值，并杀死所有敌人"""
        self.lives -= 1
        if self.lives < 0:
            self.lives = 0
        
        # 增加死亡次数（用于子弹反弹系统）
        if state is not None:
            state.death_count += 1
        
        # 当玩家受伤时，所有敌人立即死亡
        if state is not None:
            for enemy in list(state.enemies):
                # 创建血溅效果
                particles = create_death_particles(enemy.rect.centerx, enemy.rect.centery, count=20)
                state.enemy_particles.extend(particles)
                # 敌人进入死亡状态
                enemy.die(state.difficulty_level)
                state.player.score += 10

    def update(self, keys_pressed):
        """处理键盘走位（箭头键控制）"""
        dx, dy = 0.0, 0.0
        if keys_pressed[K_UP]: dy -= 1.0
        if keys_pressed[K_LEFT]: dx -= 1.0
        if keys_pressed[K_DOWN]: dy += 1.0
        if keys_pressed[K_RIGHT]: dx += 1.0

        # 是否在移动（按住任意方向）
        if dx != 0.0 or dy != 0.0:
            # 连续移动时加速
            self.current_speed = min(self.max_speed, self.current_speed + self.accel_per_frame)
            # 归一化方向并乘以当前速度
            length = math.hypot(dx, dy)
            if length > 0:
                dx = dx / length * self.current_speed
                dy = dy / length * self.current_speed
                # 记录移动角度供小跟班使用
                self.angle = math.atan2(dy, dx)
        else:
            # 停止过则重置速度
            self.current_speed = self.base_speed

        self.rect.x += dx
        self.rect.y += dy
        
        # 记录速度向量
        self.velocity = (dx, dy)

        # 边界检测
        self.rect.clamp_ip(screen.get_rect())

class Bullet(pygame.sprite.Sprite):
    """子弹, 朝鼠标目标发射，支持墙壁反弹"""

    def __init__(self, pos, target_pos, owner=None, shot_id=None, bounces_remaining=0):
        super().__init__()
        self.image = pygame.Surface((12, 12), pygame.SRCALPHA)
        pygame.draw.circle(self.image, COLOR_YELLOW, (6, 6), 6)
        self.rect   = self.image.get_rect(center=pos)

        # 计算方向
        dx, dy = target_pos[0] - pos[0], target_pos[1] - pos[1]
        dist = math.hypot(dx, dy)
        if dist == 0:
            dist = 1
        self.velocity = (dx / dist * BULLET_SPEED, dy / dist * BULLET_SPEED)
        # 记录所属发射批次/所有者（用于连击判定）
        self.owner = owner
        self.shot_id = shot_id
        # 冻结控制：当全局冻结时，子弹应停止移动但保留初始速度用于恢复
        self.stored_velocity = self.velocity
        self.frozen = False
        # 反弹系统：剩余反弹次数
        self.bounces_remaining = bounces_remaining

    def update(self):
        """子弹移动与反弹"""
        vx, vy = self.velocity
        self.rect.x += vx
        self.rect.y += vy

        # 反弹逻辑：如果子弹碰到墙壁并还有反弹次数，则反弹
        if self.bounces_remaining > 0:
            bounced = False
            # 检查左右边界
            if self.rect.left < 0:
                self.rect.left = 0
                self.velocity = (-vx, vy)
                self.bounces_remaining -= 1
                bounced = True
            elif self.rect.right > SCREEN_W:
                self.rect.right = SCREEN_W
                self.velocity = (-vx, vy)
                self.bounces_remaining -= 1
                bounced = True
            
            # 检查上下边界
            if self.rect.top < 0:
                self.rect.top = 0
                self.velocity = (self.velocity[0], -vy)
                if not bounced:
                    self.bounces_remaining -= 1
            elif self.rect.bottom > SCREEN_H:
                self.rect.bottom = SCREEN_H
                self.velocity = (self.velocity[0], -vy)
                if not bounced:
                    self.bounces_remaining -= 1
        else:
            # 无反弹次数时，出屏幕外消失
            if not screen.get_rect().colliderect(self.rect):
                # 通知所属 GameState：此子弹未命中（如果属于某次发射）
                try:
                    if hasattr(self, 'owner') and self.owner is not None:
                        self.owner.on_bullet_removed(self.shot_id, hit=False)
                except Exception:
                    pass
                self.kill()

class Follower(pygame.sprite.Sprite):
    """玩家的小跟班（被击杀的闪避敌人）"""
    
    def __init__(self, player, state=None, index=0):
        super().__init__()
        # 绘制小丑图标（与敌人闪避时相同）
        self.image = pygame.Surface((36, 36), pygame.SRCALPHA)
        w, h = self.image.get_size()
        cx, cy = w // 2, h // 2
        
        # 面部半径
        face_r = int(min(w, h) * 0.38)
        # 皮肤颜色
        skin = (255, 224, 189)
        # 头发（左右两侧）颜色
        hair_colors = [(220, 20, 60), (30, 144, 255), (34, 139, 34)]

        # 画脸
        pygame.draw.circle(self.image, skin, (cx, cy), face_r)

        # 画头发（左中右三簇小圆）
        hair_r = int(face_r * 0.45)
        offsets = [(-face_r, -int(face_r*0.2)), (0, -int(face_r*0.6)), (face_r, -int(face_r*0.2))]
        for i, (ox, oy) in enumerate(offsets):
            col = hair_colors[i % len(hair_colors)]
            pygame.draw.circle(self.image, col, (cx + ox, cy + oy), hair_r)

        # 眼睛
        eye_r = max(2, face_r // 6)
        eye_x_off = int(face_r * 0.45)
        eye_y_off = int(face_r * -0.15)
        pygame.draw.circle(self.image, (0, 0, 0), (cx - eye_x_off, cy + eye_y_off), eye_r)
        pygame.draw.circle(self.image, (0, 0, 0), (cx + eye_x_off, cy + eye_y_off), eye_r)
        # 白眼珠（小高光）
        pygame.draw.circle(self.image, (255, 255, 255), (cx - eye_x_off - 1, cy + eye_y_off - 1), max(1, eye_r//3))
        pygame.draw.circle(self.image, (255, 255, 255), (cx + eye_x_off - 1, cy + eye_y_off - 1), max(1, eye_r//3))

        # 鼻子（红色）
        nose_r = max(3, face_r // 5)
        pygame.draw.circle(self.image, (220, 20, 60), (cx, cy + int(face_r*0.05)), nose_r)

        # 嘴巴（用弧线）
        mouth_w = int(face_r * 1.0)
        mouth_h = int(face_r * 0.55)
        mouth_rect = pygame.Rect(cx - mouth_w//2, cy + int(face_r*0.15), mouth_w, mouth_h)
        try:
            pygame.draw.arc(self.image, (139, 0, 0), mouth_rect, math.radians(20), math.radians(160), max(2, face_r//10))
        except Exception:
            pygame.draw.ellipse(self.image, (139, 0, 0), mouth_rect)

        # 轻微边缘描边，增加识别度
        pygame.draw.circle(self.image, (0, 0, 0, 30), (cx, cy), face_r, 1)
        
        self.rect = self.image.get_rect()
        self.player = player
        self.state = state
        self.index = index  # 在队伍中的位置（用于排队跟随）
        
        # 发射计时器（每60帧发射一次，速度更慢）
        self.fire_timer = 0
        self.fire_interval = 60
        
        # 跟随相关属性
        self.follow_distance = 60 + self.index * 60  # 每个跟班间隔60像素（更稀疏）
        self.move_speed = 6.0  # 移动速度（能跟上玩家）
        self.position_x = float(self.rect.centerx)
        self.position_y = float(self.rect.centery)
    
    def update(self):
        """更新小跟班（沿着玩家历史轨迹跟随）"""
        # 如果处于暂停状态，不更新位置和发射
        if self.state is not None and getattr(self.state, 'freeze_mode', False):
            return
        
        # 根据历史轨迹计算目标位置
        target_x, target_y = self.get_target_position()
        
        # 平滑移动到目标位置
        dx = target_x - self.position_x
        dy = target_y - self.position_y
        dist = math.hypot(dx, dy)
        
        # 仅当距离足够远时才移动（防止抖动）
        if dist > self.move_speed:
            # 归一化方向并按速度移动
            dx = dx / dist * self.move_speed
            dy = dy / dist * self.move_speed
            self.position_x += dx
            self.position_y += dy
        else:
            # 距离很近时，直接靠近目标位置
            self.position_x = target_x
            self.position_y = target_y
        
        self.rect.centerx = int(self.position_x)
        self.rect.centery = int(self.position_y)
        
        # 更新发射计时器
        self.fire_timer += 1
        if self.fire_timer >= self.fire_interval and self.state is not None:
            # 发射子弹朝向玩家前方的随机方向
            self.fire_bullet()
            self.fire_timer = 0
    
    def get_target_position(self):
        """根据历史轨迹计算目标位置"""
        if self.state is None or not self.state.player_position_history:
            # 如果没有历史记录，就跟在玩家后面
            angle = math.pi / 2  # 默认向下
            target_x = self.player.rect.centerx
            target_y = self.player.rect.centery + self.follow_distance
            return target_x, target_y
        
        # 计算这个小跟班应该跟随历史中的哪个位置
        # 每个小跟班间隔follow_distance像素，这里转换为历史记录中的步数
        history_offset = max(0, len(self.state.player_position_history) - 1 - int(self.follow_distance / 3))
        
        if history_offset < 0 or history_offset >= len(self.state.player_position_history):
            # 如果历史记录不足，返回玩家当前位置附近
            return self.player.rect.centerx, self.player.rect.centery + self.follow_distance
        
        target_pos = self.state.player_position_history[history_offset]
        return float(target_pos[0]), float(target_pos[1])
    
    def fire_bullet(self):
        """发射子弹（对玩家无伤害，伤害敌人）"""
        if self.state is None:
            return
        
        # 随机选择射击方向（不指向玩家，而是随机方向）
        angle = random.uniform(0, 2 * math.pi)
        bullet_speed = 5.0  # 降低子弹速度
        vx = math.cos(angle) * bullet_speed
        vy = math.sin(angle) * bullet_speed
        
        # 创建子弹
        bullet = FollowerBullet(self.rect.center, vx, vy, owner=self, state=self.state)
        self.state.follower_bullets.append(bullet)
        self.state.all_sprites.add(bullet)


class FollowerBullet(pygame.sprite.Sprite):
    """小跟班发射的子弹（对玩家无伤害）"""
    
    def __init__(self, pos, vx, vy, owner=None, state=None):
        super().__init__()
        self.image = pygame.Surface((10, 10), pygame.SRCALPHA)
        # 使用浅蓝色以区别于玩家子弹
        pygame.draw.circle(self.image, (100, 200, 255), (5, 5), 5)
        self.rect = self.image.get_rect(center=pos)
        self.velocity = (vx, vy)
        self.owner = owner
        self.state = state
    
    def update(self):
        """小跟班子弹移动"""
        # 冻结时不移动
        if self.state is not None and getattr(self.state, 'freeze_mode', False):
            return

        vx, vy = self.velocity
        self.rect.x += vx
        self.rect.y += vy
        
        # 出屏幕外消失
        if not (0 <= self.rect.centerx < SCREEN_W and 0 <= self.rect.centery < SCREEN_H):
            self.kill()


class Enemy(pygame.sprite.Sprite):
    """敌方怪物"""

    def __init__(self, target, speed=None, state=None):
        super().__init__()
        self.image = pygame.Surface((36, 36), pygame.SRCALPHA)
        pygame.draw.circle(self.image, COLOR_RED, (18, 18), 18)
        self.rect = self.image.get_rect()

        # 生成在屏幕外随机位置（四个边缘）
        side = random.choice(['top', 'bottom', 'left', 'right'])
        if side == 'top':
            self.rect.centerx = random.randint(0, SCREEN_W)
            self.rect.top    = -36
        elif side == 'bottom':
            self.rect.centerx = random.randint(0, SCREEN_W)
            self.rect.bottom = SCREEN_H + 36
        elif side == 'left':
            self.rect.centery = random.randint(0, SCREEN_H)
            self.rect.left = -36
        else:  # right
            self.rect.centery = random.randint(0, SCREEN_H)
            self.rect.right = SCREEN_W + 36

        self.target = target
        self.state = state  # 游戏状态引用
        self.speed  = speed if speed is not None else ENEMY_SPEED
        
        # 随机运动参数（难度高时敌人不走直线）
        self.random_angle = random.uniform(-0.3, 0.3)  # 随机偏转角度
        self.sway_offset = 0  # 摇摆偏移
        self.sway_direction = random.choice([-1, 1])  # 摇摆方向
        
        # 死亡状态
        self.is_dying = False  # 是否正在死亡
        self.death_time = 0  # 死亡时长
        self.alpha = 255  # 透明度
        
        # 闪避状态
        self.is_dodging = False  # 是否正在闪避
        self.dodge_time = 0  # 闪避时间计数
        self.dodge_direction = (0, 0)  # 闪避方向
        self.has_dodged_before = False  # 是否曾经闪避过（用于小跟班转换）

        # 保存原始图像以便恢复
        try:
            self._orig_image = self.image.copy()
        except Exception:
            self._orig_image = None

        # 方向将根据目标位置更新
        self.update_direction()

    def set_random_motion(self, intensity=1.0):
        """设置随机运动强度（难度参数）"""
        self.random_motion_intensity = intensity

        # 冻结标记
        self.is_frozen = False

    def update_direction(self):
        """根据玩家位置更新朝向（关键修复：朝玩家跑而不是往中心跑）"""
        dx = self.target.rect.centerx - self.rect.centerx
        dy = self.target.rect.centery - self.rect.centery
        dist = math.hypot(dx, dy)
        if dist == 0:
            dist = 1
        self.vx = dx / dist * self.speed
        self.vy = dy / dist * self.speed
        # 记录主方向角度（用于随机运动）
        self.angle = math.atan2(dy, dx)

    def update(self):
        """敌人移动并监测碰撞"""
        # 如果正在死亡，只处理淡出
        if self.is_dying:
            self.death_time += 1
            # 根据死亡时长淡出
            if self.death_time > self.death_duration:
                self.kill()
            else:
                # 逐渐降低透明度
                self.alpha = int(255 * (1 - self.death_time / self.death_duration))
                self.image.set_alpha(self.alpha)
            return
        # 如果被全局冻结且不是死亡状态，直接不移动（保留视觉状态）
        if getattr(self, 'is_frozen', False) and not self.is_dying:
            return
        
        # 如果正在闪避，处理闪避动画
        if self.is_dodging:
            self.dodge_time += 1
            # 闪避持续0.3秒（18帧）
            if self.dodge_time > 18:
                self.is_dodging = False
                # 恢复原始图像
                try:
                    if hasattr(self, '_orig_image') and self._orig_image is not None:
                        self.image = self._orig_image
                except Exception:
                    pass
            else:
                # 快速闪避移动
                self.rect.x += self.dodge_direction[0]
                self.rect.y += self.dodge_direction[1]
            return
        
        # 每帧重新计算朝向（追踪玩家移动）
        self.update_direction()
        
        # 基础速度
        x_move = self.vx
        y_move = self.vy
        
        # 添加随机摇摆运动（非正弦，而是随机偏转）
        if hasattr(self, 'random_motion_intensity') and self.random_motion_intensity > 0:
            # 随机改变摇摆方向
            if random.random() < 0.1:  # 10%概率改变方向
                self.sway_direction = random.choice([-1, 1])
            
            # 垂直于主方向的随机摇摆
            perpendicular_angle = self.angle + self.sway_direction * (math.pi / 2)
            sway_speed = 1.5 * self.random_motion_intensity
            x_move += sway_speed * math.cos(perpendicular_angle)
            y_move += sway_speed * math.sin(perpendicular_angle)
        
        self.rect.x += x_move
        self.rect.y += y_move

        # 跟玩家碰撞（生命值扣减）
        if self.rect.colliderect(self.target.rect):
            self.target.lose_life(self.state)
            self.kill()
    
    def die(self, difficulty_level=1):
        """敌人死亡，进入淡出状态"""
        self.is_dying = True
        self.death_time = 0
        # 难度越高淡出越快：基础60帧，难度每增加1就减少10帧（最低20帧）
        self.death_duration = max(20, 60 - (difficulty_level - 1) * 10)
        self.vx = 0
        self.vy = 0
    
    def dodge(self):
        """敌人闪避"""
        self.is_dodging = True
        self.has_dodged_before = True  # 标记为曾经闪避过
        self.dodge_time = 0
        # 随机选择闪避方向（垂直于追踪方向）
        perp_angle = self.angle + random.choice([-1, 1]) * (math.pi / 2)
        dodge_speed = 8
        self.dodge_direction = (
            dodge_speed * math.cos(perp_angle),
            dodge_speed * math.sin(perp_angle)
        )
        # 将敌人替换为绘制的小丑图标以示闪避（确保跨平台显示）
        try:
            w, h = self.image.get_size()
            clown = pygame.Surface((w, h), pygame.SRCALPHA)
            cx, cy = w // 2, h // 2
            # 面部半径
            face_r = int(min(w, h) * 0.38)
            # 皮肤颜色
            skin = (255, 224, 189)
            # 头发（左右两侧）颜色
            hair_colors = [(220, 20, 60), (30, 144, 255), (34, 139, 34)]

            # 画脸
            pygame.draw.circle(clown, skin, (cx, cy), face_r)

            # 画头发（左中右三簇小圆）
            hair_r = int(face_r * 0.45)
            offsets = [(-face_r, -int(face_r*0.2)), (0, -int(face_r*0.6)), (face_r, -int(face_r*0.2))]
            for i, (ox, oy) in enumerate(offsets):
                col = hair_colors[i % len(hair_colors)]
                pygame.draw.circle(clown, col, (cx + ox, cy + oy), hair_r)

            # 眼睛
            eye_r = max(2, face_r // 6)
            eye_x_off = int(face_r * 0.45)
            eye_y_off = int(face_r * -0.15)
            pygame.draw.circle(clown, (0, 0, 0), (cx - eye_x_off, cy + eye_y_off), eye_r)
            pygame.draw.circle(clown, (0, 0, 0), (cx + eye_x_off, cy + eye_y_off), eye_r)
            # 白眼珠（小高光）
            pygame.draw.circle(clown, (255, 255, 255), (cx - eye_x_off - 1, cy + eye_y_off - 1), max(1, eye_r//3))
            pygame.draw.circle(clown, (255, 255, 255), (cx + eye_x_off - 1, cy + eye_y_off - 1), max(1, eye_r//3))

            # 鼻子（红色）
            nose_r = max(3, face_r // 5)
            pygame.draw.circle(clown, (220, 20, 60), (cx, cy + int(face_r*0.05)), nose_r)

            # 嘴巴（用弧线）
            mouth_w = int(face_r * 1.0)
            mouth_h = int(face_r * 0.55)
            mouth_rect = pygame.Rect(cx - mouth_w//2, cy + int(face_r*0.15), mouth_w, mouth_h)
            try:
                pygame.draw.arc(clown, (139, 0, 0), mouth_rect, math.radians(20), math.radians(160), max(2, face_r//10))
            except Exception:
                # 若 arc 不可用，画一个简单的红色椭圆代表嘴巴
                pygame.draw.ellipse(clown, (139, 0, 0), mouth_rect)

            # 轻微边缘描边，增加识别度
            pygame.draw.circle(clown, (0, 0, 0, 30), (cx, cy), face_r, 1)

            self.image = clown
        except Exception:
            pass

# ================== 主游戏状态 ==================
class GameState:
    """游戏状态管理"""

    def __init__(self):
        self.all_sprites   = pygame.sprite.Group()
        self.bullets       = pygame.sprite.Group()
        self.enemies       = pygame.sprite.Group()
        self.player        = Player()
        self.all_sprites.add(self.player)

        # 计时器
        self.last_spawn = pygame.time.get_ticks()
        
        # 难度参数
        self.difficulty_level = 1
        self.current_spawn_interval = ENEMY_SPAWN_INTERVAL
        self.current_enemy_speed = ENEMY_SPEED
        # 生成批次（同一时刻生成的敌人数）
        self.spawn_burst = 1
        
        # 死亡次数追踪（用于子弹反弹次数）
        self.death_count = 0
        
        # 小跟班系统
        self.followers = []  # 被击杀的闪避敌人变成的小跟班
        self.follower_bullets = []  # 小跟班发射的子弹
        
        # 玩家位置历史（用于小跟班跟随）
        self.player_position_history = []  # 记录玩家历史位置

        # 连击系统
        self.next_shot_id = 1
        self.shots = {}  # shot_id -> {'pending': int, 'any_hit': bool}
        self.combo_count = 0
        # 连击动画计时器（帧）和持续时长
        self.combo_anim_timer = 0
        self.combo_display_duration = 60  # 帧
        
        # 敌人血溅粒子
        self.enemy_particles = []

        # 全局冻结模式（按空格切换）——敌人与子弹停止移动，但玩家可继续操作
        self.freeze_mode = False
        
        # 弹道系统
        self.num_trajectories = 1  # 当前弹道数（初始为1）
        self.last_bullet_angles = []  # 记录上一次射击的角度用于计算新弹道

    def update_difficulty(self):
        """根据分数更新难度"""
        new_level = self.player.score // DIFFICULTY_SCORE_STEP + 1
        if new_level > self.difficulty_level:
            self.difficulty_level = new_level
            # 难度递增：生成速度加快，敌人速度增加
            # 恢复原始略微提升速度的行为，并保持生成间隔的适度加速
            self.current_spawn_interval = max(800, ENEMY_SPAWN_INTERVAL - (new_level - 1) * 200)
            # 每级略微提高敌人速度（恢复为每级 +0.5）
            self.current_enemy_speed = ENEMY_SPEED + (new_level - 1) * 0.5
            # 不增加同时出现的敌人数，保持 spawn_burst = 1
            self.spawn_burst = 1

            # 每升高2级增加一条弹道
            self.num_trajectories = 1 + (new_level - 1) // 2

    # 冻结/恢复控制
    def toggle_freeze(self):
        if self.freeze_mode:
            self.exit_freeze()
        else:
            self.enter_freeze()
        try:
            print(f"[GameState] freeze_mode -> {self.freeze_mode}")
        except Exception:
            pass

    def enter_freeze(self):
        self.freeze_mode = True
        # 冻结所有敌人（保存原速度以便恢复）
        for enemy in list(self.enemies):
            try:
                enemy.prev_vx = getattr(enemy, 'vx', 0)
                enemy.prev_vy = getattr(enemy, 'vy', 0)
                enemy.is_frozen = True
            except Exception:
                pass
        # 冻结所有现有子弹（保存速度）
        for bullet in list(self.bullets):
            try:
                bullet.stored_velocity = getattr(bullet, 'velocity', (0, 0))
                bullet.velocity = (0, 0)
                bullet.frozen = True
            except Exception:
                pass
        # 重置生成计时器，避免暂停期间累计导致解冻后立刻刷新敌人
        try:
            self.last_spawn = pygame.time.get_ticks()
        except Exception:
            pass

    def exit_freeze(self):
        self.freeze_mode = False
        # 恢复敌人速度
        for enemy in list(self.enemies):
            try:
                enemy.is_frozen = False
                if hasattr(enemy, 'prev_vx'):
                    enemy.vx = enemy.prev_vx
                    enemy.vy = enemy.prev_vy
            except Exception:
                pass
        # 恢复子弹速度
        for bullet in list(self.bullets):
            try:
                if getattr(bullet, 'frozen', False):
                    bullet.velocity = getattr(bullet, 'stored_velocity', bullet.velocity)
                    bullet.frozen = False
            except Exception:
                pass

    def spawn_enemy(self):
        """按间隔生成敌人"""
        # 不在冻结模式下才生成新敌人
        if getattr(self, 'freeze_mode', False):
            return
        curr_time = pygame.time.get_ticks()
        if curr_time - self.last_spawn > self.current_spawn_interval:
            # 生成一个批次的敌人（数量随等级增长）
            for i in range(self.spawn_burst):
                enemy = Enemy(self.player, self.current_enemy_speed, self)
                # 根据难度添加随机运动强度
                if self.difficulty_level >= 2:
                    intensity = 0.5 + (self.difficulty_level - 2) * 0.3
                    enemy.set_random_motion(intensity)
                # 轻微位置扰动，避免完全重叠
                enemy.rect.x += random.randint(-30, 30)
                enemy.rect.y += random.randint(-30, 30)
                self.enemies.add(enemy)
                self.all_sprites.add(enemy)
            self.last_spawn = curr_time

    def fire_bullet(self, target_pos):
        """发射子弹，支持多弹道，根据死亡次数设置反弹次数"""
        # 计算主要方向角度
        dx = target_pos[0] - self.player.rect.centerx
        dy = target_pos[1] - self.player.rect.centery
        main_angle = math.atan2(dy, dx)
        
        # 根据弹道数计算射击角度
        if self.num_trajectories == 1:
            angles = [main_angle]
        elif self.num_trajectories == 2:
            # 两弹道：一前一后
            angles = [main_angle, main_angle + math.pi]
        else:
            # 多弹道（3+）：均匀分布在主方向周围
            angle_spread = math.pi / 4  # 总展开角度为45度
            angles = []
            for i in range(self.num_trajectories):
                offset = (i - (self.num_trajectories - 1) / 2.0) * (angle_spread / max(1, self.num_trajectories - 1))
                angles.append(main_angle + offset)
        
        # 发射所有弹道（并创建一次发射的记录，用于连击判定）
        shot_id = self.next_shot_id
        self.next_shot_id += 1
        self.shots[shot_id] = {'pending': len(angles), 'any_hit': False}
        
        # 根据死亡次数计算反弹次数：第一次死亡后1次，第二次死亡后2次
        bounces_remaining = self.death_count

        for angle in angles:
            bullet_speed_vx = BULLET_SPEED * math.cos(angle)
            bullet_speed_vy = BULLET_SPEED * math.sin(angle)

            bullet = Bullet(self.player.rect.center, target_pos, owner=self, shot_id=shot_id, bounces_remaining=bounces_remaining)
            # 覆盖速度方向
            bullet.velocity = (bullet_speed_vx, bullet_speed_vy)
            # 保存真实速度以便冻结/恢复
            bullet.stored_velocity = bullet.velocity
            if self.freeze_mode:
                bullet.velocity = (0, 0)
                bullet.frozen = True

            if len(self.bullets) < BULLET_LIMIT * self.num_trajectories:
                self.bullets.add(bullet)
                self.all_sprites.add(bullet)

    def update(self):
        """更新所有逻辑"""
        keys = pygame.key.get_pressed()
        self.player.update(keys)
        
        # 记录玩家位置历史（每帧记录一次）
        self.player_position_history.append((self.player.rect.centerx, self.player.rect.centery))
        # 保持历史长度不超过1000个位置点（防止内存过度消耗）
        if len(self.player_position_history) > 1000:
            self.player_position_history.pop(0)

        # 更新难度
        self.update_difficulty()
        
        # 这里将处理所有更新与碰撞
        self.spawn_enemy()
        # 更新子弹和敌人，但不更新玩家（已单独处理）
        for bullet in self.bullets:
            bullet.update()
        for enemy in self.enemies:
            enemy.update()
        
        # 更新小跟班
        for follower in self.followers[:]:
            follower.update()
        
        # 更新小跟班子弹
        for fbullet in self.follower_bullets[:]:
            fbullet.update()
            if fbullet not in self.all_sprites:
                if fbullet in self.follower_bullets:
                    self.follower_bullets.remove(fbullet)
        
        # 更新敌人血溅粒子
        if self.enemy_particles:
            draw_death_particles(None, self.enemy_particles)
        
        self.handle_collisions()

    def handle_collisions(self):
        """
        子弹-敌人碰撞判定:
            - 难度1-3分别为40%、20%、10%闪避，难度4+不闪避
            - 击中时创建血溅效果并淡出
            - 玩家得分
        """
        # 根据难度计算闪避概率
        dodge_chances = {1: 0.4, 2: 0.2, 3: 0.1}
        dodge_chance = dodge_chances.get(self.difficulty_level, 0) if self.difficulty_level < 4 else 0
        
        # 子弹与敌人交集
        collisions = pygame.sprite.groupcollide(self.bullets, self.enemies, True, False)
        if collisions:
            for bullet, enemies_hit in collisions.items():
                # 标记当前子弹为命中（用于连击判断）
                try:
                    if hasattr(bullet, 'shot_id'):
                        self.on_bullet_removed(bullet.shot_id, hit=True)
                except Exception:
                    pass

                for enemy in enemies_hit:
                    if random.random() < dodge_chance and not enemy.is_dying:
                        enemy.dodge()
                    else:
                        # 检查敌人是否曾经闪避过 - 如果是，则转为小跟班而不是死亡
                        if getattr(enemy, 'has_dodged_before', False) and len(self.followers) < 3:
                            # 曾经闪避过的敌人被击中 -> 转为小跟班（上限3个）
                            follower = Follower(self.player, state=self, index=len(self.followers))
                            # 小跟班初始位置在玩家后面（沿着历史轨迹），不是敌人处
                            target_x, target_y = follower.get_target_position()
                            follower.position_x = float(target_x)
                            follower.position_y = float(target_y)
                            follower.rect.centerx = int(target_x)
                            follower.rect.centery = int(target_y)
                            self.followers.append(follower)
                            self.all_sprites.add(follower)
                            self.player.score += 10
                            enemy.kill()  # 敌人消失
                        else:
                            # 正常死亡流程（从未闪避过的敌人 或 小跟班已满3个）
                            # 创建敌人血溅效果
                            particles = create_death_particles(enemy.rect.centerx, enemy.rect.centery, count=20)
                            self.enemy_particles.extend(particles)
                            # 敌人进入死亡状态
                            enemy.die(self.difficulty_level)
                            self.player.score += 10

        # 额外注意：若没有碰撞但有子弹离开屏幕，Bullet.update 会调用 on_bullet_removed
        
        # 小跟班子弹与敌人碰撞
        for fbullet in self.follower_bullets[:]:
            for enemy in list(self.enemies):
                if fbullet.rect.colliderect(enemy.rect) and not enemy.is_dying:
                    # 小跟班子弹击中敌人
                    particles = create_death_particles(enemy.rect.centerx, enemy.rect.centery, count=20)
                    self.enemy_particles.extend(particles)
                    enemy.die(self.difficulty_level)
                    self.player.score += 10
                    
                    # 移除小跟班子弹
                    if fbullet in self.follower_bullets:
                        self.follower_bullets.remove(fbullet)
                    fbullet.kill()
                    break

    def on_bullet_removed(self, shot_id, hit=False):
        """当某个子弹因命中或出界被移除时调用。基于发射批次统计连击。"""
        if shot_id is None:
            return
        info = self.shots.get(shot_id)
        if not info:
            return
        if hit:
            info['any_hit'] = True
        info['pending'] -= 1
        if info['pending'] <= 0:
            # 此次发射结束，判断是否命中过敌人
            if info['any_hit']:
                # 连击成功，增加连击计数并触发动画
                self.combo_count += 1
                self.combo_anim_timer = self.combo_display_duration
            else:
                # 本次发射全部未命中，连击中断
                self.combo_count = 0
                self.combo_anim_timer = 0
            # 清理记录
            try:
                del self.shots[shot_id]
            except Exception:
                pass

    def draw(self, surf):
        """绘制全部"""
        surf.fill(COLOR_BLACK)
        self.all_sprites.draw(surf)
        
        # 绘制小跟班子弹
        for fbullet in self.follower_bullets:
            surf.blit(fbullet.image, fbullet.rect)
        
        # 绘制敌人血溅粒子
        if self.enemy_particles:
            draw_death_particles(surf, self.enemy_particles)
        
        # 绘制爱心血量（右上角）
        draw_hearts(surf, self.player.lives, INITIAL_LIVES)

        # HUD（左上角）
        hud = "Score: {}   Level: {}   Trajectories: {}".format(
            self.player.score, self.difficulty_level, self.num_trajectories
        )
        hud_surf = font.render(hud, True, COLOR_WHITE)
        surf.blit(hud_surf, (10, 10))

        # 连击显示与动画（在玩家上方）
        if self.combo_count >= 2 and self.combo_anim_timer > 0:
            # 计算动画进度（1.0 -> 0.0）
            progress = self.combo_anim_timer / float(max(1, self.combo_display_duration))
            # 缩放效果：从 1.6 缩放到 1.0
            scale = 1.0 + 0.6 * progress
            combo_text = "X{}".format(self.combo_count)
            # 颜色随连击数变化：黄色->橙->红
            def lerp(a, b, t):
                return int(a + (b - a) * t)
            # base colors
            yellow = (255, 215, 0)
            orange = (255, 140, 0)
            red = (220, 20, 60)
            if self.combo_count <= 2:
                color = yellow
            elif self.combo_count == 3:
                color = orange
            else:
                color = red

            # 渲染文本并进行缩放
            combo_surf = big_font.render(combo_text, True, color)
            # 应用缩放
            sw, sh = combo_surf.get_size()
            combo_surf = pygame.transform.smoothscale(combo_surf, (int(sw * scale), int(sh * scale)))
            combo_rect = combo_surf.get_rect(center=(self.player.rect.centerx, self.player.rect.top - 30))
            # 逐渐淡出（使用 progress 做 alpha）
            try:
                alpha = int(255 * progress)
                combo_surf.set_alpha(alpha)
            except Exception:
                pass
            surf.blit(combo_surf, combo_rect)
            # 计时器减少
            self.combo_anim_timer -= 1

        # 冻结模式可视化提示（在屏幕中央顶部）
        if getattr(self, 'freeze_mode', False):
            try:
                overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 100))
                surf.blit(overlay, (0, 0))
                pause_surf = big_font.render("PAUSED", True, (255, 255, 0))
                pause_rect = pause_surf.get_rect(center=(SCREEN_W // 2, 60))
                surf.blit(pause_surf, pause_rect)
                hint_surf = font.render("Right-click to resume", True, COLOR_WHITE)
                hint_rect = hint_surf.get_rect(center=(SCREEN_W // 2, 110))
                surf.blit(hint_surf, hint_rect)
            except Exception:
                pass

# ================== 辅助函数 ==================
def draw_main_menu(surf, fade_alpha=255, high_score=0):
    """首屏/结束界面 - 带背景敌人和玩家"""
    global MENU_BULLETS, MENU_BULLET_FIRE_TIMER
    
    surf.fill(COLOR_BLACK)

    # 处理子弹发射计时
    if not MENU_PAUSED:
        MENU_BULLET_FIRE_TIMER += 1
        if MENU_BULLET_FIRE_TIMER >= MENU_BULLET_FIRE_INTERVAL:
            # 中央三角形发射一颗子弹
            triangle_cx = SCREEN_W // 2
            triangle_cy = SCREEN_H // 2
            angle = random.uniform(0, 2 * math.pi)
            bullet_speed = 5.0
            vx = math.cos(angle) * bullet_speed
            vy = math.sin(angle) * bullet_speed
            MENU_BULLETS.append({'x': float(triangle_cx), 'y': float(triangle_cy), 'vx': vx, 'vy': vy})
            MENU_BULLET_FIRE_TIMER = 0

    # 更新和绘制子弹
    for bullet in MENU_BULLETS[:]:
        if not MENU_PAUSED:
            bullet['x'] += bullet['vx']
            bullet['y'] += bullet['vy']
        # 检查是否超出边界
        if bullet['x'] < 0 or bullet['x'] > SCREEN_W or bullet['y'] < 0 or bullet['y'] > SCREEN_H:
            MENU_BULLETS.remove(bullet)
        else:
            pygame.draw.circle(surf, (255, 255, 100), (int(bullet['x']), int(bullet['y'])), 3)

    # 绘制装饰性移动小球（在边缘反弹）并处理碰撞
    try:
        for b in MENU_BALLS[:]:
            if not b.get('alive', True):
                continue
            r = b.get('r', 18)
            if not MENU_PAUSED:
                # 更新位置
                b['x'] += b['vx']
                b['y'] += b['vy']
                # 边界反弹
                if b['x'] - r < 0:
                    b['x'] = r
                    b['vx'] = -b['vx']
                if b['x'] + r > SCREEN_W:
                    b['x'] = SCREEN_W - r
                    b['vx'] = -b['vx']
                if b['y'] - r < 0:
                    b['y'] = r
                    b['vy'] = -b['vy']
                if b['y'] + r > SCREEN_H:
                    b['y'] = SCREEN_H - r
                    b['vy'] = -b['vy']

                # 小幅随机扰动方向，使运动更自然
                jitter_strength = 0.18
                b['vx'] += random.uniform(-jitter_strength, jitter_strength)
                b['vy'] += random.uniform(-jitter_strength, jitter_strength)
                # 限制速度幅度，防止无限加速
                spd = math.hypot(b['vx'], b['vy'])
                min_spd, max_spd = 1.2, 3.5
                if spd < min_spd and spd > 0:
                    scale = min_spd / spd
                    b['vx'] *= scale
                    b['vy'] *= scale
                elif spd > max_spd:
                    scale = max_spd / spd
                    b['vx'] *= scale
                    b['vy'] *= scale

            # 无论是否暂停，都绘制小球在当前位置
            pygame.draw.circle(surf, (100, 0, 0), (int(b['x']), int(b['y'])), r)

        # 检测子弹与小球碰撞
        for bullet in MENU_BULLETS[:]:
            for ball in MENU_BALLS:
                if not ball.get('alive', True):
                    continue
                dx = bullet['x'] - ball['x']
                dy = bullet['y'] - ball['y']
                dist = math.hypot(dx, dy)
                if dist < ball.get('r', 18) + 3:  # 3 是子弹半径
                    # 碰撞：小球死亡，立即生成新小球
                    ball['alive'] = False
                    spawn_menu_ball()
                    if bullet in MENU_BULLETS:
                        MENU_BULLETS.remove(bullet)
                    break
    except Exception:
        pass
    
    # 绘制中心的蓝色玩家三角形
    player_center_x = SCREEN_W // 2
    player_center_y = SCREEN_H // 2
    pygame.draw.polygon(
        surf,
        COLOR_BLUE,
        [
            (player_center_x, player_center_y - 30),  # 顶点
            (player_center_x + 30, player_center_y + 30),  # 右下
            (player_center_x - 30, player_center_y + 30)  # 左下
        ]
    )

    title_surf = big_font.render("TOP-DOWN Shooting Game", True, COLOR_GREEN)
    title_rect = title_surf.get_rect(center=(SCREEN_W // 2, SCREEN_H // 3))
    
    instr_surf = font.render(
        "Up/Down/Left/Right - Move | Mouse Left Click - Shoot | ESC - Quit",
        True,
        COLOR_WHITE
    )
    instr_rect = instr_surf.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 60))
    
    start_surf = font.render("Press ENTER to start", True, COLOR_WHITE)
    start_rect = start_surf.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 120))
    
    # 最高得分显示
    high_score_surf = font.render("High Score: {}".format(high_score), True, COLOR_YELLOW)
    high_score_rect = high_score_surf.get_rect(center=(SCREEN_W // 2, SCREEN_H - 40))
    
    # 应用淡入效果
    if fade_alpha < 255:
        title_surf.set_alpha(fade_alpha)
        instr_surf.set_alpha(fade_alpha)
        start_surf.set_alpha(fade_alpha)
        high_score_surf.set_alpha(fade_alpha)
    
    surf.blit(title_surf, title_rect)
    surf.blit(instr_surf, instr_rect)
    surf.blit(start_surf, start_rect)
    surf.blit(high_score_surf, high_score_rect)
    pygame.display.flip()

def draw_game_over(surf, score, fade_alpha=255, show_bg=True):
    """游戏结束弹窗"""
    if show_bg:
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))  # 半透明
        surf.blit(overlay, (0, 0))

    msg = "Game Over! Score: {}".format(score)
    msg_surf = big_font.render(msg, True, COLOR_RED)
    msg_rect = msg_surf.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 40))
    
    replay_surf = font.render("Press R to restart or ESC to quit", True, COLOR_WHITE)
    replay_rect = replay_surf.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 30))
    
    # 应用淡入效果
    if fade_alpha < 255:
        msg_surf.set_alpha(fade_alpha)
        replay_surf.set_alpha(fade_alpha)
    
    surf.blit(msg_surf, msg_rect)
    surf.blit(replay_surf, replay_rect)
    pygame.display.flip()

def draw_hearts(surf, lives, max_lives=3):
    """在右上角绘制爱心血量"""
    heart_size = 15  # 爱心大小
    spacing = 20  # 爱心间距
    start_x = SCREEN_W - (max_lives * spacing + 10)
    start_y = 10
    
    for i in range(max_lives):
        # 计算爱心位置
        heart_x = start_x + i * spacing
        heart_y = start_y
        
        # 根据是否有血量选择颜色
        if i < lives:
            color = (255, 0, 0)  # 红色（满血）
        else:
            color = (50, 50, 50)  # 黑色（无血）
        
        # 绘制简单爱心形状（两个圆形 + 三角形）
        # 上方两个圆（心房）
        pygame.draw.circle(surf, color, (int(heart_x - 5), int(heart_y)), 5)
        pygame.draw.circle(surf, color, (int(heart_x + 5), int(heart_y)), 5)
        # 下方三角形（心尖）
        pygame.draw.polygon(surf, color, [
            (int(heart_x - 8), int(heart_y + 2)),
            (int(heart_x + 8), int(heart_y + 2)),
            (int(heart_x), int(heart_y + 12))
        ])

def draw_death_particles(surf, particles):
    """绘制和更新血溅粒子效果"""
    for particle in particles[:]:
        x, y, vx, vy, lifetime, max_lifetime = particle
        # 计算粒子透明度
        alpha = int(255 * (lifetime / max_lifetime))
        
        # 如果有surface才绘制，否则只更新
        if surf is not None:
            # 创建粒子表面
            particle_surf = pygame.Surface((6, 6), pygame.SRCALPHA)
            pygame.draw.circle(particle_surf, (255, 0, 0, alpha), (3, 3), 3)
            particle_surf.set_alpha(alpha)
            # 绘制粒子
            surf.blit(particle_surf, (int(x), int(y)))
        
        # 更新粒子
        new_x = x + vx
        new_y = y + vy
        new_lifetime = lifetime - 1
        
        if new_lifetime <= 0:
            particles.remove(particle)
        else:
            particles[particles.index(particle)] = (new_x, new_y, vx, vy * 1.05, new_lifetime, max_lifetime)

def create_death_particles(center_x, center_y, count=30):
    """创建死亡血溅效果粒子"""
    particles = []
    for _ in range(count):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2, 8)
        vx = speed * math.cos(angle)
        vy = speed * math.sin(angle)
        lifetime = random.randint(20, 40)
        particles.append((center_x, center_y, vx, vy, lifetime, lifetime))
    return particles

# ================== 主程序 ==================
def main():
    state = GameState()
    in_game = False          # 是否正在游戏中
    show_menu = True         # 是否显示菜单
    show_gameover = False    # 是否显示游戏结束界面
    
    # 加载历史最高得分
    high_score = load_high_score()
    high_score_saved = False  # 标记高分是否已保存
    
    # 淡入动画参数
    fade_in_duration = 3.0   # 淡入持续时间（秒） - 改为3秒更慢
    fade_start_time = pygame.time.get_ticks()
    animation_done = False
    
    # 死亡效果参数
    death_particles = []  # 血溅粒子列表
    show_death_effect = False  # 是否显示死亡效果
    death_effect_time = 0  # 死亡效果持续时间
    death_stage = 0  # 死亡阶段 (0=血溅, 1=屏幕变红, 2=结束界面弹出)

    while True:
        # ① 处理全局事件
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()

            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if event.key == pygame.K_RETURN:
                    if show_menu or show_gameover:
                        state = GameState()
                        in_game = True
                        show_menu = False
                        show_gameover = False
                        fade_start_time = pygame.time.get_ticks()
                        animation_done = False
                        high_score_saved = False  # 重置高分保存标记
                # (SPACE handling removed; freeze now via right mouse button)

            if event.type == MOUSEBUTTONDOWN:
                # 左键发射
                if event.button == 1:
                    if in_game:
                        state.fire_bullet(event.pos)
                # 右键切换冻结（游戏中）、暂停菜单（菜单界面）或重启（结束界面）
                elif event.button == 3:
                    if in_game:
                        try:
                            state.toggle_freeze()
                        except Exception:
                            pass
                    elif show_menu:
                        # 菜单界面右键切换暂停
                        global MENU_PAUSED
                        MENU_PAUSED = not MENU_PAUSED
                    elif show_gameover:
                        state = GameState()
                        in_game = True
                        show_menu = False
                        show_gameover = False
                        fade_start_time = pygame.time.get_ticks()
                        animation_done = False
                        high_score_saved = False  # 重置高分保存标记

        # ② 游戏状态渲染和更新
        if show_menu:
            # 计算淡入进度
            elapsed = (pygame.time.get_ticks() - fade_start_time) / 1000.0
            progress = min(elapsed / fade_in_duration, 1.0)
            fade_alpha = int(255 * progress)
            draw_main_menu(screen, fade_alpha, high_score)

        elif in_game:
            state.update()
            state.draw(screen)
            
            # 处理死亡效果
            if show_death_effect:
                # 玩家变深蓝色并停止所有敌人
                state.player.darken()
                # 停止所有敌人运动
                for enemy in state.enemies:
                    enemy.vx = 0
                    enemy.vy = 0
                
                # 绘制血溅粒子
                if death_particles:
                    draw_death_particles(screen, death_particles)
                
                death_effect_time += 1
                # 立即进入结束界面渐出阶段
                if death_effect_time == 1:
                    # 直接进入结束界面
                    fade_start_time = pygame.time.get_ticks()
                    in_game = False
                    show_gameover = True
                    show_death_effect = False
                    death_stage = 0
                    death_particles = []
            
            pygame.display.flip()

            # 检查生命值
            if state.player.lives <= 0 and not show_death_effect:
                # 创建死亡效果
                show_death_effect = True
                death_stage = 0
                death_effect_time = 0
                death_particles = create_death_particles(
                    state.player.rect.centerx, 
                    state.player.rect.centery
                )

        elif show_gameover:
            # 检查是否刚进入结束界面（更新高分）
            if not high_score_saved:
                if state.player.score > high_score:
                    high_score = state.player.score
                    save_high_score(high_score)
                high_score_saved = True
            
            # 计算结束界面淡入进度
            elapsed = (pygame.time.get_ticks() - fade_start_time) / 1000.0
            progress = min(elapsed / 0.8, 1.0)  # 结束界面快速淡入
            fade_alpha = int(255 * progress)
            
            state.draw(screen)
            draw_game_over(screen, state.player.score, fade_alpha, show_bg=True)
            pygame.display.flip()

        clock.tick(FPS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pygame.quit()
        sys.exit()
