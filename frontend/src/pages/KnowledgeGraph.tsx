import { useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Card,
  Row,
  Col,
  Typography,
  Input,
  Spin,
  Empty,
  List,
  Avatar,
  Tag,
  Space,
  Button,
  message,
  Modal,
  Descriptions,
} from 'antd';
import { SearchOutlined, InfoCircleOutlined, LinkOutlined } from '@ant-design/icons';
import { kgService, type KGSearchResult } from '@/services/kgService';
import { artifactService } from '@/services/artifactService';
import KnowledgeGraph from '@/components/KnowledgeGraph';
import type { KGNode, KGQueryResponse } from '@/types';

const { Title, Text, Paragraph } = Typography;

export default function KnowledgeGraphPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [searchKeyword, setSearchKeyword] = useState('');
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(
    searchParams.get('artifact') || null
  );
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selectedNode, setSelectedNode] = useState<KGNode | null>(null);

  // 获取文物列表用于搜索
  const { data: artifactsData } = useQuery({
    queryKey: ['artifacts-for-kg'],
    queryFn: () => artifactService.list({ page_size: 100 }),
  });

  // 获取图谱数据
  const {
    data: graphData,
    isLoading: graphLoading,
    refetch: refetchGraph,
  } = useQuery<KGQueryResponse>({
    queryKey: ['kg-graph', selectedArtifactId],
    queryFn: async () => {
      if (!selectedArtifactId) {
        // 如果没有选中文物，返回空数据
        // 后续可以扩展为获取全局图谱
        return { nodes: [], edges: [] };
      }
      const data = await kgService.queryGraph(selectedArtifactId, 2);
      return data;
    },
    enabled: true,
  });

  // 搜索相关文物
  const {
    data: searchResults,
    isLoading: searchLoading,
  } = useQuery<KGSearchResult[]>({
    queryKey: ['kg-search', searchKeyword],
    queryFn: () => kgService.search(searchKeyword, 20),
    enabled: searchKeyword.length > 0,
  });

  // 处理节点点击
  const handleNodeClick = useCallback((node: KGNode) => {
    setSelectedNode(node);
    setDetailModalVisible(true);
  }, []);

  // 选择文物进行图谱查询
  const handleSelectArtifact = (artifactId: string) => {
    setSelectedArtifactId(artifactId);
    setSearchParams({ artifact: artifactId });
    message.success('已加载该文物的图谱');
  };

  // 渲染搜索结果
  const renderSearchResults = () => {
    if (!searchKeyword) return null;

    if (searchLoading) {
      return <Spin size="small" />;
    }

    if (!searchResults || searchResults.length === 0) {
      return (
        <Text style={{ color: 'rgba(255,255,255,0.5)' }}>
          未找到 "{searchKeyword}" 相关结果
        </Text>
      );
    }

    return (
      <List
        size="small"
        dataSource={searchResults.slice(0, 10)}
        renderItem={(item) => (
          <List.Item
            style={{ cursor: 'pointer', padding: '8px 12px' }}
            onClick={() => {
              if (item.type === 'Artifact') {
                handleSelectArtifact(item.id);
              } else {
                setSelectedArtifactId(null);
                message.info(`已筛选 ${item.type}: ${item.name}`);
              }
              setSearchKeyword('');
            }}
          >
            <Space>
              <Tag color={item.type === 'Artifact' ? 'gold' : 'blue'}>
                {item.type}
              </Tag>
              <Text style={{ color: '#fff' }}>{item.name}</Text>
              {item.connections !== undefined && (
                <Text style={{ color: 'rgba(255,255,255,0.4)', fontSize: 12 }}>
                  {item.connections} 个关联
                </Text>
              )}
            </Space>
          </List.Item>
        )}
      />
    );
  };

  return (
    <div style={{ padding: 24 }}>
      {/* 页面标题 */}
      <div style={{ marginBottom: 24 }}>
        <Title
          level={2}
          style={{
            color: '#C9A962',
            margin: 0,
            fontFamily: '"Noto Serif SC", serif',
          }}
        >
          知识图谱
        </Title>
        <Text style={{ color: 'rgba(255,255,255,0.5)' }}>
          探索文物之间的历史、工艺与文化关联
        </Text>
      </div>

      <Row gutter={[24, 24]}>
        {/* 左侧：搜索和文物列表 */}
        <Col xs={24} lg={8}>
          {/* 搜索框 */}
          <Card
            style={{
              background: 'rgba(20, 20, 31, 0.9)',
              border: '1px solid rgba(201, 169, 98, 0.2)',
              marginBottom: 16,
            }}
          >
            <Input
              placeholder="搜索文物、朝代、工艺..."
              prefix={<SearchOutlined style={{ color: '#C9A962' }} />}
              value={searchKeyword}
              onChange={(e) => setSearchKeyword(e.target.value)}
              style={{
                background: 'rgba(255,255,255,0.05)',
                borderColor: 'rgba(201, 169, 98, 0.3)',
              }}
            />
            {searchKeyword && (
              <div
                style={{
                  marginTop: 8,
                  background: 'rgba(20, 20, 31, 0.8)',
                  borderRadius: 8,
                  maxHeight: 300,
                  overflow: 'auto',
                }}
              >
                {renderSearchResults()}
              </div>
            )}
          </Card>

          {/* 文物列表 */}
          <Card
            title={
              <Space>
                <InfoCircleOutlined style={{ color: '#C9A962' }} />
                <span style={{ color: '#C9A962' }}>选择文物</span>
              </Space>
            }
            extra={
              <Button
                size="small"
                onClick={() => {
                  setSelectedArtifactId(null);
                  setSearchParams({});
                }}
              >
                查看全局
              </Button>
            }
            style={{
              background: 'rgba(20, 20, 31, 0.9)',
              border: '1px solid rgba(201, 169, 98, 0.2)',
            }}
            styles={{ header: { borderColor: 'rgba(201, 169, 98, 0.2)' } }}
          >
            <div style={{ maxHeight: 500, overflow: 'auto' }}>
              {artifactsData?.items && artifactsData.items.length > 0 ? (
                <List
                  dataSource={artifactsData.items}
                  renderItem={(artifact) => (
                    <List.Item
                      style={{
                        cursor: 'pointer',
                        background:
                          selectedArtifactId === artifact.id
                            ? 'rgba(201, 169, 98, 0.1)'
                            : 'transparent',
                        borderRadius: 8,
                        padding: '12px',
                      }}
                      onClick={() => handleSelectArtifact(artifact.id)}
                    >
                      <List.Item.Meta
                        avatar={
                          <Avatar
                            style={{
                              background: 'rgba(201, 169, 98, 0.2)',
                              color: '#C9A962',
                            }}
                          >
                            {artifact.name.charAt(0)}
                          </Avatar>
                        }
                        title={
                          <Text style={{ color: '#fff' }}>{artifact.name}</Text>
                        }
                        description={
                          <Space>
                            {artifact.dynasty && (
                              <Tag color="blue">{artifact.dynasty}</Tag>
                            )}
                            {artifact.category && (
                              <Tag color="green">{artifact.category}</Tag>
                            )}
                          </Space>
                        }
                      />
                    </List.Item>
                  )}
                />
              ) : (
                <Empty
                  description={
                    <Text style={{ color: 'rgba(255,255,255,0.5)' }}>
                      暂无文物数据
                    </Text>
                  }
                />
              )}
            </div>
          </Card>
        </Col>

        {/* 右侧：图谱可视化 */}
        <Col xs={24} lg={16}>
          <KnowledgeGraph
            data={graphData}
            loading={graphLoading}
            height={600}
            onNodeClick={handleNodeClick}
            onRefresh={() => refetchGraph()}
            showControls={true}
          />

          {/* 图谱说明 */}
          <Card
            style={{
              background: 'rgba(20, 20, 31, 0.8)',
              border: '1px solid rgba(201, 169, 98, 0.2)',
              marginTop: 16,
            }}
          >
            <Title level={5} style={{ color: '#C9A962', marginBottom: 12 }}>
              图谱说明
            </Title>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text style={{ color: 'rgba(255,255,255,0.7)' }}>
                <Tag color="#C9A962">金色</Tag> 中心节点为文物节点
              </Text>
              <Text style={{ color: 'rgba(255,255,255,0.7)' }}>
                <Tag color="#4A9EFF">蓝色</Tag> 朝代关系节点
              </Text>
              <Text style={{ color: 'rgba(255,255,255,0.7)' }}>
                <Tag color="#50C878">绿色</Tag> 文物分类节点
              </Text>
              <Text style={{ color: 'rgba(255,255,255,0.7)' }}>
                <Tag color="#FF7F50">珊瑚色</Tag> 工艺技术节点
              </Text>
              <Text style={{ color: 'rgba(255,255,255,0.7)' }}>
                <Tag color="#9370DB">紫色</Tag> 材质节点
              </Text>
              <Paragraph style={{ color: 'rgba(255,255,255,0.5)', marginTop: 8 }}>
                点击节点查看详情。使用鼠标滚轮缩放，拖拽移动视图。
              </Paragraph>
            </Space>
          </Card>
        </Col>
      </Row>

      {/* 节点详情弹窗 */}
      <Modal
        title={null}
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={null}
        width={600}
        styles={{
          content: {
            background: 'rgba(20, 20, 31, 0.95)',
            border: '1px solid rgba(201, 169, 98, 0.3)',
          },
        }}
      >
        {selectedNode && (
          <div>
            <Space style={{ marginBottom: 16 }}>
              <Title level={4} style={{ color: '#C9A962', margin: 0 }}>
                {String(selectedNode.properties?.name || selectedNode.label)}
              </Title>
              <Tag color={
                selectedNode.label === 'Artifact' ? 'gold' :
                selectedNode.label === 'Dynasty' ? 'blue' :
                selectedNode.label === 'Category' ? 'green' :
                'default'
              }>
                {selectedNode.label}
              </Tag>
            </Space>

            {selectedNode.label === 'Artifact' && selectedNode.id && (
              <Descriptions
                column={1}
                size="small"
                styles={{
                  label: { color: 'rgba(255,255,255,0.5)' },
                  content: { color: '#fff' },
                }}
              >
                {selectedNode.properties?.dynasty != null ? (
                  <Descriptions.Item label="朝代">
                    {String(selectedNode.properties.dynasty as string)}
                  </Descriptions.Item>
                ) : null}
                {selectedNode.properties?.category != null ? (
                  <Descriptions.Item label="分类">
                    {String(selectedNode.properties.category as string)}
                  </Descriptions.Item>
                ) : null}
                {selectedNode.properties?.description != null ? (
                  <Descriptions.Item label="描述">
                    {String(selectedNode.properties.description as string)}
                  </Descriptions.Item>
                ) : null}
              </Descriptions>
            )}

            {selectedNode.label !== 'Artifact' && (
              <Button
                type="primary"
                icon={<LinkOutlined />}
                onClick={() => {
                  setSelectedArtifactId(selectedNode.id);
                  setDetailModalVisible(false);
                }}
              >
                查看相关文物
              </Button>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
