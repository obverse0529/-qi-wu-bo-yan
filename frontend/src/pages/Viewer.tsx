import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Card,
  Row,
  Col,
  Typography,
  Button,
  Spin,
  Space,
  Tag,
  Divider,
  message,
  Progress,
  Tabs,
  Modal,
} from 'antd';
import {
  RotateLeftOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  FullscreenOutlined,
  CameraOutlined,
  PlayCircleOutlined,
  HistoryOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { artifactService } from '@/services/artifactService';
import { ModelViewer3D, ModelViewer3DHandle } from '@/components/ModelViewer';
import apiClient from '@/services/api';

const { Title, Text, Paragraph } = Typography;

export default function ViewerPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('3d');
  const [reconstructModalVisible, setReconstructModalVisible] = useState(false);
  const [taskStatus, setTaskStatus] = useState<string>('pending');
  const [taskProgress, setTaskProgress] = useState<number>(0);
  const viewerRef = useRef<ModelViewer3DHandle>(null);

  const { data: artifact, isLoading } = useQuery({
    queryKey: ['artifact', id],
    queryFn: () => artifactService.get(id!),
    enabled: !!id,
  });

  const { data: images = [] } = useQuery({
    queryKey: ['artifact-images', id],
    queryFn: () => artifactService.listImages(id!),
    enabled: !!id,
  });

  // Polling for reconstruction status
  const { data: taskData } = useQuery({
    queryKey: ['reconstruct-task', id],
    queryFn: async () => {
      const { data } = await apiClient.get(`/artifacts/${id}/reconstruction`);
      return data;
    },
    enabled: !!id && reconstructModalVisible,
    refetchInterval: taskStatus === 'running' || taskStatus === 'pending' ? 2000 : false,
  });

  // Submit reconstruction mutation
  const reconstructMutation = useMutation({
    mutationFn: async (artifactId: string) => {
      const { data } = await apiClient.post('/reconstruct', { artifact_id: artifactId });
      return data;
    },
    onSuccess: (data) => {
      message.success('重建任务已提交');
      setReconstructModalVisible(true);
      setTaskStatus(data.status || 'pending');
      setTaskProgress(data.progress || 0);
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '提交重建任务失败');
    },
  });

  const handleReconstruct = () => {
    if (!id) return;
    reconstructMutation.mutate(id);
  };

  const handleResetView = () => {
    viewerRef.current?.resetView();
  };

  const handleZoomIn = () => {
    viewerRef.current?.zoomIn();
  };

  const handleZoomOut = () => {
    viewerRef.current?.zoomOut();
  };

  const handleFullscreen = () => {
    viewerRef.current?.toggleFullscreen();
  };

  const handleScreenshot = () => {
    const dataUrl = viewerRef.current?.screenshot();
    if (!dataUrl) {
      message.error('截图失败');
      return;
    }
    const link = document.createElement('a');
    link.download = `${artifact?.name || 'artifact'}-3d.png`;
    link.href = dataUrl;
    link.click();
    message.success('截图已保存');
  };

  // Update status from polling
  useEffect(() => {
    if (taskData) {
      if (taskData.status !== taskStatus) {
        setTaskStatus(taskData.status);
      }
      if (taskData.progress !== taskProgress) {
        setTaskProgress(taskData.progress);
      }
      if (taskData.status === 'completed') {
        message.success('3D重建完成');
        queryClient.invalidateQueries({ queryKey: ['artifact', id] });
      } else if (taskData.status === 'failed') {
        message.error(taskData.error_message || '重建失败');
      }
    }
  }, [taskData, queryClient, id]);

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!artifact) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Text style={{ color: 'rgba(255, 255, 255, 0.5)' }}>文物不存在</Text>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <Button onClick={() => navigate(-1)} style={{ marginBottom: 16 }}>
          返回
        </Button>
        <Title
          level={2}
          style={{
            color: '#C9A962',
            margin: 0,
            fontFamily: '"Noto Serif SC", serif',
          }}
        >
          {artifact.name}
        </Title>
        <Space style={{ marginTop: 8 }}>
          {artifact.dynasty && <Tag color="gold">{artifact.dynasty}</Tag>}
          {artifact.category && <Tag>{artifact.category}</Tag>}
        </Space>
      </div>

      <Row gutter={[24, 24]}>
        {/* 3D Viewer */}
        <Col xs={24} lg={16}>
          <Card
            style={{
              background: 'rgba(20, 20, 31, 0.9)',
              border: '1px solid rgba(201, 169, 98, 0.2)',
              borderRadius: 16,
            }}
            styles={{ body: { padding: 0, height: 500, position: 'relative' } }}
          >
            <Tabs
              activeKey={activeTab}
              onChange={setActiveTab}
              style={{ position: 'absolute', top: 16, right: 16, zIndex: 10 }}
              size="small"
              items={[
                { key: '3d', label: '3D模型' },
                { key: 'images', label: '图像' },
              ]}
            />

            {activeTab === '3d' && <ModelViewer3D ref={viewerRef} modelUrl={artifact.metadata?.modelUrl as string} />}

            {activeTab === 'images' && (
              <div style={{ padding: 24, height: '100%', overflow: 'auto' }}>
                {images.length > 0 ? (
                  <Row gutter={[16, 16]}>
                    {images.map((img: any) => (
                      <Col span={8} key={img.id}>
                        <img
                          src={img.image_url}
                          alt={img.view_type}
                          style={{
                            width: '100%',
                            borderRadius: 8,
                            border: '1px solid rgba(201, 169, 98, 0.2)',
                          }}
                        />
                        <div style={{ textAlign: 'center', marginTop: 8, color: '#fff' }}>
                          {img.view_type}
                        </div>
                      </Col>
                    ))}
                  </Row>
                ) : (
                  <div style={{ textAlign: 'center', color: 'rgba(255, 255, 255, 0.4)', padding: 48 }}>
                    暂无图像数据
                  </div>
                )}
              </div>
            )}

            {/* 3D Controls */}
            {activeTab === '3d' && (
              <div
                style={{
                  position: 'absolute',
                  bottom: 16,
                  left: 16,
                  display: 'flex',
                  gap: 8,
                }}
              >
                <Button icon={<RotateLeftOutlined />} size="large" ghost onClick={handleResetView} title="重置视角" />
                <Button icon={<ZoomInOutlined />} size="large" ghost onClick={handleZoomIn} title="放大" />
                <Button icon={<ZoomOutOutlined />} size="large" ghost onClick={handleZoomOut} title="缩小" />
                <Button icon={<FullscreenOutlined />} size="large" ghost onClick={handleFullscreen} title="全屏" />
                <Button icon={<CameraOutlined />} size="large" ghost onClick={handleScreenshot} title="截图">
                  截图
                </Button>
              </div>
            )}
          </Card>
        </Col>

        {/* Info Panel */}
        <Col xs={24} lg={8}>
          <Card
            style={{
              background: 'rgba(20, 20, 31, 0.8)',
              border: '1px solid rgba(201, 169, 98, 0.2)',
              marginBottom: 24,
            }}
          >
            <Title level={5} style={{ color: '#C9A962', marginBottom: 16 }}>
              文物信息
            </Title>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div>
                <Text style={{ color: 'rgba(255, 255, 255, 0.5)' }}>名称</Text>
                <div style={{ color: '#fff' }}>{artifact.name}</div>
              </div>
              <div>
                <Text style={{ color: 'rgba(255, 255, 255, 0.5)' }}>年代</Text>
                <div style={{ color: '#fff' }}>{artifact.dynasty || '不详'}</div>
              </div>
              <div>
                <Text style={{ color: 'rgba(255, 255, 255, 0.5)' }}>分类</Text>
                <div style={{ color: '#fff' }}>{artifact.category || '未分类'}</div>
              </div>
              {artifact.dimensions && (
                <div>
                  <Text style={{ color: 'rgba(255, 255, 255, 0.5)' }}>尺寸</Text>
                  <div style={{ color: '#fff' }}>
                    {artifact.dimensions.length} × {artifact.dimensions.width} ×{' '}
                    {artifact.dimensions.height} {artifact.dimensions.unit}
                  </div>
                </div>
              )}
            </div>

            {artifact.description && (
              <>
                <Divider style={{ borderColor: 'rgba(201, 169, 98, 0.2)' }} />
                <Paragraph style={{ color: 'rgba(255, 255, 255, 0.7)', lineHeight: 1.8 }}>
                  {artifact.description}
                </Paragraph>
              </>
            )}
          </Card>

          {/* Actions */}
          <Card
            style={{
              background: 'rgba(20, 20, 31, 0.8)',
              border: '1px solid rgba(201, 169, 98, 0.2)',
            }}
          >
            <Title level={5} style={{ color: '#C9A962', marginBottom: 16 }}>
              操作
            </Title>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Button
                block
                icon={<PlayCircleOutlined />}
                onClick={() => navigate(`/story/${artifact.id}`)}
                style={{
                  background: 'rgba(201, 169, 98, 0.1)',
                  borderColor: 'rgba(201, 169, 98, 0.3)',
                  color: '#C9A962',
                }}
              >
                生成文物故事
              </Button>
              <Button
                block
                icon={<HistoryOutlined />}
                onClick={handleReconstruct}
                style={{
                  background: 'rgba(201, 169, 98, 0.1)',
                  borderColor: 'rgba(201, 169, 98, 0.3)',
                  color: '#C9A962',
                }}
              >
                重新3D重建
              </Button>
            </Space>
          </Card>
        </Col>
      </Row>

      {/* Reconstruction Progress Modal */}
      <Modal
        title="3D重建进度"
        open={reconstructModalVisible}
        onCancel={() => setReconstructModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setReconstructModalVisible(false)}>
            关闭
          </Button>,
        ]}
      >
        <div style={{ padding: '20px 0' }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <Text>状态: </Text>
              <Tag color={taskData?.status === 'completed' ? 'green' : taskData?.status === 'failed' ? 'red' : 'blue'}>
                {taskData?.status === 'completed' && <CheckCircleOutlined />}
                {taskData?.status === 'failed' && <ExclamationCircleOutlined />}
                {taskData?.status === 'pending' && '等待中'}
                {taskData?.status === 'running' && '重建中'}
                {taskData?.status === 'completed' && '已完成'}
                {taskData?.status === 'failed' && '失败'}
              </Tag>
            </div>
            <div>
              <Text>进度: </Text>
              <Progress percent={taskProgress} status={taskStatus === 'failed' ? 'exception' : undefined} />
            </div>
          </Space>
        </div>
      </Modal>
    </div>
  );
}
