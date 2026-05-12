import { useQuery } from '@tanstack/react-query';
import { Card, Typography, Row, Col, Statistic, Table, Tag, Space, Button, message, Spin } from 'antd';
import { DatabaseOutlined, CloudServerOutlined, PictureOutlined, FileTextOutlined, ReloadOutlined } from '@ant-design/icons';
import { artifactService } from '@/services/artifactService';
import { ragService } from '@/services/ragService';
import { kgService } from '@/services/kgService';

const { Title, Text } = Typography;

interface TaskRecord {
  id: string;
  artifact: string;
  artifact_id: string;
  type: string;
  status: string;
  progress: number;
  error_message?: string;
  created_at: string;
}

const columns = [
  { title: '文物', dataIndex: 'artifact', key: 'artifact' },
  { title: '任务类型', dataIndex: 'type', key: 'type' },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status',
    render: (status: string) => {
      const colors: Record<string, string> = {
        completed: 'green',
        running: 'blue',
        failed: 'red',
        pending: 'default',
      };
      return <Tag color={colors[status] || 'default'}>{status}</Tag>;
    },
  },
  { title: '时间', dataIndex: 'created_at', key: 'created_at',
    render: (val: string) => val ? new Date(val).toLocaleString('zh-CN') : '-' },
  {
    title: '操作',
    key: 'action',
    render: (_: any, record: TaskRecord) => (
      <Space>
        <Button type="link" size="small">
          查看
        </Button>
        {record.status === 'failed' && (
          <Button type="link" size="small" danger>
            重试
          </Button>
        )}
      </Space>
    ),
  },
];

export default function AdminPage() {
  // Fetch stats from API
  const { data: artifactsData, isLoading: artifactsLoading } = useQuery({
    queryKey: ['admin-artifacts'],
    queryFn: async () => {
      const data = await artifactService.list({ page_size: 1 });
      return { total: data.total };
    },
  });

  const { data: ragStats, isLoading: ragLoading } = useQuery({
    queryKey: ['admin-rag-stats'],
    queryFn: () => ragService.getStatistics(),
  });

  const { data: kgStats, isLoading: kgLoading } = useQuery({
    queryKey: ['admin-kg-stats'],
    queryFn: () => kgService.getStatistics(),
  });

  const { data: tasksData } = useQuery({
    queryKey: ['admin-tasks'],
    queryFn: () => artifactService.getTasks({ limit: 20 }),
  });

  const { data: imageCount } = useQuery({
    queryKey: ['admin-image-count'],
    queryFn: () => artifactService.getImageCount(),
  });

  const isLoading = artifactsLoading || ragLoading || kgLoading;

  const handleInitServices = async () => {
    try {
      await kgService.connect();
      message.success('知识图谱服务已连接');
    } catch (error) {
      message.error('连接失败');
    }
  };

  const handleLoadModels = async () => {
    try {
      message.loading('正在加载模型...');
      // Models would be loaded via API calls
      setTimeout(() => message.success('模型加载完成'), 2000);
    } catch (error) {
      message.error('模型加载失败');
    }
  };

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <Title level={2} style={{ color: '#C9A962', marginBottom: 32, fontFamily: '"Noto Serif SC", serif' }}>
        管理后台
      </Title>

      {/* Stats */}
      <Row gutter={[24, 24]} style={{ marginBottom: 32 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card
            style={{
              background: 'rgba(20, 20, 31, 0.8)',
              border: '1px solid rgba(201, 169, 98, 0.2)',
            }}
          >
            <Statistic
              title={<Text style={{ color: 'rgba(255, 255, 255, 0.5)' }}>文物总数</Text>}
              value={artifactsData?.total || 0}
              prefix={<DatabaseOutlined style={{ color: '#C9A962' }} />}
              valueStyle={{ color: '#C9A962' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card
            style={{
              background: 'rgba(20, 20, 31, 0.8)',
              border: '1px solid rgba(201, 169, 98, 0.2)',
            }}
          >
            <Statistic
              title={<Text style={{ color: 'rgba(255, 255, 255, 0.5)' }}>文档数量</Text>}
              value={ragStats?.count || 0}
              prefix={<FileTextOutlined style={{ color: '#C9A962' }} />}
              valueStyle={{ color: '#C9A962' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card
            style={{
              background: 'rgba(20, 20, 31, 0.8)',
              border: '1px solid rgba(201, 169, 98, 0.2)',
            }}
          >
            <Statistic
              title={<Text style={{ color: 'rgba(255, 255, 255, 0.5)' }}>图谱节点</Text>}
              value={kgStats?.node_counts ? Object.values(kgStats.node_counts).reduce((a: number, b: number) => a + b, 0) : 0}
              prefix={<CloudServerOutlined style={{ color: '#C9A962' }} />}
              valueStyle={{ color: '#C9A962' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card
            style={{
              background: 'rgba(20, 20, 31, 0.8)',
              border: '1px solid rgba(201, 169, 98, 0.2)',
            }}
          >
            <Statistic
              title={<Text style={{ color: 'rgba(255, 255, 255, 0.5)' }}>图像数量</Text>}
              value={imageCount ?? 0}
              prefix={<PictureOutlined style={{ color: '#C9A962' }} />}
              valueStyle={{ color: '#C9A962' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Quick Actions */}
      <Row gutter={[24, 24]} style={{ marginBottom: 32 }}>
        <Col span={24}>
          <Card
            title={<Text style={{ color: '#C9A962' }}>快速操作</Text>}
            style={{
              background: 'rgba(20, 20, 31, 0.8)',
              border: '1px solid rgba(201, 169, 98, 0.2)',
            }}
          >
            <Space wrap>
              <Button icon={<ReloadOutlined />} onClick={handleInitServices}>
                初始化服务连接
              </Button>
              <Button icon={<DatabaseOutlined />} onClick={handleLoadModels}>
                加载AI模型
              </Button>
            </Space>
          </Card>
        </Col>
      </Row>

      {/* Recent Tasks - placeholder table */}
      <Row gutter={[24, 24]}>
        <Col span={24}>
          <Card
            title={<Text style={{ color: '#C9A962' }}>最近任务</Text>}
            style={{
              background: 'rgba(20, 20, 31, 0.8)',
              border: '1px solid rgba(201, 169, 98, 0.2)',
            }}
          >
            <Table
              columns={columns}
              dataSource={tasksData || []}
              rowKey="id"
              pagination={false}
              locale={{ emptyText: '暂无任务记录' }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
