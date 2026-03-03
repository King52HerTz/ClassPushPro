import React, { useState } from 'react';
import { Modal, Form, Input, Button, message, Typography, Popover, Image } from 'antd';
import { UserOutlined, LockOutlined, KeyOutlined, CopyOutlined, GlobalOutlined } from '@ant-design/icons';
import { api } from '../api';
import type { ConfigInput, LoginFormValues } from '../types';

const { Text } = Typography;

interface LoginModalProps {
    visible: boolean;
    onSuccess: () => void;
    onCancel?: () => void; // Optional, e.g. for re-login
    canCancel?: boolean;
}

const LoginModal: React.FC<LoginModalProps> = ({ visible, onSuccess, onCancel }) => {
    const [form] = Form.useForm();
    const [loading, setLoading] = useState(false);

    // 每次弹窗显示时，尝试加载旧数据
    React.useEffect(() => {
        if (visible) {
            const loadOldData = async () => {
                try {
                    const res = await api.getConfig();
                    if (res.status === 'success' && res.data) {
                        form.setFieldsValue({
                            username: res.data.username || '',
                            password: res.data.password || '',
                            uid: res.data.uid || ''
                        });
                    }
                } catch (e) {
                    // ignore
                }
            };
            loadOldData();
        }
    }, [visible, form]);

    const handleLogin = async (values: LoginFormValues) => {
        setLoading(true);
        try {
            // 1. 测试登录教务系统
            const loginRes = await api.loginTest(values.username, values.password);
            if (loginRes.status !== 'success') {
                message.error('教务系统登录失败: ' + loginRes.message);
                setLoading(false);
                return;
            }

            // 2. 保存配置
            const configToSave: ConfigInput = {
                username: values.username,
                password: values.password,
                uid: values.uid,
                app_token: "", // 不再硬编码 Token
                push_time: "07:00", // 默认值
                auto_start: false
            };

            // 我们可以先尝试获取配置
            try {
                const currentConfig = await api.getConfig();
                if (currentConfig.status === 'success' && currentConfig.data) {
                    configToSave.push_time = currentConfig.data.push_time || "07:00";
                    configToSave.auto_start = currentConfig.data.auto_start || false;
                    // 如果代码里硬编码了 Token，就用硬编码的，否则用原来的
                    // configToSave.app_token = currentConfig.data.app_token || "AT_...";
                }
            } catch (e) {
                // ignore
            }

            const saveRes = await api.saveConfig(configToSave);
            if (saveRes.status === 'success') {
                message.success('登录成功并已保存');
                onSuccess();
            } else {
                message.error('保存配置失败: ' + saveRes.message);
            }

        } catch (e) {
            message.error('操作异常');
        } finally {
            setLoading(false);
        }
    };

    const howToGetUidContent = (
        <div style={{ maxWidth: 300 }}>
            <p>1. 关注公众号：扫描下方二维码关注“WxPusher消息推送平台”，系统将自动发送您的 UID (形如 UID_xxx)，请复制保存。</p>
            <p>2. 下载APP：在应用商店搜索并下载“WxPusher”，使用微信登录即可接收课程推送。</p>
            <div style={{ marginBottom: 10 }}>
                <Button size="small" icon={<CopyOutlined />} onClick={() => {
                    navigator.clipboard.writeText("https://wxpusher.zjiecode.com/api/qrcode/uOkIOIyXg2AZRnwPRIVN78NLBXQaOxIlWs3QsRCoj4kZkyIidI7sFFrEGriCoftn.jpg");
                    message.success("链接已复制");
                }}>复制链接</Button>
                <Button size="small" type="primary" icon={<GlobalOutlined />} style={{ marginLeft: 8 }} onClick={() => window.open("https://wxpusher.zjiecode.com/api/qrcode/uOkIOIyXg2AZRnwPRIVN78NLBXQaOxIlWs3QsRCoj4kZkyIidI7sFFrEGriCoftn.jpg", "_blank")}>打开网页</Button>
            </div>
            <div style={{ textAlign: 'center' }}>
                <Image 
                    width={150} 
                    src="https://wxpusher.zjiecode.com/api/qrcode/uOkIOIyXg2AZRnwPRIVN78NLBXQaOxIlWs3QsRCoj4kZkyIidI7sFFrEGriCoftn.jpg" 
                    alt="WxPusher QRCode"
                />
            </div>
        </div>
    );

    return (
        <Modal
            title="登录"
            open={visible}
            onCancel={onCancel} // 始终允许点击遮罩或ESC触发取消
            footer={null}
            closable={true} // 始终显示关闭按钮
            maskClosable={true} // 始终允许点击遮罩关闭
            centered
            // closeIcon={null} // 移除这行，让默认的 X 图标显示出来
        >
            <Text type="secondary" style={{ display: 'block', marginBottom: 20 }}>
                首次登录后将安全存储在本机，后续启动自动静默登录。
            </Text>

            <Form form={form} layout="vertical" onFinish={handleLogin}>
                <Form.Item 
                    label="学号" 
                    name="username" 
                    rules={[{ required: true, message: '请输入学号' }]}
                >
                    <Input prefix={<UserOutlined />} placeholder="请输入学号" />
                </Form.Item>

                <Form.Item 
                    label="密码" 
                    name="password" 
                    rules={[{ required: true, message: '请输入密码' }]}
                >
                    <Input.Password prefix={<LockOutlined />} placeholder="请输入密码" />
                </Form.Item>

                <Form.Item 
                    label={
                        <span>
                            UID 
                            <Popover content={howToGetUidContent} title="如何获取 UID" trigger="click">
                                <Button type="link" size="small" style={{ paddingLeft: 4 }}>如何获取 UID</Button>
                            </Popover>
                        </span>
                    } 
                    name="uid" 
                    rules={[{ required: true, message: '请输入 UID' }]}
                >
                    <Input prefix={<KeyOutlined />} placeholder="请输入 UID" />
                </Form.Item>

                <Form.Item>
                    <Button type="primary" htmlType="submit" loading={loading} block style={{ height: 40, backgroundColor: '#52c41a', borderColor: '#52c41a' }}>
                        登录并保存
                    </Button>
                </Form.Item>
            </Form>
        </Modal>
    );
};

export default LoginModal;
