import { Button } from 'antd';
import { ArrowRightOutlined, CalendarOutlined, CloudOutlined, ExportOutlined, ReadOutlined, SafetyOutlined } from '@ant-design/icons';

export default function DashboardPage({ onNavigate, loggedIn }: { onNavigate: (key: string) => void; loggedIn: boolean }) {
  return <div className="console-page">
    <div className="console-heading">
      <div><span className="section-kicker">CLASS PUSH · 湖南工学院</span><h1>校园安排，一处就绪。</h1><p>电脑查课，日历随身。提醒交给云端，生活留给自己。</p></div>
      <span className="local-state"><span />{loggedIn ? '本机账号已保存' : '本地查询尚未登录'}</span>
    </div>
    <div className="console-service-grid">
      <section className="console-cloud">
        <div className="service-eyebrow"><CloudOutlined /> 云端推送<span>电脑无需常开</span></div>
        <h2>明天的课，<br />提前心中有数。</h2>
        <p>通过 WxPusher App 接收课表和成绩变化。<br />在官网完成绑定，手机上也能随时管理。</p>
        <div className="push-time-options"><div><strong>07:00</strong><span>当天课表</span></div><i /><div><strong>20:00</strong><span>次日课表</span></div></div>
        <Button type="primary" size="large" icon={<ArrowRightOutlined />} onClick={() => onNavigate('cloud')}>前往云端管理</Button>
        <small>时段可独立选择，开启状态以云端管理页为准。</small>
      </section>
      <section className="console-calendar">
        <div className="service-eyebrow"><ExportOutlined /> 日历导出</div>
        <div className="calendar-illustration" aria-hidden="true"><span>ClassPush</span><CalendarOutlined /><strong>ICS</strong><small>你的日程，由你掌握</small></div>
        <h2>把课表，放进口袋。</h2><p>导入手机系统日历，让课程提醒融入每天的日程。</p>
        <Button size="large" onClick={() => onNavigate('calendar')}>导出我的课表 <ArrowRightOutlined /></Button>
        <small>日历是快照，调课后需重新导入。</small>
      </section>
    </div>
    <div className="console-section-label"><h2>本地查询</h2><span>仅在本机使用，不必绑定 UID</span></div>
    <div className="console-query-grid">
      <button className="query-entry" onClick={() => onNavigate('preview')}><span className="query-icon"><CalendarOutlined /></span><span><strong>课表预览</strong><small>按周查看课程、时间与教室</small></span><ArrowRightOutlined /></button>
      <button className="query-entry" onClick={() => onNavigate('grades')}><span className="query-icon violet"><ReadOutlined /></span><span><strong>成绩查询</strong><small>选择学期，查看教务最新成绩</small></span><ArrowRightOutlined /></button>
    </div>
    <div className="console-privacy"><SafetyOutlined /><p>本机账号不会自动上传。云端托管需另行同意；退出本机不会关闭云端提醒。</p></div>
  </div>;
}
