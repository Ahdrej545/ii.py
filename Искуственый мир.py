import time
import random
import json
import requests
import os
from datetime import datetime

# Конфигурация мира
class WorldConfig:
    def __init__(self):
        self.world_name = "Цифровая Вечность"
        self.time_scale = 60  # 1 реальная секунда = 1 игровая минута
        self.start_date = datetime(2023, 1, 1)
        self.locations = ["Дом", "Парк", "Кафе", "Офис", "Магазин"]
        self.weather_types = ["Солнечно", "Дождливо", "Облачно", "Ветрено"]
        self.current_weather = "Солнечно"

# Житель цифрового мира
class DigitalHuman:
    def __init__(self, name, age, personality, world):
        self.name = name
        self.age = age
        self.personality = personality
        self.memories = []
        self.location = "Дом"
        self.status = "Отдыхает"
        self.relationships = {}
        self.needs = {
            "hunger": random.uniform(0.4, 0.8),
            "energy": random.uniform(0.5, 0.9),
            "social": random.uniform(0.3, 0.7),
            "happiness": random.uniform(0.6, 1.0)
        }
        self.world = world
        
        # Инициализация отношений
        for other in world.inhabitants:
            if other != self:
                self.relationships[other.name] = random.uniform(-0.5, 0.5)
    
    def add_memory(self, event):
        self.memories.append({
            "time": self.world.time.strftime("%Y-%m-%d %H:%M"),
            "event": event
        })
        if len(self.memories) > 50:
            self.memories.pop(0)
    
    def update_needs(self):
        self.needs["hunger"] -= 0.02
        self.needs["energy"] -= 0.01
        self.needs["social"] -= 0.015
        self.needs["happiness"] += random.uniform(-0.05, 0.05)
        
        for need in self.needs:
            self.needs[need] = max(0, min(1, self.needs[need]))

# Класс для работы с ИИ
class DeepSeekAI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.api_url = "https://api.deepseek.com/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.cache = {}
    
    def generate_response(self, context, max_tokens=100):
        if context in self.cache:
            return self.cache[context]
        
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": context}],
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(
                self.api_url, 
                headers=self.headers, 
                data=json.dumps(payload),
                timeout=15
            )
            response_data = response.json()
            result = response_data['choices'][0]['message']['content'].strip()
            self.cache[context] = result
            return result
        except Exception as e:
            return f"Ошибка ИИ: {str(e)}"

# Мир цифрового бессмертия
class ImmortalityWorld:
    def __init__(self, config):
        self.config = config
        self.time = config.start_date
        self.inhabitants = []
        self.ai = DeepSeekAI("sk-")  # ЗАМЕНИТЕ НА РЕАЛЬНЫЙ КЛЮЧ!
        self.events_log = []
    
    def add_inhabitant(self, name, age, personality):
        new_human = DigitalHuman(name, age, personality, self)
        self.inhabitants.append(new_human)
        self.log_event(f"В мир прибыл новый житель: {name}")
        return new_human
    
    def log_event(self, event):
        timestamp = self.time.strftime("%Y-%m-%d %H:%M")
        self.events_log.append(f"[{timestamp}] {event}")
        if len(self.events_log) > 100:
            self.events_log.pop(0)
    
    def update_time(self):
        self.time = datetime.fromtimestamp(
            self.time.timestamp() + self.config.time_scale * 60
        )
    
    def change_weather(self):
        if random.random() < 0.2:
            new_weather = random.choice(self.config.weather_types)
            if new_weather != self.config.current_weather:
                self.config.current_weather = new_weather
                self.log_event(f"Погода изменилась: {new_weather}")
    
    def random_event(self):
        events = [
            {
                "name": "Фестиваль",
                "effect": lambda h: setattr(h, 'needs', {k: min(1, v+0.3) for k,v in h.needs.items()}),
                "message": "Город празднует ежегодный фестиваль! Все жители счастливы"
            },
            {
                "name": "Технический сбой",
                "effect": lambda h: setattr(h, 'needs', {k: max(0, v-0.2) for k,v in h.needs.items()}),
                "message": "Временный сбой в матрице. Жители дезориентированы"
            },
            {
                "name": "Научный прорыв",
                "effect": lambda h: h.add_memory("Участвовал в важном научном открытии"),
                "message": "Ученые мира совершили прорыв в технологии бессмертия!"
            },
            {
                "name": "Прибытие нового жителя",
                "effect": lambda h: None,
                "message": "В мир прибыл новый житель!",
                "action": lambda: self.add_inhabitant(
                    f"Житель-{random.randint(100,999)}", 
                    random.randint(20,60),
                    random.choice(["ученый", "художник", "философ", "инженер"])
                )
            }
        ]
        
        if random.random() < 0.15:
            event = random.choice(events)
            self.log_event(f"СОБЫТИЕ: {event['message']}")
            print(f"\n⚡ {event['message']}")
            
            if "action" in event:
                event["action"]()
                
            for human in self.inhabitants:
                event['effect'](human)
    
    def social_interaction(self, human):
        others = [h for h in self.inhabitants if h != human]
        if not others:
            return
            
        other = random.choice(others)
        
        context = (
            f"Текущие отношения: {human.name} относится к {other.name} с оценкой {human.relationships.get(other.name, 0):.1f}. "
            f"{human.name} ({human.personality}) встречает {other.name} ({other.personality}) "
            f"в {human.location}. Начни диалог между ними (2-3 реплики)."
        )
        
        dialog = self.ai.generate_response(context, max_tokens=200)
        human.add_memory(f"Общался с {other.name}")
        other.add_memory(f"Общался с {human.name}")
        
        print(f"\n💬 Диалог между {human.name} и {other.name}:")
        print(dialog)
        
        reaction = random.uniform(-0.3, 0.4)
        human.relationships[other.name] = max(-1, min(1, 
            human.relationships.get(other.name, 0) + reaction
        ))
        other.relationships[human.name] = max(-1, min(1, 
            other.relationships.get(human.name, 0) + reaction * 0.7
        ))
        
        print(f"  Отношения {human.name} к {other.name}: {human.relationships[other.name]:.2f}")
        human.needs["social"] = min(1.0, human.needs["social"] + 0.3)
        other.needs["social"] = min(1.0, other.needs["social"] + 0.2)
    
    def simulate_day(self):
        self.random_event()
        print(f"\n=== День {self.time.strftime('%Y-%m-%d')} ===")
        print(f"Погода: {self.config.current_weather}")
        
        for human in self.inhabitants:
            human.update_needs()
            
            if human.needs["hunger"] < 0.3:
                human.location = "Кафе"
                human.status = "Ест"
                human.add_memory(f"Перекусил в кафе")
            elif human.needs["social"] < 0.4:
                human.location = "Парк"
                human.status = "Общается"
                self.social_interaction(human)
            elif human.needs["energy"] < 0.2:
                human.location = "Дом"
                human.status = "Спит"
                human.needs["energy"] = min(1.0, human.needs["energy"] + 0.5)
            else:
                activity = self.ai.generate_response(
                    f"Придумай одно занятие для {human.name} ({human.personality}) "
                    f"в локации {human.location} в {self.config.current_weather} погоду"
                )
                human.status = activity
                human.add_memory(activity)
            
            print(f"\n{human.name} ({human.age} лет):")
            print(f"  Место: {human.location}, Занятие: {human.status}")
            print(f"  Потребности: Голод {human.needs['hunger']:.2f}, "
                  f"Энергия {human.needs['energy']:.2f}, "
                  f"Общение {human.needs['social']:.2f}")
            print(f"  Счастье: {human.needs['happiness']:.2f}")
        
        self.update_time()
        self.change_weather()
    
    def save_world(self, filename="world_save.json"):
        data = {
            "time": self.time.timestamp(),
            "inhabitants": [
                {
                    "name": h.name,
                    "age": h.age,
                    "personality": h.personality,
                    "memories": h.memories,
                    "needs": h.needs,
                    "relationships": h.relationships,
                    "location": h.location
                } for h in self.inhabitants
            ],
            "events": self.events_log[-50:],
            "config": {
                "world_name": self.config.world_name,
                "current_weather": self.config.current_weather
            }
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\nМир сохранен в файле: {filename}")
    
    @staticmethod
    def load_world(filename="world_save.json"):
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        config = WorldConfig()
        config.world_name = data["config"]["world_name"]
        config.current_weather = data["config"]["current_weather"]
        
        world = ImmortalityWorld(config)
        world.time = datetime.fromtimestamp(data["time"])
        world.events_log = data["events"]
        
        for h_data in data["inhabitants"]:
            human = DigitalHuman(
                h_data["name"],
                h_data["age"],
                h_data["personality"],
                world
            )
            human.memories = h_data["memories"]
            human.needs = h_data["needs"]
            human.relationships = h_data["relationships"]
            human.location = h_data["location"]
            world.inhabitants.append(human)
        
        return world

# ======================
# ЗАПУСК СИМУЛЯЦИИ МИРА
# ======================

def create_new_world():
    config = WorldConfig()
    world = ImmortalityWorld(config)
    world.add_inhabitant("Алексей", 35, "интроверт, программист, любит науку")
    world.add_inhabitant("Ольга", 28, "экстраверт, художник, любит природу")
    world.add_inhabitant("Дмитрий", 42, "философ, любит книги и дискуссии")
    return world

if __name__ == "__main__":
    print("="*50)
    print("🌌 СИМУЛЯТОР ЦИФРОВОГО БЕССМЕРТИЯ")
    print("="*50)
    
    save_file = "digital_immortality_save.json"
    
    if os.path.exists(save_file):
        choice = input("Найдено сохранение. Загрузить? (y/n): ").lower()
        if choice == 'y':
            try:
                world = ImmortalityWorld.load_world(save_file)
                print("✔ Мир успешно загружен!")
            except Exception as e:
                print(f"Ошибка загрузки: {e}")
                print("Создаем новый мир...")
                world = create_new_world()
        else:
            world = create_new_world()
    else:
        world = create_new_world()
    
    print(f"\nДобро пожаловать в '{world.config.world_name}'!")
    print(f"Текущая дата: {world.time.strftime('%Y-%m-%d')}")
    print(f"Количество жителей: {len(world.inhabitants)}")
    print(f"Текущая погода: {world.config.current_weather}")
    print("\nСимуляция запускается... (Ctrl+C для остановки)")
    
    try:
        day_count = 0
        while True:
            world.simulate_day()
            day_count += 1
            
            # Автосохранение каждые 5 дней
            if day_count % 5 == 0:
                world.save_world(save_file)
                print("\n===== СВОДКА МИРА =====")
                print(f"Прошло дней: {day_count}")
                print(f"Текущая дата: {world.time.strftime('%Y-%m-%d')}")
                print(f"Жителей: {len(world.inhabitants)}")
                print("Последние события:")
                for event in world.events_log[-3:]:
                    print(f" - {event}")
                print("========================")
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        save = input("\nСимуляция остановлена. Сохранить мир? (y/n): ").lower()
        if save == 'y':
            world.save_world(save_file)
        print("\n===== ФИНАЛЬНОЕ СОСТОЯНИЕ =====")
        for human in world.inhabitants:
            print(f"\n{human.name}:")
            print(f"Последние воспоминания:")
            for memory in human.memories[-3:]:
                print(f" - {memory['time']}: {memory['event']}")
        print("\nДо новых встреч в Цифровой Вечности! 👋")