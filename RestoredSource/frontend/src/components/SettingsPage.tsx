import React, { useEffect, useState } from 'react';
import { Form, Button, Switch, TimePicker, DatePicker, Select, message, Card, Typography, Space, Divider, Popover } from 'antd';
import { api } from '../api';
import { SaveOutlined, QuestionCircleOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import type { SettingsFormValues } from '../types';

const { Text } = Typography;

const CALENDAR_ALARM_OPTIONS = [
    { label: '关闭提醒', value: 0 },
    { label: '提前 5 分钟', value: 5 },
    { label: '提前 10 分钟', value: 10 },
    { label: '提前 15 分钟（推荐）', value: 15 },
    { label: '提前 20 分钟', value: 20 },
    { label: '提前 30 分钟', value: 30 },
    { label: '提前 60 分钟', value: 60 }
];

const GRADE_CHECK_INTERVAL_OPTIONS = [
    { label: '15 分钟', value: 15 },
    { label: '30 分钟（推荐）', value: 30 },
    { label: '60 分钟', value: 60 },
    { label: '120 分钟', value: 120 }
];

interface SettingsPageProps {
    onLogout?: () => void;
    isLoggedIn?: boolean;
}

const renderCardTitle = (title: string, details: string[]) => (
    <Popover
        trigger="click"
        placement="bottomLeft"
        overlayStyle={{ maxWidth: 320 }}
        content={
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {details.map((detail) => (
                    <Text key={detail} type="secondary" style={{ fontSize: 12 }}>
                        {detail}
                    </Text>
                ))}
            </div>
        }
    >
        <Space size={6} style={{ cursor: 'pointer', userSelect: 'none' }}>
            <span>{title}</span>
            <QuestionCircleOutlined style={{ color: '#8c8c8c' }} />
            <Text type="secondary" style={{ fontSize: 12 }}>
                点击查看说明
            </Text>
        </Space>
    </Popover>
);

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
                        auto_start: data.auto_start || false,
                        weather_enabled: Boolean(data.weather_enabled),
                        grade_push_enabled: Boolean(data.grade_push_enabled),
                        grade_check_interval_minutes: Number(data.grade_check_interval_minutes ?? 30),
                        grade_check_start_time: data.grade_check_start_time ? dayjs(data.grade_check_start_time, 'HH:mm') : dayjs('07:00', 'HH:mm'),
                        grade_check_end_time: data.grade_check_end_time ? dayjs(data.grade_check_end_time, 'HH:mm') : dayjs('23:00', 'HH:mm'),
                        semester_start_date: data.semester_start_date ? dayjs(data.semester_start_date, 'YYYY-MM-DD') : undefined,
                        calendar_alarm_minutes: Number(data.calendar_alarm_minutes ?? 15)
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
                auto_start: values.auto_start,
                weather_enabled: Boolean(values.weather_enabled),
                weather_city: '',
                grade_push_enabled: Boolean(values.grade_push_enabled),
                grade_check_interval_minutes: Number(values.grade_check_interval_minutes ?? 30),
                grade_check_start_time: values.grade_check_start_time ? values.grade_check_start_time.format('HH:mm') : '07:00',
                grade_check_end_time: values.grade_check_end_time ? values.grade_check_end_time.format('HH:mm') : '23:00',
                semester_start_date: values.semester_start_date ? values.semester_start_date.format('YYYY-MM-DD') : '',
                calendar_alarm_minutes: Number(values.calendar_alarm_minutes ?? 15),
                time_slots: null
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
                <Card
                    title={renderCardTitle('账号', ['这里主要看当前登录状态，也可以直接退出后重新登录。'])}
                    style={{ marginBottom: 20, borderRadius: 8 }}
                    bodyStyle={{ padding: '24px' }}
                >
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
                <Card
                    title={renderCardTitle('推送', [
                        '天气会固定使用湖南工学院所在区域，接口异常时会自动降级为只推课表。',
                        '天气服务已经内置在程序里，不需要再额外填写接口参数。',
                        '成绩自动推送首次启用只会建立基线，不会补推历史成绩。',
                        '当前建议使用 30 分钟检查间隔，轮询时段建议为 07:00-23:00。'
                    ])}
                    style={{ marginBottom: 20, borderRadius: 8 }}
                    bodyStyle={{ padding: '24px' }}
                >
                    <Form.Item 
                        label={<span style={{ color: '#666' }}>推送时间</span>} 
                        name="push_time" 
                        required
                    >
                        <TimePicker 
                            format="HH:mm" 
                            style={{ width: '100%', borderRadius: 12, height: 40 }} 
                            placeholder="选择时间"
                        />
                    </Form.Item>
                    <Divider style={{ margin: '20px 0' }} />
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                            <Text style={{ color: '#666', display: 'block' }}>每日课表附加天气</Text>
                        </div>
                        <Form.Item name="weather_enabled" valuePropName="checked" style={{ marginBottom: 0 }}>
                            <Switch checkedChildren="开" unCheckedChildren="关" />
                        </Form.Item>
                    </div>
                    <Divider style={{ margin: '20px 0' }} />
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                            <Text style={{ color: '#666', display: 'block' }}>新成绩自动推送</Text>
                        </div>
                        <Form.Item name="grade_push_enabled" valuePropName="checked" style={{ marginBottom: 0 }}>
                            <Switch checkedChildren="开" unCheckedChildren="关" />
                        </Form.Item>
                    </div>
                    <Divider style={{ margin: '20px 0' }} />
                    <Form.Item
                        label={<span style={{ color: '#666' }}>成绩检查间隔</span>}
                        name="grade_check_interval_minutes"
                    >
                        <Select
                            options={GRADE_CHECK_INTERVAL_OPTIONS}
                            style={{ width: '100%' }}
                            placeholder="请选择检查间隔"
                        />
                    </Form.Item>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
                        <Form.Item
                            label={<span style={{ color: '#666' }}>成绩检查开始时间</span>}
                            name="grade_check_start_time"
                        >
                            <TimePicker format="HH:mm" style={{ width: '100%', borderRadius: 12, height: 40 }} />
                        </Form.Item>
                        <Form.Item
                            label={<span style={{ color: '#666' }}>成绩检查结束时间</span>}
                            name="grade_check_end_time"
                        >
                            <TimePicker format="HH:mm" style={{ width: '100%', borderRadius: 12, height: 40 }} />
                        </Form.Item>
                    </div>
                </Card>

                <Card
                    title={renderCardTitle('日历导出', [
                        '系统会根据教务教学周自动校准第 1 周周一；下方日期只作为无法自动识别时的人工兜底。',
                        '导入日历后的提醒时间会写入 ICS 文件，但部分手机日历可能只支持固定档位。',
                        '建议优先使用 15 分钟，20 分钟在部分手机上可能会被忽略或改写。',
                        '课程节次时间已经写死在程序里，导出时会自动使用默认作息。'
                    ])}
                    style={{ marginBottom: 20, borderRadius: 8 }}
                    bodyStyle={{ padding: '24px' }}
                >
                    <Form.Item
                        label={<span style={{ color: '#666' }}>学期第 1 周周一日期（可选兜底）</span>}
                        name="semester_start_date"
                    >
                        <DatePicker
                            format="YYYY-MM-DD"
                            style={{ width: '100%', borderRadius: 12, height: 40 }}
                            placeholder="通常无需填写，系统会自动校准"
                        />
                    </Form.Item>
                    <Form.Item
                        label={<span style={{ color: '#666' }}>导入日历后的提醒时间</span>}
                        name="calendar_alarm_minutes"
                    >
                        <Select
                            options={CALENDAR_ALARM_OPTIONS}
                            style={{ width: '100%' }}
                            placeholder="请选择提醒时间"
                        />
                    </Form.Item>
                </Card>

                {/* 系统设置 */}
                <Card
                    title={renderCardTitle('系统', ['这里主要是程序本身的运行设置，目前只保留开机自启。'])}
                    style={{ marginBottom: 20, borderRadius: 8 }}
                    bodyStyle={{ padding: '24px' }}
                >
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
