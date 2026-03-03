import React, { useEffect, useState } from 'react';
import { Form, Button, Switch, TimePicker, message, Card, Typography, Space } from 'antd';
import { api } from '../api';
import { SaveOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import type { SettingsFormValues } from '../types';

const { Text } = Typography;

interface SettingsPageProps {
    onLogout?: () => void;
    isLoggedIn?: boolean;
}

const SettingsPage: React.FC<SettingsPageProps> = ({ onLogout, isLoggedIn = true }) => {
    const [form] = Form.useForm();
    const [loading, setLoading] = useState(false);
    // const [isLoggedIn, setIsLoggedIn] = useState(true); // 默认已登录状态 (暂时未使用) -> 现在使用 props

    useEffect(() => {
        const loadConfig = async () => {
            setLoading(true);
            try {
                const res = await api.getConfig();
                if (res.status === 'success' && res.data) {
                    const data = res.data;
                    form.setFieldsValue({
                        ...data,
                        push_time: data.push_time ? dayjs(data.push_time, 'HH:mm') : dayjs('20:00', 'HH:mm'),
                        auto_start: data.auto_start || false
                    });
                }
            } catch (e) {
                message.error('配置加载失败');
            } finally {
                setLoading(false);
            }
        };
        loadConfig();
    }, [form]);

    const onFinish = async (values: SettingsFormValues) => {
        setLoading(true);
        try {
            const currentConfig = await api.getConfig();
            if (currentConfig.status !== 'success' || !currentConfig.data) {
                message.error('配置读取失败');
                return;
            }
            const configData = {
                ...currentConfig.data, // 保留原有的账号密码等信息
                ...values,
                push_time: values.push_time.format('HH:mm'),
                auto_start: values.auto_start
            };
            const res = await api.saveConfig(configData);
            if (res.status === 'success') {
                message.success('配置已保存');
            } else {
                message.error('保存失败: ' + res.message);
            }
        } catch (e) {
            message.error('保存异常');
        } finally {
            setLoading(false);
        }
    };

    const handleLogout = () => {
        // 调用父组件传入的 logout 方法
        if (onLogout) {
            onLogout();
        } else {
            message.info('退出登录功能待实现');
        }
    };

    const handleAutostartChange = async (checked: boolean) => {
        try {
            // 调用后端 API 设置自启动
            const res = await api.setAutostart(checked);
            if (res.status === 'success') {
                message.success(res.message);
                // 更新表单状态
                form.setFieldsValue({ auto_start: checked });
            } else {
                message.error('设置失败: ' + res.message);
                // 恢复开关状态
                form.setFieldsValue({ auto_start: !checked });
            }
        } catch (e) {
            message.error('操作异常');
            form.setFieldsValue({ auto_start: !checked });
        }
    };

    return (
        <div style={{ maxWidth: 800, margin: '0 auto', padding: '0 20px' }}>
            {/* 2. 去掉设置界面下面这个标题栏 (因为 App Header 已经有了) */}
            {/* <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                <h2 style={{ margin: 0 }}>设置</h2>
            </div> */}

            <Form form={form} layout="vertical" onFinish={onFinish}>
                {/* 账号设置 */}
                <Card title="账号" style={{ marginBottom: 20, borderRadius: 8 }} bodyStyle={{ padding: '24px' }}>
                    <div style={{ marginBottom: 20 }}>
                        <Text style={{ color: isLoggedIn ? '#52c41a' : '#ff4d4f', fontSize: 16 }}>
                            当前状态：{isLoggedIn ? '已登录' : '未登录'}
                        </Text>
                    </div>
                    <Space size="middle">
                        {isLoggedIn ? (
                            <Button onClick={handleLogout} danger style={{ borderRadius: 12, padding: '4px 24px' }}>
                                退出登录
                            </Button>
                        ) : (
                            <Button onClick={handleLogout} type="primary" style={{ borderRadius: 12, padding: '4px 24px' }}>
                                登录
                            </Button>
                        )}
                    </Space>
                </Card>

                {/* 推送设置 */}
                <Card title="推送" style={{ marginBottom: 20, borderRadius: 8 }} bodyStyle={{ padding: '24px' }}>
                    <Form.Item 
                        label={<span style={{ color: '#666' }}>推送时间</span>} 
                        name="push_time" 
                        required 
                        tooltip="每天定时推送课表的时间"
                    >
                        <TimePicker 
                            format="HH:mm" 
                            style={{ width: '100%', borderRadius: 12, height: 40 }} 
                            placeholder="选择时间"
                        />
                    </Form.Item>
                </Card>

                {/* 系统设置 */}
                <Card title="系统" style={{ marginBottom: 20, borderRadius: 8 }} bodyStyle={{ padding: '24px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Text style={{ color: '#666' }}>开机自启</Text>
                        <Form.Item name="auto_start" valuePropName="checked" style={{ marginBottom: 0 }}>
                            <Switch 
                                checkedChildren="开" 
                                unCheckedChildren="关" 
                                onChange={handleAutostartChange} 
                            />
                        </Form.Item>
                    </div>
                </Card>

                <Form.Item style={{ marginTop: 30 }}>
                    <Button 
                        type="primary" 
                        htmlType="submit" 
                        loading={loading} 
                        block 
                        icon={<SaveOutlined />}
                        style={{ 
                            height: 45, 
                            borderRadius: 12, 
                            fontSize: 16,
                            // backgroundColor: '#2ecc71', // 移除自定义绿色
                            // borderColor: '#2ecc71'
                        }}
                    >
                        保存设置
                    </Button>
                </Form.Item>
            </Form>
        </div>
    );
};

export default SettingsPage;
