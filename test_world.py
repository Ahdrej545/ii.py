import unittest, tempfile
from pathlib import Path
from datetime import timedelta
from unittest.mock import patch
from world import create_new_world, ImmortalityWorld, DeepSeekAI

class Tests(unittest.TestCase):
    def setUp(self):
        self.w = create_new_world()
        self.w.ai = DeepSeekAI('')
        self.h = self.w.inhabitants[0]
    def test_food_sleep(self):
        self.h.needs.update(hunger=.05, energy=.7)
        self.w.act(self.h)
        self.assertGreater(self.h.needs['hunger'], .6)
        self.h.needs.update(hunger=.7, energy=.05)
        self.w.act(self.h)
        self.assertGreater(self.h.needs['energy'], .6)
    def test_time(self):
        t = self.w.time
        self.w.step()
        self.assertEqual(self.w.time-t, timedelta(hours=1))
        self.w.simulate_day()
        self.assertEqual(self.w.time-t, timedelta(hours=25))
    def test_memory(self):
        self.h.memories.clear()
        self.w.act(self.h)
        self.assertEqual(self.h.location, 'Офис')
        self.h.add_memory('Хороший день', 'Парк', valence=.9)
        self.w.act(self.h)
        self.assertEqual(self.h.location, 'Парк')
        self.h.add_memory('Помог', partner='Дмитрий', valence=.9)
        self.assertEqual(self.w.choose_partner(self.h).name, 'Дмитрий')
    def test_dialog_context(self):
        other = self.w.choose_partner(self.h)
        other.add_memory('Уникальная память собеседника')
        with patch.object(self.w.ai, 'generate_response', return_value='Привет') as call:
            self.w.social_interaction(self.h)
        self.assertIn('Уникальная память собеседника', call.call_args.args[0])
        self.assertIn('идея нового исследования', call.call_args.args[0])
    def test_new_relationships(self):
        h = self.w.add_inhabitant('Новый', 30, 'ученый')
        for other in self.w.inhabitants[:-1]:
            self.assertIn(h.name, other.relationships)
            self.assertIn(other.name, h.relationships)
    def test_saves(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'test.json'
            self.w.step()
            self.w.save_world(path)
            self.assertEqual(self.w.to_dict(), ImmortalityWorld.load_world(path).to_dict())
        path = Path(__file__).with_name('digital_immortality_save.json')
        before = path.read_bytes()
        w = ImmortalityWorld.load_world(path)
        self.assertEqual(len(w.inhabitants), 5)
        w.ai = DeepSeekAI('')
        w.step()
        self.assertTrue(all(h.needs['hunger'] > .3 for h in w.inhabitants))
        self.assertEqual(path.read_bytes(), before)
    def test_api_failure(self):
        ai = DeepSeekAI('test')
        with patch('urllib.request.urlopen', side_effect=OSError()):
            self.assertEqual(ai.generate_response('context', 'Локально'), 'Локально')
        self.assertTrue(ai.last_error)
        with patch('urllib.request.urlopen') as request:
            self.assertEqual(DeepSeekAI('').generate_response('x', 'demo'), 'demo')
            request.assert_not_called()
    def test_long_run(self):
        for _ in range(500): self.w.step()
        for h in self.w.inhabitants:
            self.assertTrue(all(0 <= n <= 1 for n in h.needs.values()))
            self.assertLessEqual(len(h.memories), 50)
        self.assertLessEqual(len(self.w.events_log), 100)

if __name__ == '__main__': unittest.main()
