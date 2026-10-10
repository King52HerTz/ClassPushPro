import { useEffect, useState } from 'react';
import { Modal, Form, Input, Button, message, Typography } from 'antd';
import { api } from '../api';

interface Props { visible: boolean; onSuccess: () => void; onCancel?: () => void; canCancel?: boolean; }
export default function LoginModal({ visible, onSuccess, onCancel }: Props) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (visible) api.getConfig().then(res => { if (res.data) form.setFieldsValue({ username: res.data.username, password: '' }); });
  }, [visible, form]);
  const login = async (values: {username: string; password: string}) => {
    setLoading(true);
    try {
      const tested = await api.loginTest(values.username, values.password);
      if (tested.status !== 'success') throw new Error(tested.message || '教务登录失败');
      const result = await api.saveConfig(values);
      if (result.status !== 'success') throw new Error(result.message || '保存失败');
      message.success('本地教务登录成功');
      onSuccess();
    } catch (error) { message.error(error instanceof Error ? error.message : '登录失败，请稍后再试'); }
    finally { setLoading(false); }
  };
  return <Modal title="本地教务登录 · 湖南工学院" open={visible} footer={null} onCancel={onCancel} centered>
    <Typography.Paragraph type="secondary">仅用于本机查询和日历导出，不需要 UID，也不会自动开通云端托管。密码在本机保存，请勿在公用电脑使用。</Typography.Paragraph>
    <Form form={form} layout="vertical" onFinish={login}>
      <Form.Item name="username" label="学号" rules={[{ required: true, message: '请输入本校学号' }]}><Input autoComplete="username" /></Form.Item>
      <Form.Item name="password" label="教务密码" rules={[{ required: true, message: '请输入密码' }]}><Input.Password autoComplete="current-password" /></Form.Item>
      <Button type="primary" htmlType="submit" loading={loading} block size="large">登录并保存到本机</Button>
    </Form>
  </Modal>;
}
