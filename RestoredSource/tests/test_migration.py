import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from migration import retire_local_push


class MigrationTest(unittest.TestCase):
    def test_only_hnit_task_names_are_retired(self):
        tasks = {name: SimpleNamespace(Enabled=True) for name in (
            'ClassPush_HNIT_AutoRun', 'ClassPush_HNIT_GradeCheck')}
        folder = Mock()
        folder.GetTask.side_effect = tasks.__getitem__
        service = Mock()
        service.GetFolder.return_value = folder
        dynamic = SimpleNamespace(Dispatch=Mock(return_value=service))
        with patch.dict(sys.modules, {'win32com.client.dynamic': dynamic}), patch('migration.sys.platform', 'win32'):
            self.assertEqual(retire_local_push(), '')
        self.assertEqual([call.args[0] for call in service.GetFolder.call_args_list], ['\\ClassPush_HNIT', '\\'])
        self.assertEqual(set(call.args[0] for call in folder.DeleteTask.call_args_list), set(tasks))
        self.assertTrue(all(not task.Enabled for task in tasks.values()))

    def test_denied_task_service_returns_safe_warning(self):
        dynamic = SimpleNamespace(Dispatch=Mock(side_effect=PermissionError('FAKE_PRIVATE_DETAIL')))
        with patch.dict(sys.modules, {'win32com.client.dynamic': dynamic}), patch('migration.sys.platform', 'win32'):
            warning = retire_local_push()
        self.assertIn('无法停用', warning)
        self.assertNotIn('FAKE_PRIVATE_DETAIL', warning)


if __name__ == '__main__':
    unittest.main()
