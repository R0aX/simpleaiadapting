import tkinter as tk
import random
import math

# --- CONFIG ---
POP_SIZE = 250   # Slightly lower for better performance/no lag
GENES = 700
MUTATION = 0.15
WIDTH, HEIGHT = 900, 650

def generate_name():
    p = ["Neo", "Vex", "Flux", "Echo", "Void", "Zen", "Astra", "Mega"]
    s = ["Node", "Core", "Link", "Soul", "Bit", "Wire", "Mina", "Ray"]
    return f"{random.choice(p)}_{random.choice(s)}"

def random_rgb():
    return f'#{random.randint(100,255):02x}{random.randint(100,255):02x}{random.randint(100,255):02x}'

ORB_DATA = [{"name": generate_name(), "color": random_rgb()} for _ in range(POP_SIZE)]

class Genome:
    def __init__(self, parent_moves=None):
        if parent_moves:
            self.moves = [m if random.random() > MUTATION else 
                          (random.uniform(-2, 2), random.random() < 0.08, random.random() < 0.04) 
                          for m in parent_moves]
        else:
            self.moves = [(random.uniform(-2, 2), random.random() < 0.08, random.random() < 0.04) for _ in range(GENES)]

class Ball:
    def __init__(self, canvas, index, genome):
        self.canvas = canvas
        self.data = ORB_DATA[index]
        self.genome = genome
        self.color = self.data["color"]
        self.glow = canvas.create_oval(0,0,0,0, outline=self.color, width=1)
        self.id = canvas.create_oval(0,0,0,0, fill=self.color, outline="white")
        self.vx, self.vy = 0, 0
        self.jumps = 2
        self.alive, self.reached = True, False
        self.step, self.last_dash = 0, -200
        self.wall_side = 0

    def update(self, platforms, goal_coords):
        if not self.alive or self.reached: return
        if self.step < GENES:
            mx, jmp, dsh = self.genome.moves[self.step]
            self.vx += mx
            if dsh and self.step - self.last_dash > 120:
                self.vx *= 6
                self.last_dash = self.step
                self.canvas.itemconfig(self.id, fill="white")
            elif self.step - self.last_dash == 10:
                self.canvas.itemconfig(self.id, fill=self.color)
            if jmp:
                if self.jumps > 0: self.vy = -13; self.jumps -= 1
                elif self.wall_side != 0:
                    self.vy = -14
                    self.vx = -18 if self.wall_side == 1 else 18
                    self.wall_side = 0
            self.step += 1
        else: self.alive = False

        self.vx *= 0.92
        self.vy += 0.68
        self.canvas.move(self.id, self.vx, self.vy)
        p = self.canvas.coords(self.id)
        self.canvas.coords(self.glow, p[0]-4, p[1]-4, p[2]+4, p[3]+4)
        
        self.wall_side = 0
        for plat in platforms:
            pl = self.canvas.coords(plat)
            if p[2] > pl[0] and p[0] < pl[2] and p[3] > pl[1] and p[1] < pl[3]:
                dx1, dx2, dy1, dy2 = p[2]-pl[0], pl[2]-p[0], p[3]-pl[1], pl[3]-p[1]
                overlap = min(dx1, dx2, dy1, dy2)
                if overlap == dy1 and self.vy > 0: self.vy, self.jumps = 0, 2; self.canvas.move(self.id, 0, -dy1)
                elif overlap == dx1: self.vx, self.wall_side = 0, 1
                elif overlap == dx2: self.vx, self.wall_side = 0, -1

        if p[1] > HEIGHT or p[1] < -500: self.alive = False
        if p[2] > goal_coords[0] and p[0] < goal_coords[2] and p[3] > goal_coords[1] and p[1] < goal_coords[3]:
            self.reached = True

class Game:
    def __init__(self, root):
        self.root = root
        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="#020205", highlightthickness=0)
        self.canvas.pack()
        self.lvl, self.gen = 1, 1
        self.best_moves = None
        self.platforms, self.balls = [], []
        self.last_best = {"name": "None", "color": "white"}
        self.last_worst = {"name": "None", "color": "white"}
        self.state = "RUNNING" # Logic state to prevent double-loading
        
        # UI
        self.hud = self.canvas.create_rectangle(0, 0, WIDTH, 80, fill="#0a0a1a", outline="#11ffff")
        self.ui_m = self.canvas.create_text(WIDTH/2, 25, text="", fill="#11ffff", font=("Courier", 16, "bold"))
        self.ui_b = self.canvas.create_text(20, 45, text="", anchor="nw", font=("Courier", 10))
        self.ui_w = self.canvas.create_text(20, 60, text="", anchor="nw", font=("Courier", 10))
        
        self.load_level()
        self.loop()

    def load_level(self):
        for b in self.balls: self.canvas.delete(b.id); self.canvas.delete(b.glow)
        for p in self.platforms: self.canvas.delete(p)
        if hasattr(self, 'goal'): self.canvas.delete(self.goal)
        
        layouts = {
            1: [(0, 630, 900, 650), (350, 450, 550, 465), (700, 300, 850, 315)],
            2: [(0, 630, 200, 650), (150, 350, 180, 600), (450, 200, 480, 500)],
            3: [(0, 630, 100, 650), (120, 500, 140, 520), (250, 400, 270, 420), (450, 300, 470, 320), (650, 200, 670, 220)]
        }
        self.platforms = [self.canvas.create_rectangle(*c, fill="#111", outline="#ff00ff", width=2) for c in layouts.get(self.lvl, layouts[1])]
        self.goal = self.canvas.create_oval(820, 100, 870, 150, fill="#ffff00", outline="white", width=2)
        self.balls = [Ball(self.canvas, i, Genome(self.best_moves)) for i in range(POP_SIZE)]
        for b in self.balls: self.canvas.coords(b.id, 20, 580, 36, 596)
        self.state = "RUNNING"

    def loop(self):
        if self.state == "RUNNING":
            active_orbs, winner = 0, None
            g_c = self.canvas.coords(self.goal)
            tx, ty = g_c[0]+25, g_c[1]+25
            c_best, c_worst, max_f, min_f = None, None, -1e9, 1e9

            for b in self.balls:
                b.update(self.platforms, g_c)
                pos = self.canvas.coords(b.id)
                dist = math.sqrt((pos[0]-tx)**2 + (pos[1]-ty)**2)
                fit = 10000 / (dist + 1)
                if b.reached: fit += 100000; winner = b
                if fit > max_f: max_f, c_best = fit, b
                if fit < min_f: min_f, c_worst = fit, b
                if b.alive and not b.reached: active_orbs += 1

            self.canvas.itemconfig(self.ui_m, text=f"LVL {self.lvl} // GEN {self.gen}")
            self.canvas.itemconfig(self.ui_b, text=f"LAST BEST: {self.last_best['name']}", fill=self.last_best['color'])
            self.canvas.itemconfig(self.ui_w, text=f"LAST WORST: {self.last_worst['name']}", fill=self.last_worst['color'])

            if active_orbs == 0 or winner:
                self.state = "LOADING"
                self.last_best = {"name": c_best.data['name'], "color": c_best.data['color']}
                self.last_worst = {"name": c_worst.data['name'], "color": c_worst.data['color']}
                if winner: self.lvl += 1; self.best_moves, self.gen = None, 1
                else: self.best_moves, self.gen = c_best.genome.moves, self.gen + 1
                self.root.after(100, self.load_level)

        self.root.after(10, self.loop)

root = tk.Tk()
root.title("Stable Neon Swarm")
Game(root)
root.mainloop()