"""
Hardware-Accelerated Pygame Visual Window & Cyberpunk Quantum Telemetry HUD.
Supports authentic 1x Real-Time (60 FPS) and Sped-Up (10x-20x Fuzzing) visual playback
for Super Mario Bros, ViZDoom, GlitchGrid2D, Chess, Sudoku, and Blackjack.
"""

import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

# Suppress Pygame welcome message
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


class QuantumVisualWindow:
    """
    Renders high-DPI live gameplay frames alongside real-time Quantum Telemetry:
      - Live 4-Qubit Z-Expectation Meters
      - Quantum Kernel Anomaly Gauge & Threshold Alert
      - Dual-speed execution: 1x Real-Time (60 FPS) vs Accelerated Sped-Up Playback
      - Level progress and Flagpole / Victory celebration overlays
    """

    def __init__(
        self,
        title: str = "Quantum RL Simulation HUD",
        width: int = 768,
        height: int = 720,
        fps_realtime: int = 60,
        fps_fast: int = 240,
        enabled: bool = True
    ):
        self.title = title
        self.width = width
        self.height = height
        self.fps_realtime = fps_realtime
        self.fps_fast = fps_fast
        self.enabled = enabled and PYGAME_AVAILABLE
        self.window = None
        self.clock = None
        self.font_title = None
        self.font_sub = None
        self.font_hud = None
        self.font_badge = None
        self.is_paused = False

        if self.enabled:
            try:
                pygame.init()
                pygame.font.init()
                self.window = pygame.display.set_mode((self.width, self.height))
                pygame.display.set_caption(title)
                self.clock = pygame.time.Clock()
                self.font_title = pygame.font.SysFont("Consolas", 15, bold=True)
                self.font_sub = pygame.font.SysFont("Consolas", 13, bold=True)
                self.font_hud = pygame.font.SysFont("Consolas", 12)
                self.font_badge = pygame.font.SysFont("Consolas", 11, bold=True)
            except Exception as e:
                print(f"[VisualHUD] Warning: Pygame window initialization failed ({e}). Falling back to headless mode.")
                self.enabled = False

    def handle_events(self) -> bool:
        """Processes OS and window events. Returns False if user closed window or pressed ESC/q."""
        if not self.enabled or self.window is None:
            return True

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    return False
                elif event.key == pygame.K_SPACE:
                    self.is_paused = not self.is_paused
                    while self.is_paused:
                        for pe in pygame.event.get():
                            if pe.type == pygame.QUIT or (pe.type == pygame.KEYDOWN and pe.key in (pygame.K_ESCAPE, pygame.K_q)):
                                return False
                            elif pe.type == pygame.KEYDOWN and pe.key == pygame.K_SPACE:
                                self.is_paused = False
                        pygame.time.delay(50)
        return True

    def _draw_hud_overlays(
        self,
        game_title: str,
        iteration: int,
        total_iters: int,
        is_realtime: bool,
        is_exploit: bool,
        exploit_name: str,
        step: int,
        q_expectations: np.ndarray,
        anomaly_score: float,
        is_flagged: bool,
        status_text: str = "",
        victory: bool = False,
        victory_text: str = "★ LEVEL COMPLETE! FLAGPOLE REACHED ★"
    ):
        """Draws cyberpunk quantum header and bottom telemetry gauge."""
        w, h = self.width, self.height

        # --- TOP HEADER BANNER (Height: 46px) ---
        pygame.draw.rect(self.window, (16, 20, 30), (0, 0, w, 46))
        pygame.draw.line(self.window, (40, 60, 90), (0, 45), (w, 45), 2)

        # Game Title & Iteration
        t_title = self.font_title.render(f"{game_title.upper()}", True, (0, 240, 255))
        self.window.blit(t_title, (14, 6))

        iter_str = f"ITERATION {iteration}/{total_iters}"
        t_iter = self.font_sub.render(iter_str, True, (240, 240, 240))
        self.window.blit(t_iter, (14, 25))

        # Speed Mode Badge
        if is_realtime:
            badge_bg = (0, 100, 150)
            badge_txt = self.font_badge.render(" 1X REAL-TIME (60 FPS) ", True, (255, 255, 255))
        else:
            badge_bg = (180, 120, 0)
            badge_txt = self.font_badge.render(" SPED-UP SIMULATION (10X FAST) ", True, (255, 255, 255))

        badge_rect = pygame.Rect(w - 240, 8, 226, 16)
        pygame.draw.rect(self.window, badge_bg, badge_rect, border_radius=3)
        self.window.blit(badge_txt, (w - 238, 9))

        # State Badge (Legal vs Exploit)
        if is_flagged and exploit_name and exploit_name != "None":
            state_bg = (200, 20, 40)
            state_txt = self.font_badge.render(f" EXPLOIT DETECTED: {exploit_name.upper()} ", True, (255, 255, 255))
        elif is_exploit:
            state_bg = (180, 50, 50)
            state_txt = self.font_badge.render(f" INJECTING EXPLOIT: {exploit_name.upper()} ", True, (255, 255, 255))
        else:
            state_bg = (20, 140, 60)
            state_txt = self.font_badge.render(" LEGAL STATE - NOMINAL DYNAMICS ", True, (255, 255, 255))

        state_rect = pygame.Rect(w - 240, 26, 226, 16)
        pygame.draw.rect(self.window, state_bg, state_rect, border_radius=3)
        self.window.blit(state_txt, (w - 238, 27))

        # --- BOTTOM TELEMETRY FOOTER (Height: 94px) ---
        footer_y = h - 94
        pygame.draw.rect(self.window, (12, 16, 24), (0, footer_y, w, 94))
        pygame.draw.line(self.window, (40, 60, 90), (0, footer_y), (w, footer_y), 2)

        # Row 1: 4 Qubit Z-Expectation Bars
        q_label = self.font_badge.render("QUANTUM CIRCUIT (4-QUBIT ESTIMATOR VQC):", True, (140, 180, 220))
        self.window.blit(q_label, (14, footer_y + 6))

        bar_start_x = 14
        bar_w = 70
        bar_h = 10
        for i in range(min(4, len(q_expectations))):
            val = float(np.clip(q_expectations[i], -1.0, 1.0))
            bx = bar_start_x + i * 90
            by = footer_y + 24
            # Background bar
            pygame.draw.rect(self.window, (30, 40, 60), (bx, by, bar_w, bar_h), border_radius=2)
            # Center mark
            pygame.draw.line(self.window, (80, 100, 130), (bx + bar_w // 2, by), (bx + bar_w // 2, by + bar_h), 1)
            # Filled expectation indicator
            ind_x = int(bx + (val + 1.0) / 2.0 * (bar_w - 6))
            pygame.draw.rect(self.window, (0, 255, 200), (ind_x, by - 1, 6, bar_h + 2), border_radius=2)
            # Text
            q_txt = self.font_badge.render(f"Q{i}: {val:+.2f}", True, (180, 220, 255))
            self.window.blit(q_txt, (bx, by + 12))

        # Row 1 Right: Anomaly Meter
        am_x = w - 300
        am_y = footer_y + 14
        pygame.draw.rect(self.window, (25, 30, 45), (am_x, am_y, 280, 22), border_radius=3)
        # Score bar
        score_norm = float(np.clip((anomaly_score + 0.1) * 200, 0, 276))
        bar_col = (255, 40, 60) if is_flagged else (40, 220, 100)
        if score_norm > 2:
            pygame.draw.rect(self.window, bar_col, (am_x + 2, am_y + 2, int(score_norm), 18), border_radius=2)
        # Threshold line at nu=0.08 (~36px)
        pygame.draw.line(self.window, (255, 255, 0), (am_x + 36, am_y), (am_x + 36, am_y + 22), 2)
        score_txt = self.font_badge.render(f"ANOMALY SCORE: {anomaly_score:+6.4f} (τ=0.08)", True, (255, 255, 255))
        self.window.blit(score_txt, (am_x + 10, am_y + 4))

        # Row 2: Status Text / Action
        st_txt = self.font_hud.render(f"Step {step:04d} | {status_text}", True, (200, 215, 230))
        self.window.blit(st_txt, (14, footer_y + 56))

        # Row 3: Victory Overlay if completed
        if victory:
            vic_rect = pygame.Rect(w // 2 - 240, footer_y + 72, 480, 18)
            pygame.draw.rect(self.window, (255, 215, 0), vic_rect, border_radius=3)
            vic_txt = self.font_badge.render(f" {victory_text} ", True, (20, 20, 20))
            self.window.blit(vic_txt, (w // 2 - 210, footer_y + 73))

    def render_mario_frame(
        self,
        screen_rgb: np.ndarray,
        iteration: int,
        total_iters: int,
        is_realtime: bool,
        is_exploit: bool,
        exploit_name: str,
        step: int,
        q_expectations: np.ndarray,
        anomaly_score: float,
        is_flagged: bool,
        mario_x: float,
        action_name: str,
        level_complete: bool = False
    ) -> bool:
        """Renders NES Super Mario Bros RGB screen buffer with Quantum HUD."""
        if not self.enabled or self.window is None:
            return True

        if not self.handle_events():
            return False

        w, h = self.width, self.height
        game_view_h = h - 46 - 94 # 580px

        # Convert RGB numpy array (240, 256, 3) to Pygame surface
        # surfarray expects (width, height, 3) = (256, 240, 3)
        surf = pygame.surfarray.make_surface(np.transpose(screen_rgb, (1, 0, 2)))
        scaled_game = pygame.transform.scale(surf, (w, game_view_h))
        self.window.blit(scaled_game, (0, 46))

        # Overlays
        status_msg = f"Mario X: {mario_x:6.1f}px | Action: {action_name}"
        self._draw_hud_overlays(
            game_title="Super Mario Bros (World 1-1)",
            iteration=iteration,
            total_iters=total_iters,
            is_realtime=is_realtime,
            is_exploit=is_exploit,
            exploit_name=exploit_name,
            step=step,
            q_expectations=q_expectations,
            anomaly_score=anomaly_score,
            is_flagged=is_flagged,
            status_text=status_msg,
            victory=level_complete,
            victory_text="★ LEVEL COMPLETE! FLAGPOLE REACHED ★"
        )

        pygame.display.flip()
        target_fps = self.fps_realtime if is_realtime else self.fps_fast
        self.clock.tick(target_fps)
        return True

    def render_doom_frame(
        self,
        screen_buffer: np.ndarray,
        iteration: int,
        total_iters: int,
        is_realtime: bool,
        is_exploit: bool,
        exploit_name: str,
        step: int,
        q_expectations: np.ndarray,
        anomaly_score: float,
        is_flagged: bool,
        health: float,
        action_name: str,
        episode_complete: bool = False
    ) -> bool:
        """Renders ViZDoom screen buffer (3, H, W) or (H, W, 3) with Quantum HUD."""
        if not self.enabled or self.window is None:
            return True

        if not self.handle_events():
            return False

        w, h = self.width, self.height
        game_view_h = h - 46 - 94

        # Convert screen_buffer to (W, H, 3) for surfarray
        if screen_buffer.ndim == 3:
            if screen_buffer.shape[0] == 3:  # (3, H, W)
                arr = np.transpose(screen_buffer, (2, 1, 0)) # (W, H, 3)
            else:  # (H, W, 3)
                arr = np.transpose(screen_buffer, (1, 0, 2))
        else:
            arr = np.zeros((w, game_view_h, 3), dtype=np.uint8)

        surf = pygame.surfarray.make_surface(arr)
        scaled_game = pygame.transform.scale(surf, (w, game_view_h))
        self.window.blit(scaled_game, (0, 46))

        status_msg = f"Health: {health:5.1f}% | Action: {action_name}"
        self._draw_hud_overlays(
            game_title="ViZDoom (Corridor Combat)",
            iteration=iteration,
            total_iters=total_iters,
            is_realtime=is_realtime,
            is_exploit=is_exploit,
            exploit_name=exploit_name,
            step=step,
            q_expectations=q_expectations,
            anomaly_score=anomaly_score,
            is_flagged=is_flagged,
            status_text=status_msg,
            victory=episode_complete,
            victory_text="★ LEVEL CLEAR! CORRIDOR CLEARED ★"
        )

        pygame.display.flip()
        target_fps = 35 if is_realtime else self.fps_fast
        self.clock.tick(target_fps)
        return True

    def render_glitch_grid_frame(
        self,
        x: float,
        y: float,
        vx: float,
        collision_state: int,
        glitch_triggered: bool,
        iteration: int,
        total_iters: int,
        is_realtime: bool,
        is_exploit: bool,
        exploit_name: str,
        step: int,
        q_expectations: np.ndarray,
        anomaly_score: float,
        is_flagged: bool,
        action_name: str,
        level_complete: bool = False
    ) -> bool:
        """Renders 2D platformer graphics for GlitchGrid2D with Quantum HUD."""
        if not self.enabled or self.window is None:
            return True

        if not self.handle_events():
            return False

        w, h = self.width, self.height
        game_view_h = h - 46 - 94

        surf = pygame.Surface((w, game_view_h))
        # Sky
        surf.fill((100, 149, 237))

        # Clouds
        pygame.draw.ellipse(surf, (240, 248, 255), (100, 60, 110, 40))
        pygame.draw.ellipse(surf, (240, 248, 255), (460, 50, 150, 50))

        # Ground
        ground_y = game_view_h - 70
        pygame.draw.rect(surf, (139, 69, 19), (0, ground_y, w, 70))
        pygame.draw.rect(surf, (34, 139, 34), (0, ground_y, w, 16))

        # Obstacle Wall at x=48.0
        wall_px = int(48.0 / 100.0 * w)
        wall_w = 26
        wall_h = 170
        pygame.draw.rect(surf, (178, 34, 34), (wall_px, ground_y - wall_h, wall_w, wall_h))
        for by in range(ground_y - wall_h, ground_y, 22):
            pygame.draw.line(surf, (80, 10, 10), (wall_px, by), (wall_px + wall_w, by), 2)

        # Goal Flagpole at x=95.0
        flag_px = int(95.0 / 100.0 * w)
        pole_h = 250
        pygame.draw.rect(surf, (192, 192, 192), (flag_px, ground_y - pole_h, 8, pole_h))
        pygame.draw.polygon(surf, (255, 215, 0), [
            (flag_px + 8, ground_y - pole_h),
            (flag_px + 45, ground_y - pole_h + 20),
            (flag_px + 8, ground_y - pole_h + 40)
        ])
        pygame.draw.circle(surf, (255, 215, 0), (flag_px + 4, ground_y - pole_h), 8)

        # Player
        player_px = int(np.clip(x / 100.0 * w, 10, w - 40))
        player_py = int(ground_y - 48 - (y / 50.0 * 200))

        # Warp trail if glitched
        if glitch_triggered or is_flagged:
            pygame.draw.circle(surf, (0, 255, 255), (player_px + 16, player_py + 24), 32, 3)
            for _ in range(4):
                ox = np.random.randint(-22, 22)
                oy = np.random.randint(-22, 22)
                pygame.draw.circle(surf, (255, 0, 128), (player_px + 16 + ox, player_py + 24 + oy), 3)

        # Mario avatar
        pygame.draw.rect(surf, (220, 20, 60), (player_px + 6, player_py, 20, 12))  # Cap
        pygame.draw.rect(surf, (255, 218, 185), (player_px + 8, player_py + 12, 16, 10))  # Face
        pygame.draw.rect(surf, (30, 60, 200), (player_px + 4, player_py + 22, 24, 18))  # Overalls
        pygame.draw.rect(surf, (100, 50, 0), (player_px + 2, player_py + 40, 12, 8))  # Shoes
        pygame.draw.rect(surf, (100, 50, 0), (player_px + 18, player_py + 40, 12, 8))

        self.window.blit(surf, (0, 46))

        status_msg = f"Player X: {x:5.1f} / 100.0 | Vx: {vx:+5.2f} | Action: {action_name}"
        self._draw_hud_overlays(
            game_title="GlitchGrid 2D Physics Course",
            iteration=iteration,
            total_iters=total_iters,
            is_realtime=is_realtime,
            is_exploit=is_exploit,
            exploit_name=exploit_name,
            step=step,
            q_expectations=q_expectations,
            anomaly_score=anomaly_score,
            is_flagged=is_flagged,
            status_text=status_msg,
            victory=level_complete,
            victory_text="★ LEVEL COMPLETE! GOAL FLAG REACHED ★"
        )

        pygame.display.flip()
        target_fps = self.fps_realtime if is_realtime else self.fps_fast
        self.clock.tick(target_fps)
        return True

    def render_chess_frame(
        self,
        board: Any,
        iteration: int,
        total_iters: int,
        is_realtime: bool,
        is_exploit: bool,
        exploit_name: str,
        step: int,
        q_expectations: np.ndarray,
        anomaly_score: float,
        is_flagged: bool,
        move_san: str,
        game_over: bool = False
    ) -> bool:
        """Renders 8x8 Chessboard with live pieces and Quantum HUD."""
        if not self.enabled or self.window is None:
            return True

        if not self.handle_events():
            return False

        w, h = self.width, self.height
        game_view_h = h - 46 - 94

        surf = pygame.Surface((w, game_view_h))
        surf.fill((25, 30, 40))

        # Draw 8x8 board centered
        sq_size = 64
        board_w = sq_size * 8
        bx = (w - board_w) // 2
        by = (game_view_h - board_w) // 2

        light_color = (235, 236, 208)
        dark_color = (119, 149, 86)
        piece_font = pygame.font.SysFont("Segoe UI Symbol", 38)

        # Unicode chess piece glyphs
        piece_symbols = {
            "P": "♙", "N": "♘", "B": "♗", "R": "♖", "Q": "♕", "K": "♔",
            "p": "♟", "n": "♞", "b": "♝", "r": "♜", "q": "♛", "k": "♚"
        }

        for rank in range(8):
            for file in range(8):
                sq_rect = pygame.Rect(bx + file * sq_size, by + (7 - rank) * sq_size, sq_size, sq_size)
                col = light_color if (rank + file) % 2 == 1 else dark_color
                pygame.draw.rect(surf, col, sq_rect)

                # Draw piece
                try:
                    import chess
                    sq_idx = chess.square(file, rank)
                    piece = board.piece_at(sq_idx)
                    if piece:
                        symbol = piece_symbols.get(piece.symbol(), piece.symbol())
                        p_col = (20, 20, 20) if piece.color == chess.BLACK else (255, 255, 255)
                        # Shadow
                        p_txt_bg = piece_font.render(symbol, True, (0, 0, 0))
                        p_txt = piece_font.render(symbol, True, p_col)
                        surf.blit(p_txt_bg, (sq_rect.x + 14, sq_rect.y + 6))
                        surf.blit(p_txt, (sq_rect.x + 12, sq_rect.y + 4))
                except Exception:
                    pass

        # Border
        pygame.draw.rect(surf, (80, 100, 130), (bx - 2, by - 2, board_w + 4, board_w + 4), 3)

        self.window.blit(surf, (0, 46))

        status_msg = f"Last Move: {move_san} | Board Turn: {'White' if getattr(board, 'turn', True) else 'Black'}"
        self._draw_hud_overlays(
            game_title="Quantum Chess Engine (Groth16 Verification)",
            iteration=iteration,
            total_iters=total_iters,
            is_realtime=is_realtime,
            is_exploit=is_exploit,
            exploit_name=exploit_name,
            step=step,
            q_expectations=q_expectations,
            anomaly_score=anomaly_score,
            is_flagged=is_flagged,
            status_text=status_msg,
            victory=game_over,
            victory_text="★ MATCH COMPLETE ★"
        )

        pygame.display.flip()
        target_fps = 4 if is_realtime else 30
        self.clock.tick(target_fps)
        return True

    def close(self):
        """Safely closes Pygame window."""
        if self.enabled and PYGAME_AVAILABLE:
            try:
                pygame.quit()
            except Exception:
                pass
        self.enabled = False

