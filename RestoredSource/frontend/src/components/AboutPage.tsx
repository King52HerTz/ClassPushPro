import React from 'react';
import { Card, Typography, Tag, Button, Space, Row, Col, message } from 'antd';
import { 
    GithubOutlined, 
    SyncOutlined, 
    MailOutlined, 
    PlayCircleOutlined, 
    TeamOutlined, 
    BugOutlined,
    UserOutlined
} from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;

const AboutPage: React.FC = () => {
    const iconUrl = './icon.ico';

    const handleOpenLink = (url: string) => {
        window.open(url, '_blank');
    };

    const handleCopy = (text: string) => {
        navigator.clipboard.writeText(text).then(() => {
            message.success('复制成功');
        }).catch(() => {
            message.error('复制失败，请手动复制');
        });
    };

    const handleEmail = () => {
        window.location.href = 'mailto:shdx2024@qq.com';
    };

    return (
        <div style={{ padding: 0 }}>
            {/* 顶部主卡片 */}
            <Card style={{ textAlign: 'center', marginBottom: 24, borderRadius: 12 }}>
                <div style={{ marginBottom: 16 }}>
                    <img
                        src={iconUrl}
                        alt="ClassPush"
                        style={{ width: 100, height: 100, borderRadius: 20, display: 'block', margin: '0 auto' }}
                    />
                </div>
                
                <Title level={2} style={{ marginBottom: 4 }}>ClassPush</Title>
                <Text type="secondary" style={{ fontSize: 16 }}>Keep your classes on time</Text>
                
                <div style={{ margin: '16px 0' }}>
                    <Space>
                        <Tag color="blue">v1.0.0</Tag>
                        <Tag color="green" icon={<UserOutlined />}>开发者: Eliauk</Tag>
                    </Space>
                </div>

                <Paragraph style={{ maxWidth: 600, margin: '0 auto 24px', color: '#666' }}>
                    一款专为大学生设计的桌面端课表推送工具。<br />
                    自动抓取教务系统课表，每天定时推送到WxPusher app，让查课变得简单高效。
                </Paragraph>

                <Space size="large">
                    <Button 
                        type="primary" 
                        icon={<SyncOutlined />} 
                        style={{ backgroundColor: '#52c41a', borderColor: '#52c41a' }}
                        onClick={() => handleOpenLink('https://github.com/King52HerTz/ClassPushPro/releases/latest')}
                    >
                        检查更新
                    </Button>
                    <Button 
                        icon={<GithubOutlined />}
                        onClick={() => handleOpenLink('https://github.com/King52HerTz/ClassPushPro')}
                    >
                        GitHub 仓库
                    </Button>
                </Space>
            </Card>

            {/* 联系方式区域 */}
            <Title level={5} style={{ marginBottom: 16 }}>联系方式</Title>
            
            <Row gutter={[16, 16]}>
                {/* 开发者邮箱 */}
                <Col xs={24} sm={12} md={6}>
                    <Card hoverable style={{ textAlign: 'center', height: '100%', borderRadius: 8 }}>
                        <div style={{ fontSize: 32, color: '#1890FF', marginBottom: 8 }}>
                            <MailOutlined />
                        </div>
                        <div style={{ color: '#888', marginBottom: 4 }}>开发者邮箱</div>
                        <div style={{ fontWeight: 'bold', marginBottom: 16 }}>shdx2024@qq.com</div>
                        <Button size="small" onClick={handleEmail}>发送邮件</Button>
                    </Card>
                </Col>

                {/* B站账号 */}
                <Col xs={24} sm={12} md={6}>
                    <Card hoverable style={{ textAlign: 'center', height: '100%', borderRadius: 8 }}>
                        <div style={{ fontSize: 32, color: '#FB7299', marginBottom: 8 }}>
                            <PlayCircleOutlined />
                        </div>
                        <div style={{ color: '#888', marginBottom: 4 }}>B站账号</div>
                        <div style={{ fontWeight: 'bold', marginBottom: 16 }}>Eilauk_312</div>
                        <Button size="small" onClick={() => handleOpenLink('https://space.bilibili.com/622766790?spm_id_from=333.1387.0.0')}>访问主页</Button>
                    </Card>
                </Col>

                {/* QQ 交流群 */}
                <Col xs={24} sm={12} md={6}>
                    <Card hoverable style={{ textAlign: 'center', height: '100%', borderRadius: 8 }}>
                        <div style={{ fontSize: 32, color: '#12B7F5', marginBottom: 8 }}>
                            <TeamOutlined />
                        </div>
                        <div style={{ color: '#888', marginBottom: 4 }}>QQ 交流群</div>
                        <div style={{ fontWeight: 'bold', marginBottom: 16 }}>1084681551</div>
                        <Button size="small" onClick={() => handleCopy('1084681551')}>复制群号</Button>
                    </Card>
                </Col>

                {/* 问题反馈 */}
                <Col xs={24} sm={12} md={6}>
                    <Card hoverable style={{ textAlign: 'center', height: '100%', borderRadius: 8 }}>
                        <div style={{ fontSize: 32, color: '#FF4D4F', marginBottom: 8 }}>
                            <BugOutlined />
                        </div>
                        <div style={{ color: '#888', marginBottom: 4 }}>问题反馈</div>
                        <div style={{ fontWeight: 'bold', marginBottom: 16 }}>GitHub Issue</div>
                        <Button size="small" onClick={() => handleOpenLink('https://github.com/King52HerTz/ClassPushPro/issues')}>提交反馈</Button>
                    </Card>
                </Col>
            </Row>
        </div>
    );
};

export default AboutPage;
