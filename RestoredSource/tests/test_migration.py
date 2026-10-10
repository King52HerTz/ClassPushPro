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
        self.assertEqual([call.args[0] for call in service.GetFolder.call_args_list], ['\\ClassPush_HNIT', '\\ClassPush', '\\'])
        folder.DeleteTask.assert_not_called()
        self.assertTrue(all(not task.Enabled for task in tasks.values()))

    def test_generic_task_requires_verified_school_and_is_not_deleted(self):
        hnit = SimpleNamespace(Enabled=True)
        other = SimpleNamespace(Enabled=True)
        folder = Mock()
        tasks = {'ClassPush_AutoRun': hnit, 'ClassPush_GradeCheck': other}
        folder.GetTask.side_effect = tasks.__getitem__
        service = Mock()
        service.GetFolder.return_value = folder
        dynamic = SimpleNamespace(Dispatch=Mock(return_value=service))
        with patch.dict(sys.modules, {'win32com.client.dynamic': dynamic}), patch('migration.sys.platform', 'win32'), \
                patch('migration.is_hnit_legacy_task', side_effect=lambda task: task is hnit):
            self.assertIn('无法确认学校', retire_local_push())
        self.assertFalse(hnit.Enabled)
        self.assertTrue(other.Enabled)
        folder.DeleteTask.assert_not_called()

    def test_folder_access_denied_is_not_treated_as_missing(self):
        error = OSError('FAKE_PRIVATE_DETAIL')
        error.hresult = -2147024891
        service = Mock()
        service.GetFolder.side_effect = error
        dynamic = SimpleNamespace(Dispatch=Mock(return_value=service))
        with patch.dict(sys.modules, {'win32com.client.dynamic': dynamic}), patch('migration.sys.platform', 'win32'):
            self.assertIn('管理员', retire_local_push())

    def test_generic_target_identification_does_not_execute_old_code(self):
        import tempfile
        from migration import is_hnit_legacy_task
        with tempfile.TemporaryDirectory() as directory:
            task = SimpleNamespace(Definition=SimpleNamespace(Actions=[SimpleNamespace(Path=str(Path(directory) / 'ClassPush.exe'))]))
            with patch('migration.Path.read_text', return_value='APP_DATA_DIR_NAME = ".ClassPush_HNIT"'):
                self.assertTrue(is_hnit_legacy_task(task))
            with patch('migration.Path.read_text', return_value='APP_DATA_DIR_NAME = ".ClassPush_XTLG"'):
                self.assertFalse(is_hnit_legacy_task(task))

    def test_denied_task_service_returns_safe_warning(self):
        dynamic = SimpleNamespace(Dispatch=Mock(side_effect=PermissionError('FAKE_PRIVATE_DETAIL')))
        with patch.dict(sys.modules, {'win32com.client.dynamic': dynamic}), patch('migration.sys.platform', 'win32'):
            warning = retire_local_push()
        self.assertIn('无法停用', warning)
        self.assertNotIn('FAKE_PRIVATE_DETAIL', warning)


if __name__ == '__main__':
    unittest.main()
