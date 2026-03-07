import React, { useEffect, useState } from 'react';
import { Card, Button, Row, Col, message, Typography, List, Modal } from 'antd';
import { ThunderboltFilled, CalendarOutlined, CopyOutlined, DeleteOutlined, RightOutlined, DownOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { api } from '../api';
import dayjs from 'dayjs';
import type { AppConfig, SystemStatusData } from '../types';

const { Text } = Typography;

let activeMissedPushModal: ReturnType<typeof Modal.confirm> | null = null;

interface DashboardPageProps {
    onNavigate?: (key: string) => void;
}

import { APP_VERSION, VERSION_JSON_URL } from '../constants';

import { compareVersions, cleanVersion } from '../utils';

const DashboardPage: React.FC<DashboardPageProps> = ({ onNavigate }) => {
    const [loading, setLoading] = useState(false);
    const [config, setConfig] = useState<Partial<AppConfig>>({});
    const [logs, setLogs] = useState<string[]>([]);
    const [schedulerActive, setSchedulerActive] = useState(false);
    const [expandLogs, setExpandLogs] = useState(false);
    const [lastManualPushDate, setLastManualPushDate] = useState<string>(() => {
        try {
            return localStorage.getItem('last_manual_push_date') || '';
        } catch {
            return '';
        }
    });
    
    // 初始化加载
    useEffect(() => {
        const loadData = async () => {
            try {
                // 0. 检查更新 (轻量级)
                try {
                    const versionRes = await fetch(VERSION_JSON_URL);
                    const versionData = await versionRes.json();
                    
                    // 当前版本 (从常量获取)
                    const currentVersion = APP_VERSION;
                    
                    // 使用 compareVersions 进行版本号大小比较
                    // 如果远程版本 > 本地版本
                    if (compareVersions(versionData.version, currentVersion) > 0) {
                        
                        // 检查用户是否已在本次会话中选择了忽略该版本
                        const ignoredVersion = sessionStorage.getItem('ignored_update_version');
                        if (ignoredVersion === versionData.version) {
                            return; // 用户已忽略此版本，不再弹窗
                        }

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
                                        提示：新版安装包支持直接覆盖安装，无需卸载旧版，且会自动保留您的配置。
                                    </p>
                                </div>
                            ),
                            okText: '立即更新',
                            cancelText: '暂不更新',
                            onCancel: () => {
                                // 记录用户已忽略此版本，本次会话不再提示
                                sessionStorage.setItem('ignored_update_version', versionData.version);
                            },
                            onOk: () => {
                                window.open(versionData.download_url, '_blank');
                            }
                        });
                    }
                } catch (e) {
                    // 检查更新失败不影响主流程，忽略即可
                    console.warn('检查更新失败', e);
                }

                // 1. 获取配置信息 (推送时间等)
                const configRes = await api.getConfig();
                const configData = configRes.status === 'success' && configRes.data ? configRes.data : undefined;
                if (configData) setConfig(configData);

                // 2. 获取系统状态
                const statusRes = await api.getSystemStatus();
                const statusData = statusRes.status === 'success' && statusRes.data ? statusRes.data : undefined;
                if (statusData) setSchedulerActive(statusData.scheduler_active);
                
                // 3. 模拟加载日志 (实际应从后端读取)
                setLogs([
                    `${dayjs().format('YYYY-MM-DD HH:mm:ss')} [INFO] 系统启动成功`,
                    `${dayjs().format('YYYY-MM-DD HH:mm:ss')} [INFO] 检查更新: 当前已是最新版本`,
                    `${dayjs().format('YYYY-MM-DD HH:mm:ss')} [INFO] 计划任务已加载: 每天 ${configData?.push_time || '07:00'} 执行`
                ]);

                // 4. 健康检查：检测是否错过了今日推送
                checkMissedPush(configData, statusData);

            } catch (e) {
                console.error(e);
            }
        };
        loadData();
    }, []);

    const checkMissedPush = (configData?: Partial<AppConfig>, statusData?: SystemStatusData) => {
        if (!statusData) return;
        if (!statusData.scheduler_active) return;
        if (!configData) return;

        const lastIgnoredDate = typeof configData.last_ignored_push_date === 'string' ? configData.last_ignored_push_date : '';
        const lastPushStr = typeof configData.last_push_success_time === 'string' ? configData.last_push_success_time : '';
        const pushTimeStr = typeof configData.push_time === 'string' && configData.push_time ? configData.push_time : '07:00';
        
        const now = dayjs();
        const todayStr = now.format('YYYY-MM-DD');

        if (lastIgnoredDate === todayStr) {
            return;
        }
        
        // 解析上次推送日期
        let lastPushDate = '';
        if (lastPushStr) {
            const parsed = dayjs(lastPushStr);
            if (parsed.isValid()) {
                lastPushDate = parsed.format('YYYY-MM-DD');
            }
        }

        // 如果今天还没推送过
        if (lastPushDate !== todayStr) {
            // 检查是否已经过了设定的推送时间
            const timeParts = pushTimeStr.split(':').map((x: string) => Number(x));
            const pushHour = timeParts.length >= 1 && Number.isFinite(timeParts[0]) ? timeParts[0] : 7;
            const pushMinute = timeParts.length >= 2 && Number.isFinite(timeParts[1]) ? timeParts[1] : 0;
            const safeHour = Math.min(23, Math.max(0, Math.trunc(pushHour)));
            const safeMinute = Math.min(59, Math.max(0, Math.trunc(pushMinute)));
            const pushTimeToday = now.startOf('day').hour(safeHour).minute(safeMinute).second(0);
            if (!pushTimeToday.isValid()) {
                return;
            }

            // 如果当前时间晚于设定时间超过 30 分钟，且今天没推过
            // 并且设定时间是早上 (避免晚上设定的用户白天打开也被提示) -> 这里的逻辑要和后端保持一致
            // 简单点：只要过了时间没推，就提示。用户可以选择不推。
            if (now.diff(pushTimeToday, 'minute') > 30) {
                if (activeMissedPushModal) {
                    activeMissedPushModal.destroy();
                    activeMissedPushModal = null;
                }

                activeMissedPushModal = Modal.confirm({
                    title: '补发提醒',
                    icon: <ExclamationCircleOutlined />,
                    content: `检测到今日 (${todayStr}) 尚未执行自动推送任务（设定时间 ${pushTimeStr}），是否立即补发？`,
                    okText: '立即推送',
                    cancelText: '忽略',
                    onOk: async () => {
                        try {
                            setConfig(prev => ({ ...(prev || {}), last_ignored_push_date: todayStr }));
                            await api.ignoreMissedPush(todayStr);
                        } catch (e) {
                            console.warn('忽略状态保存失败', e);
                        } finally {
                            activeMissedPushModal = null;
                        }
                        handleManualPush();
                    },
                    onCancel: async () => {
                        try {
                            setConfig(prev => ({ ...(prev || {}), last_ignored_push_date: todayStr }));
                            await api.ignoreMissedPush(todayStr);
                        } catch (e) {
                            console.warn('忽略状态保存失败', e);
                        } finally {
                            activeMissedPushModal = null;
                        }
                    }
                });
            }
        }
    };

    const handleToggleScheduler = async () => {
        setLoading(true);
        try {
            const newState = !schedulerActive;
            const res = await api.toggleScheduler(newState);
            if (res.status === 'success') {
                setSchedulerActive(newState);
                message.success(res.message);
                setLogs(prev => [`${dayjs().format('YYYY-MM-DD HH:mm:ss')} [INFO] ${res.message}`, ...prev]);
            } else {
                message.error(res.message);
            }
        } catch (e) {
            message.error('操作失败');
        } finally {
            setLoading(false);
        }
    };

    const doManualPush = async (force: boolean) => {
        setLoading(true);
        try {
            const res = await api.manualPush(force);
            if (res.status === 'success') {
                const todayStr = dayjs().format('YYYY-MM-DD');
                try {
                    localStorage.setItem('last_manual_push_date', todayStr);
                } catch {
                }
                setLastManualPushDate(todayStr);
                message.success('推送成功，请留意手机消息');
                setLogs(prev => [`${dayjs().format('YYYY-MM-DD HH:mm:ss')} [INFO] 手动触发推送任务`, ...prev]);
            } else {
                message.error(res.message || '推送失败');
            }
        } catch (e) {
            message.error('调用失败');
        } finally {
            setLoading(false);
        }
    };

    const handleManualPush = async () => {
        const todayStr = dayjs().format('YYYY-MM-DD');
        const pushedToday = lastManualPushDate === todayStr;
        if (!pushedToday) {
            await doManualPush(false);
            return;
        }

        Modal.confirm({
            title: '今日已推送过',
            icon: <ExclamationCircleOutlined />,
            content: `系统检测到今日 (${todayStr}) 已经成功执行过推送任务。是否强制再次推送？`,
            okText: '强制推送',
            cancelText: '取消',
            onOk: async () => {
                await doManualPush(true);
            }
        });
    };

    // 计算倒计时
    const getNextPushTime = () => {
        const pushTime = config.push_time || '07:00';
        const now = dayjs();
        let next = dayjs(`${now.format('YYYY-MM-DD')} ${pushTime}`, 'YYYY-MM-DD HH:mm');
        
        if (next.isBefore(now)) {
            next = next.add(1, 'day');
        }
        
        const diffHours = next.diff(now, 'hour');
        const diffMinutes = next.diff(now, 'minute') % 60;
        
        // 格式化显示：今天/明天
        const dayStr = next.isSame(now, 'day') ? '今天' : '明天';
        
        return `${dayStr} ${pushTime} (${diffHours}小时${diffMinutes}分后)`;
    };

    return (
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
            {/* 顶部标题栏 - 已移除，统一在 App Header 显示 */}
            
            <Row gutter={[20, 20]}>
                {/* 左上：下次推送 */}
                <Col xs={24} md={10}>
                    <Card 
                        bordered={false}
                        style={{ height: '100%', borderRadius: 12, boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}
                        bodyStyle={{ padding: 24, height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}
                    >
                        <div>
                            <Text type="secondary" strong>下次推送</Text>
                            <div style={{ fontSize: 48, fontWeight: 800, margin: '10px 0', color: '#262626', lineHeight: 1 }}>
                                {config.push_time || '07:00'}
                            </div>
                            <Text type="secondary">每日推送</Text>
                        </div>
                        <div style={{ marginTop: 20 }}>
                            <div style={{ color: '#8c8c8c', marginBottom: 4 }}>
                                下次执行：{getNextPushTime()}
                            </div>
                            <div style={{ color: '#8c8c8c' }}>
                                上次推送：<Text type="success">成功</Text> · {dayjs().format('MM-DD HH:mm')} · 推送成功
                            </div>
                        </div>
                    </Card>
                </Col>

                {/* 右上：服务状态 */}
                <Col xs={24} md={14}>
                    <Card 
                        bordered={false}
                        style={{ height: '100%', borderRadius: 12, boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}
                        bodyStyle={{ padding: 24 }}
                    >
                        <Text type="secondary" strong>服务状态</Text>
                        
                        <div style={{ marginTop: 20, marginBottom: 30 }}>
                            <div style={{ display: 'flex', alignItems: 'center', marginBottom: 10 }}>
                                <span style={{ width: 8, height: 8, borderRadius: '50%', background: schedulerActive ? '#52c41a' : '#ff4d4f', marginRight: 10 }}></span>
                                <Text strong style={{ fontSize: 16 }}>{schedulerActive ? '运行中' : '已停止'}</Text>
                            </div>
                            <Text type="secondary">计划任务状态：{schedulerActive ? '已安装 (启用)' : '未安装 (已停止)'}</Text>
                        </div>

                        <Button 
                            danger={schedulerActive}
                            type="primary" 
                            block 
                            style={{ height: 40, borderRadius: 8, fontSize: 15 }}
                            onClick={handleToggleScheduler}
                        >
                            {schedulerActive ? '停止自动推送' : '开启自动推送'}
                        </Button>
                    </Card>
                </Col>

                {/* 中间：快捷操作 */}
                <Col span={24}>
                    <Card 
                        bordered={false}
                        title="快捷操作"
                        headStyle={{ borderBottom: 'none', padding: '24px 24px 0', fontSize: 16, fontWeight: 'bold' }}
                        style={{ borderRadius: 12, boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}
                        bodyStyle={{ padding: 24 }}
                    >
                        <Row gutter={16}>
                            <Col span={6}>
                                <Button 
                                    type="primary" 
                                    block 
                                    icon={<ThunderboltFilled />} 
                                    loading={loading}
                                    onClick={handleManualPush}
                                    style={{ height: 45, borderRadius: 8, fontSize: 15 }}
                                >
                                    立即推送
                                </Button>
                            </Col>
                            <Col span={6}>
                                <Button 
                                    block 
                                    icon={<CalendarOutlined />} 
                                    style={{ height: 45, borderRadius: 8, fontSize: 15, borderColor: '#1890ff', color: '#1890ff' }}
                                    onClick={() => onNavigate?.('preview')}
                                >
                                    预览课表
                                </Button>
                            </Col>
                            <Col span={6}>
                                <Button 
                                    block 
                                    icon={<CopyOutlined />} 
                                    style={{ height: 45, borderRadius: 8, fontSize: 15, borderColor: '#1890ff', color: '#1890ff' }}
                                    onClick={() => {
                                        navigator.clipboard.writeText(logs.join('\n'));
                                        message.success('日志已复制');
                                    }}
                                >
                                    复制日志
                                </Button>
                            </Col>
                            <Col span={6}>
                                <Button 
                                    block 
                                    icon={<DeleteOutlined />} 
                                    style={{ height: 45, borderRadius: 8, fontSize: 15, borderColor: '#ff4d4f', color: '#ff4d4f' }}
                                    onClick={() => setLogs([])}
                                >
                                    清除日志
                                </Button>
                            </Col>
                        </Row>
                    </Card>
                </Col>

                {/* 底部：最近日志 */}
                <Col span={24}>
                    <Card 
                        bordered={false}
                        title="最近日志"
                        headStyle={{ borderBottom: 'none', padding: '24px 24px 0', fontSize: 18, fontWeight: 'bold', color: '#333' }}
                        style={{ borderRadius: 12, boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}
                        bodyStyle={{ padding: '12px 24px 24px' }}
                    >
                         <div 
                            style={{ 
                                marginBottom: 12, 
                                cursor: 'pointer', 
                                color: '#333', 
                                fontSize: 14, 
                                display: 'flex', 
                                alignItems: 'center',
                                fontWeight: 500
                            }}
                            onClick={() => setExpandLogs(!expandLogs)}
                        >
                            {expandLogs ? <DownOutlined style={{ marginRight: 6, fontSize: 12 }} /> : <RightOutlined style={{ marginRight: 6, fontSize: 12 }} />}
                            {expandLogs ? '收起' : '展开'}
                        </div>

                        {expandLogs && (
                            <div style={{ 
                                background: '#f8f9fa', // 浅灰白背景
                                borderRadius: 8, 
                                padding: '16px',
                                fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial",
                                fontSize: 13,
                                color: '#333',
                                border: '1px solid #e8e8e8', // 浅色边框
                                height: 350,
                                overflowY: 'auto',
                                // boxShadow: 'inset 0 0 10px rgba(0,0,0,0.02)' // 移除深色阴影
                            }}>
                                {logs.length > 0 ? (
                                    <List
                                        size="small"
                                        dataSource={logs}
                                        split={false}
                                        renderItem={item => {
                                            // 尝试解析日志格式: YYYY-MM-DD HH:mm:ss [LEVEL] Msg
                                            const match = item.match(/^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})\s+(?:\[(.*?)\]\s*)?(.*)$/);
                                            let time = '';
                                            let level = 'INFO';
                                            let msg = item;
                                            
                                            if (match) {
                                                time = match[2]; // HH:mm:ss
                                                if (match[3]) level = match[3].trim();
                                                msg = match[4];
                                            }
                                            
                                            const isError = level.includes('ERROR');
                                            
                                            return (
                                                <List.Item style={{ padding: '6px 0', borderBottom: '1px dashed #f0f0f0' }}>
                                                    <div style={{ display: 'flex', width: '100%' }}>
                                                        {time && (
                                                            <span style={{ 
                                                                color: '#8c8c8c', 
                                                                marginRight: 12, 
                                                                fontFamily: 'Monaco, monospace',
                                                                fontSize: 12,
                                                                minWidth: 60
                                                            }}>
                                                                {time}
                                                            </span>
                                                        )}
                                                        <span style={{ 
                                                            color: isError ? '#ff4d4f' : '#1890ff', // 蓝色/红色主题
                                                            marginRight: 8,
                                                            fontWeight: 500
                                                        }}>
                                                            [{level}]
                                                        </span>
                                                        <span style={{ color: '#262626', flex: 1, wordBreak: 'break-all' }}>
                                                            {msg}
                                                        </span>
                                                    </div>
                                                </List.Item>
                                            );
                                        }}
                                    />
                                ) : (
                                    <div style={{ textAlign: 'center', color: '#999', padding: '40px 0' }}>暂无日志</div>
                                )}
                            </div>
                        )}
                    </Card>
                </Col>
            </Row>
        </div>
    );
};

export default DashboardPage;
