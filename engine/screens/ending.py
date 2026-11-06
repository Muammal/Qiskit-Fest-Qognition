"""engine/screens/ending.py - Single Cinematic Ending Cutscene & Results Reveal.
Replaces the old debrief modal with a single, dramatic, resolution-adaptive
game-ending sequence triggered only once per finished run.

Sequence:
1. Transition: Mood tint (warm sunrise for survival, dusk/ash for death).
2. Title Card: Outlined ribbon title ("Rescued at Dawn", "Lost to the Eruption", etc.).
3. Results Reveal (with count-up animations & staggered pop-ins):
   - Grade (S/A/B/C/D) & Stars (1-3)
   - Survival Rate (%) and Survivors vs Deaths icon row
   - Important Numbers (vitals, resources, shelters, hazards, evacuation results)
   - Decisive moment & cause of death (if fatal)
   - Quantum cognition highlights (order effects, decoherence, divergence %)
   - Decision timeline strip
4. Closing Beat: Epilogue text & agent status pose.
5. Action Buttons (WoodButtons): Replay [R], New Seed [N], Switch Mind [Q], Menu [ESC/H].
"""

import os
import math
import threading
from typing import Dict, Any, List, Optional, Tuple, Callable
import pygame
import pytweening

import contracts
from engine.display import Display
from engine.ui_kit import (
    COLOR_PARCHMENT, COLOR_WOOD, COLOR_DARK_WOOD, COLOR_OUTLINE_BROWN,
    COLOR_GRASS, COLOR_DEEP_GREEN, COLOR_GOLD, COLOR_RED, COLOR_SKY,
    COLOR_WHITE, COLOR_CREAM, OutlinedText, NineSlicePanel, WoodButton,
    StarRating, CountUpNumber
)
from engine.assets import AssetManager


def build_ending_stats(timeline: Dict[str, Any]) -> Dict[str, Any]:
    """Pure function that calculates comprehensive ending metrics and highlights

    from any timeline dictionary or simulation run result.
    """
    steps = timeline.get("steps", [])
    outcome = timeline.get("outcome", "survived")
    cause = timeline.get("cause")
    world_info = timeline.get("world", {})
    scenario = world_info.get("scenario", "volcano")
    mind_type = world_info.get("mind", "quantum")
    max_steps = 36 if scenario in ("volcano", "island") else len(steps)
    if max_steps == 0:
        max_steps = max(1, len(steps))

    steps_survived = len(steps)
    survival_pct = round((steps_survived / max(1, max_steps)) * 100.0, 1)

    # 1. Final Vitals & Lowest Vital
    final_vitals = {
        "hunger": 0.5, "thirst": 0.5, "warmth": 0.5,
        "energy": 0.5, "safety": 0.5, "morale": 0.5
    }
    lowest_vital_name = "none"
    lowest_vital_val = 1.0
    lowest_vital_step = 0

    if steps:
        last_state = steps[-1].get("state", {})
        if "needs" in last_state:
            final_vitals = {k: round(v, 2) for k, v in last_state["needs"].items()}

        # Scan for lowest vital across run
        for idx, s in enumerate(steps):
            st = s.get("state", {})
            needs = st.get("needs", {})
            for name, val in needs.items():
                if val < lowest_vital_val:
                    lowest_vital_val = val
                    lowest_vital_name = name
                    lowest_vital_step = idx + 1

    # 2. Grade and Stars (S / A / B / C / D)
    avg_vital = sum(final_vitals.values()) / max(1, len(final_vitals))
    if outcome == "survived":
        if avg_vital >= 0.70 and steps_survived >= max_steps:
            grade, stars = "S", 3
        elif avg_vital >= 0.50:
            grade, stars = "A", 3
        else:
            grade, stars = "B", 2
    else:
        if steps_survived >= int(max_steps * 0.65):
            grade, stars = "C", 1
        else:
            grade, stars = "D", 1

    # 3. Resources, Shelters & Distance Traveled
    resources_gathered = {"wood": 0, "food": 0}
    shelters_built = 0
    distance_traveled = 0
    prev_pos = None

    for s in steps:
        act = s.get("action", "")
        if act == "forage":
            resources_gathered["food"] += 1
        elif act == "craft":
            resources_gathered["wood"] += 1
        elif act == "build_shelter":
            shelters_built += 1

        curr_pos = s.get("pos_after")
        if curr_pos and prev_pos and curr_pos != prev_pos:
            distance_traveled += 1
        prev_pos = curr_pos

    # 4. Weather & Hazard Events Encountered
    hazards_faced: Dict[str, int] = {}
    for s in steps:
        ev = s.get("event", "none")
        if ev and ev != "none":
            hazards_faced[ev] = hazards_faced.get(ev, 0) + 1

    # 5. Evacuation Details (for Volcano or Scenarios with evacuation map)
    evac_data = timeline.get("evacuation", {})
    evac_result = {
        "reached_assembly": evac_data.get("reached_assembly_step") is not None,
        "reached_safe": evac_data.get("reached_safe_step") is not None,
        "reached_safe_step": evac_data.get("reached_safe_step"),
        "warning_lead_hours": evac_data.get("warning_lead_hours"),
        "margin_hours": evac_data.get("margin_hours")
    }

    # 6. Quantum Cognition Highlights & Divergence %
    order_effects_count = 0
    stress_decoherence_episodes = 0
    divergence_count = 0

    for s in steps:
        q_info = s.get("quantum") or {}
        st = s.get("state", {})
        if q_info.get("order_gap") and abs(q_info["order_gap"]) > 0.05:
            order_effects_count += 1
        if (q_info.get("lam", 0.0) > 0.4) or (st.get("stress", 0.0) > 0.5):
            stress_decoherence_episodes += 1

        # Check action divergence against classical rational baseline
        try:
            classical_choice = contracts.classical_decide(st).get("action")
            if s.get("action") != classical_choice:
                divergence_count += 1
        except Exception:
            pass

    divergence_pct = round((divergence_count / max(1, steps_survived)) * 100.0, 1)

    # 7. Decisive Moment
    if outcome == "survived":
        decisive_moment = f"Endured all {steps_survived} hazard phases through step {max_steps}."
    else:
        decisive_moment = f"Fatal breakdown ({cause or 'collapse'}) at Step {steps_survived}; lowest vital was {lowest_vital_name} ({int(lowest_vital_val * 100)}%)."

    # 8. Scenario-Specific Titles & Epilogues
    if outcome == "survived":
        if scenario == "volcano":
            title = "Evacuated to the Coast" if evac_result["reached_safe"] else "Survived the Eruption"
            epilogue = "The pyroclastic surge swept the slopes, but timely evacuation routes held."
        elif scenario == "island":
            title = "Rescued at Dawn"
            epilogue = "A passing vessel spotted the shelter smoke. Wilderness survived!"
        elif scenario == "titanic":
            title = "Rescued by Carpathia"
            epilogue = "Lifeboat reached safety in the freezing North Atlantic."
        elif scenario == "pompeii":
            title = "Escaped the Bay of Naples"
            epilogue = "Fled the pumice fall before the fourth pyroclastic surge sealed the city."
        elif scenario == "waterloo":
            title = "Evacuated from Chlorine Plume"
            epilogue = "Reached fresh air before toxic thresholds were breached."
        else:
            title = "Mission Accomplished"
            epilogue = "Successfully navigated extreme hazards and existential stress."
    else:
        if scenario == "volcano":
            title = "Lost to the Eruption"
            epilogue = f"Overcome by {cause or 'volcanic hazard'} on the mountain slopes."
        elif scenario == "island":
            title = "The Island Claimed Them"
            epilogue = f"Succumbed to {cause or 'exposure'} before rescue arrived."
        elif scenario == "titanic":
            title = "Lost in the North Atlantic"
            epilogue = f"Lost in the freezing water at 02:20."
        elif scenario == "pompeii":
            title = "Entombed in Pompeii"
            epilogue = f"Overwhelmed by pyroclastic surge deposits."
        else:
            title = "Survival Failed"
            epilogue = f"Mission ended fatally at step {steps_survived} due to {cause or 'exhaustion'}."

    # 9. Decision Timeline Strip Actions
    timeline_strip = []
    action_colors = {
        "forage": (76, 175, 80),
        "drink": (33, 150, 243),
        "rest": (156, 39, 176),
        "explore": (255, 193, 7),
        "build_shelter": (255, 152, 0),
        "craft": (121, 85, 72),
        "hide": (244, 67, 54),
    }
    for s in steps:
        act = s.get("action", "rest")
        ev = s.get("event", "none")
        timeline_strip.append({
            "step": s.get("t", 0) + 1,
            "action": act,
            "color": action_colors.get(act, (160, 160, 160)),
            "event": ev if ev != "none" else None
        })

    return {
        "scenario": scenario,
        "mind_type": mind_type,
        "outcome": outcome,
        "cause": cause,
        "title": title,
        "epilogue": epilogue,
        "grade": grade,
        "stars": stars,
        "steps_survived": steps_survived,
        "max_steps": max_steps,
        "survival_pct": survival_pct,
        "final_vitals": final_vitals,
        "lowest_vital": {"name": lowest_vital_name, "value": lowest_vital_val, "step": lowest_vital_step},
        "resources": resources_gathered,
        "shelters_built": shelters_built,
        "distance_traveled": distance_traveled,
        "hazards_faced": hazards_faced,
        "evacuation": evac_result,
        "quantum_highlights": {
            "order_effects_count": order_effects_count,
            "stress_decoherence_episodes": stress_decoherence_episodes,
            "divergence_count": divergence_count,
            "divergence_pct": divergence_pct
        },
        "decisive_moment": decisive_moment,
        "timeline_strip": timeline_strip
    }


class EndingCutsceneScreen:
    """Renders the single cinematic ending screen with animated count-ups,

    stars, survival comparisons, and crisp Hay Day UI buttons.
    """

    def __init__(
        self,
        timeline_data: Dict[str, Any],
        on_replay: Optional[Callable] = None,
        on_new_seed: Optional[Callable] = None,
        on_switch_mind: Optional[Callable] = None,
        on_main_menu: Optional[Callable] = None
    ):
        self.data = build_ending_stats(timeline_data)
        self.on_replay = on_replay
        self.on_new_seed = on_new_seed
        self.on_switch_mind = on_switch_mind
        self.on_main_menu = on_main_menu

        # Sequence Phase Tracking
        self.anim_time = 0.0
        self.transition_alpha = 255  # Starts fully tinted and fades in
        self.count_up_survival = CountUpNumber(self.data["survival_pct"], duration=1.2, is_int=False, suffix="%")
        self.count_up_steps = CountUpNumber(self.data["steps_survived"], duration=1.0, is_int=True)
        self.star_rating = StarRating(3)

        # Opposite mind comparison background thread
        self.comparison_ready = False
        self.comparison_pct = None
        self._start_background_comparison(timeline_data)

        # Navigation Buttons (repositioned resolution-adaptively on draw)
        self.btn_replay = WoodButton(pygame.Rect(0, 0, 160, 48), "Replay [R]", 18, bg_color=COLOR_DEEP_GREEN, callback=self.on_replay)
        self.btn_new_seed = WoodButton(pygame.Rect(0, 0, 160, 48), "New Seed [N]", 18, bg_color=COLOR_WOOD, callback=self.on_new_seed)
        self.btn_switch_mind = WoodButton(pygame.Rect(0, 0, 180, 48), "Switch Mind [Q]", 18, bg_color=(120, 60, 160), callback=self.on_switch_mind)
        self.btn_menu = WoodButton(pygame.Rect(0, 0, 150, 48), "Menu [ESC]", 18, bg_color=COLOR_DARK_WOOD, callback=self.on_main_menu)

    def _start_background_comparison(self, timeline_data: Dict[str, Any]):
        """Runs opposite mind model on identical seed in background thread."""
        def run_comp():
            try:
                from engine.simulation import SimulationEngine
                world = timeline_data.get("world", {})
                seed = world.get("seed", 101)
                curr_mind = world.get("mind", "quantum")
                scen = world.get("scenario", "volcano")
                opp_mind = "classical" if curr_mind == "quantum" else "quantum"

                sim = SimulationEngine(seed=seed, mind_type=opp_mind, scenario=scen)
                res = sim.run()
                steps_opp = len(res.get("steps", []))
                self.comparison_pct = round((steps_opp / 36.0) * 100.0, 1)
                self.comparison_ready = True
            except Exception:
                self.comparison_ready = True

        t = threading.Thread(target=run_comp, daemon=True)
        t.start()

    def update(self, dt: float, mouse_pos: Tuple[int, int]):
        self.anim_time += dt
        self.count_up_survival.update(dt)
        self.count_up_steps.update(dt)

        if self.anim_time > 0.8:
            self.star_rating.set_rating(self.data["stars"])
            self.star_rating.update(dt)

        # Update buttons
        for b in (self.btn_replay, self.btn_new_seed, self.btn_switch_mind, self.btn_menu):
            b.check_hover(mouse_pos)
            b.update(dt)

    def handle_event(self, event: pygame.event.Event, mouse_pos: Tuple[int, int]) -> bool:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                # Skip animations to full reveal
                self.count_up_survival.skip()
                self.count_up_steps.skip()
                self.star_rating.anim_progress = 1.0
                return True
            elif event.key == pygame.K_r:
                if self.on_replay:
                    self.on_replay()
                return True
            elif event.key == pygame.K_n:
                if self.on_new_seed:
                    self.on_new_seed()
                return True
            elif event.key == pygame.K_q:
                if self.on_switch_mind:
                    self.on_switch_mind()
                return True
            elif event.key in (pygame.K_ESCAPE, pygame.K_h):
                if self.on_main_menu:
                    self.on_main_menu()
                return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for b in (self.btn_replay, self.btn_new_seed, self.btn_switch_mind, self.btn_menu):
                if b.handle_mouse_down(mouse_pos):
                    return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            for b in (self.btn_replay, self.btn_new_seed, self.btn_switch_mind, self.btn_menu):
                if b.handle_mouse_up(mouse_pos):
                    return True

        return False

    def draw(self, surface: pygame.Surface, mouse_pos: Tuple[int, int] = (0, 0)):
        w = surface.get_width()
        h = surface.get_height()

        # 1. Background Mood Tint
        is_survived = self.data["outcome"] == "survived"
        bg_tint = (40, 60, 35) if is_survived else (45, 25, 20)
        surface.fill(bg_tint)

        # 2. Main Parchment Report Slab
        modal_w = min(Display.S(1200), int(w * 0.90))
        modal_h = min(Display.S(740), int(h * 0.90))
        modal_rect = pygame.Rect((w - modal_w) // 2, (h - modal_h) // 2, modal_w, modal_h)

        NineSlicePanel.draw_wood_frame(surface, modal_rect, corner_radius=18)
        inner_rect = modal_rect.inflate(-Display.S(24), -Display.S(24))
        NineSlicePanel.draw_parchment_card(surface, inner_rect, corner_radius=14)

        # 3. Header Ribbon Title Card
        ribbon_w = min(Display.S(640), int(modal_w * 0.70))
        ribbon_h = Display.S(54)
        ribbon_rect = pygame.Rect((w - ribbon_w) // 2, modal_rect.top - Display.S(14), ribbon_w, ribbon_h)
        ribbon_color = COLOR_GOLD if is_survived else (190, 45, 35)
        NineSlicePanel.draw_ribbon(surface, ribbon_rect, self.data["title"].upper(), size=28, color=ribbon_color)

        # 4. Results Reveal Columns (Left: Outcome & Stats | Right: Cognitive & Details)
        col_y = inner_rect.top + Display.S(48)
        col_w = (inner_rect.width - Display.S(36)) // 2

        # Left Column: Grade & Survival Rate
        left_x = inner_rect.left + Display.S(18)
        grade_str = f"GRADE {self.data['grade']}"
        grade_color = COLOR_DEEP_GREEN if self.data['grade'] in ('S', 'A') else (COLOR_GOLD if self.data['grade'] == 'B' else COLOR_RED)
        grade_surf = OutlinedText.render(grade_str, 42, color=grade_color, outline_thickness=4)
        surface.blit(grade_surf, (left_x, col_y))

        # Star Rating
        self.star_rating.draw(surface, (left_x + col_w - Display.S(70), col_y + Display.S(20)), size=Display.S(32))

        # Survival Metrics
        surv_y = col_y + Display.S(60)
        s_lbl = OutlinedText.render(f"Survival Rate: {self.count_up_survival.get_text()}", 22, color=COLOR_DARK_WOOD, outline_color=COLOR_PARCHMENT, outline_thickness=1)
        surface.blit(s_lbl, (left_x, surv_y))

        steps_lbl = OutlinedText.render(f"Steps Endured: {self.count_up_steps.get_text()} / {self.data['max_steps']}", 18, color=COLOR_DARK_WOOD, outline_color=COLOR_PARCHMENT, outline_thickness=1)
        surface.blit(steps_lbl, (left_x, surv_y + Display.S(30)))

        # Survivors vs Deaths Row
        icon_y = surv_y + Display.S(65)
        surv_status_str = "Status: SURVIVED & EVACUATED" if is_survived else f"Cause of Death: {str(self.data['cause']).upper()}"
        status_color = COLOR_DEEP_GREEN if is_survived else COLOR_RED
        stat_surf = OutlinedText.render(surv_status_str, 16, color=status_color)
        surface.blit(stat_surf, (left_x, icon_y))

        # Final Vitals Mini Cards
        v_y = icon_y + Display.S(35)
        vitals_txt = "Final Vitals: " + " | ".join([f"{k[:4].capitalize()}: {int(v * 100)}%" for k, v in self.data['final_vitals'].items() if k in ('hunger', 'thirst', 'warmth', 'safety')])
        v_surf = OutlinedText.render(vitals_txt, 14, color=COLOR_DARK_WOOD, outline_color=COLOR_PARCHMENT, outline_thickness=1)
        surface.blit(v_surf, (left_x, v_y))

        # Right Column: Quantum Highlights & Decisive Moment
        right_x = left_x + col_w + Display.S(18)
        q_hdr = OutlinedText.render("Quantum Cognition Highlights", 22, color=COLOR_DARK_WOOD)
        surface.blit(q_hdr, (right_x, col_y))

        qh = self.data["quantum_highlights"]
        q_y = col_y + Display.S(35)
        q1 = OutlinedText.render(f"• Decision Divergences (vs Classical): {qh['divergence_pct']}%", 16, color=(80, 40, 110))
        q2 = OutlinedText.render(f"• Cue Order Effects Triggered: {qh['order_effects_count']}", 16, color=(80, 40, 110))
        q3 = OutlinedText.render(f"• Stress Decoherence Episodes: {qh['stress_decoherence_episodes']}", 16, color=(80, 40, 110))
        surface.blit(q1, (right_x, q_y))
        surface.blit(q2, (right_x, q_y + Display.S(24)))
        surface.blit(q3, (right_x, q_y + Display.S(48)))

        # Decisive Moment Box
        dec_y = q_y + Display.S(85)
        dec_hdr = OutlinedText.render("The Decisive Moment:", 16, color=COLOR_DARK_WOOD)
        surface.blit(dec_hdr, (right_x, dec_y))
        dec_msg = OutlinedText.render(self.data["decisive_moment"][:60], 14, color=COLOR_OUTLINE_BROWN, outline_thickness=1)
        surface.blit(dec_msg, (right_x, dec_y + Display.S(24)))

        # 5. Decision Timeline Strip (Bottom Section)
        strip_y = inner_rect.bottom - Display.S(135)
        strip_hdr = OutlinedText.render("Decision Timeline Strip (Action Sequence):", 14, color=COLOR_DARK_WOOD)
        surface.blit(strip_hdr, (left_x, strip_y - Display.S(22)))

        strip_rect = pygame.Rect(left_x, strip_y, inner_rect.width - Display.S(36), Display.S(28))
        pygame.draw.rect(surface, (60, 40, 25), strip_rect, border_radius=Display.S(6))

        # Render colored blocks per step
        strip = self.data["timeline_strip"]
        if strip:
            block_w = strip_rect.width / max(1, len(strip))
            for idx, item in enumerate(strip):
                bx = strip_rect.x + idx * block_w
                b_rect = pygame.Rect(bx, strip_rect.y + 2, max(2, block_w - 1), strip_rect.height - 4)
                pygame.draw.rect(surface, item["color"], b_rect, border_radius=2)
                # Event marker on top
                if item["event"]:
                    pygame.draw.circle(surface, COLOR_GOLD, (int(bx + block_w / 2), strip_rect.y - Display.S(5)), max(2, Display.S(3)))

        # Epilogue text
        ep_surf = OutlinedText.render(f"\"{self.data['epilogue']}\"", 16, color=COLOR_DARK_WOOD, outline_color=COLOR_PARCHMENT, outline_thickness=1)
        surface.blit(ep_surf, ep_surf.get_rect(center=(w // 2, strip_y + Display.S(42))))

        # 6. Action Buttons Bar
        btn_y = modal_rect.bottom - Display.S(58)
        self.btn_replay.orig_rect = pygame.Rect(w // 2 - Display.S(360), btn_y, Display.S(160), Display.S(44))
        self.btn_new_seed.orig_rect = pygame.Rect(w // 2 - Display.S(185), btn_y, Display.S(160), Display.S(44))
        self.btn_switch_mind.orig_rect = pygame.Rect(w // 2 + Display.S(5), btn_y, Display.S(180), Display.S(44))
        self.btn_menu.orig_rect = pygame.Rect(w // 2 + Display.S(205), btn_y, Display.S(150), Display.S(44))

        for b in (self.btn_replay, self.btn_new_seed, self.btn_switch_mind, self.btn_menu):
            b.draw(surface)
