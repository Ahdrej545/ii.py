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
        self.relationship_history = {}
        self.goal_history = []
        self.goal = self.make_goal()

    def make_goal(self, kind=None):
        kind = kind or ('exhibition' if 'художник' in self.personality else
                        'friendship' if 'философ' in self.personality else 'project')
        titles = dict(project='Закончить исследовательский проект',
                      exhibition='Подготовить выставку', friendship='Укрепить дружбу')
        return dict(kind=kind, title=titles[kind], progress=0,
                    target=3 if kind == 'friendship' else 12,
                    started=self.world.time.isoformat(), deadline=(self.world.time + timedelta(days=7)).isoformat(),
                    state='active', daily_date='', daily_work=0, supported=False,
                    last_request='', last_progress_day='', note='Первый шаг ещё впереди')

    def add_memory(self, event, location=None, partner=None, valence=.2, kind='routine'):
        self.memories.append(dict(time=self.world.time.isoformat(timespec='minutes'),
                                 event=event, location=location, partner=partner, valence=valence, kind=kind))
        self.memories = self.memories[-50:]

    def relevant_memories(self):
        useful = [m for m in self.memories if not m['event'].startswith('Ошибка ИИ')]
        important = [m for m in useful if m.get('kind') in ('goal', 'relationship')][-6:]
        return [m for m in useful if m not in important][-6:] + important

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

    def relationship_event(self, human, other, cause, delta, detail):
        """Every change has a cause, shared by both participants and saved."""
        event = f'{human.name} — {other.name}: {cause}. {detail}'
        for a, b in [(human, other), (other, human)]:
            a.relationships[b.name] = clamp(a.relationships.get(b.name, 0) + delta, -1, 1)
            history = a.relationship_history.setdefault(b.name, [])
            history.append(dict(time=self.time.isoformat(), cause=cause, delta=delta, detail=detail))
            a.relationship_history[b.name] = history[-12:]
            a.add_memory(event, a.location, b.name, delta, kind='relationship')
        self.log_event(event)

    def recent_interaction(self, human, other, hours=8):
        history = human.relationship_history.get(other.name, [])
        return bool(history and self.time - datetime.fromisoformat(history[-1]['time']) < timedelta(hours=hours))

    def request_help(self, human):
        goal = human.goal
        candidates = []
        for other in self.inhabitants:
            if other is human:
                continue
            refusals = [e for e in human.relationship_history.get(other.name, [])
                        if e['cause'] == 'Отказ' and self.time - datetime.fromisoformat(e['time']) < timedelta(days=2)]
            if not refusals:
                candidates.append(other)
        if not candidates:
            goal['note'] = 'Память об отказах: пока готовится самостоятельно'
            return
        other = max(candidates, key=lambda h: human.relationships.get(h.name, 0) + human.affinity('partner', h.name))
        goal['last_request'] = self.time.isoformat()
        busy_project = (other.goal['state'] == 'active' and other.goal['kind'] == 'project'
                        and other.goal['daily_work'] >= 2 and other.goal['daily_date'] == self.time.date().isoformat())
        if other.needs['energy'] < .4 or other.needs['hunger'] < .35 or busy_project:
            reason = 'занят своим проектом' if busy_project else 'нуждается в еде или отдыхе'
            goal['note'] = f'{other.name} отказал: {reason}; будет искать другого помощника'
            self.relationship_event(human, other, 'Отказ', -.12, goal['note'])
        else:
            goal['supported'] = True
            goal['note'] = f'{other.name} помог с подготовкой'
            other.needs['energy'] = clamp(other.needs['energy'] - .08)
            self.relationship_event(human, other, 'Помощь', .18, goal['note'])

    def finish_goal(self, human, success):
        goal = human.goal
        goal['state'] = 'completed' if success else 'failed'
        goal['finished'] = self.time.isoformat()
        goal['note'] = 'Цель достигнута' if success else 'Срок истёк; опыт поможет в новой попытке'
        event = f'{human.name}: {goal["title"]} — {goal["note"].lower()}'
        human.add_memory(event, human.location, valence=.6 if success else -.25, kind='goal')
        human.needs['happiness'] = clamp(human.needs['happiness'] + (.15 if success else -.1))
        self.log_event(event)

    def maintain_goal(self, human):
        goal = human.goal
        if goal['state'] != 'active':
            if self.time - datetime.fromisoformat(goal['finished']) >= timedelta(days=1):
                human.goal_history = (human.goal_history + [dict(goal)])[-5:]
                # After a failure repeat with the experience; after success try another kind.
                next_kind = goal['kind'] if goal['state'] == 'failed' else {
                    'project': 'friendship', 'friendship': 'exhibition', 'exhibition': 'project'}[goal['kind']]
                human.goal = human.make_goal(next_kind)
                failures = sum(g['state'] == 'failed' for g in human.goal_history)
                if failures:
                    human.goal['target'] = max(3, human.goal['target'] - min(3, failures))
                    human.goal['note'] = 'После неудачи выбран меньший объём работы'
                self.log_event(f'{human.name}: новая цель — {human.goal["title"]}')
        elif self.time >= datetime.fromisoformat(goal['deadline']):
            self.finish_goal(human, False)

    def advance_goal(self, human):
        goal = human.goal
        today = self.time.date().isoformat()
        if goal['state'] != 'active' or not 10 <= self.time.hour <= 18:
            return False
        if goal['daily_date'] != today:
            goal.update(daily_date=today, daily_work=0)
        if goal['kind'] == 'friendship' or goal['daily_work'] >= 3:
            return False
        human.location = 'Парк' if goal['kind'] == 'exhibition' and self.config.current_weather != 'Дождливо' else 'Офис'
        human.status = 'Работает над целью: ' + goal['title'].lower()
        human.reason = f'Личная цель; сегодня {goal["daily_work"]}/3 этапов, остальное время — потребности и отдых'
        if goal['kind'] == 'exhibition' and goal['progress'] >= 3 and not goal['supported']:
            if not goal['last_request'] or self.time - datetime.fromisoformat(goal['last_request']) >= timedelta(days=1):
                self.request_help(human)
            if not goal['supported'] and goal['progress'] >= goal['target'] - 1:
                # A lone inhabitant can still finish, with extra time rather than a permanent deadlock.
                if self.time - datetime.fromisoformat(goal['started']) < timedelta(days=5):
                    human.reason = 'Финальная подготовка ждёт помощи; после пяти дней попробует справиться самостоятельно'
                    return True
                goal['note'] = 'После ожидания помощи завершает подготовку самостоятельно'
        goal['progress'] += 1
        goal['daily_work'] += 1
        if goal['note'] == 'Первый шаг ещё впереди':
            goal['note'] = 'Работа разбита на небольшие ежедневные этапы'
        human.needs['energy'] = clamp(human.needs['energy'] - .03)
        if goal['daily_work'] == 1:
            event = f'{human.name}: {goal["title"]}, готово {goal["progress"]}/{goal["target"]}. {goal["note"]}'
            human.add_memory(event, human.location, valence=.15, kind='goal')
            self.log_event(event)
        if goal['progress'] >= goal['target']:
            self.finish_goal(human, True)
        return True

    def friendship_progress(self, human, other):
        goal = human.goal
        today = self.time.date().isoformat()
        if (goal['state'] == 'active' and goal['kind'] == 'friendship'
                and goal['last_progress_day'] != today and human.relationships[other.name] > 0):
            goal['last_progress_day'] = today
            goal['progress'] += 1
            goal['note'] = f'Тёплая встреча с {other.name}; нужны встречи в разные дни'
            self.log_event(f'{human.name}: дружба, {goal["progress"]}/{goal["target"]}. {goal["note"]}')
            if goal['progress'] >= goal['target']:
                self.finish_goal(human, True)

    def social_interaction(self, human):
        other = self.choose_partner(human)
        if other is None:
            human.status = 'Пишет письмо будущим жителям'
            human.needs['social'] = clamp(human.needs['social'] + .2)
            return
        if self.recent_interaction(human, other):
            human.status = f'Проводит время рядом с {other.name}'
            human.reason += '; недавняя встреча уже учтена, отношения не меняются повторно'
            human.needs['social'] = clamp(human.needs['social'] + .3)
            return
        other.location = human.location
        memories = human.relevant_memories()
        reference = (memories[-1]['event'][:120] if memories else 'наше знакомство')
        history = human.relationship_history.get(other.name, [])
        unresolved = bool(history and history[-1]['cause'] in ('Отказ', 'Ссора'))
        if unresolved and min(human.needs['energy'], other.needs['energy']) < .4:
            cause, delta = 'Ссора', -.15
            detail = 'Усталость мешает спокойно обсудить прежнюю обиду'
        elif unresolved or human.relationships.get(other.name, 0) < 0:
            cause, delta = 'Примирение', .16
            detail = 'Обсудили прежнее разногласие и согласились начать заново'
        else:
            cause, delta = 'Тёплая беседа', .04
            detail = 'Выслушали друг друга и поделились планами'
        fallback = f'{human.name}: Вспоминаю: «{reference}».\n{other.name}: {detail}.'
        context = (f'Напиши короткий диалог по-русски: {human.name} ({human.personality}) и '
                   f'{other.name} ({other.personality}) в {human.location}. '
                   f'Отношения: {human.relationships[other.name]:.2f}. '
                   f'Событие уже определено правилами: {cause}. {detail}. Не меняй исход. '
                   f'Цели: {human.goal["title"]}; {other.goal["title"]}. '
                   f'Память первого: {json.dumps(memories, ensure_ascii=False)}. '
                   f'Память второго: {json.dumps(other.relevant_memories(), ensure_ascii=False)}.')
        dialog = self.ai.generate_response(context, fallback)
        human.status = f'Беседует с {other.name}'
        human.reason += f'; выбран {other.name}: отношения и память о встречах'
        self.relationship_event(human, other, cause, delta, detail)
        for a, b in [(human, other), (other, human)]:
            a.needs['social'] = clamp(a.needs['social'] + .4)
            if delta > 0:
                self.friendship_progress(a, b)
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
        elif self.advance_goal(human):
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
        routine = [m for m in human.memories if m.get('kind', 'routine') == 'routine']
        if not routine or routine[-1]['event'] != human.status:
            human.add_memory(human.status, human.location, valence=.12)

    def step(self):
        self.time += timedelta(hours=1)
        if self.rng.random() < .15:
            weather = self.rng.choice(self.config.weather_types)
            if weather != self.config.current_weather:
                self.config.current_weather = weather
                self.log_event(f'Погода: {self.config.current_weather}')
        for human in self.inhabitants:
            human.update_needs()
            self.maintain_goal(human)
        for human in self.inhabitants:
            self.act(human)

    def simulate_day(self):
        for _ in range(24):
            self.step()

    def to_dict(self):
        return dict(version=3, time=self.time.isoformat(), config=dict(
            world_name=self.config.world_name, current_weather=self.config.current_weather),
            events=self.events_log, inhabitants=[{k: getattr(h, k) for k in
                ['name', 'age', 'personality', 'memories', 'needs', 'relationships', 'location', 'status', 'reason',
                 'goal', 'goal_history', 'relationship_history']}
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
            for k in ['memories', 'relationships', 'status', 'reason', 'goal', 'goal_history', 'relationship_history']:
                if k in item:
                    setattr(h, k, item[k])
            h.memories = h.memories[-50:]
            for m in h.memories:
                event = m['event']
                m.setdefault('location', 'Кафе' if 'кафе' in event.lower() else None)
                m.setdefault('partner', event.removeprefix('Общался с ') if event.startswith('Общался с ') else None)
                m.setdefault('valence', .1)
                m.setdefault('kind', 'routine')
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
