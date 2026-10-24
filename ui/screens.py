"""Walk-up-friendly console-style navigation, six-game gallery and match screens."""
import math
import pygame
from games import GAME_CARDS,MODES,SURVIVAL_RULES
from match import ranking_key
from avatar import demonstration_pose
from tracking_types import neutral_pose
from ui.art import gradient
from ui.components import Button,GameCard,ModeCard
from ui.worlds import Worlds,playfields,hand_area
from ui.theme import *


class Screens:
    def __init__(self,app):
        self.a=app
        self.worlds=Worlds(app)
        self.preview_key=None
        self.preview_image=None
        self.cards=[GameCard(card,(40+(i%3)*462,222+(i//3)*294,436,270),app.art) for i,card in enumerate(GAME_CARDS)]
        self.modes=[ModeCard("mode_"+key,(40+(i%2)*692,270+(i//2)*209,668,179),title,description,[1,0,2,3][i],[CYAN,PURPLE,ORANGE,GREEN][i]) for i,(key,(title,description)) in enumerate(MODES.items())]
        self.veil=pygame.Surface((W,H),pygame.SRCALPHA)
        for x in range(W):
            alpha=round(235-175*(x/W)**1.25)
            pygame.draw.line(self.veil,(5,17,31,alpha),(x,0),(x,H))

    def b(self,key,rect,label,subtitle="",color=CYAN,enabled=True,primary=False):
        return Button(key,pygame.Rect(rect),label,subtitle,color,enabled,primary)

    def buttons(self):
        a=self.a
        b=self.b
        scene=a.scene
        common=[b("input_toggle",(1220,24,180,43),"USE HAND" if a.input_mode!="hand" else "USE MOUSE",color=CYAN)]
        if scene not in ("welcome","handoff","menu","connected"):
            common.append(b("back",(40,107,139,47),"PAUSE" if scene=="game" else "BACK",color=MUTED))
        if scene in ("welcome","handoff"):
            return [b("join_demo",(60,725,420,76),"JOIN / ENTER" if a.demo else "TRY KEYBOARD DEMO",color=ORANGE,primary=True),b("exit",(501,725,185,76),"EXIT",color=MUTED)]+common
        if scene=="menu":
            return [b("play",(60,484,550,88),"LET'S PLAY","Choose from six motion challenges",ORANGE,primary=True),
                    b("how",(60,591,264,70),"HOW TO PLAY"),b("settings",(346,591,264,70),"SETTINGS"),
                    b("exit",(60,680,264,58),"EXIT",color=MUTED)]+common
        if scene=="select":
            return self.cards+common
        if scene=="mode":
            return self.modes+common
        if scene=="briefing":
            result=[b("start",(760,743,640,73),"START THE CHALLENGE",color=ORANGE,primary=True)]
            result+=[b("variant_endless",(64,600,305,62),"ENDLESS SURVIVAL",color=ORANGE,primary=a.config.endless),
                     b("variant_challenge",(385,600,305,62),"TIMED CHALLENGE",color=CYAN,primary=not a.config.endless)]
            if a.session_mode=="party" and a.party_results:
                for button in result[1:]:
                    button.enabled=False
            if a.session_mode=="ai":
                result+=[b("difficulty_"+key,(760+i*217,649,206,54),key.upper(),color=PURPLE,primary=a.config.ai_difficulty==key) for i,key in enumerate(("easy","normal","hard"))]
            elif a.session_mode=="party":
                result+=[b("party_less",(762,649,160,54),"- PLAYER"),b("party_more",(1240,649,160,54),"+ PLAYER")]
            return result+common
        if scene=="lobby":
            return ([b("join_demo",(535,772,370,50),"JOIN BOTH / ENTER",color=ORANGE,primary=True)] if a.demo else [])+common
        if scene=="how":
            return [b("play",(760,742,640,74),"I'M READY / CHOOSE A GAME",color=ORANGE,primary=True)]+common
        if scene=="settings":
            return [b("less",(74,347,240,63),"- LOWER"),b("more",(338,347,240,63),"+ HIGHER"),
                    b("sound",(74,456,504,68),"SOUND: "+("ON" if a.config.sound else "OFF")),
                    b("preview",(74,547,504,68),"CAMERA PREVIEW: "+("ON" if a.config.show_preview else "OFF")),
                    b("calibrate",(796,624,560,69),"RECALIBRATE PLAYER",color=PURPLE),
                    b("menu",(74,741,504,74),"DONE",color=ORANGE,primary=True),
                    b("camera_mode",(796,741,560,74),"USE WEBCAM" if a.demo else "USE KEYBOARD DEMO",color=CYAN)]+common
        if scene=="game" and a.match and a.match.paused:
            valid=all(a.bank.players[i].valid and a.bank.players[i].registered or a.match.games[i].finished for i in range(a.match.human_count))
            return [b("resume",(480,472,480,67),"RESUME",color=ORANGE,enabled=valid,primary=True),
                    b("rejoin",(480,555,480,62),"RECONNECT / KEEP THIS RUN",color=PURPLE),
                    b("end_run",(480,633,480,62),"BANK SCORE / RESULTS",color=CYAN)]+common
        if scene=="results":
            next_turn=a.session_mode=="party" and a.party_index+1<a.party_count
            return [b("next_player" if next_turn else "again",(40,737,420,77),f"PLAYER {a.party_index+2} / NEXT" if next_turn else "REMATCH",color=ORANGE,primary=True),
                    b("all_games",(486,737,420,77),"ALL SIX GAMES"),b("menu",(932,737,468,77),"HOME")]+common
        return common

    def hand_area(self,slot=0):
        count=len(self.a.match.games) if self.a.match else 1
        return hand_area(playfields(count)[slot])

    def draw(self,now):
        a=self.a
        s=a.canvas
        s.blit(a.art.image("stadium",W,H),(0,0))
        if a.scene in ("welcome","menu","handoff","connected"):
            s.blit(self.veil,(0,0))
        else:
            s.blit(gradient(W,H,215,246),(0,0))
        # Fine airborne time particles keep every page alive without visual noise.
        for i in range(24):
            x=(i*167+now*(5+i%4))%W
            y=(i*131-now*(3+i%3))%H
            pygame.draw.circle(s,(132,146,135),(round(x),round(y)),1)
        getattr(self,"draw_"+a.scene)(now)
        self.header(now)
        self.footer()
    def reconnect_overlay(self,now):
        a=self.a
        s=a.canvas
        shade=pygame.Surface((W,H),pygame.SRCALPHA)
        shade.fill((4,16,29,210))
        s.blit(shade,(0,0))
        panel(s,(345,280,750,324),(16,36,53),CYAN,24)
        player=a.bank.players[0]
        title="RAISE A HAND TO RECONNECT" if player.neutral is not None else "STEP BACK INTO THE ARENA"
        text(s,title,(720,325),31,CYAN,True,True)
        wrapped(s,player.message,(394,385),650,23,WHITE)
        wrapped(s,"Stand still with arms down, then hold a hand above your head. Your menu is saved.",(394,461),650,20,MUTED)
        progress=player.join_progress if player.neutral is not None else player.calibration_progress
        ring(s,(720,556),22,progress,CYAN,4)

    def header(self,now):
        a=self.a
        s=a.canvas
        # Solid header makes input mode and back navigation readable over every world.
        pygame.draw.rect(s,(9,24,39),(0,0,W,83))
        clock_icon(s,(62,44),19,ORANGE,now*.2)
        text(s,"CHRONO",(94,25),31,WHITE,True)
        text(s,"ARENA",(261,25),31,CYAN,True)
        text(s,"OXHACK / TIME IN MOTION",(415,36),14,MUTED,mono=True)
        if a.menu_controller==1:
            text(s,"P2 MENU CONTROL",(774,36),12,ORANGE,mono=True)
        live=a.source_frame.frame is not None and now-a.source_frame.timestamp<a.config.tracking_stale_seconds
        status="KEYBOARD DEMO" if a.demo else "WEBCAM LIVE" if live else "CAMERA CONNECTING" if a.camera and a.camera.thread.is_alive() else "CAMERA NEEDED"
        pill(s,status,(978,29),GREEN if live and not a.demo else ORANGE,12)
        pygame.draw.line(s,(55,76,90),(40,83),(1400,83))

    def footer(self):
        a=self.a
        s=a.canvas
        pygame.draw.rect(s,(8,22,36),(0,845,W,55))
        pygame.draw.line(s,EDGE,(40,845),(1400,845))
        if a.scene in ("welcome","handoff") and a.demo:
            hint="H: HOLD TO RAISE YOUR HAND   /   ENTER: JOIN QUICKLY   /   F2: RESTART DEMO"
        elif a.scene=="lobby" and a.demo:
            hint="PLAYER 1: HOLD H   /   PLAYER 2: HOLD T   /   ENTER: JOIN BOTH QUICKLY"
        elif a.scene=="game" and a.demo and a.selected_game=="lightning":
            hint="P1: MOVE MOUSE TO AIM YOUR HAND   /   P2: W A S D TO AIM   /   REACH THE GLOWING ORB"
        elif a.scene=="game" and a.demo:
            hint={"red_green":"P1: HOLD SPACE TO JOG / RELEASE TO FREEZE   |   P2: HOLD SHIFT / RELEASE TO FREEZE",
                  "sprint":"P1: HOLD SPACE TO JOG   |   P2: HOLD SHIFT TO JOG   |   KEEP GOING THROUGH TIME WARP",
                  "dodge":"P1: LEFT / RIGHT ARROWS TO LEAN, C TO DUCK   |   P2: A / D TO LEAN, S TO DUCK",
                  "timekeeper":"P1: TAP H WHEN RINGS MEET   |   P2: TAP T   |   RELEASE BETWEEN BEATS",
                  "echo":"P1: ARROWS LEAN / C DUCK / U HANDS UP   |   P2: A D / S / W   |   WATCH, THEN REPEAT"}.get(a.selected_game,"")
        elif a.scene=="game":
            hint=a.card["control"]+"  /  FOLLOW THE LARGE MOVEMENT PROMPT"
        else:
            hint="HAND: HOVER + HOLD 1s   /   MOUSE: CLICK   /   ARROWS + ENTER"
        fit_text(s,hint,(40,866),1055,15,MUTED,mono=True)
        text(s,"ESC BACK   F1 STATS   F11 FULL",(1092,868),13,MUTED,mono=True)

    def title(self,title,subtitle="",color=WHITE):
        s=self.a.canvas
        fit_text(s,title,(207,107),1180,45,color,True)
        if subtitle:
            fit_text(s,subtitle,(208,164),1140,21,MUTED)

    def preview(self,rect,now):
        a=self.a
        s=a.canvas
        rect=pygame.Rect(rect)
        panel(s,rect,(7,22,35),EDGE,16)
        frame=a.source_frame
        if a.config.show_preview and frame.frame is not None:
            key=(frame.timestamp,rect.size)
            if self.preview_key!=key:
                rgb=frame.frame
                source=pygame.image.frombuffer(rgb.tobytes(),(rgb.shape[1],rgb.shape[0]),"RGB")
                ratio=min((rect.width-8)/source.get_width(),(rect.height-8)/source.get_height())
                self.preview_image=pygame.transform.smoothscale(source,(round(source.get_width()*ratio),round(source.get_height()*ratio)))
                self.preview_key=key
            s.blit(self.preview_image,self.preview_image.get_rect(center=rect.center))
            if a.dual_active:
                pygame.draw.line(s,ORANGE,(rect.centerx,rect.top+8),(rect.centerx,rect.bottom-8),2)
            pill(s,"YOU / MIRRORED",(rect.x+9,rect.y+8),CYAN,10)
        else:
            clock_icon(s,(rect.centerx,rect.centery-15),22,CYAN,now*.4)
            text(s,"SIMULATED BODY" if a.demo else "PREVIEW OFF" if not a.config.show_preview else "WAITING FOR CAMERA",(rect.centerx,rect.centery+28),14,MUTED,center=True,mono=True)

    def hero_avatar(self,now,cx=1014,top=241,height=375):
        a=self.a
        s=a.canvas
        floor=pygame.Rect(cx-200,top+height,400,65)
        pygame.draw.ellipse(s,(12,47,60),floor)
        pygame.draw.ellipse(s,(75,194,194),floor,3)
        pygame.draw.ellipse(s,(182,234,215),floor.inflate(-33,-12),1)
        p=a.player.smoothed if a.player.valid else None
        a.avatar.draw(s,p,cx,top,height,a.frame.aspect,now,neutral=a.player.neutral if a.player.valid else None)

    def draw_welcome(self,now):
        self.join_page(now,False)

    def draw_handoff(self,now):
        self.join_page(now,True)

    def join_page(self,now,handoff):
        a=self.a
        s=a.canvas
        pill(s,"THE TIME-TRAVEL SPORTS CLUB" if not handoff else f"PARTY / TURN {a.party_index+1} OF {a.party_count}",(60,128),ORANGE,14)
        if handoff:
            text(s,f"PLAYER {a.party_index+1}",(57,205),86,WHITE,True)
            text(s,"YOU'RE UP.",(57,294),86,CYAN,True)
        else:
            text(s,"WELCOME TO",(64,208),26,MUTED)
            text(s,"CHRONO",(55,244),97,WHITE,True)
            text(s,"ARENA",(55,337),97,CYAN,True)
        wrapped(s,"Step back until your body is visible." if not handoff else "Your turn. Everyone else, step out of the camera.",(64,458),635,25,WHITE)
        panel(s,(60,530,646,154),(13,34,51),(68,101,119),22)
        player=a.player
        progress=player.join_progress if player.neutral is not None else player.calibration_progress
        ring(s,(115,604),31,progress,CYAN,5)
        text(s,"02" if player.neutral is not None else "01",(115,604),18,CYAN,True,True,True)
        title="RAISE A HAND TO JOIN" if player.neutral is not None else "STAND STILL / ARMS DOWN"
        text(s,title,(170,554),25,WHITE,True)
        message="Hold H for 1.2 seconds, or press Enter." if a.demo and player.neutral is not None else "Calibrating your neutral stance..." if a.demo else player.message
        wrapped(s,message,(171,601),500,18,MUTED)
        self.hero_avatar(now,1000,229,357)
        self.preview((1080,625,300,179),now)
        pill(s,"YOUR BODY. YOUR CONTROLLER.",(842,638),CYAN,12)
        if not a.demo and not player.valid:
            message=a.camera.status if a.camera and a.camera.status!="Camera ready" else a.source_frame.status
            fit_text(s,message,(62,813),1330,16,ORANGE)

    def draw_connected(self,now):
        self.hero_avatar(now,1000,233,364)
        pill(self.a.canvas,"CONNECTED",(60,204),GREEN,16)
        text(self.a.canvas,"YOU'RE IN.",(54,265),104,WHITE,True)
        text(self.a.canvas,"Your next second starts here.",(64,394),29,MUTED)
        ring(self.a.canvas,(350,553),54,min(1.,now-self.a.scene_started),GREEN,5)
        text(self.a.canvas,"READY",(350,553),19,GREEN,True,True)

    def draw_menu(self,now):
        a=self.a
        s=a.canvas
        pill(s,"6 GAMES. ONE RACE AGAINST TIME.",(60,129),CYAN,14)
        text(s,"OWN THE",(53,194),91,WHITE,True)
        text(s,"NEXT SECOND.",(53,289),86,WHITE,True)
        text(s,"Move your body. Challenge your timing.",(63,405),26,MUTED)
        self.hero_avatar(now,1038,224,395)
        pill(s,"LIVE MOTION AVATAR",(921,686),CYAN,14)
        for i,(number,title,detail) in enumerate([("01","CHOOSE","Six games, four ways to play"),("02","MOVE","Hands, knees and perfect stillness"),("03","REPEAT","Chase your next personal best")]):
            x=60+i*455
            panel(s,(x,762,432,61),(12,31,46),EDGE,15)
            text(s,number,(x+17,778),21,ORANGE,True,mono=True)
            text(s,title,(x+64,770),17,WHITE,True)
            text(s,detail,(x+64,797),13,MUTED)

    def draw_select(self,now):
        self.title("CHOOSE YOUR CHALLENGE","Six ways to play with time. Pick any card to begin.")

    def draw_mode(self,now):
        a=self.a
        self.title("WHO'S TAKING THE CHALLENGE?",a.card["title"]+"  /  "+a.card["control"])
        wrapped(a.canvas,"Side-by-side needs two full bodies in view. Party mode gives everyone a turn at the same challenge.",(65,733),1290,23,MUTED)
        pill(a.canvas,"ALL SIX GAMES SUPPORT EVERY MODE",(65,791),GREEN,13)

    def draw_briefing(self,now):
        a=self.a
        s=a.canvas
        self.title(a.card["title"],MODES[a.session_mode][0]+"  /  "+a.current_name+"  /  "+a.card["theme"])
        art=a.art.image(a.card["art"],674,605)
        s.blit(art,(40,211))
        s.blit(gradient(674,605,0,230),(40,211))
        pygame.draw.rect(s,EDGE,(40,211,674,605),1,border_radius=20)
        pill(s,a.card["tag"],(62,234),a.card["color"],14)
        wrapped(s,a.card["control"],(66,695),610,36,WHITE,bold=True)
        text(s,"THREE THINGS TO KNOW",(760,223),24,a.card["color"],True)
        for i,rule in enumerate(SURVIVAL_RULES[a.selected_game] if a.config.endless else a.card["rules"]):
            y=273+i*113
            panel(s,(760,y,640,96),(17,36,53),EDGE,17)
            ring(s,(796,y+45),20,1.,a.card["color"],2)
            text(s,str(i+1),(796,y+45),17,a.card["color"],True,True)
            wrapped(s,rule,(832,y+19),540,21,WHITE)
        if a.session_mode=="ai":
            text(s,"NOVA'S DIFFICULTY",(764,616),15,MUTED,mono=True)
        elif a.session_mode=="party":
            text(s,"HOW MANY PLAYERS?",(764,616),15,MUTED,mono=True)
            text(s,str(a.party_count)+" PLAYERS",(1080,677),24,ORANGE,True,True)
        elif a.session_mode=="duo":
            pill(s,"BOTH PLAYERS CONNECTED",(760,650),GREEN,15)
        else:
            text(s,"Take your time. Start when you're ready.",(763,657),22,MUTED)

    def draw_lobby(self,now):
        a=self.a
        s=a.canvas
        self.title("TWO PLAYERS. ONE MOMENT.","Stand side by side. Player 1 stays LEFT in the mirrored preview; Player 2 stays RIGHT.")
        for i,player in enumerate(a.bank.players):
            x=40+i*692
            color=CYAN if i==0 else ORANGE
            panel(s,(x,218,668,529),(13,32,48),color,23)
            pill(s,f"PLAYER {i+1} / "+("LEFT LANE" if i==0 else "RIGHT LANE"),(x+24,241),color,14)
            a.avatar.draw(s,player.smoothed if player.valid else None,x+334,306,269,
                          a.bank.frames[i].aspect if len(a.bank.frames)>i else 4/3,now,i>0,
                          player.neutral if player.valid else None,color)
            progress=player.join_progress if player.neutral is not None else player.calibration_progress
            ready=player.registered and player.valid
            text(s,"READY!" if ready else "RAISE A HAND" if player.neutral is not None else "STAND STILL / ARMS DOWN",(x+334,648),25,GREEN if ready else color,True,True)
            ring(s,(x+334,704),21,1. if ready else progress,color,4)
        self.preview((581,437,278,183),now)
        if not a.demo:
            text(s,"Keep your arms inside your half. The game opens when both players have joined.",(720,790),21,MUTED,center=True)

    def draw_how(self,now):
        a=self.a
        s=a.canvas
        self.title("WALK UP. STEP IN. PLAY.","No controller. No complicated setup. Just you and the clock.")
        panel(s,(40,220,674,596),(13,33,49),EDGE,22)
        pose=["IDLE","LEFT HAND","LEFT","DUCK","RUN"][int(now/2)%5]
        a.avatar.draw(s,demonstration_pose(pose,now),377,273,351,now=now,neutral=neutral_pose())
        pill(s,"YOUR AVATAR COPIES YOUR MOVEMENT",(183,698),CYAN,14)
        steps=[("01","GET IN VIEW","Keep your head, hands and feet visible. Stand still with arms down."),
               ("02","RAISE TO JOIN","Raise either hand above your head for 1.2 seconds."),
               ("03","POINT TO CHOOSE","Aim with a hand. Hold one second; move away to select again."),
               ("04","FOLLOW THE PROMPT","Each game gives three rules first, then large movement instructions.")]
        for i,(num,title,detail) in enumerate(steps):
            y=221+i*119
            panel(s,(760,y,640,102),(17,36,53),EDGE,16)
            text(s,num,(781,y+20),24,ORANGE,True,mono=True)
            text(s,title,(843,y+14),24,WHITE,True)
            wrapped(s,detail,(844,y+50),529,18,MUTED)

    def draw_settings(self,now):
        a=self.a
        s=a.canvas
        self.title("FIND YOUR RHYTHM","Simple settings for a comfortable motion session.")
        panel(s,(40,220,572,450))
        text(s,"MOVEMENT SENSITIVITY",(75,252),18,MUTED,mono=True)
        text(s,f"{a.config.sensitivity:.1f}x",(75,286),38,CYAN,True)
        wrapped(s,"Higher sensitivity responds to smaller movements.",(75,629),500,18,MUTED)
        panel(s,(754,220,646,490))
        text(s,"YOUR CAMERA POSITION",(792,250),27,WHITE,True)
        self.preview((970,314,382,271),now)
        wrapped(s,"Head, hands and feet visible. Recalibration ends the current round.",(793,324),155,19,MUTED)

    def draw_game(self,now):
        a=self.a
        s=a.canvas
        self.title(a.card["title"],MODES[a.session_mode][0]+"  /  "+a.card["control"])
        for i,(rect,game) in enumerate(zip(playfields(len(a.match.games)),a.match.games)):
            self.worlds.draw(s,rect,game,i,now)
        pill(s,"RUN BANKED" if a.match.finished else "POINT AT PAUSE + HOLD",(40,791),MUTED,13)
        fit_text(s,"Your score is saved. Results are coming up..." if a.match.finished else "ENDLESS SURVIVAL / Keep going. Build your score." if a.config.endless else a.card["description"],(326,795),1060,21,MUTED)
        if a.match.paused:
            overlay=pygame.Surface((W,H),pygame.SRCALPHA)
            overlay.fill((4,16,29,210))
            s.blit(overlay,(0,0))
            panel(s,(398,237,644,493),(16,36,53),ORANGE,24)
            countdown=a.match.recovery_countdown
            text(s,f"BACK IN {math.ceil(countdown)}" if countdown>0 else "TIME IS ON HOLD",(720,288),41,ORANGE,True,True)
            missing=[i+1 for i in range(a.match.human_count) if not (a.bank.players[i].valid and a.bank.players[i].registered) and not a.match.games[i].finished]
            message="Take a breather. Everyone's clock is paused."
            if missing:
                message="Player "+", ".join(map(str,missing))+": stand still, arms down; then raise a hand to rejoin."
            elif countdown>0:
                message="Players ready. Your score is safe. Get back into position."
            wrapped(s,message,(446,344),550,23,WHITE)
            wrapped(s,"Reconnect with your body. Your run resumes automatically. P1 stays LEFT; P2 stays RIGHT." if a.dual_active else "Reconnect with your body. Your run resumes automatically after a short countdown.",(446,415),550,18,MUTED)
            if missing:
                self.preview((1068,504,312,208),now)

    def draw_results(self,now):
        a=self.a
        g=a.game
        s=a.canvas
        next_turn=a.session_mode=="party" and a.party_index+1<a.party_count
        if a.session_mode=="party":
            entries=sorted(a.party_results,key=lambda row:ranking_key(row[1]),reverse=True)
            party_winners=[name for name,game in entries if ranking_key(game)==ranking_key(entries[0][1])]
            title=a.current_name.upper()+" FINISHED" if next_turn else "PARTY TIE / SHARED FIRST PLACE" if len(party_winners)>1 else entries[0][0].upper()+" WINS THE PARTY"
        else:
            entries=sorted(zip(a.match.names,a.match.games),key=lambda row:ranking_key(row[1]),reverse=True)
            tied=len(a.match.winner_indices)>1
            title="IT'S A TIE!" if tied and len(entries)>1 else entries[0][0].upper()+" WINS" if len(entries)>1 else "RUN COMPLETE / GO AGAIN?" if g.endless else "CHALLENGE COMPLETE"
        champion=a.session_mode=="party" and not next_turn
        shown_name=entries[0][0] if champion else a.current_name
        if champion:
            g=entries[0][1]
        self.title(title,a.card["title"]+"  /  "+MODES[a.session_mode][0])
        celebratory=g.won or a.personal_best or (g.endless and g.score>0)
        if celebratory:
            for i in range(70):
                x=(i*179+math.sin(now+i)*24)%W
                y=((now-a.scene_started)*80+i*53)%670+150
                pygame.draw.rect(s,[CYAN,GREEN,PURPLE,ORANGE][i%4],(x,y,4,8),border_radius=2)
        panel(s,(40,224,788,476),(14,34,51),EDGE,22)
        badge=("SHARED FIRST PLACE" if len(party_winners)>1 else "PARTY CHAMPION") if champion else "NEW PERSONAL BEST" if a.personal_best else "CHALLENGE CLEARED" if g.won else "ANOTHER SECOND. ANOTHER CHANCE."
        pill(s,badge,(68,249),GREEN if g.won else ORANGE,14)
        text(s,shown_name,(70,307),25,MUTED)
        value=f"{g.elapsed:.2f}s" if g.metric=="time" and g.won else "TIME OUT" if g.metric=="time" else f"{g.score:,}"
        text(s,value,(65,344),81,WHITE,True)
        text(s,"COMPLETION TIME" if g.metric=="time" else "POINTS SCORED",(72,445),15,MUTED,mono=True)
        current_value=g.elapsed if g.metric=="time" and g.won else g.score if g.metric=="score" else None
        best=a.previous_best
        if champion:
            lookup=a.storage.best if g.metric=="time" else a.storage.best_score
            best=lookup(shown_name,a.mode,a.selected_game,a.session_mode,a.variant)
        if current_value is not None:
            best=current_value if best is None else min(best,current_value) if g.metric=="time" else max(best,current_value)
        values=[("PERSONAL BEST","--" if best is None else f"{best:.2f}s" if g.metric=="time" else f"{best:,}"),
                ("SURVIVED" if g.endless else "TIME LEFT",f"{g.elapsed if g.endless else g.remaining:.1f}s"),("LEVEL REACHED" if g.endless else "VIOLATIONS" if g.game_id=="red_green" else "MISSES",str(g.level if g.endless else g.violations))]
        for i,(label,value) in enumerate(values):
            x=68+i*245
            panel(s,(x,510,224,142),(21,44,61),EDGE,16)
            text(s,label,(x+17,531),13,MUTED,mono=True)
            text(s,value,(x+17,565),34,GREEN if i==0 else WHITE,True)
        panel(s,(858,224,542,476),(14,34,51),EDGE,22)
        text(s,"PARTY STANDINGS" if a.session_mode=="party" else "MATCH STANDINGS" if len(entries)>1 else "YOUR LOCAL RECORDS",(887,250),26,CYAN,True)
        if len(entries)>1 or a.session_mode=="party":
            for i,(name,game) in enumerate(entries):
                y=308+i*74
                panel(s,(882,y,494,61),(22,45,62),ORANGE if i==0 else EDGE,13)
                rank=1+sum(ranking_key(other)>ranking_key(game) for _,other in entries)
                text(s,f"{rank:02d}",(900,y+20),18,ORANGE,True,mono=True)
                fit_text(s,name,(952,y+18),235,22,WHITE,True)
                val=f"{game.elapsed:.2f}s" if game.metric=="time" and game.won else f"{game.progress:.0%}" if game.metric=="time" else f"{game.score:,}"
                fit_text(s,val,(1248,y+20),115,21,WHITE,True)
        else:
            rows=a.storage.leaderboard(a.mode,4,a.selected_game,a.session_mode,g.metric,a.variant)
            if not rows:
                wrapped(s,"Your first finish starts the leaderboard. Give it another go.",(891,329),455,23,MUTED)
            for i,(name,value,_) in enumerate(rows):
                y=318+i*58
                text(s,f"{i+1:02d}",(892,y),19,ORANGE,mono=True)
                fit_text(s,name,(941,y),260,22,WHITE)
                text(s,f"{value:.2f}s" if g.metric=="time" else f"{value:,}",(1240,y),20,WHITE,mono=True)
        text(s,"SAME CHALLENGE / FAIR STARTS" if len(entries)>1 else "DEMO RECORDS" if a.demo else "CAMERA RECORDS",(888,655),14,MUTED,mono=True)
