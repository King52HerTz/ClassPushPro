import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from push_content import generate_push_content


class PushContentTest(unittest.TestCase):
    def test_original_copy_inline_colors_and_school_times(self):
        course = {'courseName': '合成课程', 'location': '演示教室',
                  'teacherName': '演示老师', 'classTime': '5-6节'}
        content, title = generate_push_content([course], '10月12日', '星期一', day_label='明天')
        self.assertEqual(title, '小主，明天有 1 节课，记得按时上课哟 🍬')
        for text in ['#ff7875', '#0984e3', '#e17055', '📖', '📍', '⏰', '🧑‍🏫',
                     '14:00-15:35', '第5-6节', '10月12日 星期一', '演示教室', '演示老师']:
            self.assertIn(text, content)
        self.assertNotIn('<style>', content)
        self.assertNotIn('border-left:4px solid #1677ff', content)

    def test_empty_day_keeps_original_balloon_and_correct_day(self):
        for day in ['今天', '明天']:
            content, title = generate_push_content([], '10月12日', '星期一', day_label=day)
            self.assertEqual(title, f'小主，{day}全天没课，好好休息吧 🛌')
            self.assertIn('🎈', content)
            self.assertIn('自由时光，做点喜欢的事吧~', content)

    def test_fields_are_escaped_and_unknown_period_not_guessed(self):
        content, _ = generate_push_content([{'courseName': '<script>', 'location': '<b>',
                                             'teacherName': 'A&B', 'classTime': '待定'}],
                                           '<date>', '<weekday>')
        for text in ['&lt;script&gt;', '&lt;b&gt;', 'A&amp;B', '&lt;date&gt;', '&lt;weekday&gt;', '待定']:
            self.assertIn(text, content)
        self.assertNotIn('<script>', content)
        self.assertNotIn('08:30', content)

    def test_late_class_time(self):
        content, _ = generate_push_content([{'classTime': '11-12'}], '10月12日', '星期一')
        self.assertIn('20:45-22:20', content)


if __name__ == '__main__':
    unittest.main()
