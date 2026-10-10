import { lazy, Suspense, useEffect, useState, type ReactNode } from 'react';
import { Avatar, Button, ConfigProvider, Dropdown, Layout, Menu, message, Modal, Spin, Tooltip } from 'antd';
import { AppstoreOutlined, CalendarOutlined, CloudOutlined, ExportOutlined, GiftOutlined, GlobalOutlined, InfoCircleOutlined, LogoutOutlined, MenuFoldOutlined, MenuUnfoldOutlined, ReadOutlined, SwapOutlined, UserOutlined } from '@ant-design/icons';
import DashboardPage from './components/DashboardPage';
import LoginModal from './components/LoginModal';
import DeveloperEgg from './components/DeveloperEgg';
import { useResponsiveLayout } from './hooks/useResponsiveLayout';
import { api } from './api';
import { OFFICIAL_WEBSITE_URL } from './constants';

const CoursePreviewPage = lazy(() => import('./components/CoursePreviewPage'));
const GradesPage = lazy(() => import('./components/GradesPage'));
const AboutPage = lazy(() => import('./components/AboutPage'));
const CalendarPage = lazy(() => import('./components/CalendarPage'));
const CloudPage = lazy(() => import('./components/CloudPage'));
const titles: Record<string, string> = { dashboard: '控制台', preview: '课表预览', grades: '成绩', calendar: '日历导出', cloud: '云端推送', about: '关于 ClassPush' };

export default function App() {
  const [collapsed, setCollapsed] = useState(false);
  const [selectedKey, setSelectedKey] = useState('dashboard');
  const [checking, setChecking] = useState(true);
  const [loggedIn, setLoggedIn] = useState(false);
  const [loginVisible, setLoginVisible] = useState(false);
  const [pendingPage, setPendingPage] = useState('dashboard');
  const [eggOpen, setEggOpen] = useState(false);
  const { isMobile } = useResponsiveLayout();
  const [notice, contextHolder] = message.useMessage();

  useEffect(() => {
    let started = false;
    const check = async () => {
      if (started || !window.pywebview) return;
      started = true;
      try {
        const result = await api.getConfig();
        setLoggedIn(Boolean(result.data?.username && result.data.has_password));
      } catch { notice.error('无法读取本机账号，请重新打开软件后重试。');
      } finally { setChecking(false); }
    };
    window.addEventListener('pywebviewready', check);
    const poll = setInterval(check, 200);
    const timeout = setTimeout(() => {
      if (!started) { setChecking(false); notice.error('本机服务尚未就绪，请重新打开软件。'); }
    }, 10000);
    check();
    return () => { window.removeEventListener('pywebviewready', check); clearInterval(poll); clearTimeout(timeout); };
  }, [notice]);

  const navigate = (key: string) => {
    if (!loggedIn && ['preview', 'grades', 'calendar'].includes(key)) {
      setPendingPage(key); setLoginVisible(true);
    } else setSelectedKey(key);
    if (isMobile) setCollapsed(true);
  };
  const logout = () => Modal.confirm({
    title: '退出本机教务账号？',
    content: '会清除本机保存的账号和课程缓存，但不会关闭服务器上的云端提醒。',
    okText: '退出本机', cancelText: '取消',
    onOk: async () => {
      const result = await api.saveConfig({ username: '', password: '' });
      if (result.status !== 'success') throw new Error('退出失败，请重试');
      setLoggedIn(false); setSelectedKey('dashboard');
      notice.success('已退出本机账号，云端提醒不受影响');
    },
  });
  const content: Record<string, ReactNode> = {
    dashboard: <DashboardPage onNavigate={navigate} loggedIn={loggedIn} />,
    preview: <CoursePreviewPage />, grades: <GradesPage />,
    calendar: <CalendarPage />, cloud: <CloudPage />, about: <AboutPage />,
  };

  return <ConfigProvider theme={{ token: { colorPrimary: '#1677ff', colorText: '#182230', colorTextSecondary: '#596579', colorBorderSecondary: '#e6ebf2', borderRadius: 12, fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif' }, components: { Button: { controlHeight: 40 }, Menu: { itemHeight: 46, itemBorderRadius: 10, itemMarginBlock: 5 } } }}>
    {contextHolder}
    <Layout className="desktop-shell">
      {isMobile && !collapsed && <button className="sidebar-scrim" aria-label="关闭导航" onClick={() => setCollapsed(true)} />}
      <Layout.Sider className="workspace-sidebar" trigger={null} collapsible collapsed={collapsed} width={224} collapsedWidth={isMobile ? 0 : 76} breakpoint="lg" onBreakpoint={broken => setCollapsed(broken)}>
        <a className="workspace-brand" href="#console" onClick={event => { event.preventDefault(); navigate('dashboard'); }} aria-label="ClassPush 控制台">
          <img src="./icon.ico" alt="" /><span>Class<span className="brand-ink">Push</span><small>湖南工学院 · 学习空间</small></span>
        </a>
        <Menu mode="inline" selectedKeys={[selectedKey]} onClick={({ key }) => navigate(key)} items={[
          { type: 'group', label: '学习空间', children: [
            { key: 'dashboard', icon: <AppstoreOutlined aria-hidden />, label: '控制台' },
            { key: 'preview', icon: <CalendarOutlined aria-hidden />, label: '课表预览' },
            { key: 'grades', icon: <ReadOutlined aria-hidden />, label: '成绩' },
          ] },
          { type: 'group', label: '随身服务', children: [
            { key: 'calendar', icon: <ExportOutlined aria-hidden />, label: '日历导出' },
            { key: 'cloud', icon: <CloudOutlined aria-hidden />, label: '云端推送' },
          ] },
          { type: 'divider' },
          { key: 'about', icon: <InfoCircleOutlined aria-hidden />, label: '关于 ClassPush' },
        ]} />
        <div className="sidebar-bottom">
          <Tooltip title="开发者的秘密基地"><Button className="developer-egg-trigger" type="text" aria-label="打开开发者彩蛋" icon={<GiftOutlined />} onClick={() => setEggOpen(true)}>{!collapsed && '发现一枚彩蛋'}</Button></Tooltip>
          <Tooltip title={collapsed ? '展开导航' : '收起导航'}>
            <Button className="sidebar-toggle" type="text" aria-label={collapsed ? '展开导航' : '收起导航'} icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />} onClick={() => setCollapsed(!collapsed)} />
          </Tooltip>
        </div>
      </Layout.Sider>
      <Layout className="workspace-main" style={{ marginLeft: isMobile ? 0 : collapsed ? 76 : 224 }}>
        <Layout.Header className="workspace-header">
          <div className="workspace-location">
            {isMobile && <Button type="text" aria-label="展开导航" icon={<MenuUnfoldOutlined />} onClick={() => setCollapsed(false)} />}
            <span className="header-parent">ClassPush</span><span className="header-separator">/</span><strong>{titles[selectedKey]}</strong>
          </div>
          <div className="header-actions">
            <Tooltip title="打开官网"><Button type="text" aria-label="打开官网" icon={<GlobalOutlined />} onClick={() => window.open(OFFICIAL_WEBSITE_URL, '_blank', 'noopener')} /></Tooltip>
            {loggedIn ? <Dropdown trigger={['click']} menu={{ items: [
              { key: 'state', label: '本机账号已保存', disabled: true },
              { key: 'switch', label: '切换本机账号', icon: <SwapOutlined />, onClick: () => { setPendingPage('dashboard'); setLoginVisible(true); } },
              { type: 'divider' },
              { key: 'logout', label: '退出本机账号', icon: <LogoutOutlined />, danger: true, onClick: logout },
            ] }}><Button className="account-button" aria-label="管理本机账号"><Avatar size={24} icon={<UserOutlined />} /> 本机账号</Button></Dropdown> :
            <Button icon={<UserOutlined />} onClick={() => { setPendingPage('dashboard'); setLoginVisible(true); }}>登录教务</Button>}
          </div>
        </Layout.Header>
        <Layout.Content className="workspace-content">
          {checking ? <div className="page-loading"><Spin size="large" /><p>正在连接本机服务…</p></div> :
            <Suspense fallback={<div className="page-loading"><Spin /><p>正在加载页面…</p></div>}>{content[selectedKey]}</Suspense>}
        </Layout.Content>
      </Layout>
      <LoginModal visible={loginVisible} onCancel={() => setLoginVisible(false)} onSuccess={() => { setLoggedIn(true); setLoginVisible(false); setSelectedKey(pendingPage); }} />
      <DeveloperEgg open={eggOpen} onClose={() => setEggOpen(false)} />
    </Layout>
  </ConfigProvider>;
}
