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
  weather_enabled?: boolean;
  weather_city?: string;
  grade_push_enabled?: boolean;
  grade_check_interval_minutes?: number;
  grade_check_start_time?: string;
  grade_check_end_time?: string;
  grade_push_initialized?: boolean;
  semester_start_date?: string;
  time_slots?: Record<string, [string, string]> | null;
  calendar_alarm_minutes?: number;
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
  scheduleStatus?: 'active' | 'vacation' | 'unpublished' | 'unknown';
  isTeachingWeek?: boolean;
  semesterId?: string;
  semesterName?: string;
  weekOneMonday?: string;
  availableWeeks?: number[];
  scheduleMessage?: string;
}

export interface CalendarExportData {
  file_path: string;
  file_name: string;
  course_count: number;
  export_scope?: 'current_week' | 'next_7_days' | 'term';
  export_scope_label?: string;
}

export interface SystemStatusData {
  autostart?: boolean;
  scheduler_active: boolean;
  grade_scheduler_active?: boolean;
}

export interface GradeSemester {
  semester_id: string;
  semester_name: string;
}

export interface GradeItem {
  grade_id: string;
  semester_id: string;
  semester_name: string;
  course_name: string;
  score: string;
  credit: string;
  gpa: string;
  exam_name: string;
  examination_nature: string;
  course_nature: string;
  curriculum_attributes: string;
  course_code: string;
  pass_status: string;
  publish_time?: string;
  snapshot_hash?: string;
}

export interface GradeStudentInfo {
  student_name?: string;
  student_no?: string;
  class_name?: string;
  academy_name?: string;
}

export interface GradeQueryData {
  current_term: GradeSemester;
  semester_list: GradeSemester[];
  selected_semester?: GradeSemester;
  student_info?: GradeStudentInfo;
  summary?: Record<string, string>;
  grades: GradeItem[];
  source?: 'online' | 'offline';
  update_time_str?: string;
}

export interface GradeCheckData {
  current_term?: GradeSemester;
  checked_semester?: GradeSemester;
  new_items: GradeItem[];
  updated_items: Array<{
    before: GradeItem;
    after: GradeItem;
  }>;
  push_result?: {
    attempted: boolean;
    success: boolean;
    message: string;
  };
}

export interface LoginFormValues {
  username: string;
  password: string;
  uid: string;
}

export interface SettingsFormValues {
  push_time: import('dayjs').Dayjs;
  auto_start: boolean;
  weather_enabled?: boolean;
  weather_city?: string;
  grade_push_enabled?: boolean;
  grade_check_interval_minutes?: number;
  grade_check_start_time?: import('dayjs').Dayjs;
  grade_check_end_time?: import('dayjs').Dayjs;
  semester_start_date?: import('dayjs').Dayjs;
  calendar_alarm_minutes?: number;
}
