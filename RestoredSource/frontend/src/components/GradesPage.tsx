import { useEffect, useState } from 'react';
import { Alert, Button, Card, Descriptions, Select, Space, message } from 'antd';
import { api } from '../api';
import GradeResults from './grades/GradeResults';
import type { GradeQueryData } from '../types';
import './GradesPage.css';

export default function GradesPage() {
  const [data, setData] = useState<GradeQueryData>();
  const [semester, setSemester] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const load = async (id?: string) => {
    setLoading(true); setError('');
    try {
      const response = id ? await api.getGrades(id) : await api.getGradeSemesters();
      if (response.status !== 'success' || !response.data) throw new Error(response.message || '成绩加载失败');
      setData(response.data);
      setSemester(response.data.selected_semester?.semester_id || response.data.current_term?.semester_id || '');
    } catch (err) {
      const text = err instanceof Error ? err.message : '加载失败';
      setError(text); message.error(text);
      setData(undefined); // Never display a previous semester as the newly requested one.
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);
  return <Space direction="vertical" size="middle" style={{ width: '100%' }} className="grades-page">
    <Card><Space wrap>
      <Select aria-label="成绩查询学期" value={semester || undefined} placeholder="选择学期" style={{ width: 220 }} onChange={id => { setSemester(id); load(id); }} options={(data?.semester_list || []).map(item => ({ value: item.semester_id, label: item.semester_name }))} />
      <Button loading={loading} onClick={() => load(semester || undefined)}>刷新成绩</Button>
    </Space></Card>
    {error && <Alert type="error" showIcon message={error} />}
    {data?.source === 'offline' && <Alert type="warning" showIcon message="显示本账号、所选学期的本地缓存" description={data.update_time_str} />}
    <Card><Descriptions items={[
      { key: 'student', label: '姓名', children: data?.student_info?.student_name || '--' },
      { key: 'term', label: '学期', children: data?.selected_semester?.semester_name || '--' },
      { key: 'total', label: '课程数', children: data?.grades?.length ?? 0 },
    ]} /></Card>
    <Card><GradeResults grades={data?.grades || []} loading={loading} hasSelectedSemester={Boolean(semester)} /></Card>
    <Alert type="info" showIcon message="成绩变化提醒请在“云端推送”中开启，本页只查询，不发送消息。" />
  </Space>;
}
