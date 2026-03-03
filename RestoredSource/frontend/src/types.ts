export interface ApiResponse<T = unknown> {
  status: 'success' | 'error';
  message?: string;
  data?: T;
  hint?: string;
  action?: string;
}

export interface AppConfig {
  username: string;
  password: string;
  uid: string;
  app_token: string;
  push_time: string;
  auto_start: boolean;
  last_push_success_time?: string;
  last_ignored_push_date?: string;
  jw_cached_username?: string;
  jw_cached_time?: string;
}

export type ConfigInput = Partial<AppConfig>;

export interface Course {
  xqmc?: string;
  weekday?: number;
  classTime: string;
  startNode?: number;
  endNode?: number;
  courseName: string;
  location: string;
  teacherName: string;
  classWeek?: string;
  classWeekDetails?: string;
}

export interface PreviewCoursesData {
  currentWeek: number | string;
  courses: Course[];
  source?: 'online' | 'offline'; // 数据来源：在线或离线缓存
  update_time_str?: string;      // 缓存更新时间描述 (如 "10分钟前")
}

export interface SystemStatusData {
  autostart?: boolean;
  scheduler_active: boolean;
}

export interface LoginFormValues {
  username: string;
  password: string;
  uid: string;
}

export interface SettingsFormValues {
  push_time: import('dayjs').Dayjs;
  auto_start: boolean;
}
