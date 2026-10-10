import { Alert, Button, Card, Space, Typography } from 'antd';
import { CloudOutlined, GlobalOutlined } from '@ant-design/icons';
import { api } from '../api';

export default function CloudPage() {
  return <Space direction="vertical" size="large" style={{ width: '100%', maxWidth: 850 }}>
    <Card title={<><CloudOutlined /> 云端推送 · 不用让电脑开着</>}>
      <Typography.Paragraph>在官网绑定本校教务账号和 WxPusher UID，由服务器定时检查并发送微信消息。电脑和手机使用同一个管理页，设置不会保存在两处。</Typography.Paragraph>
      <Typography.Paragraph>可独立开启北京时间 07:00 当天课表、20:00 次日课表，以及成绩变化提醒。随时暂停或删除托管资料。</Typography.Paragraph>
      <Button type="primary" size="large" icon={<GlobalOutlined />} onClick={() => api.openCloudPortal()}>打开官网云端管理</Button>
    </Card>
    <Alert type="info" showIcon message="本地登录不等于云端托管" description="云端管理会单独征求同意，并通过微信验证码验证。不会自动上传你本机的密码；本地查询和日历导出不需要绑定 UID。" />
    <Alert type="warning" showIcon message="旧版本地定时推送已退役" description="新版不再创建电脑定时任务。首次启动会停用本校旧任务；若出现迁移失败提示，请按提示处理后再开启云端推送，避免旧版重复发送。" />
  </Space>;
}
