import React, { useMemo } from 'react';
import { Empty } from 'antd';
import dayjs from 'dayjs';
import type { Course } from '../types';

// 仿截图配色方案 (背景色 + 深色边框)
const COURSE_THEMES = [
    { bg: '#E6FFFB', border: '#5CDBD3' }, // 浅青 (软件工程风格)
    { bg: '#FFF7E6', border: '#FFC069' }, // 浅橙 (人工智能风格)
    { bg: '#E6F7FF', border: '#69C0FF' }, // 浅蓝 (算法设计风格)
    { bg: '#FFF0F6', border: '#FF85C0' }, // 浅粉 (体育风格)
    { bg: '#F9F0FF', border: '#B37FEB' }, // 浅紫 (毛概风格)
    { bg: '#FCFFE6', border: '#D3F261' }, // 浅柠檬 (数据库风格)
    { bg: '#FFF1B8', border: '#FFEC3D' }, // 浅黄
    { bg: '#F0F5FF', border: '#85A5FF' }, // 浅靛蓝
    { bg: '#FFF2E8', border: '#FFBB96' }, // 浅橘
    { bg: '#F6FFED', border: '#95DE64' }, // 浅绿
];

interface WeekTimetableProps {
    courses: Course[];
    currentWeek: number;
    weekMonday: dayjs.Dayjs;
    onCourseClick?: (course: Course) => void;
}

const WeekTimetable: React.FC<WeekTimetableProps> = ({ courses, currentWeek, weekMonday, onCourseClick }) => {
    // 1. 过滤当前周课程
    const weekCourses = useMemo(() => {
        return courses.filter(course => {
            if (!course.classWeekDetails) return true; // 如果没有详情，默认显示
            // 假设 classWeekDetails 是逗号分隔的周次字符串 "1,2,3..."
            const weeks = course.classWeekDetails.split(',');
            return weeks.includes(String(currentWeek));
        });
    }, [courses, currentWeek]);

    // 2. 生成网格数据
    // 5大节 (10小节) x 7天
    const ROWS = 5; 
    const COLS = 7;
    const WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
    
    // 渲染单元格
    const renderCell = (row: number, col: number) => {
        // row: 0-4 (对应一大节到五大节)
        // col: 0-6 (对应周一到周日)
        
        // 找到该位置的课程
        // 课程的 weekday: 1-7 (对应 col+1)
        // 课程的 startNode: 1, 3, 5, 7, 9 (对应 row*2 + 1)
        
        const targetWeekday = col + 1;
        const targetStartNode = row * 2 + 1;
        
        const cellCourses = weekCourses.filter(c => 
            c.weekday === targetWeekday && 
            c.startNode === targetStartNode
        );

        if (cellCourses.length === 0) {
            return null;
        }

        return (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, height: '100%' }}>
                {cellCourses.map((course, idx) => {
                    // 根据课程名生成固定的颜色索引
                    const colorIndex = Math.abs(course.courseName.split('').reduce((a: number, b: string) => a + b.charCodeAt(0), 0)) % COURSE_THEMES.length;
                    const theme = COURSE_THEMES[colorIndex];
                    
                    return (
                        <div 
                            key={idx}
                            onClick={() => onCourseClick && onCourseClick(course)}
                            style={{ 
                                backgroundColor: theme.bg, 
                                borderRadius: 8, 
                                padding: 8, 
                                flex: 1,
                                fontSize: 12,
                                boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
                                borderLeft: `4px solid ${theme.border}`, // 专门的左边框颜色
                                cursor: 'pointer',
                                transition: 'all 0.3s'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.02)'}
                            onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
                        >
                            <div style={{ fontWeight: 'bold', fontSize: 13, marginBottom: 4, color: '#4a4a4a' }}>{course.courseName}</div>
                            <div style={{ color: '#666' }}>{course.teacherName}</div>
                            <div style={{ color: '#888' }}>{course.location}</div>
                        </div>
                    );
                })}
            </div>
        );
    };

    if (weekCourses.length === 0) {
        return <Empty description="本周没有课哦" />;
    }

    return (
        <div style={{ overflowX: 'auto', minWidth: 800 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '80px repeat(7, 1fr)', gap: 1, backgroundColor: '#eee', border: '1px solid #eee' }}>
                {/* 表头 */}
                <div style={{ backgroundColor: '#fafafa', padding: 12, textAlign: 'center', fontWeight: 'bold', color: '#999' }}>
                    节次\星期
                </div>
                {WEEKDAYS.map((day, index) => {
                    // 计算日期：周一 = weekMonday + 0 days
                    const date = weekMonday.add(index, 'day');
                    const dateStr = date.format('MM-DD');
                    
                    return (
                        <div key={day} style={{ backgroundColor: '#fff', padding: 12, textAlign: 'center', fontWeight: 'bold' }}>
                            <div>{day}</div>
                            <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>{dateStr}</div>
                        </div>
                    );
                })}

                {/* 网格内容 */}
                {Array.from({ length: ROWS }).map((_, rowIndex) => (
                    <React.Fragment key={rowIndex}>
                        {/* 左侧节次 */}
                        <div style={{ backgroundColor: '#fafafa', padding: 12, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', color: '#666', minHeight: 120 }}>
                            <div style={{ fontWeight: 'bold' }}>
                                {['一大节', '二大节', '三大节', '四大节', '五大节'][rowIndex]}
                            </div>
                            <div style={{ fontSize: 12, color: '#999' }}>
                                {`${String(rowIndex * 2 + 1).padStart(2, '0')},${String(rowIndex * 2 + 2).padStart(2, '0')}`}
                            </div>
                        </div>
                        
                        {/* 课程单元格 */}
                        {Array.from({ length: COLS }).map((_, colIndex) => (
                            <div key={`${rowIndex}-${colIndex}`} style={{ backgroundColor: '#fff', padding: 4, minHeight: 120 }}>
                                {renderCell(rowIndex, colIndex)}
                            </div>
                        ))}
                    </React.Fragment>
                ))}
            </div>
        </div>
    );
};

export default WeekTimetable;
