import React from 'react';
import { Empty, Space, Spin, Table, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import type { GradeItem } from '../../types';

const { Text } = Typography;

const columns: ColumnsType<GradeItem> = [
    {
        title: '课程',
        dataIndex: 'course_name',
        key: 'course_name',
        render: (_, record) => (
            <div className="grade-course-cell">
                <Text strong>{record.course_name || '未知课程'}</Text>
                <Text type="secondary">{record.course_code || '无课程编号'}</Text>
            </div>
        )
    },
    {
        title: '成绩',
        dataIndex: 'score',
        key: 'score',
        width: 96,
        render: (value: string) => {
            const score = Number(value);
            const failed = (Number.isFinite(score) && score < 60) || value === '不及格';
            return <Text className="grade-score" type={failed ? 'danger' : 'success'}>{value || '--'}</Text>;
        }
    },
    {
        title: '学分',
        dataIndex: 'credit',
        key: 'credit',
        width: 76,
        render: (value: string) => <Text>{value || '--'}</Text>
    },
    {
        title: '绩点',
        dataIndex: 'gpa',
        key: 'gpa',
        width: 76,
        render: (value: string) => <Text strong>{value || '--'}</Text>
    },
    {
        title: '考核',
        key: 'exam',
        width: 190,
        responsive: ['md'],
        render: (_, record) => (
            <Space size={[4, 4]} wrap>
                <Tag bordered={false}>{record.exam_name || '--'}</Tag>
                <Tag bordered={false} color="blue">{record.examination_nature || '--'}</Tag>
            </Space>
        )
    },
    {
        title: '状态',
        dataIndex: 'pass_status',
        key: 'pass_status',
        width: 94,
        responsive: ['sm'],
        render: (value: string) => {
            if (!value) return <Text type="secondary">--</Text>;
            const passed = value.includes('合格') || value.includes('通过') || value === '及格';
            return <Tag color={passed ? 'success' : 'error'} bordered={false}>{value}</Tag>;
        }
    }
];

interface GradeResultsProps {
    grades: GradeItem[];
    loading: boolean;
    hasSelectedSemester: boolean;
}

const GradeResults: React.FC<GradeResultsProps> = ({ grades, loading, hasSelectedSemester }) => (
    <Spin spinning={loading}>
        {grades.length > 0 ? (
            <Table
                className="grades-table"
                rowKey="grade_id"
                columns={columns}
                dataSource={grades}
                pagination={{ pageSize: 10, showSizeChanger: false, hideOnSinglePage: true }}
                scroll={{ x: 680 }}
                size="middle"
            />
        ) : (
            <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={hasSelectedSemester ? '该学期暂无成绩' : '请先选择学期'}
                style={{ padding: '44px 0' }}
            />
        )}
    </Spin>
);

export default React.memo(GradeResults);
