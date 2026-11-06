"""Pixel-bounded panels, configuration and run review."""
import pygame
from engine.events import VOLCANIC

INK = (36, 53, 57)  # assumption: readable cartographic interface palette
MUTED = (66, 84, 86)  # assumption: secondary text, dark enough on the pale panels
RED = (185, 62, 43)  # assumption: volcanic event emphasis
TEAL = (35, 113, 105)  # assumption: neutral action emphasis
PAPER = (241, 240, 229)  # assumption: warm map-adjacent panel


def wrapped(font, text, width):
    lines, line = [], ''
    for word in str(text).split():
        candidate = (line+' '+word).strip()
        if font.size(candidate)[0] > width and line:
            lines.append(line)
            line = word
        else:
            line = candidate
        while font.size(line)[0] > width:
            cut = len(line)
            while cut>1 and font.size(line[:cut])[0]>width:
                cut -= 1
            lines.append(line[:cut])
            line=line[cut:]
    return lines+[line] if line else lines


def card(app, rect):
    pygame.draw.rect(app.canvas,(252,250,239),rect,border_radius=7)
    pygame.draw.rect(app.canvas,(210,217,204),rect,1,border_radius=7)


def dashboard(app):
    s=app.canvas
    pygame.draw.rect(s,PAPER,(760,0,520,760))
    app.text('QOGNITION',784,18,font=app.font_hero)
    app.text(f'{app.mind_type.capitalize()}-labelled stub  /  Seed {app.seed}',784,56,color=MUTED)
    a=app.agent
    app.text(f'Day {a.day}  {a.hour:02d}:00    Step {app.step_idx} / {app.max_steps}',784,84,font=app.font_sub)
    app.text(f'{app.current_weather.capitalize()}   |   Wind toward {app.wind_deg:.0f} deg',784,108)
    phase=app.engine.volcano.phases[max(0,app.step_idx-1)] if app.step_idx else 'unrest'
    app.text(f'{phase.capitalize()}  |  hidden from the mind',784,132,color=MUTED,font=app.font_small)
    card(app,pygame.Rect(780,163,480,45))
    event=app.current_event.replace('_',' ').capitalize()
    app.text('EVENT',794,175,color=MUTED,font=app.font_small)
    app.text(event,860,172,color=RED if app.current_event in VOLCANIC else INK,font=app.font_sub)
    app.text('PHYSICAL STATE',784,222,color=MUTED,font=app.font_small)
    needs=a.needs
    for i,(key,val) in enumerate(needs.items()):
        row,col=divmod(i,2)
        x,y=784+col*242,246+row*42
        app.text(key.capitalize(),x,y,font=app.font_small)
        app.text(f'{val:.0%}',x+174,y,font=app.font_small)
        pygame.draw.rect(s,(211,218,207),(x,y+22,210,5),border_radius=2)
        pygame.draw.rect(s,TEAL if val>.35 else RED,(x,y+22,round(210*val),5),border_radius=2)
    mood = 'Hungry and depleted' if needs['hunger']<.25 else 'Injured' if a.injured else 'Under strain' if a.stress>.45 else 'Low spirits' if needs['morale']<.4 else 'Holding steady'
    app.text(f'{mood}   |   Stress {a.stress:.0%}',784,377,font=app.font_sub,color=RED if a.stress>.45 else INK)
    app.text(f"Rations {a.inventory['food']}   Wood {a.inventory['wood']}   Tools {a.inventory['tools']}",784,405,color=MUTED)
    app.text('RUN HISTORY  |  2 HOURS PER CELL',784,439,color=MUTED,font=app.font_small)
    width=468/app.max_steps
    for t in range(app.max_steps):
        night=(8+2*t)%24>=20 or (8+2*t)%24<=6
        color=(197,205,199) if night else (220,224,213)
        if t<len(app.history):
            event=app.history[t]['event']
            color=RED if event in VOLCANIC else (106,148,144) if event!='none' else (162,180,162)
        pygame.draw.rect(s,color,(784+int(t*width),465,max(1,int(width)-2),15))
        if night:
            pygame.draw.rect(s,(94,109,116),(784+int(t*width),477,max(1,int(width)-2),3))
    card(app,pygame.Rect(780,497,480,214))
    d=app.current_decision
    app.text('DECISION  /  '+d['action'].replace('_',' ').upper(),794,508,font=app.font_sub)
    top=max(d['probs'],key=d['probs'].get)
    note='Chosen action differs from highest bar (stub override).' if top!=d['action'] and app.step_idx else 'Synthetic heuristic probabilities | no quantum execution'
    app.text(note,794,535,color=MUTED,font=app.font_small)
    for i,(name,value) in enumerate(d['probs'].items()):
        x,y=794+(i%4)*115,560+(i//4)*41
        color=TEAL if name==d['action'] else (137,154,145)
        if name==d['action']:
            pygame.draw.rect(s,(227,237,220),(x-4,y-2,111,37),border_radius=3)
        label=name.replace('build_shelter','build').replace('_',' ')
        app.text(label,x,y,font=app.font_small,color=color)
        pygame.draw.rect(s,(218,223,211),(x,y+20,62,4))
        pygame.draw.rect(s,color,(x,y+20,round(value*62),4))
        app.text(f'{value:.1%}',x+65,y+12,font=app.font_small)
    lines=wrapped(app.font_small,d['reason'],444)
    for i,line in enumerate(lines[:2]):
        if i==1 and len(lines)>2:
            line=app.elide(line,428,app.font_small)+'...'
        app.text(line,794,650+i*21,font=app.font_small,color=MUTED)
    app.text('Space pause  |  N step  |  E zones  |  Tab history  |  Esc menu',784,730,font=app.font_small,color=MUTED)


def home(app):
    app.canvas.fill(PAPER)
    app.text('QOGNITION',72,46,font=app.font_hero)
    app.text('An island. A warning. A decision to leave.',72,95,font=app.font_title)
    app.text('VOLCANO EVACUATION SCENARIO',72,166,font=app.font_small,color=MUTED)
    for i,line in enumerate(('Follow an autonomous survivor through changing weather,',
                             'volcanic unrest and finite supplies. Terrain shapes escape routes.',
                             'Both minds use honest heuristic stubs on the same event seed.')):
        app.text(line,72,195+i*26)
    app.text('DECISION POLICY',72,306,font=app.font_small,color=MUTED)
    app.btn_home_quantum.is_active=app.mind_type=='quantum'
    app.btn_home_classical.is_active=app.mind_type=='classical'
    app.text('EVENT SEED',72,424,font=app.font_small,color=MUTED)
    card(app,pygame.Rect(128,456,160,44))
    app.text(str(app.seed),147,465,font=app.font_sub)
    app.text('DURATION',72,532,font=app.font_small,color=MUTED)
    for steps,btn in app.horizon_buttons.items():
        btn.is_active=app.max_steps==steps
    for button in app.home_buttons:
        button.draw(app.canvas)
    app.canvas.blit(app.preview_mini_map,(808,176))
    app.text('Fixed island | topographic relief',808,505,font=app.font_sub)
    app.text('Red danger / amber caution',808,535,font=app.font_small,color=MUTED)
    app.text('A / B assembly and clean springs',808,559,font=app.font_small,color=MUTED)
    app.text('Dashed lines: walking routes',808,583,font=app.font_small,color=MUTED)
    app.text('Eruption timing is hidden from the mind.',808,623,font=app.font_small,color=MUTED)
    app.text('Enter launch  |  F11 fullscreen',72,717,color=MUTED,font=app.font_small)


def modal_background(app,rect):
    veil=pygame.Surface((1280,760),pygame.SRCALPHA)
    veil.fill((14,33,37,155))
    app.canvas.blit(veil,(0,0))
    card(app,rect)


def debrief(app):
    rect=pygame.Rect(320,105,640,550)
    modal_background(app,rect)
    app.text('Run debrief',348,128,font=app.font_hero)
    app.text(f'{app.step_idx*2} hours observed / {app.max_steps*2} hour horizon',348,174,color=MUTED)
    summary=app.engine.timeline()['evacuation']
    labels=(('First sign','first_sign_step'),('First left danger zone','left_danger_step'),
            ('Reached safety','reached_safe_step'),('Assembly point','reached_assembly_step'),
            ('Eruption onset','onset_step'),('First flow','first_pdc_step'))
    for i,(label,key) in enumerate(labels):
        value=summary[key]
        app.text(label,348,216+i*33)
        observed=value is not None and value<app.step_idx
        detail=f'+{value*2} h  (step {value+1})' if observed else 'Not observed'
        app.text(detail,680,216+i*33,color=MUTED)
    margin=summary['margin_hours']
    app.text('Margin before first flow',348,420,font=app.font_sub)
    app.text(f'{margin:+} hours' if margin is not None else 'Not applicable',680,420,font=app.font_sub)
    outcome=('Died: '+str(app.agent.cause_of_death).replace('_',' ')) if not app.agent.is_alive else 'Alive at the end of this observation'
    app.text(outcome,348,460,font=app.font_sub,color=RED if not app.agent.is_alive else INK)
    app.text(f"Final: hunger {app.agent.needs['hunger']:.0%}, thirst {app.agent.needs['thirst']:.0%}, energy {app.agent.needs['energy']:.0%}",348,491)
    app.text(f"Warmth {app.agent.needs['warmth']:.0%}, safety {app.agent.needs['safety']:.0%}, morale {app.agent.needs['morale']:.0%}",348,512,font=app.font_small)
    app.text(f"Stress {app.agent.stress:.0%} | Injured: {'yes' if app.agent.injured else 'no'} | Rations {app.agent.inventory['food']} | Wood {app.agent.inventory['wood']}",348,533,font=app.font_small)
    app.text('Heuristic stubs; no quantum or hardware results.',348,555,font=app.font_small,color=MUTED)
    for btn in app.modal_buttons:
        btn.draw(app.canvas)


def history(app):
    modal_background(app,pygame.Rect(210,40,860,680))
    app.text('Action history',238,60,font=app.font_hero)
    app.text('Wheel to scroll  |  Esc or Tab to return  |  Hours since start',238,105,color=MUTED)
    old_clip=app.canvas.get_clip()
    app.canvas.set_clip(pygame.Rect(230,144,810,510))
    rows=app.history[app.history_scroll:app.history_scroll+7]
    for i,row in enumerate(rows):
        y=148+i*74
        pygame.draw.line(app.canvas,(214,221,207),(238,y+68),(1038,y+68))
        event=row['event'].replace('_',' ')
        app.text(f"+{(row['t']-1)*2:02d} h   {event}",238,y,color=RED if row['event'] in VOLCANIC else INK,font=app.font_sub)
        app.text(row['action'].replace('_',' '),520,y,font=app.font_sub)
        lines=wrapped(app.font_small,row['decision']['reason'],774)
        for j,line in enumerate(lines[:2]):
            if j==1 and len(lines)>2:
                line=app.elide(line,745,app.font_small)+'...'
            app.text(app.elide(line,770,app.font_small),238,y+25+j*17,color=MUTED,font=app.font_small)
    app.canvas.set_clip(old_clip)
    app.text(f'{app.history_scroll+1 if app.history else 0} - {min(len(app.history),app.history_scroll+7)} of {len(app.history)} steps',238,680,color=MUTED,font=app.font_small)
    app.btn_hist_close.draw(app.canvas)
