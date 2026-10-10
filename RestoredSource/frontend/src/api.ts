import type { ApiResponse, AppConfig, CalendarExportData, ConfigInput, GradeQueryData, PreviewCoursesData, UpdateDownloadData } from './types';

interface Bridge {
  get_config: () => Promise<ApiResponse<AppConfig>>;
  save_config: (data: ConfigInput) => Promise<ApiResponse<null>>;
  login_test: (username: string, password: string) => Promise<ApiResponse<Record<string, unknown>>>;
  get_preview_courses: () => Promise<ApiResponse<PreviewCoursesData>>;
  get_grade_semesters: () => Promise<ApiResponse<GradeQueryData>>;
  get_grades: (id?: string) => Promise<ApiResponse<GradeQueryData>>;
  refresh_grades: (id?: string) => Promise<ApiResponse<GradeQueryData>>;
  export_calendar_ics: (scope?: string) => Promise<ApiResponse<CalendarExportData>>;
  check_update: () => Promise<ApiResponse<Record<string, string>>>;
  download_update: () => Promise<ApiResponse<UpdateDownloadData>>;
  open_cloud_portal: () => Promise<ApiResponse>;
  open_calendar_guide: () => Promise<ApiResponse>;
  open_export_folder: () => Promise<ApiResponse>;
}
declare global { interface Window { pywebview: { api: Bridge }; } }

function call<K extends keyof Bridge>(method: K, ...args: Parameters<Bridge[K]>): ReturnType<Bridge[K]> {
  const fn = window.pywebview?.api?.[method];
  if (!fn) return Promise.resolve({ status: 'error', message: '本机服务尚未就绪，请重新打开软件' }) as ReturnType<Bridge[K]>;
  return (fn as (...values: unknown[]) => unknown)(...args) as ReturnType<Bridge[K]>;
}
export const api = {
  getConfig: () => call('get_config'),
  saveConfig: (data: ConfigInput) => call('save_config', data),
  loginTest: (username: string, password: string) => call('login_test', username, password),
  getPreviewCourses: () => call('get_preview_courses'),
  getGradeSemesters: () => call('get_grade_semesters'),
  getGrades: (id?: string) => call('get_grades', id),
  refreshGrades: (id?: string) => call('refresh_grades', id),
  exportCalendarIcs: (scope: 'current_week' | 'next_7_days' | 'term' = 'term') => call('export_calendar_ics', scope),
  checkUpdate: () => call('check_update'),
  downloadUpdate: () => call('download_update'),
  openCloudPortal: () => call('open_cloud_portal'),
  openCalendarGuide: () => call('open_calendar_guide'),
  openExportFolder: () => call('open_export_folder'),
};
