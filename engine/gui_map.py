"""Cached relief cartography and transient hazard layers."""
import math
from functools import lru_cache
import numpy as np
import pygame

MAP_SIZE = 760  # assumption: virtual map canvas
TILE_SIZE = 19  # assumption: 760 px / 40 tiles
ZONE_COLORS = ((76, 151, 142), (230, 164, 52), (194, 64, 57))  # assumption: map semantics
COLUMN_PUFFS = 14  # assumption: enough puffs to read as a plume at this map scale
PULSE_FADE_SECONDS = 1.6  # assumption: a pulse settles into a deposit within one normal replay step


def point(p):
    return round((p[0]+.5)*TILE_SIZE), round((p[1]+.5)*TILE_SIZE)


@lru_cache(maxsize=8)  # assumption: small process-wide relief cache
def baked_terrain(seed, field, tiles):
    return _bake(np.asarray(field), np.asarray(tiles), seed)



def _bake(elevation, tiles, seed):
    n = MAP_SIZE
    axis = np.linspace(0, 39, n)
    xp, yp = np.meshgrid(axis, axis)
    ix, iy = np.minimum(xp.astype(int),38), np.minimum(yp.astype(int),38)
    fx, fy = xp-ix, yp-iy
    h = ((1-fx)*(1-fy)*elevation[iy,ix]+fx*(1-fy)*elevation[iy,ix+1]+
         (1-fx)*fy*elevation[iy+1,ix]+fx*fy*elevation[iy+1,ix+1])
    offsets = np.arange(-24,25)
    kernel = np.exp(-.5*(offsets/8)**2)  # assumption: eight-pixel relief smoothing
    kernel /= kernel.sum()
    for axis_index in (0,1):
        h = np.apply_along_axis(lambda row: np.convolve(np.pad(row,(24,24),mode='edge'),kernel,mode='valid'),axis_index,h)
    heights = [-100,0,35,150,400,750,1050]  # assumption: hypsometric stops in metres
    palette = np.array([(34,75,92),(112,165,161),(212,207,160),(151,177,112),
                        (100,139,100),(151,142,116),(208,198,177)])  # assumption: tropical map palette
    rgb = np.stack([np.interp(h,heights,palette[:,i]) for i in range(3)],axis=2)
    gy, gx = np.gradient(h)
    shade = np.clip(.91+(-gx+gy)*.035,.65,1.15)  # assumption: northwest illumination
    rgb *= shade[:,:,None]
    forest = (h>100)&(h<750)
    texture = np.random.default_rng(seed).normal(0,1.4,(n,n))  # assumption: fine canopy grain
    rgb += texture[:,:,None]*forest[:,:,None]
    contours = (np.mod(h,100)<1.8)&(h>20)  # assumption: 100 m contours
    rgb[contours] *= .83
    coast = abs(h)<2.5  # assumption: softened shoreline
    rgb[coast] = rgb[coast]*.6+np.array([215,222,191])*.4
    return pygame.surfarray.make_surface(np.clip(rgb,0,255).astype('uint8').swapaxes(0,1))


def soft_mask(world, cells, color, alpha):
    small = pygame.Surface((world.width,world.height),pygame.SRCALPHA)
    for x,y in cells:
        small.set_at((x,y),(*color,alpha))
    return pygame.transform.smoothscale(small,(MAP_SIZE,MAP_SIZE))


def soft_puff(color, size):
    """A round sprite whose alpha falls smoothly to zero at its edge."""
    surface = pygame.Surface((size,size),pygame.SRCALPHA)
    surface.fill((*color,0))
    axis = (np.arange(size)+.5)/size*2-1
    radius = np.hypot(*np.meshgrid(axis,axis))
    alpha = pygame.surfarray.pixels_alpha(surface)
    alpha[:] = (255*np.clip(1-radius,0,1)**1.4).astype('uint8')
    del alpha
    return surface


def flow_mottle(seed):
    """Patchy multiply texture, so a flow reads as billowing cloud rather than a flat shape."""
    grain = np.random.default_rng(seed).integers(190,256,(30,30))
    small = pygame.Surface((30,30),pygame.SRCALPHA)
    for (x,y),value in np.ndenumerate(grain):
        small.set_at((x,y),(int(value),int(value),int(value),int(value)))
    return pygame.transform.smoothscale(small,(MAP_SIZE,MAP_SIZE))


class MapRenderer:
    def __init__(self, world):
        self.terrain = baked_terrain(world.seed,tuple(map(tuple,world.elevation)),tuple(map(tuple,world.tiles)))
        self.zones = pygame.Surface((MAP_SIZE,MAP_SIZE),pygame.SRCALPHA)
        self.zone_lines = pygame.Surface((MAP_SIZE,MAP_SIZE),pygame.SRCALPHA)
        for z in (1,2):
            cells = [(x,y) for y in range(40) for x in range(40) if world.get_tile(x,y) and world.zones[y][x]==z]
            layer = soft_mask(world,cells,ZONE_COLORS[z],22)
            self.zones.blit(layer,(0,0))
            boundary = pygame.mask.from_surface(soft_mask(world,cells,ZONE_COLORS[z],255),127).outline(8)
            if len(boundary)>2:
                pygame.draw.lines(self.zone_lines,(*ZONE_COLORS[z],230),True,boundary,2)
        self.hazard_key = None
        self.layers = []
        self.night = pygame.Surface((MAP_SIZE,MAP_SIZE),pygame.SRCALPHA)
        self.furniture = pygame.Surface((MAP_SIZE,MAP_SIZE),pygame.SRCALPHA)
        self.mottle = flow_mottle(world.seed)
        self.billow = soft_puff((232,226,212),26)
        # assumption: column of puffs widening with height, from 30 px up.
        self.column_puffs = [soft_puff((98,92,88),30+i*8) for i in range(COLUMN_PUFFS)]
        self.pulse = None
        self.pulse_born = 0.

    def refresh(self, app):
        world = app.world
        self.flow_front = [p for p in sorted(world.active_pdc)
                           if any(q not in world.active_pdc for q in world.neighbors(p))][::4]
        self.background_key = None
        self.pulse = None
        if world.active_pdc:
            self.pulse = soft_mask(world,world.active_pdc,(226,220,206),255)
            self.pulse.blit(self.mottle,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
            self.pulse_born = app.visual_time
        self.layers = [soft_mask(world,world.pdc,(110,96,82),150),
                       soft_mask(world,world.active_lahar,(66,49,31),235),
                       soft_mask(world,world.surge,(192,175,152),105)]
        self.lava_glow = soft_mask(world,world.lava,(255,80,12),150)
        self.lava_core = soft_mask(world,world.lava,(255,185,45),255)
        ash = pygame.Surface((40,40),pygame.SRCALPHA)
        for y in range(40):
            for x in range(40):
                amount = world.ash_at(x,y)
                ash.set_at((x,y),(126,119,112,round(amount*65)))  # assumption: translucent local deposition
        self.layers.append(pygame.transform.smoothscale(ash,(MAP_SIZE,MAP_SIZE)))

    def _draw_background(self, app):
        surface, world = app.canvas, app.world
        surface.blit(self.terrain,(0,0))
        for valley in world.valleys[:1]:
            pygame.draw.aalines(surface,(94,179,189),False,[point(p) for p in valley[1:]])
        for p in world.food_tiles:
            if p not in world.depleted_food:
                pygame.draw.circle(surface,(193,199,117),point(p),1)
        if app.show_evacuation_map:
            surface.blit(self.zones,(0,0))
            for route in world.routes_from_spawn:
                for i,(a,b) in enumerate(zip(route,route[1:])):
                    if i%2==0:
                        pygame.draw.line(surface,(243,232,194),point(a),point(b),2)
                    if i%5==2:
                        ax,ay = point(a); bx,by = point(b)
                        vx,vy = (bx-ax)/19,(by-ay)/19
                        pygame.draw.polygon(surface,(251,241,202),[(bx,by),(bx-vx*7-vy*3,by-vy*7+vx*3),(bx-vx*7+vy*3,by-vy*7-vx*3)])
        for layer in self.layers:
            surface.blit(layer,(0,0))
        if app.show_evacuation_map:
            surface.blit(self.zone_lines,(0,0))
        for p in world.shelter_tiles:
            x,y = point(p)
            pygame.draw.polygon(surface,(224,209,170),[(x-7,y+5),(x,y-6),(x+7,y+5)])
            pygame.draw.circle(surface,(255,157,59),(x+7,y+4),3)
        for i,p in enumerate(world.assembly_points):
            x,y = point(p)
            pygame.draw.circle(surface,(248,240,214),(x,y),11)
            pygame.draw.circle(surface,(33,100,93),(x,y),11,2)
            app.text(chr(65+i),x-5,y-9,color=(22,66,61),font=app.font_sub)
        vx,vy = point(world.vent)
        pygame.draw.polygon(surface,(78,50,40),[(vx-8,vy+5),(vx,vy-9),(vx+8,vy+5)])
    def draw(self, app):
        surface, world = app.canvas, app.world
        key = app.show_evacuation_map
        if self.background_key != key:
            self._draw_background(app)
            self.background = app.canvas.subsurface((0,0,760,760)).copy().convert()
            self.background_key = key
        surface.blit(self.background,(0,0))
        hour = (app.agent.hour-app.lighting_lag) % 24
        daylight = max(0.,min(1.,(hour-5)/3,(19-hour)/3))  # assumption: tropical dawn/dusk
        self.night.fill((12,23,48,round(125*(1-daylight))))
        surface.blit(self.night,(0,0))
        for p in world.shelter_tiles:
            x,y=point(p)
            pygame.draw.circle(surface,(255,157,59),(x+7,y+4),3)
        # assumption: low-amplitude ocean ripples, only offshore.
        for i in range(8):
            x, y = 25+i*87, 696+int(5*math.sin(app.visual_time*.4+i))
            if not world.get_tile(x//19,y//19):
                pygame.draw.line(surface,(70,116,128),(x,y),(x+27,y),1)
        if self.pulse:
            age = max(0.,app.visual_time-self.pulse_born)
            strength = max(0.,1-age/PULSE_FADE_SECONDS)
            self.pulse.set_alpha(round(95+160*strength))
            surface.blit(self.pulse,(0,0))
            if strength:
                # Billows live at the moving front, and vanish as the pulse settles.
                self.billow.set_alpha(round(200*strength))
                for i,p in enumerate(self.flow_front):
                    x,y=point(p)
                    x+=round(3*math.sin(app.visual_time*3+i))
                    y+=round(3*math.cos(app.visual_time*2.3+i))
                    surface.blit(self.billow,(x-13,y-13))
        vx,vy = point(world.vent)
        t = max(0,app.step_idx-1)
        if app.engine.volcano.phases[t]=='erupting' and app.step_idx:
            angle = math.radians(app.wind_deg)
            wx,wy = math.sin(angle),-math.cos(angle)
            # The plume rises, bends downwind, widens and thins. Drawn far end first.
            for i in reversed(range(COLUMN_PUFFS)):
                share = i/(COLUMN_PUFFS-1)
                drift = 150*share*share
                puff = self.column_puffs[i]
                size = puff.get_width()
                x = vx+wx*drift+2*math.sin(app.visual_time*.8+i)
                y = vy-105*share**.7+wy*drift*.6+2*math.cos(app.visual_time*.6+i)
                puff.set_alpha(round(215*(1-share)**.6+30))
                surface.blit(puff,(round(x-size/2),round(y-size/2)))
        # Glowing lava shows through night, flow dust and plume alike.
        surface.blit(self.lava_glow,(0,0))
        surface.blit(self.lava_core,(0,0))
        self.draw_weather(app)
        x,y = round(app.char_screen_x),round(app.char_screen_y)
        pygame.draw.circle(surface,(33,40,41),(x,y),7)
        pygame.draw.circle(surface,(255,241,197),(x,y),5)
        pygame.draw.circle(surface,(56,62,64),(x,y),7,2)
        if app.bubble_timer>0:
            label = app.font_body.render(app.bubble_text,True,(36,48,50))
            rect = label.get_rect(midbottom=(x,y-14)).inflate(16,10)
            rect.clamp_ip(pygame.Rect(8,52,744,650))
            pygame.draw.rect(surface,(252,246,224),rect,border_radius=5)
            surface.blit(label,(rect.x+8,rect.y+5))
        self.map_furniture(app)

    def draw_weather(self, app):
        if app.current_weather in ('rain','storm'):
            color = (135,178,189) if app.current_weather=='rain' else (169,192,202)
            for i in range(70 if app.current_weather=='rain' else 130):
                x=(i*113+app.visual_time*35)%760
                y=(i*73+app.visual_time*270)%760
                pygame.draw.line(app.canvas,color,(x,y),(x-3,y+9))
        if app.world.ash>.1:
            angle=math.radians(app.wind_deg)
            for i in range(45):
                x=(i*97+app.visual_time*18*math.sin(angle))%760
                y=(i*137+app.visual_time*(12-10*math.cos(angle)))%760
                if app.world.ash_at(int(x//19),int(y//19))>.15:
                    pygame.draw.circle(app.canvas,(194,185,169),(int(x),int(y)),1)

    def map_furniture(self, app):
        s=app.canvas
        ink = (235,236,217)
        pygame.draw.rect(s,(24,49,54),(16,600,282,144),border_radius=6)
        app.text('EVACUATION MAP   [E]',28,607,color=ink,font=app.font_sub)
        for i,(label,color) in enumerate(zip(('Safe','Caution','Danger'),ZONE_COLORS)):
            pygame.draw.line(s,color,(28+i*86,640),(40+i*86,640),3)
            app.text(label,44+i*86,631,color=ink,font=app.font_small)
        hazards = (('Lava',(255,150,30)),('Active flow',(226,220,206)),('Deposit',(122,106,90)),
                   ('Lahar',(92,68,44)),('Ash',(150,143,135)))
        for i,(label,color) in enumerate(hazards):
            row,col = divmod(i,3)
            x,y = 28+col*86,658+row*21
            pygame.draw.rect(s,color,(x,y+3,12,12),border_radius=2)
            app.text(label,x+16,y,color=ink,font=app.font_small)
        app.text('A, B  Assembly points, with a clean spring',28,700,color=(218,226,215),font=app.font_small)
        pygame.draw.line(s,(239,237,214),(28,731),(104,731),3)
        app.text('1 km',115,721,color=(239,237,214),font=app.font_small)
        pygame.draw.polygon(s,(244,238,210),[(721,66),(716,85),(726,85)])
        app.text('N',716,44,color=(244,238,210),font=app.font_sub)
        if app.step_idx and app.engine.volcano.phases[app.step_idx-1]=='erupting':
            a=math.radians(app.wind_deg); x,y=721,125
            end=(x+math.sin(a)*20,y-math.cos(a)*20)
            pygame.draw.line(s,(241,215,159),(x,y),end,3)
            pygame.draw.circle(s,(241,215,159),end,4)
            app.text('Wind',702,151,color=(241,215,159),font=app.font_small)

    def tooltip(self, app, mouse):
        x,y=mouse[0]//19,mouse[1]//19
        if not (0<=x<40 and 0<=y<40) or mouse[1]<45:
            return
        w=app.world
        hazards=[name for name,cells in [('Lava',w.lava),('Active flow',w.active_pdc),('Surge',w.surge),
                  ('Active lahar',w.active_lahar),('Hot deposit',w.pdc-w.active_pdc)] if (x,y) in cells]
        lines=[f"{('Safe','Caution','Danger')[w.zones[y][x]]} zone | {round(w.elevation[y][x])} m",
               ('Ocean','Plains','Forest','Mountain','Shelter')[w.get_tile(x,y)], ', '.join(hazards) or 'No active flow']
        rect=pygame.Rect(mouse[0]+12,mouse[1]+12,250,76)
        rect.clamp_ip(pygame.Rect(8,50,744,696))
        pygame.draw.rect(app.canvas,(249,244,226),rect,border_radius=5)
        for i,line in enumerate(lines):
            app.text(line,rect.x+10,rect.y+7+i*21,font=app.font_small)
