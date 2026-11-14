"""Local simulation. Need values mean satisfaction: 1 is fully satisfied."""
import json
import os
import random
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path


def clamp(value, low=0, high=1):
    return max(low, min(high, float(value)))


class WorldConfig:
    def __init__(self):
        self.world_name = 'Цифровая Вечность'
        self.start_date = datetime(2023, 1, 1, 8)
        self.locations = ['Дом', 'Парк', 'Кафе', 'Офис', 'Магазин']
        self.weather_types = ['Солнечно', 'Дождливо', 'Облачно', 'Ветрено']
        self.current_weather = 'Солнечно'


class DeepSeekAI:
    def __init__(self, api_key=None):
        self.api_key = api_key if api_key is not None else os.getenv('DEEPSEEK_API_KEY', '')
        self.last_error = ''

    def generate_response(self, context, fallback, max_tokens=200):
        if not self.api_key or self.api_key == 'sk-':
            return fallback
        try:
            request = urllib.request.Request(
                'https://api.deepseek.com/chat/completions',
                data=json.dumps({'model': 'deepseek-chat', 'messages': [
                    {'role': 'user', 'content': context}], 'max_tokens': max_tokens}).encode(),
                headers={'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'})
            with urllib.request.urlopen(request, timeout=8) as response:
                result = json.load(response)['choices'][0]['message']['content'].strip()
            if not result:
                raise ValueError('empty response')
            self.last_error = ''
            return result[:2000]
        except Exception:
            self.last_error = 'DeepSeek недоступен. Использован локальный диалог.'
            return fallback


class DigitalHuman:
    def __init__(self, name, age, personality, world):
        self.name, self.age, self.personality, self.world = name, age, personality, world
        self.memories, self.relationships = [], {}
        self.location, self.status, self.reason = 'Дом', 'Отдыхает', 'Начало нового дня'
        self.needs = dict(hunger=.65, energy=.8, social=.55, happiness=.7)

    def add_memory(self, event, location=None, partner=None, valence=.2):
        self.memories.append(dict(time=self.world.time.isoformat(timespec='minutes'),
                                 event=event, location=location, partner=partner, valence=valence))
        self.memories = self.memories[-50:]

    def relevant_memories(self):
        return [m for m in self.memories if not m['event'].startswith('Ошибка ИИ')][-12:]

    def affinity(self, key, value):
        return sum(m.get('valence', .1) * (.9 ** i) for i, m in
                   enumerate(reversed(self.relevant_memories())) if m.get(key) == value)

    def update_needs(self):
        for key, loss in [('hunger', .07), ('energy', .045), ('social', .06), ('happiness', .015)]:
            self.needs[key] = clamp(self.needs[key] - loss)


class ImmortalityWorld:
    def __init__(self, config=None, seed=None):
        self.config = config or WorldConfig()
        self.time = self.config.start_date
        self.inhabitants, self.events_log = [], []
        self.rng = random.Random(seed)
        self.ai = DeepSeekAI()

    def log_event(self, event):
        self.events_log.append(f'[{self.time:%d.%m %H:%M}] {event}')
        self.events_log = self.events_log[-100:]

    def add_inhabitant(self, name, age, personality):
        if any(h.name == name for h in self.inhabitants):
            raise ValueError('Имена жителей должны быть уникальными')
        human = DigitalHuman(name, age, personality, self)
        for other in self.inhabitants:
            human.relationships[other.name] = 0
            other.relationships.setdefault(name, 0)
        self.inhabitants.append(human)
        self.log_event(f'Прибыл житель: {name}')
        return human

    def choose_partner(self, human):
        others = [h for h in self.inhabitants if h is not human]
        return max(others, key=lambda h: human.relationships.get(h.name, 0) +
                   human.affinity('partner', h.name), default=None)

    def social_interaction(self, human):
        other = self.choose_partner(human)
        if other is None:
            human.status = 'Пишет письмо будущим жителям'
            human.needs['social'] = clamp(human.needs['social'] + .2)
            return
        other.location = human.location
        memories = human.relevant_memories()
        reference = memories[-1]['event'] if memories else 'наше знакомство'
        fallback = f'{human.name}: Помнишь: «{reference}»?\n{other.name}: Давай создадим ещё одно хорошее воспоминание.'
        context = (f'Напиши короткий диалог по-русски: {human.name} ({human.personality}) и '
                   f'{other.name} ({other.personality}) в {human.location}. '
                   f'Отношения: {human.relationships[other.name]:.2f}. '
                   f'Память первого: {json.dumps(memories, ensure_ascii=False)}. '
                   f'Память второго: {json.dumps(other.relevant_memories(), ensure_ascii=False)}.')
        dialog = self.ai.generate_response(context, fallback)
        human.status = f'Беседует с {other.name}'
        human.reason += f'; выбран {other.name}: отношения и память о встречах'
        reaction = self.rng.uniform(-.12, .25)
        for a, b in [(human, other), (other, human)]:
            a.relationships[b.name] = clamp(a.relationships.get(b.name, 0) + reaction, -1, 1)
            a.needs['social'] = clamp(a.needs['social'] + .4)
            a.add_memory(f'Беседа с {b.name}: {dialog}', a.location, b.name, reaction)
        self.log_event(dialog)

    def act(self, human):
        n = human.needs
        if n['hunger'] < .3 or n['energy'] < .2:
            if n['hunger'] <= n['energy']:
                human.location, human.status = 'Кафе', 'Ест горячий обед'
                human.reason = 'Низкая сытость: пора поесть'
                n['hunger'] = clamp(n['hunger'] + .65)
            else:
                human.location, human.status = 'Дом', 'Спит'
                human.reason = 'Мало энергии: нужен сон'
                n['energy'] = clamp(n['energy'] + .65)
        elif n['social'] < .4:
            human.location = 'Кафе' if self.config.current_weather == 'Дождливо' else 'Парк'
            human.reason = 'Не хватает общения'
            self.social_interaction(human)
            return
        else:
            base = {'Дом': .15, 'Парк': .25, 'Кафе': .1, 'Офис': .15, 'Магазин': .05}
            preferred = 'Парк' if 'природ' in human.personality else 'Офис' if any(
                s in human.personality for s in ['наук', 'учен', 'программист']) else 'Дом'
            base[preferred] += .3
            if self.config.current_weather == 'Дождливо':
                base['Парк'] -= .8
            scores = {loc: score + human.affinity('location', loc) for loc, score in base.items()}
            human.location = max(scores, key=scores.get)
            human.reason = ('Память о прошлых занятиях, интересы и погода; '
                            f'оценка места {scores[human.location]:.2f}')
            human.status = {'Дом': 'Читает и размышляет', 'Парк': 'Наблюдает природу',
                            'Кафе': 'Рисует за чашкой чая', 'Офис': 'Исследует цифровой мир',
                            'Магазин': 'Выбирает книги'}[human.location]
            n['happiness'] = clamp(n['happiness'] + .08)
        human.add_memory(human.status, human.location, valence=.12)
        self.log_event(f'{human.name}: {human.status}. {human.reason}')

    def step(self):
        self.time += timedelta(hours=1)
        if self.rng.random() < .15:
            self.config.current_weather = self.rng.choice(self.config.weather_types)
            self.log_event(f'Погода: {self.config.current_weather}')
        for human in self.inhabitants:
            human.update_needs()
        for human in self.inhabitants:
            self.act(human)

    def simulate_day(self):
        for _ in range(24):
            self.step()

    def to_dict(self):
        return dict(version=2, time=self.time.isoformat(), config=dict(
            world_name=self.config.world_name, current_weather=self.config.current_weather),
            events=self.events_log, inhabitants=[{k: getattr(h, k) for k in
                ['name', 'age', 'personality', 'memories', 'needs', 'relationships', 'location', 'status', 'reason']}
                for h in self.inhabitants])

    def save_world(self, filename='world_save.json'):
        path = Path(filename)
        temp = path.with_suffix(path.suffix + '.tmp')
        temp.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')
        temp.replace(path)

    @staticmethod
    def load_world(filename='world_save.json'):
        data = json.loads(Path(filename).read_text(encoding='utf-8'))
        world = ImmortalityWorld()
        t = data['time']
        world.time = datetime.fromtimestamp(t) if isinstance(t, (int, float)) else datetime.fromisoformat(t)
        for k in ['world_name', 'current_weather']:
            setattr(world.config, k, data.get('config', {}).get(k, getattr(world.config, k)))
        for item in data['inhabitants']:
            h = world.add_inhabitant(item['name'], item['age'], item['personality'])
            for k in ['memories', 'relationships', 'status', 'reason']:
                if k in item:
                    setattr(h, k, item[k])
            h.memories = h.memories[-50:]
            for m in h.memories:
                event = m['event']
                m.setdefault('location', 'Кафе' if 'кафе' in event.lower() else None)
                m.setdefault('partner', event.removeprefix('Общался с ') if event.startswith('Общался с ') else None)
                m.setdefault('valence', .1)
            h.needs = {k: clamp(item.get('needs', {}).get(k, v)) for k, v in h.needs.items()}
            h.location = item.get('location', 'Дом')
            if h.location not in world.config.locations:
                h.location = 'Дом'
        for h in world.inhabitants:
            h.relationships = {other.name: clamp(h.relationships.get(other.name, 0), -1, 1)
                               for other in world.inhabitants if other is not h}
        world.events_log = data.get('events', [])[-100:]
        return world


def create_new_world():
    world = ImmortalityWorld()
    for args in [('Алексей', 35, 'интроверт, программист, любит науку'),
                 ('Ольга', 28, 'экстраверт, художник, любит природу'),
                 ('Дмитрий', 42, 'философ, любит книги и дискуссии')]:
        world.add_inhabitant(*args)
    world.inhabitants[0].add_memory('В парке родилась идея нового исследования', 'Парк', valence=.7)
    world.inhabitants[1].add_memory('Дмитрий поддержал мой рисунок', 'Парк', 'Дмитрий', .7)
    world.inhabitants[1].needs['social'] = .35
    return world
