import React, { useState } from 'react';
import { Card, Typography, Tag, Button, Space, Row, Col, message, Modal } from 'antd';
import { 
    GithubOutlined, 
    GlobalOutlined,
    SyncOutlined, 
    MailOutlined, 
    PlayCircleOutlined, 
    TeamOutlined, 
    BugOutlined,
    UserOutlined,
    ThunderboltFilled
} from '@ant-design/icons';
import { APP_VERSION, APP_NAME, DEVELOPER_NAME, GITHUB_REPO_URL, OFFICIAL_WEBSITE_URL } from '../constants';
import { api } from '../api';

const { Title, Text, Paragraph } = Typography;

import { compareVersions, cleanVersion } from '../utils';

const AboutPage: React.FC = () => {
    const iconUrl = './icon.ico';
    const [checking, setChecking] = useState(false);
    const [downloading, setDownloading] = useState(false);

    const handleOpenLink = (url: string) => {
        window.open(url, '_blank');
    };

    const handleDownloadUpdate = async (downloadPageUrl: string) => {
        setDownloading(true);
        try {
            const downloadRes = await api.downloadUpdate();
            if (downloadRes.status === 'success' && downloadRes.data) {
                message.success(`更新包已下载到：${downloadRes.data.file_path}。请退出软件后运行安装包覆盖更新。`);
                return;
            }
            if (downloadRes.action === 'open_download_page') {
                message.info('当前下载源需要网页验证，已打开官方下载页');
                handleOpenLink(downloadPageUrl);
                return;
            }
            message.error(downloadRes.message || '更新包下载失败，请稍后重试');
        } catch (e) {
            message.error('更新包下载失败，请稍后重试');
        } finally {
            setDownloading(false);
        }
    };

    const handleCheckUpdate = async () => {
        setChecking(true);
        try {
            const versionRes = await api.checkUpdate();
            if (versionRes.status !== 'success' || !versionRes.data) {
                message.error(versionRes.message || '检查更新失败，请稍后重试');
                return;
            }
            const versionData = versionRes.data;
            
            // 当前版本
            const currentVersion = APP_VERSION;
            
            // 使用 compareVersions 进行版本号大小比较
            if (compareVersions(versionData.version, currentVersion) > 0) {
                Modal.confirm({
                    title: `🎉 发现新版本 v${cleanVersion(versionData.version)}`,
                    icon: <ThunderboltFilled style={{ color: '#1890ff' }} />,
                    content: (
                        <div>
                            <p>发布日期: {versionData.release_date}</p>
                            <div style={{ background: '#f5f5f5', padding: '8px', borderRadius: '4px', marginBottom: '10px', whiteSpace: 'pre-line', maxHeight: '100px', overflowY: 'auto' }}>
                                {versionData.changelog}
                            </div>
                            <p style={{ color: '#8c8c8c', fontSize: '12px' }}>
                                提示：新版安装包支持直接覆盖安装，无需卸载旧版。
                            </p>
                        </div>
                    ),
                    okText: '立即更新',
                    cancelText: '暂不更新',
                    onOk: () => handleDownloadUpdate(versionData.download_url)
                });
            } else {
                message.success(`当前已是最新版本 v${currentVersion}`);
            }
        } catch (e) {
            message.error('检查更新失败，请稍后重试');
        } finally {
            setChecking(false);
        }
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
                        alt={APP_NAME}
                        style={{ width: 100, height: 100, borderRadius: 20, display: 'block', margin: '0 auto' }}
                    />
                </div>
                
                <Title level={2} style={{ marginBottom: 4 }}>{APP_NAME}</Title>
                <Text type="secondary" style={{ fontSize: 16 }}>Keep your classes on time</Text>
                
                <div style={{ margin: '16px 0' }}>
                    <Space>
                        <Tag color="blue">v{APP_VERSION}</Tag>
                        <Tag color="green" icon={<UserOutlined />}>开发者: {DEVELOPER_NAME}</Tag>
                    </Space>
                </div>

                <Paragraph style={{ maxWidth: 600, margin: '0 auto 24px', color: '#666' }}>
                    一款专为大学生设计的桌面端课表推送工具。<br />
                    自动抓取教务系统课表，每天定时推送到WxPusher app，让查课变得简单高效。
                </Paragraph>

                <Space size="large">
                    <Button 
                        type="primary" 
                        icon={<SyncOutlined spin={checking} />} 
                        style={{ backgroundColor: '#52c41a', borderColor: '#52c41a' }}
                        onClick={handleCheckUpdate}
                        loading={checking || downloading}
                    >
                        检查更新
                    </Button>
                    <Button 
                        icon={<GithubOutlined />}
                        onClick={() => handleOpenLink(GITHUB_REPO_URL)}
                    >
                        GitHub 仓库
                    </Button>
                    <Button
                        icon={<GlobalOutlined />}
                        onClick={() => handleOpenLink(OFFICIAL_WEBSITE_URL)}
                    >
                        打开官网
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
