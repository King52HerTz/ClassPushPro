import React, { useEffect, useState, useMemo } from 'react';
import { Spin, message, Select, Radio, Button, Space, Card, Row, Col, Modal, Descriptions, Alert } from 'antd';
import { api } from '../api';
import { ReloadOutlined, AppstoreOutlined, TableOutlined, EnvironmentOutlined, UserOutlined, ClockCircleOutlined, WifiOutlined } from '@ant-design/icons';
import WeekTimetable from './WeekTimetable'; // 刚才创建的新组件
import dayjs from 'dayjs';
import 'dayjs/locale/zh-cn';
import type { Course, PreviewCoursesData } from '../types';

dayjs.locale('zh-cn');

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

const CoursePreviewPage: React.FC = () => {
    const [loading, setLoading] = useState(false);
    const [courses, setCourses] = useState<Course[]>([]);
    const [currentWeek, setCurrentWeek] = useState('1'); // 后端返回的当前周
    const [selectedWeek, setSelectedWeek] = useState('1'); // 用户选择查看的周
    const [viewMode, setViewMode] = useState<'card' | 'table'>('table'); // 'card' 是列表卡片模式, 'table' 是网格模式
    const [detailModalVisible, setDetailModalVisible] = useState(false);
    const [selectedCourse, setSelectedCourse] = useState<Course | null>(null);
    const [offlineInfo, setOfflineInfo] = useState<{ isOffline: boolean; timeStr: string }>({ isOffline: false, timeStr: '' });

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
                setOfflineInfo({ isOffline, timeStr });

                if (isOffline) {
                    message.warning({ 
                        content: `网络不可用，已加载${timeStr}的缓存数据`, 
                        key: 'offline_warning',
                        duration: 3
                    });
                }
                
                // 生成数据签名 (用于比对是否更新)
                const newSignature = JSON.stringify({
                    courses: newCourses,
                    week: newCurrentWeek
                });
                const lastSignature = sessionStorage.getItem('course_data_signature');
                const isDataChanged = newSignature !== lastSignature;

                if (isDataChanged || isManual) {
                    setCourses(newCourses);
                    setCurrentWeek(newCurrentWeek);
                    
                    // 更新缓存
                    sessionStorage.setItem('course_data_signature', newSignature);
                    sessionStorage.setItem('course_data_cache', JSON.stringify(res.data));
                    
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
                message.error({ content: '加载失败: ' + res.message, key: 'course_error' });
            }
        } catch (e) {
            message.error({ content: '网络错误', key: 'course_error' });
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        // 1. 尝试从缓存加载 (实现秒开)
        const cachedDataStr = sessionStorage.getItem('course_data_cache');
        let hasCache = false;
        
        if (cachedDataStr) {
            try {
                const cachedData = JSON.parse(cachedDataStr) as PreviewCoursesData;
                setCourses(Array.isArray(cachedData.courses) ? cachedData.courses : []);
                const cachedWeek = String(cachedData.currentWeek);
                setCurrentWeek(cachedWeek);
                
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
                    message="当前处于离线模式"
                    description={`由于网络连接失败，正在显示${offlineInfo.timeStr}缓存的课表数据。请检查网络后点击“刷新”重试。`}
                    type="warning"
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
        </div>
    );
};

export default CoursePreviewPage;
