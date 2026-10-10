import { useEffect, useState } from 'react';
import { Alert, Button, Card, Descriptions, Space } from 'antd';
import { api } from '../api';

export default function SettingsPage({ onLogout, isLoggedIn }: {onLogout: () => void; isLoggedIn: boolean}) {
  const [username, setUsername] = useState('');
  useEffect(() => { api.getConfig().then(res => setUsername(res.data?.username || '')); }, [isLoggedIn]);
  return <Space direction="vertical" size="large" style={{ width: '100%', maxWidth: 800 }}>
    <Card title="本机教务账号">
      <Descriptions column={1} items={[{ key: 'school', label: '学校', children: '湖南工学院' }, { key: 'student', label: '学号', children: username || '尚未登录' }]} />
      <Button onClick={onLogout}>{isLoggedIn ? '退出本地账号 / 切换账号' : '登录教务账号'}</Button>
    </Card>
    <Alert showIcon type="info" message="本地与云端独立管理" description="退出本机不会关闭云端推送。关闭提醒或删除服务器资料，请进入“云端推送”。日历提醒及课时设置已移动到“日历导出”。" />
  </Space>;
}
