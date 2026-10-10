// Public interactive showcase: synthetic data only; no real bridge or network APIs.
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';
import 'antd/dist/reset.css';

const success = (data: unknown = null) => Promise.resolve({ status: 'success' as const, data });
const disabled = () => Promise.resolve({ status: 'error' as const, message: '这是交互演示，不验证账号、不导出文件、不发送通知。' });
const term = { semester_id: '2026-2027-1', semester_name: '2026-2027-1' };
const grades = () => success({ current_term: term, selected_semester: term, semester_list: [term], grades: [] });
const config = { username: 'DEMO2026', has_password: true, calendar_alarm_minutes: 15,
  time_slots: { '1-2': ['08:30', '10:05'], '3-4': ['10:25', '12:00'], '5-6': ['14:30', '16:05'] } };
const preview = { currentWeek: 6, semesterName: term.semester_name, weekOneMonday: '2026-08-31', scheduleStatus: 'active', source: 'online', availableWeeks: [2, 3, 4, 5, 6, 7],
  courses: [['演示 · 计算机网络', 1, 1, 2], ['演示 · 操作系统', 3, 3, 4], ['演示 · 机器学习', 5, 5, 6]].map(([courseName, weekday, startNode, endNode]) => ({
    courseName, weekday, startNode, endNode, xqmc: `星期${'一二三四五六日'[Number(weekday) - 1]}`, classTime: `${startNode}-${endNode}`,
    classWeekDetails: '2,3,4,5,6,7', classWeek: '2-7周', location: '演示教室 A101', teacherName: '演示教师',
  })) };
// The showcase deliberately does not expose the native desktop bridge.
window.pywebview = { api: {
  get_config: () => success(config), get_preview_courses: () => success(preview),
  get_grade_semesters: grades, get_grades: grades, refresh_grades: grades,
  save_config: disabled, login_test: disabled, export_calendar_ics: disabled,
  check_update: disabled, download_update: disabled, open_export_folder: disabled,
  open_cloud_portal: () => { window.open('/cloud.html', '_blank', 'noopener'); return success(); },
  open_calendar_guide: () => { window.open('/calendar.html', '_blank', 'noopener'); return success(); },
} } as unknown as Window['pywebview'];
ReactDOM.createRoot(document.getElementById('root')!).render(<App />);
