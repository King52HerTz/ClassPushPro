import { Alert, Button, Card, Col, Row, Space, Typography } from 'antd';
import { CloudOutlined, CalendarOutlined, ReadOutlined } from '@ant-design/icons';
import { APP_VERSION } from '../constants';

export default function DashboardPage({ onNavigate }: { onNavigate?: (key: string) => void }) {
  return <Space direction="vertical" size="large" style={{ width: '100%' }}>
    <div><Typography.Title level={2}>课表随身，电脑不用一直开着</Typography.Title><Typography.Text type="secondary">ClassPush {APP_VERSION} · 湖南工学院</Typography.Text></div>
    <Row gutter={[20, 20]}>
      {[{ key: 'cloud', title: '云端推送', icon: <CloudOutlined />, text: '手机管理，早 07:00 看当天，晚 20:00 看次日；随时暂停。' },
        { key: 'calendar', title: '日历导出', icon: <CalendarOutlined />, text: '把课表导入手机日历，系统提醒不依赖电脑开机。' },
        { key: 'preview', title: '本地查询', icon: <ReadOutlined />, text: '保留课表与成绩查询，不必填写推送 UID。' }].map(item =>
          <Col xs={24} lg={8} key={item.key}><Card title={<>{item.icon} {item.title}</>} style={{ height: '100%' }}>
            <Typography.Paragraph>{item.text}</Typography.Paragraph><Button type="primary" onClick={() => onNavigate?.(item.key)}>打开{item.title}</Button>
          </Card></Col>)}
    </Row>
    <Alert type="info" showIcon message="升级说明" description="电脑定时推送与 GitHub Actions 推送已移除。需要微信提醒请主动绑定云端；本地账号不会自动上传。日历是快照，调课后记得重新导出。" />
  </Space>;
}
