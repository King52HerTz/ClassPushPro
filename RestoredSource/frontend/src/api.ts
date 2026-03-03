import type { ApiResponse, AppConfig, ConfigInput, PreviewCoursesData, SystemStatusData } from './types';

// 假设 pywebview 会注入 window.pywebview.api
declare global {
    interface Window {
        pywebview: {
            api: {
                get_config: () => Promise<ApiResponse<AppConfig>>;
                save_config: (data: ConfigInput) => Promise<ApiResponse<null>>;
                login_test: (username: string, password: string) => Promise<ApiResponse<Record<string, unknown>>>;
                get_preview_courses: () => Promise<ApiResponse<PreviewCoursesData>>;
                manual_push: () => Promise<ApiResponse<null>>;
                ignore_missed_push: (dateStr: string) => Promise<ApiResponse<null>>;
                set_autostart: (enable: boolean) => Promise<ApiResponse<null>>;
                get_system_status: () => Promise<ApiResponse<SystemStatusData>>;
                toggle_scheduler: (enable: boolean) => Promise<ApiResponse<null>>;
                check_today_pushed: () => Promise<ApiResponse<{ pushed: boolean; last_time?: string }>>;
            }
        }
    }
}

export const api = {
    checkTodayPushed: async (): Promise<ApiResponse<{ pushed: boolean; last_time?: string }>> => {
        if (window.pywebview?.api?.check_today_pushed) {
            return await window.pywebview.api.check_today_pushed();
        }
        return { status: 'error', message: 'API未就绪' };
    },
    getConfig: async (): Promise<ApiResponse<AppConfig>> => {
        if (window.pywebview?.api?.get_config) {
            return await window.pywebview.api.get_config();
        }
        return { status: 'error', message: 'API未就绪' };
    },
    saveConfig: async (data: ConfigInput): Promise<ApiResponse<null>> => {
        if (window.pywebview?.api?.save_config) {
            return await window.pywebview.api.save_config(data);
        }
        return { status: 'error', message: 'API未就绪' };
    },
    loginTest: async (u: string, p: string): Promise<ApiResponse<Record<string, unknown>>> => {
        if (window.pywebview?.api?.login_test) {
            return await window.pywebview.api.login_test(u, p);
        }
        return { status: 'error', message: 'API未就绪' };
    },
    getPreviewCourses: async (): Promise<ApiResponse<PreviewCoursesData>> => {
        if (window.pywebview?.api?.get_preview_courses) {
            return await window.pywebview.api.get_preview_courses();
        }
        return { status: 'error', message: 'API未就绪' };
    },
    manualPush: async (force = true): Promise<ApiResponse<null>> => {
        if (window.pywebview?.api?.manual_push) {
            // @ts-ignore
            return await window.pywebview.api.manual_push(force);
        }
        return { status: 'error', message: 'API未就绪' };
    },
    ignoreMissedPush: async (dateStr: string): Promise<ApiResponse<null>> => {
        if (window.pywebview?.api?.ignore_missed_push) {
            return await window.pywebview.api.ignore_missed_push(dateStr);
        }
        return { status: 'error', message: 'API未就绪' };
    },
    setAutostart: async (enable: boolean): Promise<ApiResponse<null>> => {
        if (window.pywebview?.api?.set_autostart) {
            return await window.pywebview.api.set_autostart(enable);
        }
        return { status: 'error', message: 'API未就绪' };
    },
    getSystemStatus: async (): Promise<ApiResponse<SystemStatusData>> => {
        if (window.pywebview?.api?.get_system_status) {
            return await window.pywebview.api.get_system_status();
        }
        return { status: 'error', message: 'API未就绪' };
    },
    toggleScheduler: async (enable: boolean): Promise<ApiResponse<null>> => {
        if (window.pywebview?.api?.toggle_scheduler) {
            return await window.pywebview.api.toggle_scheduler(enable);
        }
        return { status: 'error', message: 'API未就绪' };
    }
};
