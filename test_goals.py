"""Behavioral checks for several-day stories, without a network or user save writes."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from world import create_new_world, ImmortalityWorld, DeepSeekAI


class GoalTests(unittest.TestCase):
    def setUp(self):
        self.w = create_new_world()
        self.w.ai = DeepSeekAI('')
        self.w.rng.seed(4)
        self.alex, self.olga, self.dmitry = self.w.inhabitants

    def test_project_takes_several_days_and_finishes_autonomously(self):
        for _ in range(48):
            self.w.step()
        self.assertEqual(self.alex.goal['state'], 'active')
        self.assertGreater(self.alex.goal['progress'], 0)
        self.assertLessEqual(self.alex.goal['progress'], 9)
        for _ in range(96):
            self.w.step()
        goals = self.alex.goal_history + [self.alex.goal]
        completed = [g for g in goals if g['kind'] == 'project' and g['state'] == 'completed']
        self.assertTrue(completed)
        started = datetime.fromisoformat(completed[0]['started'])
        finished = datetime.fromisoformat(completed[0]['finished'])
        self.assertGreaterEqual(finished - started, timedelta(days=3))

    def test_refusal_remembered_and_another_helper_chosen_after_save(self):
        self.alex.goal.update(daily_work=2, daily_date=self.w.time.date().isoformat())
        # Equal preferences make insertion order select Alex, whose own project is busy.
        self.olga.memories.clear()
        self.w.request_help(self.olga)
        self.assertFalse(self.olga.goal['supported'])
        self.assertEqual(self.olga.relationship_history['Алексей'][-1]['cause'], 'Отказ')
        self.assertLess(self.olga.affinity('partner', 'Алексей'), 0)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'world.json'
            self.w.save_world(path)
            w = ImmortalityWorld.load_world(path)
        w.time += timedelta(days=1)
        olga = w.inhabitants[1]
        w.request_help(olga)
        self.assertTrue(olga.goal['supported'])
        self.assertEqual(olga.relationship_history['Дмитрий'][-1]['cause'], 'Помощь')
        self.assertEqual(len(olga.relationship_history['Алексей']), 1)

    def test_quarrel_and_reconciliation_have_conditions_and_cooldown(self):
        self.w.relationship_event(self.alex, self.olga, 'Отказ', -.12, 'Ольга нуждается в отдыхе')
        self.alex.relationships['Дмитрий'] = -1
        self.w.time += timedelta(hours=9)
        self.olga.needs['energy'] = .3
        self.w.social_interaction(self.alex)
        self.assertEqual(self.alex.relationship_history['Ольга'][-1]['cause'], 'Ссора')
        before = self.alex.relationships['Ольга']
        self.w.social_interaction(self.alex)
        self.assertEqual(before, self.alex.relationships['Ольга'])
        self.w.time += timedelta(hours=9)
        self.olga.needs['energy'] = .8
        self.w.social_interaction(self.alex)
        self.assertEqual(self.alex.relationship_history['Ольга'][-1]['cause'], 'Примирение')
        self.assertGreater(self.alex.relationships['Ольга'], before)

    def test_friendship_progress_once_per_day(self):
        for _ in range(5):
            self.w.friendship_progress(self.dmitry, self.olga)
        self.assertEqual(self.dmitry.goal['progress'], 0)
        self.dmitry.relationships['Ольга'] = .2
        for _ in range(5):
            self.w.friendship_progress(self.dmitry, self.olga)
        self.assertEqual(self.dmitry.goal['progress'], 1)
        for _ in range(2):
            self.w.time += timedelta(days=1)
            self.w.friendship_progress(self.dmitry, self.olga)
        self.assertEqual(self.dmitry.goal['state'], 'completed')

    def test_failure_is_remembered_and_reduces_next_scope(self):
        self.w.time += timedelta(days=7)
        self.w.maintain_goal(self.alex)
        self.assertEqual(self.alex.goal['state'], 'failed')
        self.assertTrue(any('срок истёк' in m['event'] for m in self.alex.memories))
        self.w.time += timedelta(days=1)
        self.w.maintain_goal(self.alex)
        self.assertEqual(self.alex.goal['kind'], 'project')
        self.assertLess(self.alex.goal['target'], 12)
        self.assertEqual(self.alex.goal_history[-1]['state'], 'failed')

    def test_single_resident_exhibition_can_finish(self):
        w = ImmortalityWorld(seed=4)
        w.ai = DeepSeekAI('')
        h = w.add_inhabitant('Художник', 30, 'художник')
        for _ in range(24 * 7):
            w.step()
        self.assertTrue(any(g['kind'] == 'exhibition' and g['state'] == 'completed'
                            for g in h.goal_history + [h.goal]))

    def test_legacy_v2_and_v3_roundtrip(self):
        for _ in range(80):
            self.w.step()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'world.json'
            self.w.save_world(path)
            self.assertEqual(self.w.to_dict(), ImmortalityWorld.load_world(path).to_dict())
            data = self.w.to_dict()
            data['version'] = 2
            for item in data['inhabitants']:
                for key in ['goal', 'goal_history', 'relationship_history']:
                    del item[key]
            path.write_text(json.dumps(data), encoding='utf-8')
            w = ImmortalityWorld.load_world(path)
            self.assertTrue(all(h.goal['state'] == 'active' for h in w.inhabitants))
            self.assertEqual(w.time, self.w.time)

    def test_causal_records_and_event_bounds(self):
        for _ in range(24 * 20):
            self.w.step()
        allowed = {'Помощь', 'Отказ', 'Ссора', 'Примирение', 'Тёплая беседа'}
        for h in self.w.inhabitants:
            for records in h.relationship_history.values():
                self.assertLessEqual(len(records), 12)
                self.assertTrue(all(r['cause'] in allowed and r['detail'] for r in records))
            self.assertLessEqual(len(h.goal_history), 5)
        self.assertLessEqual(len(self.w.events_log), 100)
        # No routine hourly action messages flood the significant-event feed.
        self.assertFalse(any('Ест горячий обед.' in event for event in self.w.events_log))


if __name__ == '__main__':
    unittest.main()
