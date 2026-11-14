"""Russian Tkinter viewer. Network work stays off the UI thread."""
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from world import create_new_world, ImmortalityWorld


class App:
    def __init__(self, root):
        self.root, self.world = root, create_new_world()
        self.running, self.busy = False, False
        self.results = queue.Queue()
        self.selected = self.world.inhabitants[0].name
        root.title('Цифровая Вечность — живой мир')
        root.geometry('1180x800')
        root.minsize(880, 650)
        root.configure(bg='#101d2b')
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', padding=7)
        header = tk.Frame(root, bg='#101d2b')
        header.pack(fill='x', padx=20, pady=12)
        tk.Label(header, text='ЦИФРОВАЯ ВЕЧНОСТЬ', font=('Segoe UI', 21, 'bold'),
                 bg='#101d2b', fg='#8ce6c3').pack(side='left')
        self.clock = tk.Label(header, bg='#101d2b', fg='white', font=('Segoe UI', 11))
        self.clock.pack(side='right')
        controls = ttk.Frame(root)
        controls.pack(fill='x', padx=20)
        self.play = ttk.Button(controls, text='▶ Продолжить', command=self.toggle)
        self.play.pack(side='left')
        self.step_button = ttk.Button(controls, text='+1 час', command=self.step)
        self.step_button.pack(side='left', padx=5)
        ttk.Label(controls, text='Скорость:').pack(side='left', padx=5)
        self.speed = ttk.Combobox(controls, values=['1×', '2×', '5×'], state='readonly', width=4)
        self.speed.set('1×')
        self.speed.pack(side='left')
        self.file_buttons = []
        for text, command in [('Новый мир', self.new), ('Загрузить…', self.load), ('Сохранить…', self.save)]:
            b = ttk.Button(controls, text=text, command=command)
            b.pack(side='right', padx=3)
            self.file_buttons.append(b)
        body = ttk.Panedwindow(root, orient='horizontal')
        body.pack(fill='both', expand=True, padx=20, pady=12)
        left, right = ttk.Frame(body), ttk.Frame(body)
        body.add(left, weight=3)
        body.add(right, weight=2)
        root.after(50, lambda: body.sashpos(0, int(root.winfo_width() * .53)))
        ttk.Label(left, text='Карта мира · нажмите на имя жителя', font=('Segoe UI', 12, 'bold')).pack(anchor='w')
        self.canvas = tk.Canvas(left, bg='#172d3c', height=340, highlightthickness=0)
        self.canvas.pack(fill='both', expand=True, pady=8)
        self.canvas.bind('<Configure>', lambda e: self.draw_map())
        ttk.Label(left, text='Лента событий', font=('Segoe UI', 12, 'bold')).pack(anchor='w')
        self.events = tk.Text(left, height=10, wrap='word', bg='#eff5f3', font=('Segoe UI', 10))
        self.events.pack(fill='both', expand=True)
        self.people = ttk.Combobox(right, state='readonly')
        self.people.pack(fill='x', padx=10)
        self.people.bind('<<ComboboxSelected>>', lambda e: self.select(self.people.get()))
        self.card = tk.Text(right, wrap='word', bg='#f6f4ee', font=('Segoe UI', 11), padx=16, pady=14)
        self.card.pack(fill='both', expand=True, padx=(10, 0), pady=8)
        self.notice = tk.Label(root, text='', anchor='w', bg='#101d2b', fg='#b9cdd6')
        self.notice.pack(fill='x', padx=20, pady=(0, 10))
        self.refresh()
        root.after(100, self.poll)

    def select(self, name):
        self.selected = name
        self.refresh()

    def draw_map(self):
        c = self.canvas
        c.delete('all')
        w, h = max(c.winfo_width(), 200), max(c.winfo_height(), 200)
        radius = min(75, w * .145)
        positions = [( .18, .25), (.5, .2), (.82, .25), (.3, .7), (.72, .7)]
        centers = [(x*w, y*h) for x, y in positions]
        for a, b in [(0, 1), (1, 2), (0, 3), (1, 3), (1, 4), (2, 4), (3, 4)]:
            c.create_line(*centers[a], *centers[b], fill='#385767', width=8)
        for loc, (x, y) in zip(self.world.config.locations, centers):
            residents = [p for p in self.world.inhabitants if p.location == loc]
            height = max(72, 40 + 24*len(residents))
            c.create_rectangle(x-radius, y-25, x+radius, y+height-25, fill='#244b55', outline='#69b6a4', width=2)
            c.create_text(x, y-8, text=loc, fill='#9de9ce', font=('Segoe UI', 12, 'bold'))
            for i, person in enumerate(residents):
                item = c.create_text(x, y+20+i*24, text='● '+person.name,
                    fill='#ffe19c' if person.name == self.selected else 'white', font=('Segoe UI', 10))
                c.tag_bind(item, '<Button-1>', lambda e, name=person.name: self.select(name))

    @staticmethod
    def set_text(widget, text):
        widget.configure(state='normal')
        widget.delete('1.0', 'end')
        widget.insert('1.0', text)
        widget.configure(state='disabled')

    def refresh(self):
        self.clock.configure(text=f'{self.world.time:%d.%m.%Y · %H:%M}  |  {self.world.config.current_weather}')
        self.people['values'] = [h.name for h in self.world.inhabitants]
        self.people.set(self.selected)
        h = next(p for p in self.world.inhabitants if p.name == self.selected)
        labels = dict(hunger='Сытость', energy='Энергия', social='Общение', happiness='Счастье')
        needs = '\n'.join(f'{labels[k]:12} {"■"*round(v*10)} {v:.0%}' for k, v in h.needs.items())
        relations = '\n'.join(f'{name}: {v:+.2f}' for name, v in h.relationships.items()) or 'Пока никого'
        memories = '\n\n'.join(f'{m["time"]}\n{m["event"]}' for m in reversed(h.memories[-8:])) or 'История только начинается'
        self.set_text(self.card, f'{h.name}, {h.age} лет\n{h.personality}\n\n{h.location} · {h.status}\n\n'
                      f'ПОЧЕМУ ЭТО РЕШЕНИЕ\n{h.reason}\n\nПОТРЕБНОСТИ\n{needs}\n\nОТНОШЕНИЯ (−1…+1)\n{relations}\n\nВОСПОМИНАНИЯ\n{memories}')
        self.set_text(self.events, '\n\n'.join(reversed(self.world.events_log[-25:])))
        self.notice.configure(text=self.world.ai.last_error or (
            'DeepSeek включён · диалоги через API' if self.world.ai.api_key else 'Локальная демонстрация · ключ не нужен · 1 шаг = 1 игровой час'))
        self.draw_map()

    def toggle(self):
        self.running = not self.running
        self.play.configure(text='Ⅱ Пауза' if self.running else '▶ Продолжить')

    def step(self):
        if self.busy:
            return
        self.busy = True
        for b in self.file_buttons + [self.step_button]:
            b.configure(state='disabled')
        def worker():
            try:
                self.world.step()
                self.results.put(None)
            except Exception as exc:
                self.results.put(str(exc))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        try:
            error = self.results.get_nowait()
            self.busy = False
            for b in self.file_buttons + [self.step_button]:
                b.configure(state='normal')
            if error:
                self.running = False
                self.play.configure(text='▶ Продолжить')
                messagebox.showerror('Ошибка шага', error)
            self.refresh()
        except queue.Empty:
            pass
        if self.running and not self.busy:
            self.step()
        self.root.after(int(1000/int(self.speed.get()[0])) if self.running else 100, self.poll)

    def new(self):
        self.running = False
        self.play.configure(text='▶ Продолжить')
        self.world = create_new_world()
        self.selected = self.world.inhabitants[0].name
        self.refresh()

    def load(self):
        self.running = False
        self.play.configure(text='▶ Продолжить')
        filename = filedialog.askopenfilename(initialdir=Path(__file__).parent, filetypes=[('Мир JSON', '*.json')])
        if filename:
            try:
                world = ImmortalityWorld.load_world(filename)
                if not world.inhabitants:
                    raise ValueError('В сохранении нет жителей')
                self.world = world
                self.selected = world.inhabitants[0].name
                self.refresh()
            except Exception:
                messagebox.showerror('Загрузка', 'Не удалось прочитать мир. Текущий мир сохранён в памяти.')

    def save(self):
        filename = filedialog.asksaveasfilename(initialfile='world_save.json', defaultextension='.json', filetypes=[('Мир JSON', '*.json')])
        if filename:
            if Path(filename).resolve() == Path(__file__).with_name('digital_immortality_save.json').resolve():
                messagebox.showwarning('Исходный мир', 'Выберите другое имя: исходное сохранение защищено.')
                return
            try:
                self.world.save_world(filename)
                self.notice.configure(text='Мир сохранён: '+filename)
            except OSError:
                messagebox.showerror('Сохранение', 'Не удалось записать файл.')


def main():
    try:
        import ctypes
        ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
