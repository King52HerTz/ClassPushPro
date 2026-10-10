import { useEffect, useState } from 'react';
import { Alert, Button, Card, Descriptions, Empty, Modal, Radio, Select, Space, Spin, message } from 'antd';
import dayjs from 'dayjs';
import WeekTimetable from './WeekTimetable';
import { api } from '../api';
import type { Course, PreviewCoursesData } from '../types';

export default function CoursePreviewPage() {
  const [data, setData] = useState<PreviewCoursesData>();
  const [loading, setLoading] = useState(false);
  const [week, setWeek] = useState('all');
  const [view, setView] = useState('table');
  const [detail, setDetail] = useState<Course>();
  const load = async () => {
    setLoading(true);
    try {
      const response = await api.getPreviewCourses();
      if (response.status !== 'success' || !response.data) throw new Error(response.message || '加载失败');
      setData(response.data);
      setWeek(response.data.scheduleStatus === 'active' ? String(response.data.currentWeek) : 'all');
    } catch (error) { message.error(error instanceof Error ? error.message : '加载失败，请重试'); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);
  const courses = data?.courses || [];
  const weeks = [...new Set([...(data?.availableWeeks || []), ...courses.flatMap(c => (c.classWeekDetails || '').split(',').map(Number))])].filter(n => n > 0).sort((a, b) => a - b);
  const anchor = data?.weekOneMonday ? dayjs(data.weekOneMonday).add(week === 'all' ? 0 : Number(week) - 1, 'week') : dayjs();
  const visible = week === 'all' ? courses : courses.filter(c => !c.classWeekDetails || c.classWeekDetails.split(',').includes(week));
  return <Space direction="vertical" size="middle" style={{ width: '100%' }}>
    {data?.source === 'offline' && <Alert type="warning" showIcon message={'正在显示本账号的本地缓存 · ' + (data.update_time_str || '')} description="缓存可能不是最新课表，请联网刷新。" />}
    {data && data.scheduleStatus !== 'active' && <Alert type="info" showIcon message={data.scheduleMessage || '当前非教学周'} description="未开学默认显示全部课程，日期只使用已确认的学期基准。" />}
    <Card>
      <Space wrap>
        <strong>{data?.semesterName || '本校课表'}</strong>
        <Select aria-label="课表周次" style={{ width: 120 }} value={week} onChange={setWeek} options={[{ value: 'all', label: '全部课程' }, ...weeks.map(n => ({ value: String(n), label: '第 ' + n + ' 周' }))]} />
        <Radio.Group value={view} onChange={event => setView(event.target.value)} optionType="button" options={[{ value: 'table', label: '课表' }, { value: 'card', label: '列表' }]} />
        <Button loading={loading} onClick={load}>刷新</Button>
      </Space>
    </Card>
    <Spin spinning={loading}><Card>
      {!courses.length ? <Empty description="暂无课程，请先登录或等待教务发布" /> : view === 'table' ?
        <div style={{ overflowX: 'auto' }}><WeekTimetable courses={courses} currentWeek={week === 'all' ? 'all' : Number(week)} weekMonday={anchor} showDates={week !== 'all' && Boolean(data?.weekOneMonday)} onCourseClick={setDetail} /></div> :
        <Space direction="vertical" style={{ width: '100%' }}>{visible.map((course, i) =>
          <Card key={i} size="small" hoverable onClick={() => setDetail(course)} title={course.courseName}>{course.xqmc} · {course.classTime} · {course.location} · {course.teacherName}</Card>)}</Space>}
    </Card></Spin>
    <Modal open={Boolean(detail)} title="课程详情" footer={null} onCancel={() => setDetail(undefined)}>
      <Descriptions column={1} items={detail ? [
        { key: 'name', label: '课程', children: detail.courseName }, { key: 'time', label: '节次', children: detail.classTime },
        { key: 'place', label: '地点', children: detail.location }, { key: 'teacher', label: '教师', children: detail.teacherName },
        { key: 'weeks', label: '周次', children: detail.classWeek }, { key: 'day', label: '星期', children: detail.xqmc },
      ] : []} />
    </Modal>
  </Space>;
}
