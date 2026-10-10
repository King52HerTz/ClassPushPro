// Local visual preview only. No school requests, credentials, or real messages.
(() => {
  const success = data => Promise.resolve({ status: 'success', data });
  const disabled = () => Promise.resolve({ status: 'error', message: '界面预览不执行下载、导出或真实通知。' });
  let config = { username: '20260001', has_password: true, calendar_alarm_minutes: 15,
    time_slots: { '1-2': ['08:30', '10:05'], '3-4': ['10:25', '12:00'], '5-6': ['14:30', '16:05'], '7-8': ['16:25', '18:00'] } };
  const term = { semester_id: '2026-2027-1', semester_name: '2026-2027-1' };
  const grades = () => success({ current_term: term, selected_semester: term, semester_list: [term], grades: [] });
  const preview = { currentWeek: 6, semesterName: term.semester_name, weekOneMonday: '2026-08-31',
    scheduleStatus: 'active', source: 'online', availableWeeks: Array.from({ length: 17 }, (_, i) => i + 2),
    courses: [
      ['演示 · 计算机网络', 1, 1, 2, '演示教室 A101'],
      ['演示 · 操作系统', 2, 3, 4, '演示教室 B202'],
      ['演示 · 嵌入式系统', 3, 5, 6, '演示实验室 C303'],
      ['演示 · 机器学习', 5, 1, 2, '演示教室 A102'],
    ].map(([courseName, weekday, startNode, endNode, location]) => ({ courseName, weekday,
      xqmc: `星期${'一二三四五六日'[weekday - 1]}`, classTime: `${startNode}-${endNode}`, startNode, endNode,
      classWeekDetails: '2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18', classWeek: '2-18周', location, teacherName: '演示教师' })) };
  const open = window.open.bind(window);
  window.open = (url, ...args) => {
    const target = new URL(url, location.href);
    if (target.hostname === 'classpush.eliauk312.top') return open(target.pathname + target.search + target.hash, ...args);
    return open(url, ...args);
  };
  window.pywebview = { api: {
    get_config: () => success(config),
    save_config: data => { config = { ...config, username: data.username || '', has_password: !!data.password }; return success(null); },
    login_test: () => success({}),
    get_preview_courses: () => success(preview),
    get_grade_semesters: grades, get_grades: grades, refresh_grades: grades,
    open_cloud_portal: () => { open('/cloud.html?preview=account', '_blank'); return success(null); },
    open_calendar_guide: () => { open('/calendar.html', '_blank'); return success(null); },
    open_export_folder: disabled, export_calendar_ics: disabled, download_update: disabled, check_update: disabled,
  } };
})();
