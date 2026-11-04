"""Simulation controller; drawing lives in gui_map and gui_panels."""
import math
import os
import random
import time
import pygame
import contracts
from engine.simulation import SimulationEngine, DEFAULT_STEPS
from engine.gui_map import MapRenderer, MAP_SIZE, TILE_SIZE
from engine import gui_panels as panels

WINDOW_WIDTH = 1280  # assumption: virtual display width
WINDOW_HEIGHT = 760  # assumption: virtual display height
FPS = 60  # assumption: animation target; independent of simulation clock


def ui_font(size, bold=False):
    """Segoe UI by file, because pygame resolves the family name 'segoeui' to the Light cut."""
    path=os.path.join(os.environ.get('WINDIR',r'C:\Windows'),'Fonts','seguisb.ttf' if bold else 'segoeui.ttf')
    return pygame.font.Font(path,size) if os.path.exists(path) else pygame.font.SysFont('arial',size,bold=bold)


class UIButton:
    def __init__(self, rect, text, font):
        self.rect, self.text, self.font = pygame.Rect(rect), text.strip() or 'X', font
        self.is_active = False

    def draw(self, surface, dt=0.):
        pygame.draw.rect(surface,(41,106,101) if self.is_active else (226,230,215),self.rect,border_radius=5)
        pygame.draw.rect(surface,(129,151,139),self.rect,1,border_radius=5)
        label=self.font.render(self.text,True,(249,246,224) if self.is_active else panels.INK)
        surface.blit(label,label.get_rect(center=self.rect.center))


class WeatherSystem:
    def __init__(self):
        self.particles=[]

    def update(self, weather, dt):
        self.particles=[]  # Particle positions are deterministic functions of visual time.


class IslandVisualizerApp:
    def __init__(self, seed=101, mind_type='quantum', noise_source='stub', start_screen='home'):
        pygame.init()
        pygame.display.set_caption('Stranded | Volcano evacuation')
        self.screen=pygame.display.set_mode((WINDOW_WIDTH,WINDOW_HEIGHT),pygame.RESIZABLE)
        self.canvas=pygame.Surface((WINDOW_WIDTH,WINDOW_HEIGHT))
        self.clock=pygame.time.Clock()
        self.font_hero=ui_font(32,True)
        self.font_title=ui_font(21,True)
        self.font_sub=ui_font(16,True)
        self.font_body=ui_font(15)
        self.font_small=ui_font(13)
        self.font_mono=self.font_small
        self.font_bubble=self.font_body
        self.seed,self.mind_type,self.noise_source=seed,mind_type,noise_source
        self.max_steps=DEFAULT_STEPS
        self.app_state=start_screen
        self.is_fullscreen=False
        self.speed_multiplier=1.
        self.step_delay=.8  # assumption: readable default replay cadence
        self.weather=WeatherSystem()
        self._init_simulation()
        self._build_buttons()
        self.preview_mini_map=self._generate_mini_map(seed,320)

    def text(self, text, x, y, color=panels.INK, font=None):
        self.canvas.blit((font or self.font_body).render(str(text),True,color),(x,y))

    def elide(self, text, width, font):
        if font.size(text)[0]<=width:
            return text
        while text and font.size(text+'...')[0]>width:
            text=text[:-1]
        return text+'...'

    def _build_buttons(self):
        def button(rect,text):
            return UIButton(rect,text,self.font_body)
        self.btn_nav_home=button((14,10,76,30),'Menu')
        self.btn_nav_pause=button((98,10,76,30),'Pause')
        self.btn_nav_step=button((182,10,76,30),'Step')
        self.btn_nav_speed=button((266,10,76,30),'Speed')
        self.btn_nav_mind=button((350,10,136,30),'Switch stub')
        self.btn_nav_log=button((494,10,116,30),'Action log')
        self.btn_nav_fs=button((618,10,126,30),'Fullscreen')
        self.sim_buttons=[self.btn_nav_home,self.btn_nav_pause,self.btn_nav_step,self.btn_nav_speed,self.btn_nav_mind,self.btn_nav_log,self.btn_nav_fs]
        self.btn_modal_replay=button((348,582,155,40),'Replay run')
        self.btn_modal_switch=button((516,582,183,40),'Compare stub mind')
        self.btn_modal_home=button((712,582,155,40),'Home')
        self.btn_modal_close=button((906,125,32,32),'X')
        self.modal_buttons=[self.btn_modal_replay,self.btn_modal_switch,self.btn_modal_home,self.btn_modal_close]
        self.btn_hist_close=button((1014,60,32,32),'X')
        self.btn_home_quantum=button((72,340,272,56),'Quantum-labelled stub')
        self.btn_home_classical=button((360,340,272,56),'Classical heuristic stub')
        self.btn_seed_down=button((72,456,44,44),'-')
        self.btn_seed_up=button((300,456,44,44),'+')
        self.btn_seed_random=button((360,456,132,44),'Random seed')
        self.horizon_buttons={n:button((72+i*184,565,168,44),f'{n*2} hours / {n} steps') for i,n in enumerate((12,24,36))}
        self.btn_launch=UIButton((72,643,560,48),'Start simulation',self.font_title)
        self.btn_launch.is_active=True
        self.home_buttons=[self.btn_home_quantum,self.btn_home_classical,self.btn_seed_down,self.btn_seed_up,self.btn_seed_random,*self.horizon_buttons.values(),self.btn_launch]

    def _init_simulation(self):
        self.engine=SimulationEngine(self.seed,self.mind_type,self.noise_source)
        self.world,self.agent=self.engine.world,self.engine.agent
        self.event_gen=self.engine.event_gen
        self.decide_fn=self.engine.decide_fn
        self.history=[]
        self.history_scroll=0
        self.step_idx=0
        self.current_event='none'
        self.current_weather=self.event_gen.weather[0]
        self.wind_deg=self.engine.volcano.hazard_by_step[0]['wind_deg']
        self.current_decision=dict(action='none',probs={a:1/7 for a in contracts.ACTIONS},reason='Waiting for the first decision.')
        self.show_evacuation_map=True
        self.show_debrief_modal=self.show_history_overlay=False
        self.is_paused=False
        self.last_step_time=time.time()
        self.char_screen_x=(self.agent.pos[0]+.5)*TILE_SIZE
        self.char_screen_y=(self.agent.pos[1]+.5)*TILE_SIZE
        self.char_bob=0.
        self.bubble_text='Listening for signs of unrest'
        self.bubble_timer=0.
        self.visual_time=0.
        self.lighting_lag=0.
        self.shake_timer=0.
        self.weather.particles.clear()
        self.renderer=MapRenderer(self.world)
        self.renderer.refresh(self)

    def _generate_mini_map(self, seed, size=240):
        preview=self.renderer.terrain.copy()
        preview.blit(self.renderer.zones,(0,0))
        preview.blit(self.renderer.zone_lines,(0,0))
        from engine.gui_map import point
        for route in self.world.routes_from_spawn:
            for i,(a,b) in enumerate(zip(route,route[1:])):
                if i%2==0:
                    pygame.draw.line(preview,(249,235,194),point(a),point(b),3)
        for i,p in enumerate(self.world.assembly_points):
            x,y=point(p)
            pygame.draw.circle(preview,(250,244,215),(x,y),15)
            label=self.font_title.render(chr(65+i),True,(20,78,70))
            preview.blit(label,label.get_rect(center=(x,y)))
        return pygame.transform.smoothscale(preview,(size,size))

    def _switch_mind(self):
        self.mind_type='classical' if self.mind_type=='quantum' else 'quantum'
        self.decide_fn=contracts.classical_decide if self.mind_type=='classical' else contracts.quantum_decide
        self.engine.decide_fn,self.engine.mind_type=self.decide_fn,self.mind_type

    def step_forward(self):
        if self.step_idx>=self.max_steps or not self.agent.is_alive:
            self.show_debrief_modal=True
            return
        self.engine.decide_fn=self.decide_fn
        record=self.engine.step()
        if record is None:
            return
        self.lighting_lag=2.  # assumption: interpolate the latest two-hour light change
        self.current_event=record['event']
        self.current_weather=self.event_gen.weather[record['t']]
        self.wind_deg=self.engine.volcano.hazard_by_step[record['t']]['wind_deg']
        self.current_decision={k:record[k] for k in ('action','probs','reason')}
        self.step_idx+=1
        self.history.append(dict(t=self.step_idx,state=self.agent.get_state(),event=record['event'],action=record['action'],decision=self.current_decision))
        self.history_scroll=max(0,len(self.history)-7)
        self.bubble_text=self._narrative(record['action'])
        self.bubble_timer=3.
        self.shake_timer=.3 if record['event'] in ('tremor','eruption') else 0.  # assumption: brief tremor cue
        self.renderer.refresh(self)
        if not self.agent.is_alive or self.step_idx>=self.max_steps:
            self.show_debrief_modal=True

    def _narrative(self, action):
        if not self.agent.is_alive:
            return 'Caught by the flow' if self.agent.cause_of_death in ('pyroclastic_flow','lahar','lava') else 'Unable to continue'
        p=tuple(self.agent.pos)
        if action=='hide' and self.world.volcanic_sign_seen:
            if p in self.world.assembly_points:
                return 'Waiting at assembly point '+chr(65+self.world.assembly_points.index(p))
            route=self.world.path(p,self.world.assembly_points)
            if route:
                return 'Heading for assembly point '+chr(65+self.world.assembly_points.index(route[-1]))
        if action=='drink':
            return 'Drinking at the spring' if any(math.dist(p,q)<=2 for q in self.world.clean_springs) else 'Seeking drinking water'
        if action=='rest':
            return 'Resting in the shelter' if self.world.is_in_shelter(*p) else 'Stopping to recover'
        return dict(forage='Searching for food and wood',build_shelter='Preparing a place to shelter',explore='Looking for a way through',craft='Making a useful tool',hide='Keeping a low profile').get(action,'Watching the island')

    def handle_event(self, ev):
        if ev.type==pygame.QUIT:
            return False
        if ev.type==pygame.KEYDOWN:
            key=ev.key
            if key==pygame.K_F11:
                self.toggle_fullscreen()
            elif self.show_history_overlay and key in (pygame.K_ESCAPE,pygame.K_TAB):
                self.show_history_overlay=False
            elif self.app_state=='home':
                if key in (pygame.K_RETURN,pygame.K_SPACE):
                    self._init_simulation(); self.app_state='sim'
            elif key==pygame.K_ESCAPE and self.show_debrief_modal:
                self.show_debrief_modal=False; self.is_paused=True
            elif key in (pygame.K_ESCAPE,pygame.K_h):
                self.app_state='home'
            elif key in (pygame.K_TAB,pygame.K_l):
                self.show_history_overlay=not self.show_history_overlay
            elif key==pygame.K_e:
                self.show_evacuation_map=not self.show_evacuation_map
            elif key==pygame.K_r:
                self._init_simulation()
            elif key==pygame.K_SPACE:
                self.is_paused=not self.is_paused
            elif key in (pygame.K_RIGHT,pygame.K_n) and not self.show_debrief_modal:
                self.step_forward()
            elif key==pygame.K_q:
                self._switch_mind()
            elif key in (pygame.K_1,pygame.K_2,pygame.K_3):
                self.speed_multiplier={pygame.K_1:1.,pygame.K_2:2.5,pygame.K_3:6.}[key]
        elif ev.type==pygame.MOUSEWHEEL and self.show_history_overlay:
            self.history_scroll=max(0,min(max(0,len(self.history)-7),self.history_scroll-ev.y))
        elif ev.type==pygame.MOUSEBUTTONDOWN:
            if ev.button in (4,5) and self.show_history_overlay:
                self.history_scroll=max(0,min(max(0,len(self.history)-7),self.history_scroll+(-1 if ev.button==4 else 1)))
            elif ev.button==1:
                pos=self.get_virtual_mouse_pos()
                if self.app_state=='home':
                    self._handle_home_click(pos)
                else:
                    self._handle_sim_click(pos)
        return True

    def _handle_home_click(self, pos):
        if self.btn_home_quantum.rect.collidepoint(pos):
            self.mind_type='quantum'
        elif self.btn_home_classical.rect.collidepoint(pos):
            self.mind_type='classical'
        elif self.btn_seed_down.rect.collidepoint(pos):
            self.seed=max(0,self.seed-1)
        elif self.btn_seed_up.rect.collidepoint(pos):
            self.seed+=1
        elif self.btn_seed_random.rect.collidepoint(pos):
            self.seed=random.SystemRandom().randrange(100000)
        elif self.btn_launch.rect.collidepoint(pos):
            self._init_simulation(); self.app_state='sim'
        for n,btn in self.horizon_buttons.items():
            if btn.rect.collidepoint(pos):
                self.max_steps=n

    def _handle_sim_click(self, pos):
        if self.show_history_overlay:
            if self.btn_hist_close.rect.collidepoint(pos):
                self.show_history_overlay=False
            return
        if self.show_debrief_modal:
            if self.btn_modal_close.rect.collidepoint(pos):
                self.show_debrief_modal=False; self.is_paused=True
            elif self.btn_modal_home.rect.collidepoint(pos):
                self.app_state='home'; self.show_debrief_modal=False
            elif self.btn_modal_replay.rect.collidepoint(pos):
                self._init_simulation()
            elif self.btn_modal_switch.rect.collidepoint(pos):
                self._switch_mind(); self._init_simulation()
            return
        if self.btn_nav_home.rect.collidepoint(pos):
            self.app_state='home'
        elif self.btn_nav_pause.rect.collidepoint(pos):
            self.is_paused=not self.is_paused
        elif self.btn_nav_step.rect.collidepoint(pos):
            self.step_forward()
        elif self.btn_nav_speed.rect.collidepoint(pos):
            self.speed_multiplier={1.:2.5,2.5:6.,6.:1.}[self.speed_multiplier]
        elif self.btn_nav_mind.rect.collidepoint(pos):
            self._switch_mind()
        elif self.btn_nav_log.rect.collidepoint(pos):
            self.show_history_overlay=True
        elif self.btn_nav_fs.rect.collidepoint(pos):
            self.toggle_fullscreen()

    def update_visuals(self, dt):
        self.visual_time+=dt
        self.lighting_lag*=max(0.,1-dt*5)  # assumption: smooth daylight interpolation
        self.bubble_timer=max(0.,self.bubble_timer-dt)
        self.shake_timer=max(0.,self.shake_timer-dt)
        self.char_screen_x+=((self.agent.pos[0]+.5)*19-self.char_screen_x)*min(1,dt*10)
        self.char_screen_y+=((self.agent.pos[1]+.5)*19-self.char_screen_y)*min(1,dt*10)
        self.weather.update(self.current_weather,dt)

    def draw(self, mouse_pos=(0,0)):
        if self.app_state=='home':
            panels.home(self)
            return
        self.renderer.draw(self)
        if self.shake_timer:
            offset=round(2*math.sin(self.visual_time*57))  # assumption: bounded two-pixel shake
            self.canvas.blit(self.canvas,(offset,0),pygame.Rect(0,0,760,760))
        pygame.draw.rect(self.canvas,(26,49,54),(0,0,760,48))
        self.btn_nav_pause.text='Play' if self.is_paused else 'Pause'
        for btn in self.sim_buttons:
            btn.draw(self.canvas)
        panels.dashboard(self)
        if mouse_pos!=(0,0) and not self.show_history_overlay and not self.show_debrief_modal:
            self.renderer.tooltip(self,mouse_pos)
        if self.show_debrief_modal:
            panels.debrief(self)
        if self.show_history_overlay:
            panels.history(self)

    def toggle_fullscreen(self):
        self.is_fullscreen=not self.is_fullscreen
        self.screen=pygame.display.set_mode((0,0),pygame.FULLSCREEN) if self.is_fullscreen else pygame.display.set_mode((1280,760),pygame.RESIZABLE)

    def get_virtual_mouse_pos(self):
        x,y=pygame.mouse.get_pos()
        w,h=self.screen.get_size()
        scale=min(w/1280,h/760)
        return max(0,min(1279,int((x-(w-1280*scale)/2)/scale))),max(0,min(759,int((y-(h-760*scale)/2)/scale)))

    def present(self):
        w,h=self.screen.get_size()
        scale=min(w/1280,h/760)
        size=(int(1280*scale),int(760*scale))
        self.screen.fill((18,31,34))
        self.screen.blit(pygame.transform.scale(self.canvas,size),((w-size[0])//2,(h-size[1])//2))
        pygame.display.flip()

    def run(self):
        running=True
        while running:
            dt=min(.1,self.clock.tick(FPS)/1000)
            for ev in pygame.event.get():
                if not self.handle_event(ev):
                    running=False
            if self.app_state=='sim' and not (self.is_paused or self.show_history_overlay or self.show_debrief_modal):
                if time.time()-self.last_step_time>=self.step_delay/self.speed_multiplier:
                    self.step_forward(); self.last_step_time=time.time()
            self.update_visuals(dt)
            self.draw(self.get_virtual_mouse_pos())
            self.present()
        pygame.quit()


def launch_gui(seed=101, mind='quantum', noise='stub', start_screen='home'):
    IslandVisualizerApp(seed,mind,noise,start_screen).run()
