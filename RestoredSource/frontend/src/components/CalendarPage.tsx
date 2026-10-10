import { useEffect, useState } from 'react';
import { Alert, Button, Card, Descriptions, Form, Input, InputNumber, message, Select, Space, Typography } from 'antd';
import { DownloadOutlined, FolderOpenOutlined, ReadOutlined } from '@ant-design/icons';
import { api } from '../api';
import type { PreviewCoursesData } from '../types';

export default function CalendarPage() {
  const [data, setData] = useState<PreviewCoursesData>();
  const [loading, setLoading] = useState(false);
  const [scope, setScope] = useState<'current_week' | 'next_7_days' | 'term'>('current_week');
  const [form] = Form.useForm();
  const [savedFile, setSavedFile] = useState('');
  const load = async () => {
    setLoading(true);
    try {
      const [config, preview] = await Promise.all([api.getConfig(), api.getPreviewCourses()]);
      if (config.data) form.setFieldsValue({ alarm: config.data.calendar_alarm_minutes ?? 15, slots: config.data.time_slots });
      if (preview.status === 'success') setData(preview.data);
      else message.warning(preview.message || '请先通过右上角登录本校教务账号');
    } catch { message.error('课表加载失败，请重试'); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);
  const exportFile = async () => {
    setLoading(true);
    try {
      const values = await form.validateFields();
      const saved = await api.saveConfig({ calendar_alarm_minutes: values.alarm, time_slots: values.slots });
      if (saved.status !== 'success') throw new Error(saved.message);
      const result = await api.exportCalendarIcs(scope);
      if (result.status !== 'success' || !result.data) throw new Error(result.message || '导出失败');
      setSavedFile(result.data.file_path);
      message.success(`已生成 ${result.data.course_count} 条日历事件${result.data.source === 'offline' ? '（使用本地缓存，请核对调课）' : ''}`);
    } catch (error) { message.error(error instanceof Error ? error.message : '请检查课时设置后重试'); }
    finally { setLoading(false); }
  };
  return <Space direction="vertical" size="large" style={{ width: '100%' }}>
    <Alert showIcon type="warning" message="日历是导出时的课表快照，不会自动跟随调课" description="建议先导出本周测试。确认日期、时间和提醒正确后，再导入整学期。再次导入前先删除旧的独立课表日历，避免重复。" />
    <Card title="独立日历导出" extra={<Button loading={loading} onClick={load}>刷新教务课表</Button>}>
      <Descriptions column={2} items={[
        { key: 'term', label: '学期', children: data?.semesterName || '待获取' },
        { key: 'anchor', label: '第一周周一', children: data?.weekOneMonday || '尚未确认，不能导出' },
        { key: 'source', label: '数据来源', children: data?.source === 'offline' ? '本地缓存（可能过期）' : '教务系统' },
        { key: 'count', label: '课程安排', children: `${data?.courses.length || 0} 条` },
      ]} />
      <Form form={form} layout="vertical" initialValues={{ alarm: 15 }} style={{ marginTop: 24 }}>
        <Form.Item label="导出范围"><Select value={scope} onChange={setScope} options={[
          { value: 'current_week', label: '本周（建议首次测试）' }, { value: 'next_7_days', label: '未来 7 天' }, { value: 'term', label: '全学期' },
        ]} /></Form.Item>
        <Form.Item name="alarm" label="提前提醒（分钟，0 表示不提醒）"><InputNumber min={0} max={1440} /></Form.Item>
        <Typography.Paragraph type="secondary">本校课时如下。如学校调整作息，可修改后重新导出；不会影响云端推送时段。</Typography.Paragraph>
        {Object.keys(form.getFieldValue('slots') || {}).map(key => <div key={key}><Space wrap align="baseline">
          <span style={{ display: 'inline-block', width: 60 }}>第{key}节</span>
          <Form.Item name={['slots', key, 0]} rules={[{ pattern: /^(?:[01]\d|2[0-3]):[0-5]\d$/, message: '格式 HH:mm' }]}><Input aria-label={`第${key}节开始时间`} style={{ width: 100 }} /></Form.Item>
          <span>至</span>
          <Form.Item name={['slots', key, 1]} rules={[{ pattern: /^(?:[01]\d|2[0-3]):[0-5]\d$/, message: '格式 HH:mm' }]}><Input aria-label={`第${key}节结束时间`} style={{ width: 100 }} /></Form.Item>
        </Space></div>)}
      </Form>
      <Space wrap>
        <Button type="primary" size="large" loading={loading} disabled={!data?.weekOneMonday || !data?.courses.length} icon={<DownloadOutlined />} onClick={exportFile}>导出 ICS 文件</Button>
        <Button size="large" icon={<ReadOutlined />} onClick={() => api.openCalendarGuide()}>查看手机图文导入教程</Button>
        <Button size="large" icon={<FolderOpenOutlined />} onClick={async () => { const res = await api.openExportFolder(); if (res.status !== 'success') message.info(res.message); }}>打开导出文件夹</Button>
      </Space>
      {savedFile && <Typography.Paragraph copyable style={{ marginTop: 16 }}>{savedFile}</Typography.Paragraph>}
    </Card>
  </Space>;
}
