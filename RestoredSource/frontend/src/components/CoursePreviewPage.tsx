import React, { useEffect, useState, useMemo } from 'react';
import { Spin, message, Select, Radio, Button, Space, Card, Row, Col, Modal, Descriptions, Alert } from 'antd';
import { api } from '../api';
import { ReloadOutlined, AppstoreOutlined, TableOutlined, EnvironmentOutlined, UserOutlined, ClockCircleOutlined, WifiOutlined, CalendarOutlined, QuestionCircleOutlined } from '@ant-design/icons';
import WeekTimetable from './WeekTimetable'; // 刚才创建的新组件
import dayjs from 'dayjs';
import 'dayjs/locale/zh-cn';
import type { Course, PreviewCoursesData } from '../types';

dayjs.locale('zh-cn');

const COURSE_CACHE_KEY = 'course_data_cache_v2';
const COURSE_SIGNATURE_KEY = 'course_data_signature_v2';
const EMPTY_COURSE_CACHE_MESSAGE = '当前暂无本地课表缓存，请联网后首次加载';

// 仿截图配色方案 (与 WeekTimetable 保持一致)
const COURSE_THEMES = [
    { bg: '#E6FFFB', border: '#5CDBD3' }, // 浅青
    { bg: '#FFF7E6', border: '#FFC069' }, // 浅橙
    { bg: '#E6F7FF', border: '#69C0FF' }, // 浅蓝
    { bg: '#FFF0F6', border: '#FF85C0' }, // 浅粉
    { bg: '#F9F0FF', border: '#B37FEB' }, // 浅紫
    { bg: '#FCFFE6', border: '#D3F261' }, // 浅柠檬
    { bg: '#FFF1B8', border: '#FFEC3D' }, // 浅黄
    { bg: '#F0F5FF', border: '#85A5FF' }, // 浅靛蓝
    { bg: '#FFF2E8', border: '#FFBB96' }, // 浅橘
    { bg: '#F6FFED', border: '#95DE64' }, // 浅绿
];

const { Option } = Select;
const EXPORT_SCOPE_OPTIONS = [
    {
        value: 'current_week' as const,
        title: '先试本周',
        description: '适合第一次测试导入，范围最小，安卓导错后也更容易清理。'
    },
    {
        value: 'next_7_days' as const,
        title: '未来 7 天',
        description: '适合测试最近几天的提醒和时间是否正常。'
    },
    {
        value: 'term' as const,
        title: '全学期',
        description: '确认没问题后再导出完整课表，避免一次导错太多。'
    }
];

const buildCourseCacheMessage = (timeStr: string) => `当前网络不可用，正在显示${timeStr || '较早前'}的本地课表缓存`;

const CoursePreviewPage: React.FC = () => {
    const [loading, setLoading] = useState(false);
    const [courses, setCourses] = useState<Course[]>([]);
    const [currentWeek, setCurrentWeek] = useState('1'); // 后端返回的当前周
    const [selectedWeek, setSelectedWeek] = useState('1'); // 用户选择查看的周
    const [viewMode, setViewMode] = useState<'card' | 'table'>('table'); // 'card' 是列表卡片模式, 'table' 是网格模式
    const [detailModalVisible, setDetailModalVisible] = useState(false);
    const [guideVisible, setGuideVisible] = useState(false);
    const [exportModalVisible, setExportModalVisible] = useState(false);
    const [selectedCourse, setSelectedCourse] = useState<Course | null>(null);
    const [offlineInfo, setOfflineInfo] = useState<{ isOffline: boolean; timeStr: string; cacheMissing: boolean }>({
        isOffline: false,
        timeStr: '',
        cacheMissing: false,
    });
    const [exporting, setExporting] = useState(false);
    const [exportScope, setExportScope] = useState<'current_week' | 'next_7_days' | 'term'>('current_week');
    const [localCacheTimeStr, setLocalCacheTimeStr] = useState('');

    const formatRelativeTime = (timestamp: number) => {
        if (!Number.isFinite(timestamp) || timestamp <= 0) {
            return '';
        }
        const seconds = Math.max(Math.floor((Date.now() - timestamp) / 1000), 0);
        if (seconds < 60) return '刚刚';
        if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟前`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}小时前`;
        return `${Math.floor(seconds / 86400)}天前`;
    };

    const readCourseCache = () => {
        try {
            const raw = localStorage.getItem(COURSE_CACHE_KEY);
            if (!raw) return null;
            const parsed = JSON.parse(raw) as { savedAt?: number; data?: PreviewCoursesData };
            if (!parsed?.data) return null;
            return parsed;
        } catch (e) {
            return null;
        }
    };

    const restoreCoursesFromBrowserCache = () => {
        const cached = readCourseCache();
        if (!cached?.data) {
            return false;
        }
        const cachedData = cached.data;
        const cachedCourses = Array.isArray(cachedData.courses) ? cachedData.courses : [];
        const cachedWeek = String(cachedData.currentWeek || '1');
        const timeStr = cachedData.update_time_str || formatRelativeTime(Number(cached.savedAt || 0)) || '较早前';

        setCourses(cachedCourses);
        setCurrentWeek(cachedWeek);
        if (selectedWeek === '1') {
            setSelectedWeek(cachedWeek === '1' ? '2' : cachedWeek);
        }
        setLocalCacheTimeStr(timeStr);
        setOfflineInfo({ isOffline: true, timeStr, cacheMissing: false });
        message.warning({ content: buildCourseCacheMessage(timeStr), key: 'course_error' });
        return true;
    };

    const keepCurrentCoursesAsOffline = () => {
        if (courses.length === 0) {
            return false;
        }
        const timeStr = offlineInfo.timeStr || localCacheTimeStr || '较早前';
        setOfflineInfo({ isOffline: true, timeStr, cacheMissing: false });
        message.warning({ content: buildCourseCacheMessage(timeStr), key: 'course_error' });
        return true;
    };

    // 计算当前选中周的周一日期
    // 假设学期开始时间是基于当前周倒推出来的
    // 算法：CurrentDate - (CurrentWeek - 1) weeks - (CurrentDayOfWeek - 1) days
    // 但为了确保准确，我们假设当前周的周一是基准
    // 注意：教务系统返回的 currentWeek 是基于开学日期的
    // 我们用 dayjs 来处理日期
    const selectedWeekMonday = useMemo(() => {
        const today = dayjs();
        const currentWeekNum = parseInt(currentWeek) || 1;
        const selectedWeekNum = parseInt(selectedWeek) || 1;
        
        // 计算当前周的周一
        // dayjs().day(1) 返回本周一 (注意：如果今天是周日(0)，day(1)会变成下周一，需特殊处理)
        // ISO周：1=周一, 7=周日
        const currentMonday = today.subtract(today.day() === 0 ? 6 : today.day() - 1, 'day');
        
        // 计算目标周的周一
        // 目标周一 = 当前周一 + (目标周 - 当前周) * 7天
        return currentMonday.add((selectedWeekNum - currentWeekNum) * 7, 'day');
    }, [currentWeek, selectedWeek]);

    // 映射节次到具体时间
    const getTimeRange = (classTime: string) => {
        if (classTime.includes('1-2')) return '08:30 - 10:05 (1-2节)';
        if (classTime.includes('3-4')) return '10:25 - 12:00 (3-4节)';
        if (classTime.includes('5-6')) return '14:00 - 15:35 (5-6节)';
        if (classTime.includes('7-8')) return '15:55 - 17:30 (7-8节)';
        if (classTime.includes('9-10')) return '19:00 - 20:35 (9-10节)';
        return classTime;
    };

    // 加载数据
    const fetchData = async (keepSelection = false, isManual = false) => {
        if (isManual || courses.length === 0) setLoading(true);
        try {
            const res = await api.getPreviewCourses();
            if (res.status === 'success' && res.data) {
                const newCourses = res.data.courses;
                const newCurrentWeek = String(res.data.currentWeek);
                
                // 处理离线状态
                const isOffline = res.data.source === 'offline';
                const timeStr = res.data.update_time_str || '';
                setOfflineInfo({ isOffline, timeStr, cacheMissing: false });

                if (isOffline) {
                    message.warning({ 
                        content: buildCourseCacheMessage(timeStr), 
                        key: 'offline_warning',
                        duration: 3
                    });
                }
                
                // 生成数据签名 (用于比对是否更新)
                const newSignature = JSON.stringify({
                    courses: newCourses,
                    week: newCurrentWeek
                });
                const lastSignature = sessionStorage.getItem(COURSE_SIGNATURE_KEY) || localStorage.getItem(COURSE_SIGNATURE_KEY);
                const isDataChanged = newSignature !== lastSignature;

                if (isDataChanged || isManual) {
                    setCourses(newCourses);
                    setCurrentWeek(newCurrentWeek);
                    
                    // 更新缓存
                    sessionStorage.setItem(COURSE_SIGNATURE_KEY, newSignature);
                    localStorage.setItem(COURSE_SIGNATURE_KEY, newSignature);
                    const cachePayload = JSON.stringify({ savedAt: Date.now(), data: res.data });
                    sessionStorage.setItem(COURSE_CACHE_KEY, cachePayload);
                    localStorage.setItem(COURSE_CACHE_KEY, cachePayload);
                    setLocalCacheTimeStr('刚刚');
                    
                    // 如果不保持选择（即初始化时且无缓存），设置默认周次
                    if (!keepSelection) {
                        if (newCurrentWeek === '1') {
                            setSelectedWeek('2');
                        } else {
                            setSelectedWeek(newCurrentWeek);
                        }
                    }
                    
                    // 仅当数据确实变化时提示
                    if (!isOffline) {
                        message.success({ content: isManual ? '刷新成功' : '课表数据已更新', key: 'course_update' });
                    }
                } else {
                    // 数据未变
                    if (isManual && !isOffline) {
                        message.info({ content: '当前已是最新数据', key: 'course_update' });
                    }
                }
            } else {
                if (keepCurrentCoursesAsOffline() || restoreCoursesFromBrowserCache()) {
                    return;
                }
                setOfflineInfo({ isOffline: true, timeStr: '', cacheMissing: true });
                message.info({ content: res.message || EMPTY_COURSE_CACHE_MESSAGE, key: 'course_error' });
            }
        } catch (e) {
            if (keepCurrentCoursesAsOffline() || restoreCoursesFromBrowserCache()) {
                return;
            }
            setOfflineInfo({ isOffline: true, timeStr: '', cacheMissing: true });
            message.info({ content: EMPTY_COURSE_CACHE_MESSAGE, key: 'course_error' });
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        // 1. 尝试从缓存加载 (实现秒开)
        const cachedDataStr = sessionStorage.getItem(COURSE_CACHE_KEY);
        let hasCache = false;
        
        if (cachedDataStr) {
            try {
                const parsed = JSON.parse(cachedDataStr) as { savedAt?: number; data?: PreviewCoursesData };
                const cachedData = parsed?.data as PreviewCoursesData;
                setCourses(Array.isArray(cachedData.courses) ? cachedData.courses : []);
                const cachedWeek = String(cachedData.currentWeek);
                setCurrentWeek(cachedWeek);
                setLocalCacheTimeStr(formatRelativeTime(Number(parsed?.savedAt || 0)));
                
                // 恢复上次的周次选择，或者默认
                if (cachedWeek === '1') {
                    setSelectedWeek('2');
                } else {
                    setSelectedWeek(cachedWeek);
                }
                hasCache = true;
                // message.success({ content: '已加载本地课表缓存', key: 'course_cache', duration: 1 });
            } catch (e) {
                console.error('Cache parse error', e);
            }
        }

        if (!hasCache) {
            const localCache = readCourseCache();
            if (localCache?.data) {
                const cachedData = localCache.data;
                setCourses(Array.isArray(cachedData.courses) ? cachedData.courses : []);
                const cachedWeek = String(cachedData.currentWeek);
                setCurrentWeek(cachedWeek);
                setLocalCacheTimeStr(formatRelativeTime(Number(localCache.savedAt || 0)));
                if (cachedWeek === '1') {
                    setSelectedWeek('2');
                } else {
                    setSelectedWeek(cachedWeek);
                }
                hasCache = true;
            }
        }

        // 2. 发起网络请求 (静默更新或初始化加载)
        // 如果有缓存，则保持当前选择 (keepSelection=true)，且是非手动 (isManual=false)
        // 如果无缓存，则不保持选择 (让 fetchData 设置默认值)
        fetchData(hasCache, false);
    }, []);

    // 过滤当前选中周的课程
    const filteredCourses = useMemo(() => {
        return courses.filter(course => {
            if (!course.classWeekDetails) return true;
            const weeks = course.classWeekDetails.split(',');
            return weeks.includes(selectedWeek);
        });
    }, [courses, selectedWeek]);

    // 对过滤后的课程按日期分组 (用于卡片视图)
    const groupedCourses = useMemo(() => {
        const groups: Record<string, Course[]> = {};
        // 按照 weekday 排序: 1-7
        const sorted = [...filteredCourses].sort((a, b) => {
            const wa = a.weekday || 0;
            const wb = b.weekday || 0;
            if (wa !== wb) return wa - wb;
            return (a.startNode || 0) - (b.startNode || 0);
        });

        sorted.forEach(course => {
            // 计算具体日期
            // weekday: 1-7
            const offset = (course.weekday || 1) - 1;
            const courseDate = selectedWeekMonday.add(offset, 'day');
            const dateStr = courseDate.format('YYYY-MM-DD');
            const weekStr = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][courseDate.day()];
            
            const key = `${dateStr} ${weekStr}`;
            if (!groups[key]) groups[key] = [];
            groups[key].push(course);
        });
        return groups;
    }, [filteredCourses, selectedWeekMonday]);

    const handleCourseClick = (course: Course) => {
        setSelectedCourse(course);
        setDetailModalVisible(true);
    };

    const handleExportCalendar = async () => {
        setExporting(true);
        try {
            const res = await api.exportCalendarIcs(exportScope);
            if (res.status === 'success' && res.data) {
                const scopeLabel = res.data.export_scope_label || '所选范围';
                message.success(
                    `${scopeLabel}导出成功，共生成 ${res.data.course_count} 条日历事件，文件已保存到 ${res.data.file_path}。注意：当前导出的是课表快照，后续如果教务系统调课，不会自动同步到已导入的日历。`
                );
                setExportModalVisible(false);
                return;
            }
            message.error(res.message || '导出失败');
        } catch (e) {
            message.error('导出失败，请稍后重试');
        } finally {
            setExporting(false);
        }
    };

    // 渲染卡片视图 (对应截图2)
    const renderCardView = () => {
        if (Object.keys(groupedCourses).length === 0) {
            return <div style={{ padding: 40, textAlign: 'center', color: '#999' }}>本周没有课程</div>;
        }

        return (
            <Row gutter={[16, 16]}>
                {Object.entries(groupedCourses).map(([dateTitle, dayCourses]) => (
                    <Col xs={24} sm={12} md={8} lg={6} key={dateTitle}>
                        <Card 
                            title={dateTitle} 
                            bordered={false} 
                            headStyle={{ borderBottom: 'none', fontWeight: 'bold', fontSize: 16 }}
                            bodyStyle={{ padding: 12, paddingTop: 0 }}
                            style={{ height: '100%', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' }}
                        >
                            {dayCourses.map((course, idx) => {
                                const colorIndex = Math.abs(course.courseName.split('').reduce((a: number, b: string) => a + b.charCodeAt(0), 0)) % COURSE_THEMES.length;
                                const theme = COURSE_THEMES[colorIndex];
                                
                                return (
                                <div 
                                    key={idx} 
                                    onClick={() => handleCourseClick(course)}
                                    style={{ 
                                        backgroundColor: theme.bg, // 使用主题背景色
                                        borderRadius: 8,
                                        padding: 12,
                                        marginBottom: 12,
                                        borderLeft: `4px solid ${theme.border}`, // 使用主题边框色
                                        cursor: 'pointer',
                                        transition: 'all 0.3s'
                                    }}
                                    onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.02)'}
                                    onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
                                >
                                    <div style={{ fontWeight: 'bold', fontSize: 15, marginBottom: 4, color: '#4a4a4a' }}>
                                        {course.courseName}
                                    </div>
                                    <div style={{ fontSize: 13, color: '#666', display: 'flex', alignItems: 'center', gap: 4 }}>
                                        <ClockCircleOutlined /> {course.classTime}
                                    </div>
                                    <div style={{ fontSize: 13, color: '#666', display: 'flex', alignItems: 'center', gap: 4 }}>
                                        <EnvironmentOutlined /> {course.location}
                                    </div>
                                    <div style={{ fontSize: 13, color: '#666', display: 'flex', alignItems: 'center', gap: 4 }}>
                                        <UserOutlined /> {course.teacherName}
                                    </div>
                                </div>
                                );
                            })}
                        </Card>
                    </Col>
                ))}
            </Row>
        );
    };

    return (
        <div style={{ padding: 0 }}>
            {offlineInfo.isOffline && (
                <Alert
                    message={offlineInfo.cacheMissing ? '当前暂无可用课表缓存' : '当前处于离线模式'}
                    description={
                        offlineInfo.cacheMissing
                            ? '本机还没有可用的课表缓存，请先联网成功加载一次课表，之后断网时才可以继续查看。'
                            : `${buildCourseCacheMessage(offlineInfo.timeStr)}。请检查网络后点击“刷新”重试。`
                    }
                    type={offlineInfo.cacheMissing ? 'info' : 'warning'}
                    showIcon
                    icon={<WifiOutlined />}
                    style={{ marginBottom: 16, borderRadius: 8 }}
                    action={
                        <Button size="small" type="text" icon={<ReloadOutlined />} onClick={() => fetchData(true, true)}>
                            重试
                        </Button>
                    }
                />
            )}

            {/* 顶部工具栏 */}
            <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center', 
                marginBottom: 16,
                backgroundColor: '#fff',
                padding: '16px 24px',
                borderRadius: 8,
                boxShadow: '0 1px 2px rgba(0,0,0,0.03)'
            }}>
                <div style={{ fontSize: 18, fontWeight: 'bold' }}>课表预览</div>
                
                <Space>
                    <span>周次</span>
                    <Select 
                        value={selectedWeek} 
                        onChange={setSelectedWeek} 
                        style={{ width: 120 }}
                    >
                        {/* 生成第2周到第19周的选项 */}
                        {Array.from({ length: 18 }).map((_, i) => (
                            <Option key={i + 2} value={String(i + 2)}>第 {i + 2} 周</Option>
                        ))}
                    </Select>
                    <span style={{ color: '#999', fontSize: 12 }}>当前: 第 {selectedWeek} 周</span>
                    
                    <Radio.Group value={viewMode} onChange={e => setViewMode(e.target.value)} buttonStyle="solid">
                        <Radio.Button value="card"><AppstoreOutlined /> 卡片</Radio.Button>
                        <Radio.Button value="table"><TableOutlined /> 课表</Radio.Button>
                    </Radio.Group>
                    
                    <Button icon={<CalendarOutlined />} loading={exporting} onClick={() => setExportModalVisible(true)}>
                        导出到日历
                    </Button>
                    <Button icon={<QuestionCircleOutlined />} onClick={() => setGuideVisible(true)}>
                        查看导入教程
                    </Button>
                    <Button icon={<ReloadOutlined />} onClick={() => fetchData(true, true)}>刷新</Button>
                </Space>
            </div>

            <Spin spinning={loading}>
                {viewMode === 'card' ? renderCardView() : (
                    <div style={{ backgroundColor: '#fff', padding: 24, borderRadius: 8 }}>
                        <WeekTimetable 
                            courses={courses} 
                            currentWeek={parseInt(selectedWeek)} 
                            weekMonday={selectedWeekMonday}
                            onCourseClick={handleCourseClick}
                        />
                    </div>
                )}
            </Spin>

            <Modal
                title="选择导出范围"
                open={exportModalVisible}
                onCancel={() => !exporting && setExportModalVisible(false)}
                onOk={handleExportCalendar}
                confirmLoading={exporting}
                okText="开始导出"
                cancelText="取消"
            >
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <Alert
                        type="info"
                        showIcon
                        message="安卓用户建议先做小范围测试"
                        description="OPPO 等安卓日历导错后，往往不能像订阅日历那样整包删除。建议先导出“本周”或“未来 7 天”，确认时间和提醒都正常后，再导出全学期。"
                        style={{ borderRadius: 12 }}
                    />
                    <Radio.Group
                        value={exportScope}
                        onChange={(e) => setExportScope(e.target.value)}
                        style={{ display: 'flex', flexDirection: 'column', gap: 12 }}
                    >
                        {EXPORT_SCOPE_OPTIONS.map((item) => (
                            <Radio key={item.value} value={item.value} style={{ marginInlineEnd: 0 }}>
                                <div>
                                    <div style={{ fontWeight: 600 }}>{item.title}</div>
                                    <div style={{ color: '#666', fontSize: 13 }}>{item.description}</div>
                                </div>
                            </Radio>
                        ))}
                    </Radio.Group>
                </div>
            </Modal>

            <Modal
                title="课程详情"
                open={detailModalVisible}
                onCancel={() => setDetailModalVisible(false)}
                footer={[
                    <Button key="close" onClick={() => setDetailModalVisible(false)}>
                        关闭
                    </Button>
                ]}
            >
                {selectedCourse && (
                    <Descriptions column={1} bordered>
                        <Descriptions.Item label="课程名称">{selectedCourse.courseName}</Descriptions.Item>
                        <Descriptions.Item label="上课时间">{getTimeRange(selectedCourse.classTime)}</Descriptions.Item>
                        <Descriptions.Item label="上课地点">{selectedCourse.location}</Descriptions.Item>
                        <Descriptions.Item label="任课教师">{selectedCourse.teacherName}</Descriptions.Item>
                        <Descriptions.Item label="周次">{selectedCourse.classWeek}</Descriptions.Item>
                        <Descriptions.Item label="星期">{selectedCourse.xqmc}</Descriptions.Item>
                    </Descriptions>
                )}
            </Modal>

            <Modal
                title="ICS 导入教程"
                open={guideVisible}
                onCancel={() => setGuideVisible(false)}
                footer={[
                    <Button key="close" onClick={() => setGuideVisible(false)}>
                        我知道了
                    </Button>
                ]}
            >
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12, lineHeight: 1.8 }}>
                    <div>1. 先在“设置”页面填写学期第 1 周周一日期、节次时间表和提醒时间。</div>
                    <div>2. 回到本页点击“导出到日历”后，建议先选择“本周”或“未来 7 天”做小范围测试；确认没问题后，再导出“全学期”。</div>
                    <div>3. 电脑端一般可以双击 `.ics` 导入系统日历，手机端通常需要先通过微信、QQ、网盘或数据线把文件传到手机。</div>
                    <div>4. 不同品牌手机、不同日历 App 的导入入口差异很大；如果你找不到入口，建议直接去小红书搜索 `ics 文件导入教程`，再加上你的手机品牌或日历 App 名称一起搜。</div>
                    <div>5. iPhone、安卓系统日历、QQ 邮箱日历、小米日历、华为日历等应用，对 ICS 的支持程度和提醒展示方式也可能不一样；部分日历只支持 `5/10/15/30/60` 这类固定提醒时间。</div>
                    <div>6. ICS 导出的内容只是你导出当下的课表快照，不一定永远是最新的；如果后面教务系统临时调课、换教室或改时间，已经导入到日历里的课表不会自动同步更新。</div>
                    <div>7. 如果学校后续有调课，建议重新刷新课表后再次导出新的 `.ics`，再手动重新导入日历。</div>
                    <div>8. 如果你是安卓手机，误导入整学期后通常很难批量删除，所以一定要先小范围试；如果导入后时间不对，优先检查设置页里的节次时间表是否和学校作息一致。</div>
                    <div>9. 如果想改提醒时间，也需要重新导出并重新导入新的 `.ics`；目前更推荐优先使用 `15 分钟提醒`。</div>
                </div>
            </Modal>
        </div>
    );
};

export default CoursePreviewPage;
