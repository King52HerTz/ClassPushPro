import React, { useEffect, useMemo, useState } from 'react';
import {
    Alert,
    Button,
    Card,
    Col,
    Empty,
    Row,
    Select,
    Space,
    Spin,
    Statistic,
    Switch,
    Table,
    Tag,
    Typography,
    message
} from 'antd';
import { BellOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons';

import { api } from '../api';
import type { AppConfig, GradeItem, GradeQueryData, GradeSemester } from '../types';

const { Text } = Typography;

const GradesPage: React.FC = () => {
    const [loading, setLoading] = useState(false);
    const [checking, setChecking] = useState(false);
    const [configLoading, setConfigLoading] = useState(false);
    const [gradePushEnabled, setGradePushEnabled] = useState(false);
    const [queryData, setQueryData] = useState<GradeQueryData | null>(null);
    const [selectedSemesterId, setSelectedSemesterId] = useState('');
    const [errorMessage, setErrorMessage] = useState('');

    const semesterOptions = queryData?.semester_list || [];
    const grades = queryData?.grades || [];
    const studentInfo = queryData?.student_info || {};

    const totalCredits = useMemo(() => {
        return grades.reduce((sum, item) => {
            const value = Number(item.credit || 0);
            return sum + (Number.isFinite(value) ? value : 0);
        }, 0);
    }, [grades]);

    const loadPushConfig = async () => {
        setConfigLoading(true);
        try {
            const res = await api.getConfig();
            if (res.status === 'success' && res.data) {
                const config = res.data as AppConfig;
                setGradePushEnabled(Boolean(config.grade_push_enabled));
            }
        } finally {
            setConfigLoading(false);
        }
    };

    const loadSemesters = async () => {
        setLoading(true);
        setErrorMessage('');
        try {
            const res = await api.getGradeSemesters();
            if (res.status !== 'success' || !res.data) {
                setErrorMessage(res.message || '学期列表获取失败');
                return;
            }

            const data = res.data;
            setQueryData(prev => ({
                current_term: data.current_term,
                semester_list: data.semester_list || [],
                selected_semester: prev?.selected_semester,
                student_info: prev?.student_info,
                summary: prev?.summary,
                grades: prev?.grades || [],
                source: data.source
            }));

            const targetSemesterId =
                data.current_term?.semester_id ||
                data.semester_list?.[0]?.semester_id ||
                '';
            setSelectedSemesterId(targetSemesterId);

            if (targetSemesterId) {
                await loadGrades(targetSemesterId, false);
            }
        } catch (e) {
            setErrorMessage('成绩接口暂时不可用，请稍后重试');
        } finally {
            setLoading(false);
        }
    };

    const loadGrades = async (semesterId: string, showSuccess = false) => {
        if (!semesterId) return;
        setLoading(true);
        setErrorMessage('');
        try {
            const res = await api.getGrades(semesterId);
            if (res.status !== 'success' || !res.data) {
                setErrorMessage(res.message || '成绩获取失败');
                return;
            }

            setQueryData(res.data);
            setSelectedSemesterId(res.data.selected_semester?.semester_id || semesterId);

            if (showSuccess) {
                message.success(res.data.source === 'offline' ? '已加载本地缓存成绩' : '成绩已更新');
            }
        } catch (e) {
            setErrorMessage('成绩获取失败，请检查网络或登录状态');
        } finally {
            setLoading(false);
        }
    };

    const refreshGrades = async () => {
        if (!selectedSemesterId) return;
        setLoading(true);
        setErrorMessage('');
        try {
            const res = await api.refreshGrades(selectedSemesterId);
            if (res.status !== 'success' || !res.data) {
                setErrorMessage(res.message || '成绩刷新失败');
                return;
            }
            setQueryData(res.data);
            message.success(res.message || '刷新成功');
        } catch (e) {
            setErrorMessage('成绩刷新失败，请稍后再试');
        } finally {
            setLoading(false);
        }
    };

    const handleCheckNewGrades = async () => {
        setChecking(true);
        try {
            const res = await api.checkNewGrades();
            if (res.status !== 'success' || !res.data) {
                message.error(res.message || '新成绩检测失败');
                return;
            }

            const newItems = res.data.new_items || [];
            const pushMessage = res.data.push_result?.message;
            if (newItems.length > 0) {
                message.success(`检测到 ${newItems.length} 条新增成绩`);
            } else {
                message.info(pushMessage || '当前没有新增成绩');
            }

            if (selectedSemesterId) {
                await loadGrades(selectedSemesterId, false);
            }
        } catch (e) {
            message.error('新成绩检测失败');
        } finally {
            setChecking(false);
        }
    };

    const handleToggleGradePush = async (checked: boolean) => {
        setGradePushEnabled(checked);
        try {
            const res = await api.saveGradePushSettings(checked);
            if (res.status !== 'success') {
                setGradePushEnabled(!checked);
                message.error(res.message || '保存失败');
                return;
            }
            message.success(checked ? '已开启新成绩自动推送' : '已关闭新成绩自动推送');
        } catch (e) {
            setGradePushEnabled(!checked);
            message.error('保存成绩推送设置失败');
        }
    };

    useEffect(() => {
        loadPushConfig();
        loadSemesters();
    }, []);

    const selectedSemester: GradeSemester | undefined = semesterOptions.find(
        item => item.semester_id === selectedSemesterId
    ) || queryData?.selected_semester;

    const columns = [
        {
            title: '课程',
            dataIndex: 'course_name',
            key: 'course_name',
            render: (_: string, record: GradeItem) => (
                <div>
                    <div style={{ fontWeight: 600 }}>{record.course_name || '未知课程'}</div>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                        {record.course_code || '无课程编号'}
                    </Text>
                </div>
            )
        },
        {
            title: '成绩',
            dataIndex: 'score',
            key: 'score',
            width: 110,
            render: (value: string) => <Text strong>{value || '--'}</Text>
        },
        {
            title: '学分',
            dataIndex: 'credit',
            key: 'credit',
            width: 90,
            render: (value: string) => value || '--'
        },
        {
            title: '绩点',
            dataIndex: 'gpa',
            key: 'gpa',
            width: 90,
            render: (value: string) => value || '--'
        },
        {
            title: '考核',
            key: 'exam',
            width: 180,
            render: (_: string, record: GradeItem) => (
                <div>
                    <div>{record.exam_name || '--'}</div>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                        {record.examination_nature || '--'}
                    </Text>
                </div>
            )
        },
        {
            title: '状态',
            dataIndex: 'pass_status',
            key: 'pass_status',
            width: 100,
            render: (value: string) => {
                if (!value) return '--';
                const color = value.includes('合格') ? 'success' : 'default';
                return <Tag color={color}>{value}</Tag>;
            }
        }
    ];

    return (
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
            <Row gutter={[20, 20]}>
                <Col span={24}>
                    <Card bordered={false} style={{ borderRadius: 12, boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
                        <Row gutter={[16, 16]} align="middle">
                            <Col xs={24} md={10}>
                                <Text type="secondary">当前查询学期</Text>
                                <Select
                                    value={selectedSemesterId || undefined}
                                    placeholder="请选择学期"
                                    style={{ width: '100%', marginTop: 8 }}
                                    options={semesterOptions.map(item => ({
                                        label: item.semester_name,
                                        value: item.semester_id
                                    }))}
                                    onChange={(value) => {
                                        setSelectedSemesterId(value);
                                        loadGrades(value, false);
                                    }}
                                />
                            </Col>
                            <Col xs={24} md={14}>
                                <Space wrap style={{ width: '100%', justifyContent: 'flex-end' }}>
                                    <Button icon={<ReloadOutlined />} onClick={refreshGrades} loading={loading}>
                                        刷新成绩
                                    </Button>
                                    <Button icon={<SearchOutlined />} onClick={handleCheckNewGrades} loading={checking}>
                                        检测新成绩
                                    </Button>
                                    <Space>
                                        <BellOutlined />
                                        <Text>新成绩自动推送</Text>
                                        <Switch
                                            checked={gradePushEnabled}
                                            loading={configLoading}
                                            onChange={handleToggleGradePush}
                                        />
                                    </Space>
                                </Space>
                            </Col>
                        </Row>
                    </Card>
                </Col>

                {errorMessage && (
                    <Col span={24}>
                        <Alert type="error" showIcon message={errorMessage} />
                    </Col>
                )}

                <Col xs={24} md={8}>
                    <Card bordered={false} style={{ borderRadius: 12, boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
                        <Statistic
                            title="课程数"
                            value={grades.length}
                            suffix="门"
                        />
                        <div style={{ marginTop: 16 }}>
                            <Text type="secondary">总学分</Text>
                            <div style={{ fontSize: 28, fontWeight: 700 }}>{totalCredits.toFixed(1)}</div>
                        </div>
                    </Card>
                </Col>

                <Col xs={24} md={8}>
                    <Card bordered={false} style={{ borderRadius: 12, boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
                        <Text type="secondary">学生信息</Text>
                        <div style={{ marginTop: 12, lineHeight: 2 }}>
                            <div>姓名：{studentInfo.student_name || '--'}</div>
                            <div>学号：{studentInfo.student_no || '--'}</div>
                            <div>班级：{studentInfo.class_name || '--'}</div>
                        </div>
                    </Card>
                </Col>

                <Col xs={24} md={8}>
                    <Card bordered={false} style={{ borderRadius: 12, boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
                        <Text type="secondary">数据来源</Text>
                        <div style={{ marginTop: 12, lineHeight: 2 }}>
                            <div>当前学期：{queryData?.current_term?.semester_name || '--'}</div>
                            <div>选中学期：{selectedSemester?.semester_name || '--'}</div>
                            <div>来源：{queryData?.source === 'offline' ? '本地缓存' : '在线抓取'}</div>
                        </div>
                    </Card>
                </Col>

                <Col span={24}>
                    <Card
                        bordered={false}
                        title="成绩列表"
                        style={{ borderRadius: 12, boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}
                    >
                        <Spin spinning={loading}>
                            {grades.length > 0 ? (
                                <Table
                                    rowKey="grade_id"
                                    columns={columns}
                                    dataSource={grades}
                                    pagination={{ pageSize: 10, showSizeChanger: false }}
                                    scroll={{ x: 900 }}
                                />
                            ) : (
                                <Empty
                                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                                    description={selectedSemesterId ? '该学期暂无成绩' : '请先选择学期'}
                                />
                            )}
                        </Spin>
                    </Card>
                </Col>
            </Row>
        </div>
    );
};

export default GradesPage;
