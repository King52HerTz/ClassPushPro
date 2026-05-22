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
const GRADE_CACHE_KEY = 'grades_query_cache_v1';
const EMPTY_GRADE_CACHE_MESSAGE = '当前暂无本地成绩缓存，请联网后首次加载';
const buildGradesCacheMessage = (timeStr: string) => `当前网络不可用，正在显示${timeStr || '较早前'}的本地成绩缓存`;

const styles = `
.grades-table .ant-table-tbody > tr:nth-child(even) > td {
    background-color: #fafbfc;
}
.grades-table .ant-table-tbody > tr:hover > td {
    background-color: #f0f7ff !important;
    transition: background-color 0.3s ease;
}
.grades-table .ant-table-thead > tr > th {
    background-color: #f8f9fa;
    font-weight: 600;
    color: #4b5563;
    border-bottom: 1px solid #f0f0f0;
}
.grades-table .ant-table-cell {
    padding: 16px 16px !important;
}
.grades-card {
    border-radius: 16px !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.03) !important;
    transition: all 0.3s ease;
    border: 1px solid #f0f0f0;
}
.grades-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.06) !important;
}
.student-name-text {
    background: linear-gradient(90deg, #1890ff, #36cfc9);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 28px;
    font-weight: bold;
    letter-spacing: 2px;
}
`;

const GradesPage: React.FC = () => {
    const [loading, setLoading] = useState(false);
    const [checking, setChecking] = useState(false);
    const [configLoading, setConfigLoading] = useState(false);
    const [gradePushEnabled, setGradePushEnabled] = useState(false);
    const [queryData, setQueryData] = useState<GradeQueryData | null>(null);
    const [selectedSemesterId, setSelectedSemesterId] = useState('');
    const [alertInfo, setAlertInfo] = useState<{ type: 'error' | 'warning' | 'info'; message: string } | null>(null);

    const semesterOptions = queryData?.semester_list || [];
    const grades = queryData?.grades || [];
    const studentInfo = queryData?.student_info || {};

    const formatRelativeTime = (timestamp: number) => {
        if (!Number.isFinite(timestamp) || timestamp <= 0) {
            return '';
        }
        const seconds = Math.max(Math.floor((Date.now() - timestamp) / 1000), 0);
        if (seconds < 60) return '刚刚';
        if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟前`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}小时前`;
        return `${Math.floor(seconds / 86400)}天前`;
    };

    const readGradesCache = () => {
        try {
            const raw = localStorage.getItem(GRADE_CACHE_KEY);
            if (!raw) return null;
            const parsed = JSON.parse(raw) as {
                savedAt?: number;
                selectedSemesterId?: string;
                data?: GradeQueryData;
            };
            if (!parsed?.data) {
                return null;
            }
            return parsed;
        } catch (e) {
            return null;
        }
    };

    const saveGradesCache = (data: GradeQueryData, semesterId: string) => {
        try {
            localStorage.setItem(
                GRADE_CACHE_KEY,
                JSON.stringify({
                    savedAt: Date.now(),
                    selectedSemesterId: semesterId,
                    data,
                })
            );
        } catch (e) {
            // ignore local cache write errors
        }
    };

    const applyCachedGrades = (cached: { savedAt?: number; selectedSemesterId?: string; data?: GradeQueryData } | null) => {
        if (!cached?.data) {
            return false;
        }
        const cachedData: GradeQueryData = {
            ...cached.data,
            source: 'offline',
            update_time_str: cached.data.update_time_str || formatRelativeTime(Number(cached.savedAt || 0)),
        };
        setQueryData(cachedData);
        setSelectedSemesterId(cached.selectedSemesterId || cachedData.selected_semester?.semester_id || cachedData.current_term?.semester_id || '');
        return true;
    };

    const hasVisibleGradeData = (data: GradeQueryData | null | undefined) => {
        if (!data) {
            return false;
        }
        return Boolean(
            (data.grades && data.grades.length > 0) ||
            (data.semester_list && data.semester_list.length > 0) ||
            data.student_info?.student_name
        );
    };

    const keepCurrentGradesAsOffline = () => {
        if (!hasVisibleGradeData(queryData)) {
            return false;
        }
        const timeStr = queryData?.update_time_str || '较早前';
        setQueryData(prev => prev ? { ...prev, source: 'offline', update_time_str: prev.update_time_str || timeStr } : prev);
        setAlertInfo({ type: 'warning', message: buildGradesCacheMessage(timeStr) });
        return true;
    };

    const restoreGradesFromLocalCache = () => {
        const cached = readGradesCache();
        if (!applyCachedGrades(cached)) {
            return false;
        }
        const timeStr = formatRelativeTime(Number(cached?.savedAt || 0)) || '较早前';
        setAlertInfo({ type: 'warning', message: buildGradesCacheMessage(timeStr) });
        return true;
    };

    const recoverGradesAfterFailure = (emptyMessage = EMPTY_GRADE_CACHE_MESSAGE) => {
        if (keepCurrentGradesAsOffline()) {
            return true;
        }
        if (restoreGradesFromLocalCache()) {
            return true;
        }
        setAlertInfo({ type: 'info', message: emptyMessage });
        return false;
    };

    const stats = useMemo(() => {
        let totalCredit = 0;
        let totalGpaCredit = 0;
        let validGpaCount = 0;

        grades.forEach((item) => {
            const credit = Number(item.credit || 0);
            const gpa = Number(item.gpa || 0);
            
            if (Number.isFinite(credit)) {
                totalCredit += credit;
                if (Number.isFinite(gpa) && gpa > 0) {
                    totalGpaCredit += gpa * credit;
                    validGpaCount += 1;
                }
            }
        });

        const averageGpa = totalCredit > 0 && validGpaCount > 0 
            ? (totalGpaCredit / totalCredit).toFixed(2) 
            : '0.00';

        return {
            totalCredit: totalCredit.toFixed(1),
            averageGpa
        };
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
        setAlertInfo(null);
        try {
            const res = await api.getGradeSemesters();
            if (res.status !== 'success' || !res.data) {
                recoverGradesAfterFailure(res.message || EMPTY_GRADE_CACHE_MESSAGE);
                return;
            }

            const data = res.data;
            const mergedData: GradeQueryData = {
                current_term: data.current_term,
                semester_list: data.semester_list || [],
                selected_semester: data.selected_semester || queryData?.selected_semester,
                student_info: data.student_info || queryData?.student_info,
                summary: data.summary || queryData?.summary,
                grades: data.grades || queryData?.grades || [],
                source: data.source,
                update_time_str: data.update_time_str
            };
            setQueryData(mergedData);

            if (data.source === 'offline') {
                setAlertInfo({ type: 'warning', message: buildGradesCacheMessage(data.update_time_str || '较早前') });
            }

            const targetSemesterId =
                data.selected_semester?.semester_id ||
                data.current_term?.semester_id ||
                data.semester_list?.[0]?.semester_id ||
                '';
            setSelectedSemesterId(targetSemesterId);

            if (targetSemesterId && data.source !== 'offline' && !data.selected_semester) {
                await loadGrades(targetSemesterId, false);
            } else if (hasVisibleGradeData(mergedData)) {
                saveGradesCache(mergedData, targetSemesterId);
            }
        } catch (e) {
            recoverGradesAfterFailure(EMPTY_GRADE_CACHE_MESSAGE);
        } finally {
            setLoading(false);
        }
    };

    const loadGrades = async (semesterId: string, showSuccess = false) => {
        if (!semesterId) return;
        setLoading(true);
        setAlertInfo(null);
        try {
            const res = await api.getGrades(semesterId);
            if (res.status !== 'success' || !res.data) {
                recoverGradesAfterFailure(res.message || EMPTY_GRADE_CACHE_MESSAGE);
                return;
            }

            setQueryData(res.data);
            setSelectedSemesterId(res.data.selected_semester?.semester_id || semesterId);
            saveGradesCache(res.data, res.data.selected_semester?.semester_id || semesterId);

            if (res.data.source === 'offline') {
                setAlertInfo({ type: 'warning', message: buildGradesCacheMessage(res.data.update_time_str || '较早前') });
            }

            if (showSuccess) {
                message.success(res.data.source === 'offline' ? '已加载本地缓存成绩' : '成绩已更新');
            }
        } catch (e) {
            recoverGradesAfterFailure(EMPTY_GRADE_CACHE_MESSAGE);
        } finally {
            setLoading(false);
        }
    };

    const refreshGrades = async () => {
        if (!selectedSemesterId) return;
        setLoading(true);
        setAlertInfo(null);
        try {
            const res = await api.refreshGrades(selectedSemesterId);
            if (res.status !== 'success' || !res.data) {
                recoverGradesAfterFailure(res.message || EMPTY_GRADE_CACHE_MESSAGE);
                return;
            }
            setQueryData(res.data);
            saveGradesCache(res.data, res.data.selected_semester?.semester_id || selectedSemesterId);
            message.success(res.message || '刷新成功');
        } catch (e) {
            recoverGradesAfterFailure(EMPTY_GRADE_CACHE_MESSAGE);
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
        applyCachedGrades(readGradesCache());
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
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    <Text strong style={{ fontSize: 15, color: '#1f2937' }}>{record.course_name || '未知课程'}</Text>
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
            width: 100,
            render: (value: string) => {
                const num = Number(value);
                const isDanger = (!isNaN(num) && num < 60) || value === '不及格';
                const color = isDanger ? '#cf1322' : '#3f8600';
                return <Text strong style={{ color, fontSize: 18 }}>{value || '--'}</Text>;
            }
        },
        {
            title: '学分',
            dataIndex: 'credit',
            key: 'credit',
            width: 80,
            render: (value: string) => <Tag color="blue" bordered={false} style={{ fontWeight: 500 }}>{value || '--'}</Tag>
        },
        {
            title: '绩点',
            dataIndex: 'gpa',
            key: 'gpa',
            width: 80,
            render: (value: string) => {
                const num = Number(value);
                return <Text strong type={num >= 3.0 ? 'success' : num < 2.0 ? 'danger' : 'secondary'} style={{ fontSize: 15 }}>{value || '--'}</Text>;
            }
        },
        {
            title: '考核类型',
            key: 'exam',
            width: 180,
            render: (_: string, record: GradeItem) => (
                <Space size={[0, 4]} wrap>
                    <Tag bordered={false} color="cyan">{record.exam_name || '--'}</Tag>
                    <Tag bordered={false} color="geekblue">{record.examination_nature || '--'}</Tag>
                </Space>
            )
        },
        {
            title: '状态',
            dataIndex: 'pass_status',
            key: 'pass_status',
            width: 100,
            render: (value: string) => {
                if (!value) return '--';
                const isPass = value.includes('合格') || value.includes('通过') || value === '及格';
                return <Tag color={isPass ? 'success' : 'error'} bordered={false} style={{ padding: '2px 8px' }}>{value}</Tag>;
            }
        }
    ];

    return (
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
            <style>{styles}</style>
            <Row gutter={[20, 20]}>
                <Col span={24}>
                    <Card bordered={false} className="grades-card">
                        <Row gutter={[16, 16]} align="middle">
                            <Col xs={24} md={10}>
                                <Text type="secondary" style={{ fontSize: 14 }}>当前查询学期</Text>
                                <Select
                                    value={selectedSemesterId || undefined}
                                    placeholder="请选择学期"
                                    style={{ width: '100%', marginTop: 8 }}
                                    size="large"
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
                                <Space wrap style={{ width: '100%', justifyContent: 'flex-end' }} size="middle">
                                    <Button size="large" icon={<ReloadOutlined />} onClick={refreshGrades} loading={loading}>
                                        刷新成绩
                                    </Button>
                                    <Button size="large" type="primary" icon={<SearchOutlined />} onClick={handleCheckNewGrades} loading={checking}>
                                        检测新成绩
                                    </Button>
                                    <Space size="small" style={{ marginLeft: 8, background: '#f5f5f5', padding: '8px 16px', borderRadius: 8 }}>
                                        <BellOutlined style={{ color: '#1890ff' }} />
                                        <Text strong>新成绩自动推送</Text>
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

                {alertInfo && (
                    <Col span={24}>
                        <Alert type={alertInfo.type} showIcon message={alertInfo.message} style={{ borderRadius: 12 }} />
                    </Col>
                )}

                <Col xs={24} md={8}>
                    <Card bordered={false} className="grades-card" style={{ height: '100%' }}>
                        <Row>
                            <Col span={12}>
                                <Statistic
                                    title={<Text type="secondary" style={{ fontSize: 14 }}>课程数</Text>}
                                    value={grades.length}
                                    suffix="门"
                                    valueStyle={{ fontWeight: 600, fontSize: 28 }}
                                />
                            </Col>
                            <Col span={12}>
                                <Statistic
                                    title={<Text type="secondary" style={{ fontSize: 14 }}>平均绩点</Text>}
                                    value={stats.averageGpa}
                                    valueStyle={{ color: Number(stats.averageGpa) >= 3.0 ? '#3f8600' : '#cf1322', fontWeight: 600, fontSize: 28 }}
                                />
                            </Col>
                        </Row>
                        <div style={{ marginTop: 24 }}>
                            <Text type="secondary" style={{ fontSize: 14 }}>总学分</Text>
                            <div style={{ fontSize: 32, fontWeight: 700, color: '#1f2937' }}>{stats.totalCredit}</div>
                        </div>
                    </Card>
                </Col>

                {studentInfo.student_name && (
                    <Col xs={24} md={8}>
                        <Card bordered={false} className="grades-card" style={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                            <div style={{ textAlign: 'center', padding: '10px 0' }}>
                                <Text type="secondary" style={{ fontSize: 14, marginBottom: 12, display: 'block' }}>小主姓名</Text>
                                <span className="student-name-text">{studentInfo.student_name}</span>
                            </div>
                        </Card>
                    </Col>
                )}

                <Col xs={24} md={studentInfo.student_name ? 8 : 16}>
                    <Card bordered={false} className="grades-card" style={{ height: '100%' }}>
                        <Text type="secondary" style={{ display: 'block', marginBottom: 16, fontSize: 14 }}>数据来源</Text>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <Text type="secondary">当前学期</Text>
                                <Text strong>{queryData?.current_term?.semester_name || '--'}</Text>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <Text type="secondary">选中学期</Text>
                                <Text strong style={{ color: '#1890ff' }}>{selectedSemester?.semester_name || '--'}</Text>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <Text type="secondary">数据来源</Text>
                                <Tag bordered={false} color={queryData?.source === 'offline' ? 'default' : 'green'} style={{ margin: 0, padding: '2px 10px', fontSize: 13 }}>
                                    {queryData?.source === 'offline' ? '本地缓存' : '在线抓取'}
                                </Tag>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <Text type="secondary">缓存时间</Text>
                                <Text strong>{queryData?.update_time_str || '--'}</Text>
                            </div>
                        </div>
                    </Card>
                </Col>

                <Col span={24}>
                    <Card
                        bordered={false}
                        className="grades-card"
                        title={<span style={{ fontSize: 18, fontWeight: 600 }}>成绩列表</span>}
                        styles={{ body: { padding: '0 0 16px 0' }, header: { borderBottom: 'none', padding: '20px 24px 8px 24px' } }}
                    >
                        <Spin spinning={loading}>
                            {grades.length > 0 ? (
                                <Table
                                    className="grades-table"
                                    rowKey="grade_id"
                                    columns={columns}
                                    dataSource={grades}
                                    pagination={{ pageSize: 10, showSizeChanger: false }}
                                    scroll={{ x: 900 }}
                                    size="middle"
                                />
                            ) : (
                                <Empty
                                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                                    description={selectedSemesterId ? '该学期暂无成绩' : '请先选择学期'}
                                    style={{ padding: '40px 0' }}
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
