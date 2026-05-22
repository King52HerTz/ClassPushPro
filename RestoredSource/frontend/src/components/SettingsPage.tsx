import React, { useEffect, useState } from 'react';
import { Form, Button, Switch, TimePicker, DatePicker, Input, Select, message, Card, Typography, Space, Divider } from 'antd';
import { api } from '../api';
import { SaveOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import type { SettingsFormValues } from '../types';

const { Text } = Typography;

const DEFAULT_TIME_SLOTS = {
    '1-2': ['08:30', '10:05'],
    '3-4': ['10:25', '12:00'],
    '5-6': ['14:00', '15:35'],
    '7-8': ['15:55', '17:30'],
    '9-10': ['19:00', '20:35'],
    '11-12': ['20:45', '22:20']
} as const;

const TIME_SLOT_FIELDS = [
    { key: '1-2', name: 'time_slot_1_2', label: '1-2 节' },
    { key: '3-4', name: 'time_slot_3_4', label: '3-4 节' },
    { key: '5-6', name: 'time_slot_5_6', label: '5-6 节' },
    { key: '7-8', name: 'time_slot_7_8', label: '7-8 节' },
    { key: '9-10', name: 'time_slot_9_10', label: '9-10 节' },
    { key: '11-12', name: 'time_slot_11_12', label: '11-12 节' }
] as const;

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
                    const timeSlots = data.time_slots || {};
                    const timeSlotValues = Object.fromEntries(
                        TIME_SLOT_FIELDS.map(item => {
                            const slot = timeSlots[item.key] || DEFAULT_TIME_SLOTS[item.key];
                            return [item.name, `${slot[0]}-${slot[1]}`];
                        })
                    );
                    form.setFieldsValue({
                        ...data,
                        push_time: data.push_time ? dayjs(data.push_time, 'HH:mm') : dayjs('20:00', 'HH:mm'),
                        auto_start: data.auto_start || false,
                        grade_push_enabled: Boolean(data.grade_push_enabled),
                        grade_check_interval_minutes: Number(data.grade_check_interval_minutes ?? 30),
                        grade_check_start_time: data.grade_check_start_time ? dayjs(data.grade_check_start_time, 'HH:mm') : dayjs('07:00', 'HH:mm'),
                        grade_check_end_time: data.grade_check_end_time ? dayjs(data.grade_check_end_time, 'HH:mm') : dayjs('23:00', 'HH:mm'),
                        semester_start_date: data.semester_start_date ? dayjs(data.semester_start_date, 'YYYY-MM-DD') : undefined,
                        calendar_alarm_minutes: Number(data.calendar_alarm_minutes ?? 15),
                        ...timeSlotValues
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
            const timeSlots = Object.fromEntries(
                TIME_SLOT_FIELDS.map(item => {
                    const rawValue = String(values[item.name] || '').trim();
                    const matched = rawValue.match(/^([0-2]\d:\d{2})\s*-\s*([0-2]\d:\d{2})$/);
                    if (!matched) {
                        throw new Error(`${item.label} 时间格式应为 HH:mm-HH:mm`);
                    }
                    return [item.key, [matched[1], matched[2]] as [string, string]];
                })
            ) as Record<string, [string, string]>;
            const configData = {
                ...currentConfig.data, // 保留原有的账号密码等信息
                ...values,
                push_time: values.push_time.format('HH:mm'),
                auto_start: values.auto_start,
                grade_push_enabled: Boolean(values.grade_push_enabled),
                grade_check_interval_minutes: Number(values.grade_check_interval_minutes ?? 30),
                grade_check_start_time: values.grade_check_start_time ? values.grade_check_start_time.format('HH:mm') : '07:00',
                grade_check_end_time: values.grade_check_end_time ? values.grade_check_end_time.format('HH:mm') : '23:00',
                semester_start_date: values.semester_start_date ? values.semester_start_date.format('YYYY-MM-DD') : '',
                calendar_alarm_minutes: Number(values.calendar_alarm_minutes ?? 15),
                time_slots: timeSlots
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
                    <Divider style={{ margin: '20px 0' }} />
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                            <Text style={{ color: '#666', display: 'block' }}>新成绩自动推送</Text>
                            <Text type="secondary" style={{ fontSize: 12 }}>成绩会在设定时段内按固定间隔自动检查；首次启用只建立基线，不推历史成绩。</Text>
                        </div>
                        <Form.Item name="grade_push_enabled" valuePropName="checked" style={{ marginBottom: 0 }}>
                            <Switch checkedChildren="开" unCheckedChildren="关" />
                        </Form.Item>
                    </div>
                    <Divider style={{ margin: '20px 0' }} />
                    <Form.Item
                        label={<span style={{ color: '#666' }}>成绩检查间隔</span>}
                        name="grade_check_interval_minutes"
                        tooltip="仅对成绩自动推送生效，推荐 30 分钟。"
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
                            tooltip="仅在这个时间之后执行成绩轮询。"
                        >
                            <TimePicker format="HH:mm" style={{ width: '100%', borderRadius: 12, height: 40 }} />
                        </Form.Item>
                        <Form.Item
                            label={<span style={{ color: '#666' }}>成绩检查结束时间</span>}
                            name="grade_check_end_time"
                            tooltip="超过这个时间后停止当天成绩轮询。"
                        >
                            <TimePicker format="HH:mm" style={{ width: '100%', borderRadius: 12, height: 40 }} />
                        </Form.Item>
                    </div>
                    <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
                        当前建议使用 `30 分钟`、`07:00-23:00`。首次启用时仅建立成绩基线，不会把历史成绩一次性推送到手机。
                    </Text>
                </Card>

                <Card title="日历导出" style={{ marginBottom: 20, borderRadius: 8 }} bodyStyle={{ padding: '24px' }}>
                    <Form.Item
                        label={<span style={{ color: '#666' }}>学期第 1 周周一日期</span>}
                        name="semester_start_date"
                        tooltip="ICS 需要根据这个日期推算每门课的具体上课日期，请填写开学第一周的周一。"
                    >
                        <DatePicker
                            format="YYYY-MM-DD"
                            style={{ width: '100%', borderRadius: 12, height: 40 }}
                            placeholder="请选择周一日期"
                        />
                    </Form.Item>
                    <Form.Item
                        label={<span style={{ color: '#666' }}>导入日历后的提醒时间</span>}
                        name="calendar_alarm_minutes"
                        tooltip="会写入 ICS 文件，支持的日历在导入后会默认带上这个提醒时间。"
                    >
                        <Select
                            options={CALENDAR_ALARM_OPTIONS}
                            style={{ width: '100%' }}
                            placeholder="请选择提醒时间"
                        />
                    </Form.Item>
                    <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
                        建议优先使用 `15 分钟`。部分手机日历只支持 `5/10/15/30/60` 这类固定档位，`20 分钟` 可能会被忽略或改写。
                    </Text>
                    <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
                        节次时间表格式为 `HH:mm-HH:mm`，例如 `08:30-10:05`。
                    </Text>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
                        {TIME_SLOT_FIELDS.map(item => (
                            <Form.Item
                                key={item.key}
                                label={<span style={{ color: '#666' }}>{item.label}</span>}
                                name={item.name}
                                rules={[
                                    { required: true, message: `请输入 ${item.label} 时间` },
                                    { pattern: /^([0-2]\d:\d{2})\s*-\s*([0-2]\d:\d{2})$/, message: '格式应为 HH:mm-HH:mm' }
                                ]}
                            >
                                <Input
                                    placeholder={`${DEFAULT_TIME_SLOTS[item.key][0]}-${DEFAULT_TIME_SLOTS[item.key][1]}`}
                                    style={{ borderRadius: 12, height: 40 }}
                                />
                            </Form.Item>
                        ))}
                    </div>
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
