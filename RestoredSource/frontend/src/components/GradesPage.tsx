import React, { useEffect, useMemo, useState } from 'react';
import {
    Alert,
    Button,
    Card,
    Col,
    Row,
    Select,
    Space,
    Statistic,
    Switch,
    Typography,
    message
} from 'antd';
import { BellOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons';

import { api } from '../api';
import type { AppConfig, GradeQueryData, GradeSemester } from '../types';
import GradeResults from './grades/GradeResults';
import './GradesPage.css';

const { Text } = Typography;
const GRADE_CACHE_KEY = 'grades_query_cache_v2';
const EMPTY_GRADE_CACHE_MESSAGE = '当前暂无本地成绩缓存，请联网后首次加载';
const buildGradesCacheMessage = (timeStr: string) => `当前网络不可用，正在显示${timeStr || '较早前'}的本地成绩缓存`;

interface GradeCacheSnapshot {
    savedAt: number;
    data: GradeQueryData;
}

interface GradeCacheStore {
    version: 2;
    selectedSemesterId: string;
    snapshots: Record<string, GradeCacheSnapshot>;
}

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

    const readGradesCache = (semesterId = '') => {
        try {
            const raw = localStorage.getItem(GRADE_CACHE_KEY);
            if (!raw) return null;
            const store = JSON.parse(raw) as GradeCacheStore;
            if (store?.version !== 2 || !store.snapshots) {
                return null;
            }
            const targetId = semesterId || store.selectedSemesterId || Object.keys(store.snapshots)[0] || '';
            const snapshot = store.snapshots[targetId];
            if (!snapshot?.data) return null;
            return { ...snapshot, selectedSemesterId: targetId };
        } catch (e) {
            return null;
        }
    };

    const saveGradesCache = (data: GradeQueryData, semesterId: string) => {
        if (!semesterId) return;
        try {
            let store: GradeCacheStore = { version: 2, selectedSemesterId: semesterId, snapshots: {} };
            const raw = localStorage.getItem(GRADE_CACHE_KEY);
            if (raw) {
                const existing = JSON.parse(raw) as GradeCacheStore;
                if (existing?.version === 2 && existing.snapshots) store = existing;
            }
            store.selectedSemesterId = semesterId;
            store.snapshots[semesterId] = { savedAt: Date.now(), data };
            localStorage.setItem(
                GRADE_CACHE_KEY,
                JSON.stringify(store)
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

    const restoreGradesFromLocalCache = (semesterId = '') => {
        const cached = readGradesCache(semesterId);
        if (!applyCachedGrades(cached)) {
            return false;
        }
        const timeStr = formatRelativeTime(Number(cached?.savedAt || 0)) || '较早前';
        setAlertInfo({ type: 'warning', message: buildGradesCacheMessage(timeStr) });
        return true;
    };

    const recoverGradesAfterFailure = (emptyMessage = EMPTY_GRADE_CACHE_MESSAGE, semesterId = '') => {
        const visibleSemesterId = queryData?.selected_semester?.semester_id || selectedSemesterId;
        if (semesterId && semesterId !== visibleSemesterId && restoreGradesFromLocalCache(semesterId)) {
            return true;
        }
        if (keepCurrentGradesAsOffline()) {
            return true;
        }
        if (restoreGradesFromLocalCache(semesterId)) {
            return true;
        }
        setAlertInfo({ type: 'info', message: emptyMessage });
        return false;
    };

    const stats = useMemo(() => {
        let totalCredit = 0;
        let totalGpaCredit = 0;
        let validGpaCredit = 0;

        grades.forEach((item) => {
            const credit = Number(item.credit || 0);
            const gpa = Number(item.gpa || 0);
            
            if (Number.isFinite(credit)) {
                totalCredit += credit;
                if (Number.isFinite(gpa) && gpa > 0) {
                    totalGpaCredit += gpa * credit;
                    validGpaCredit += credit;
                }
            }
        });

        const averageGpa = validGpaCredit > 0
            ? (totalGpaCredit / validGpaCredit).toFixed(2)
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
                recoverGradesAfterFailure(res.message || EMPTY_GRADE_CACHE_MESSAGE, semesterId);
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
            recoverGradesAfterFailure(EMPTY_GRADE_CACHE_MESSAGE, semesterId);
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
                recoverGradesAfterFailure(res.message || EMPTY_GRADE_CACHE_MESSAGE, selectedSemesterId);
                return;
            }
            setQueryData(res.data);
            saveGradesCache(res.data, res.data.selected_semester?.semester_id || selectedSemesterId);
            message.success(res.message || '刷新成功');
        } catch (e) {
            recoverGradesAfterFailure(EMPTY_GRADE_CACHE_MESSAGE, selectedSemesterId);
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
            const updatedItems = res.data.updated_items || [];
            const pushMessage = res.data.push_result?.message;
            if (newItems.length > 0 || updatedItems.length > 0) {
                message.success(`检测完成：新增 ${newItems.length} 门，修改 ${updatedItems.length} 门`);
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

    return (
        <div className="grades-page">
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
                                <Space wrap className="grades-toolbar-actions" style={{ width: '100%', justifyContent: 'flex-end' }} size="middle">
                                    <Button size="large" icon={<ReloadOutlined />} onClick={refreshGrades} loading={loading}>
                                        刷新成绩
                                    </Button>
                                    <Button size="large" type="primary" icon={<SearchOutlined />} onClick={handleCheckNewGrades} loading={checking}>
                                        检测新成绩
                                    </Button>
                                    <Space size="small" className="grade-push-switch">
                                        <BellOutlined />
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

                <Col xs={24} lg={14}>
                    <Card bordered={false} className="grades-card" style={{ height: '100%' }}>
                        <Row gutter={[20, 20]}>
                            <Col span={8}>
                                <Statistic
                                    title="课程数"
                                    value={grades.length}
                                    suffix="门"
                                />
                            </Col>
                            <Col span={8}>
                                <Statistic
                                    title="平均绩点"
                                    value={stats.averageGpa}
                                    valueStyle={{ color: Number(stats.averageGpa) >= 3.0 ? '#027a48' : '#b54708' }}
                                />
                            </Col>
                            <Col span={8}>
                                <Statistic title="总学分" value={stats.totalCredit} />
                            </Col>
                        </Row>
                    </Card>
                </Col>

                <Col xs={24} lg={10}>
                    <Card bordered={false} className="grades-card" style={{ height: '100%' }}>
                        <Text strong style={{ display: 'block', marginBottom: 12 }}>学期与数据</Text>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                            {studentInfo.student_name && (
                                <div className="grade-owner-row">
                                    <Text className="grade-owner-label">小主姓名</Text>
                                    <Text strong className="grade-owner-name">{studentInfo.student_name}</Text>
                                </div>
                            )}
                            <div className="grade-meta-row">
                                <Text type="secondary">选中学期</Text>
                                <Text strong>{selectedSemester?.semester_name || '--'}</Text>
                            </div>
                            <div className="grade-meta-row">
                                <Text type="secondary">数据来源</Text>
                                <Text strong>{queryData?.source === 'offline' ? '本地缓存' : '教务系统'}</Text>
                            </div>
                            <div className="grade-meta-row">
                                <Text type="secondary">更新时间</Text>
                                <Text strong>{queryData?.update_time_str || '--'}</Text>
                            </div>
                        </div>
                    </Card>
                </Col>

                <Col span={24}>
                    <Card
                        bordered={false}
                        className="grades-card"
                        styles={{ body: { padding: '0 0 16px 0' } }}
                    >
                        <GradeResults grades={grades} loading={loading} hasSelectedSemester={Boolean(selectedSemesterId)} />
                    </Card>
                </Col>
            </Row>
        </div>
    );
};

export default GradesPage;
