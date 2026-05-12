import { useCallback, useEffect, useRef, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { Card, Spin, Empty, Tag, Typography, Space, Button, Tooltip, Select } from 'antd';
import { ReloadOutlined, ZoomInOutlined, ZoomOutOutlined, FullscreenOutlined } from '@ant-design/icons';
import type { KGNode, KGQueryResponse } from '@/types';
import './index.css';

const { Text } = Typography;

// 节点类型到颜色的映射
const NODE_CATEGORY_COLORS: Record<string, string> = {
  Artifact: '#C9A962',      // 金色 - 文物
  Dynasty: '#4A9EFF',       // 蓝色 - 朝代
  Category: '#50C878',     // 绿色 - 分类
  Technique: '#FF7F50',    // 珊瑚色 - 工艺
  Material: '#9370DB',     // 紫色 - 材质
  Site: '#20B2AA',         // 青色 - 出土地点
  Person: '#FF69B4',       // 粉色 - 人物
  Event: '#FFD700',        // 金黄色 - 事件
  Museum: '#00CED1',       // 深青色 - 博物馆
  Unknown: '#808080',      // 灰色 - 未知
};

// 关系类型到颜色的映射
const EDGE_COLOR_MAP: Record<string, string> = {
  BELONGS_TO_DYNASTY: '#4A9EFF',
  CATEGORY_IS: '#50C878',
  MADE_USING: '#FF7F50',
  MADE_OF: '#9370DB',
  EXCAVATED_FROM: '#20B2AA',
  RELATED_TO: '#C9A962',
  SIMILAR_TO: '#FF69B4',
  SAME_DYNASTY: '#4A9EFF',
  SAME_CATEGORY: '#50C878',
  MADE_BY: '#FF7F50',
  COLLECTED_BY: '#00CED1',
  default: 'rgba(201, 169, 98, 0.5)',
};

// 关系类型中文映射
const RELATION_LABELS: Record<string, string> = {
  BELONGS_TO_DYNASTY: '所属朝代',
  CATEGORY_IS: '文物分类',
  MADE_USING: '使用工艺',
  MADE_OF: '材质',
  EXCAVATED_FROM: '出土地点',
  RELATED_TO: '相关',
  SIMILAR_TO: '相似',
  SAME_DYNASTY: '同朝代',
  SAME_CATEGORY: '同分类',
  MADE_BY: '制作者',
  COLLECTED_BY: '收藏于',
};

interface KnowledgeGraphProps {
  data?: KGQueryResponse;
  loading?: boolean;
  height?: number | string;
  onNodeClick?: (node: KGNode) => void;
  onRefresh?: () => void;
  showControls?: boolean;
  autoFit?: boolean;
}

interface EchartsNode {
  id: string;
  name: string;
  category: string;
  value: number;
  symbolSize: number;
  itemStyle: {
    color: string;
    borderColor?: string;
    borderWidth?: number;
  };
  label: {
    show: boolean;
    formatter: string;
    color: string;
    fontSize: number;
  };
  nodeData: KGNode;
}

interface EchartsEdge {
  source: string;
  target: string;
  name: string;
  lineStyle: {
    color: string;
    width: number;
    curveness: number;
  };
  label: {
    show: boolean;
    formatter: string;
    fontSize: number;
    color: string;
  };
  edgeData: any;
}

export default function KnowledgeGraph({
  data,
  loading = false,
  height = 500,
  onNodeClick,
  onRefresh,
  showControls = true,
  autoFit = true,
}: KnowledgeGraphProps) {
  const chartRef = useRef<ReactECharts>(null);
  const [selectedNode, setSelectedNode] = useState<KGNode | null>(null);
  const [showLabels, setShowLabels] = useState(true);
  const [filterType, setFilterType] = useState<string | null>(null);

  // 转换图谱数据为 ECharts 格式
  const transformData = useCallback((): { nodes: EchartsNode[]; edges: EchartsEdge[] } => {
    if (!data || !data.nodes || data.nodes.length === 0) {
      return { nodes: [], edges: [] };
    }

    // 过滤节点
    const filteredNodes = filterType
      ? data.nodes.filter(n => n.label === filterType)
      : data.nodes;
    const filteredNodeIds = new Set(filteredNodes.map(n => n.id));

    // 转换节点
    const echartsNodes: EchartsNode[] = filteredNodes.map(node => ({
      id: node.id,
      name: String(node.properties?.name || node.label || '未知'),
      category: node.label,
      value: node.label === 'Artifact' ? 30 : 20,
      symbolSize: node.label === 'Artifact' ? 50 : 40,
      itemStyle: {
        color: NODE_CATEGORY_COLORS[node.label] || NODE_CATEGORY_COLORS.Unknown,
        borderColor: selectedNode?.id === node.id ? '#fff' : undefined,
        borderWidth: selectedNode?.id === node.id ? 3 : 1,
      },
      label: {
        show: showLabels,
        formatter: String(node.properties?.name || node.label || ''),
        color: '#fff',
        fontSize: 12,
      },
      nodeData: node,
    }));

    // 转换边
    const echartsEdges: EchartsEdge[] = (data.edges || [])
      .filter(edge =>
        filteredNodeIds.has(edge.source) &&
        filteredNodeIds.has(edge.target)
      )
      .map(edge => ({
        source: edge.source,
        target: edge.target,
        name: RELATION_LABELS[edge.type] || edge.type,
        lineStyle: {
          color: EDGE_COLOR_MAP[edge.type] || EDGE_COLOR_MAP.default,
          width: 1.5,
          curveness: 0.1,
        },
        label: {
          show: showLabels,
          formatter: String(RELATION_LABELS[edge.type] || edge.type),
          fontSize: 10,
          color: '#aaa',
        },
        edgeData: edge,
      }));

    return { nodes: echartsNodes, edges: echartsEdges };
  }, [data, selectedNode, showLabels, filterType]);

  // 获取所有节点类型
  const nodeCategories = data?.nodes
    ? [...new Set(data.nodes.map(n => n.label || 'Unknown'))]
    : [];

  // 获取图表配置
  const getOption = useCallback(() => {
    const { nodes, edges } = transformData();

    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item' as const,
        backgroundColor: 'rgba(20, 20, 31, 0.95)',
        borderColor: 'rgba(201, 169, 98, 0.3)',
        textStyle: {
          color: '#fff',
        },
        formatter: (params: any) => {
          if (params.dataType === 'edge') {
            return String(params.data.name);
          }
          const node = params.data;
          const nodeData = node?.nodeData as KGNode;
          if (!nodeData) return String(node?.name);

          let content = `<div style="font-weight: bold; color: #C9A962; margin-bottom: 8px;">${node.name}</div>`;
          content += `<div style="color: #888;">类型: ${node.category}</div>`;

          if (nodeData.properties) {
            const props = nodeData.properties;
            if (props.dynasty) content += `<div style="color: #4A9EFF;">朝代: ${String(props.dynasty)}</div>`;
            if (props.category) content += `<div style="color: #50C878;">分类: ${String(props.category)}</div>`;
          }

          return content;
        },
      },
      legend: {
        show: false,
      },
      series: [
        {
          type: 'graph' as const,
          layout: autoFit ? 'force' : 'none',
          roam: true,
          draggable: true,
          symbol: 'circle',
          symbolSize: (_val: number, params: any) => params.data?.symbolSize || 40,
          edgeSymbol: ['circle', 'arrow'],
          edgeSymbolSize: [4, 8],
          force: {
            repulsion: 300,
            gravity: 0.1,
            edgeLength: [80, 200],
            layoutAnimation: true,
          },
          label: {
            show: showLabels,
            position: 'right' as const,
            formatter: '{b}',
            fontSize: 12,
            color: '#fff',
          },
          labelLayout: {
            hideOverlap: true,
          },
          emphasis: {
            focus: 'adjacency' as const,
            lineStyle: {
              width: 3,
            },
            itemStyle: {
              borderWidth: 3,
              borderColor: '#fff',
            },
          },
          lineStyle: {
            opacity: 0.8,
            curveness: 0.1,
          },
          data: nodes,
          links: edges,
          categories: nodeCategories.map(cat => ({
            name: cat,
            itemStyle: {
              color: NODE_CATEGORY_COLORS[cat] || NODE_CATEGORY_COLORS.Unknown,
            },
          })),
        },
      ],
    };
  }, [transformData, showLabels, autoFit, nodeCategories]);

  // 处理节点点击
  const onEvents = {
    click: (params: any) => {
      if (params.dataType === 'node' && params.data?.nodeData) {
        const node = params.data.nodeData as KGNode;
        setSelectedNode(node);
        onNodeClick?.(node);
      }
    },
  };

  // 工具栏操作
  const handleZoomIn = () => {
    const chart = chartRef.current?.getEchartsInstance();
    if (chart) {
      chart.dispatchAction({ type: 'zoom', scaleFactor: 1.2 });
    }
  };

  const handleZoomOut = () => {
    const chart = chartRef.current?.getEchartsInstance();
    if (chart) {
      chart.dispatchAction({ type: 'zoom', scaleFactor: 0.8 });
    }
  };

  const handleFullscreen = () => {
    const chart = chartRef.current?.getEchartsInstance();
    if (chart) {
      chart.dispatchAction({ type: 'graphRoam', zoom: 0 });
    }
  };

  const handleRefresh = () => {
    chartRef.current?.getEchartsInstance().setOption(getOption());
    onRefresh?.();
  };

  // 重新设置选项当数据变化时
  useEffect(() => {
    if (chartRef.current) {
      chartRef.current.getEchartsInstance().setOption(getOption(), true);
    }
  }, [getOption]);

  // 渲染加载状态
  if (loading) {
    return (
      <Card className="kg-card">
        <div className="kg-loading">
          <Spin size="large" />
          <Text style={{ color: '#C9A962', marginTop: 16 }}>正在加载图谱数据...</Text>
        </div>
      </Card>
    );
  }

  // 渲染空状态
  if (!data || data.nodes.length === 0) {
    return (
      <Card className="kg-card">
        <Empty
          description={
            <Text style={{ color: 'rgba(255,255,255,0.5)' }}>
              暂无图谱数据
            </Text>
          }
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      </Card>
    );
  }

  return (
    <Card className="kg-card" styles={{ body: { padding: 0 } }}>
      {/* 工具栏 */}
      {showControls && (
        <div className="kg-toolbar">
          <Space>
            <Text strong style={{ color: '#C9A962', marginRight: 8 }}>
              图谱可视化
            </Text>
            <Tag color="gold">
              {data.nodes.length} 节点
            </Tag>
            <Tag color="blue">
              {data.edges.length} 关系
            </Tag>
          </Space>

          <Space>
            <Select
              placeholder="筛选类型"
              allowClear
              style={{ width: 120 }}
              onChange={(val) => setFilterType(val)}
              options={nodeCategories.map(cat => ({
                value: cat,
                label: (
                  <span>
                    <span
                      style={{
                        display: 'inline-block',
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        backgroundColor: NODE_CATEGORY_COLORS[cat] || '#808080',
                        marginRight: 6,
                      }}
                    />
                    {cat}
                  </span>
                ),
              }))}
            />

            <Tooltip title="显示/隐藏标签">
              <Button
                icon={<span className="kg-icon">T</span>}
                onClick={() => setShowLabels(!showLabels)}
                type={showLabels ? 'primary' : 'default'}
              />
            </Tooltip>

            <Tooltip title="放大">
              <Button icon={<ZoomInOutlined />} onClick={handleZoomIn} />
            </Tooltip>

            <Tooltip title="缩小">
              <Button icon={<ZoomOutOutlined />} onClick={handleZoomOut} />
            </Tooltip>

            <Tooltip title="重置视图">
              <Button icon={<FullscreenOutlined />} onClick={handleFullscreen} />
            </Tooltip>

            {onRefresh && (
              <Tooltip title="刷新">
                <Button icon={<ReloadOutlined />} onClick={handleRefresh} />
              </Tooltip>
            )}
          </Space>
        </div>
      )}

      {/* 图例 */}
      <div className="kg-legend">
        {nodeCategories.map(cat => (
          <Tag
            key={cat}
            color={NODE_CATEGORY_COLORS[cat] || '#808080'}
            className={filterType && filterType !== cat ? 'legend-hidden' : ''}
            onClick={() => setFilterType(filterType === cat ? null : cat)}
            style={{ cursor: 'pointer' }}
          >
            {cat}
          </Tag>
        ))}
      </div>

      {/* 图表 */}
      <ReactECharts
        ref={chartRef}
        option={getOption()}
        style={{ height: typeof height === 'number' ? `${height}px` : height }}
        onEvents={onEvents}
        opts={{ renderer: 'canvas' }}
      />

      {/* 选中节点信息 */}
      {selectedNode && (
        <div className="kg-node-info">
          <Text strong style={{ color: '#C9A962' }}>
            {String(selectedNode.properties?.name || selectedNode.label)}
          </Text>
          <Tag color={NODE_CATEGORY_COLORS[selectedNode.label] || '#808080'}>
            {selectedNode.label}
          </Tag>
          {selectedNode.properties?.dynasty != null ? (
            <Text style={{ color: '#4A9EFF' }}>
              朝代: {String(selectedNode.properties.dynasty as string)}
            </Text>
          ) : null}
          {selectedNode.properties?.category != null ? (
            <Text style={{ color: '#50C878' }}>
              分类: {String(selectedNode.properties.category as string)}
            </Text>
          ) : null}
        </div>
      )}
    </Card>
  );
}
