import { useState, useEffect } from 'react';
import { Layout, Menu, message, Spin, Modal } from 'antd';
import {
  DashboardOutlined,
  CalendarOutlined,
  SettingOutlined,
  InfoCircleOutlined,
  LeftOutlined,
  RightOutlined
} from '@ant-design/icons';
import DashboardPage from './components/DashboardPage';
import CoursePreviewPage from './components/CoursePreviewPage';
import SettingsPage from './components/SettingsPage';
import AboutPage from './components/AboutPage';
import LoginModal from './components/LoginModal';
import { useResponsiveLayout } from './hooks/useResponsiveLayout';
import { api } from './api';

const { Header, Sider, Content } = Layout;

const App = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [selectedKey, setSelectedKey] = useState('dashboard');
  const [, contextHolder] = message.useMessage();
  
  // 登录状态管理
  const [isCheckingLogin, setIsCheckingLogin] = useState(true);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [showLoginModal, setShowLoginModal] = useState(false);

  // 检查登录状态
  const checkLoginStatus = async () => {
    setIsCheckingLogin(true);
    try {
      const res = await api.getConfig();
      if (res.status === 'success' && res.data && res.data.username && res.data.password) {
        setIsLoggedIn(true);
        setShowLoginModal(false);
      } else {
        setIsLoggedIn(false);
        // 只有未登录时才显示弹窗
        setShowLoginModal(true);
      }
    } catch (e) {
      // 如果后端没启动或出错，也视为未登录
      setIsLoggedIn(false);
      setShowLoginModal(true);
    } finally {
      setIsCheckingLogin(false);
    }
  };

  useEffect(() => {
    let timer: ReturnType<typeof setInterval> | null = null;

    const performCheck = () => {
        if (timer) clearInterval(timer);
        checkLoginStatus();
    };

    if (window.pywebview) {
      performCheck();
    } else {
      window.addEventListener('pywebviewready', performCheck);
      
      // 轮询作为备份方案
      timer = setInterval(() => {
        if (window.pywebview) {
          performCheck();
        }
      }, 200);

      // 超时清理
      setTimeout(() => {
        if (timer) clearInterval(timer);
      }, 5000);
    }

    return () => {
      window.removeEventListener('pywebviewready', performCheck);
      if (timer) clearInterval(timer);
    };
  }, []);

  const { isMobile } = useResponsiveLayout();

  // Handle logout (triggered from SettingsPage)
  const handleLogout = async () => {
    if (!isLoggedIn) {
        // 如果未登录，点击按钮直接显示登录弹窗
        setShowLoginModal(true);
        return;
    }

    // 弹出确认框
    Modal.confirm({
        title: '确认退出登录？',
        content: '退出后需要重新输入账号密码才能登录。',
        okText: '确认退出',
        cancelText: '取消',
        onOk: async () => {
            // 如果已登录，执行退出逻辑
            try {
                await api.saveConfig({
                    username: "",
                    password: "",
                    uid: "",
                    app_token: "",
                    push_time: "07:00",
                    auto_start: false
                });
                setIsLoggedIn(false);
                setShowLoginModal(true);
                // message.success("已退出登录"); // 移除提示，避免重复弹窗
            } catch (e) {
                message.error("退出失败");
            }
        }
    });
  };

  // Handle re-login (triggered from SettingsPage) - 已合并到 handleLogout
  // const handleReLogin = () => {
  //   setShowLoginModal(true);
  // };

  const renderContent = () => {
    switch (selectedKey) {
      case 'dashboard':
        return <DashboardPage />;
      case 'preview':
        return <CoursePreviewPage />;
      case 'settings':
        // 传递 logout 处理函数给 SettingsPage
        return <SettingsPage onLogout={handleLogout} isLoggedIn={isLoggedIn} />;
      case 'about':
        return <AboutPage />;
      default:
        return <DashboardPage />;
    }
  };

  // 如果正在检查登录且没有结果，显示 Loading
  if (isCheckingLogin) {
    return (
        <div style={{ height: '100vh', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
            <Spin size="large" tip="正在初始化..." />
        </div>
    );
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {contextHolder}
      
      {/* 登录弹窗 */}
      <LoginModal 
        visible={showLoginModal} 
        onSuccess={() => {
            setIsLoggedIn(true);
            setShowLoginModal(false);
            // 登录成功后刷新一下配置或状态
        }}
        onCancel={() => {
            // 用户点击关闭按钮，无论是否已登录，都关闭弹窗
            setShowLoginModal(false);
        }}
        canCancel={true} // 始终允许关闭 (满足用户需求：误触退出登录后可以关闭窗口)
      />

      <Sider 
        trigger={null} 
        collapsible 
        collapsed={collapsed}
        breakpoint="lg"
        collapsedWidth={isMobile ? 0 : 80}
        onBreakpoint={(broken) => {
            if (broken) setCollapsed(true);
        }}
        width={200}
        style={{
            height: '100vh', // 确保占满整个视口高度
            position: 'fixed', // 固定定位
            left: 0,
            top: 0,
            bottom: 0,
            zIndex: 100,
            overflow: 'auto',
            background: '#ffffff', // 修改为白色背景
            borderRight: '1px solid #f0f0f0', // 添加右侧边框
        }}
      >
        <div className="demo-logo-vertical" style={{ 
            height: 32, 
            margin: 16, 
            background: 'rgba(0, 0, 0, 0.05)', // 修改Logo背景
            borderRadius: 6,
            // 简单的 Logo 占位
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 'bold',
            fontSize: 16, // 稍微加大字体
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial',
        }}>
            {/* 4. 左上角软件名：展开显示 ClassPush，收起显示 CP，蓝白配色 */}
            {!collapsed ? (
                <span>
                    <span style={{ color: '#1890ff' }}>Class</span>
                    <span style={{ color: '#333' }}>Push</span>
                </span>
            ) : (
                <span>
                    <span style={{ color: '#1890ff' }}>C</span>
                    <span style={{ color: '#333' }}>P</span>
                </span>
            )}
        </div>
        <Menu
          theme="light" // 修改主题为 light
          mode="inline"
          selectedKeys={[selectedKey]}
          onClick={({ key }) => {
              setSelectedKey(key);
              if (isMobile) setCollapsed(true);
          }}
          style={{ borderRight: 0 }} // 去除菜单默认右边框
          items={[
            {
              key: 'dashboard',
              icon: <DashboardOutlined />,
              label: '仪表盘',
            },
            {
              key: 'preview',
              icon: <CalendarOutlined />,
              label: '课表预览',
            },
            {
              key: 'settings',
              icon: <SettingOutlined />,
              label: '设置',
            },
            {
              key: 'about',
              icon: <InfoCircleOutlined />,
              label: '关于',
            },
          ]}
        />
        {/* 底部折叠按钮 */}
        <div style={{
            position: 'absolute',
            bottom: 0,
            width: '100%',
            padding: '12px 0',
            borderTop: '1px solid #f0f0f0',
            textAlign: 'center',
            cursor: 'pointer',
            background: '#fff', // 确保背景色
        }} onClick={() => setCollapsed(!collapsed)}>
             {/* 3. 将收起按钮换为截图三所示 (LeftOutlined / RightOutlined) */}
             {collapsed ? <RightOutlined style={{ color: '#999', fontSize: 14 }} /> : <LeftOutlined style={{ color: '#999', fontSize: 14 }} />}
        </div>
      </Sider>
      <Layout style={{ marginLeft: collapsed ? (isMobile ? 0 : 80) : (isMobile ? 0 : 200), transition: 'all 0.2s' }}>
        <Header style={{ padding: 0, background: '#fff', display: 'flex', alignItems: 'center' }}>
            {/* 顶部折叠按钮已移到底部，这里可以保留或移除，根据设计图不需要顶部折叠按钮了，或者保留作为备用 */}
            {/* 这里为了符合设计图，可以移除顶部的折叠按钮，或者保留但修改样式 */}
            {/* 考虑到用户需求是“功能切换栏下面加一个收起按钮”，通常指侧边栏底部 */}
            {/* 顶部的折叠按钮先保留，因为侧边栏底部的按钮在移动端可能不好点 */}
          
          <div style={{ fontSize: 18, fontWeight: 'bold', marginLeft: 24 }}> {/* 增加左边距 */}
            {selectedKey === 'dashboard' && '仪表盘'}
            {selectedKey === 'preview' && '课表预览'}
            {selectedKey === 'settings' && '设置'}
            {selectedKey === 'about' && '关于'}
          </div>
        </Header>
        <Content
          style={{
            margin: '24px 16px',
            padding: 24,
            minHeight: 280,
            background: '#f0f2f5', // 稍微灰一点的背景，让卡片更突出
            overflowY: 'auto'
          }}
        >
          {renderContent()}
        </Content>
      </Layout>
    </Layout>
  );
};

export default App;
