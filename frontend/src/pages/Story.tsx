import { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Card,
  Typography,
  Button,
  Spin,
  Space,
  Tag,
  message,
  Empty,
  Modal,
} from 'antd';
import {
  PlayCircleOutlined,
  SoundOutlined,
  ShareAltOutlined,
  EditOutlined,
} from '@ant-design/icons';
import { artifactService } from '@/services/artifactService';
import { storyService } from '@/services/storyService';

const { Title, Paragraph } = Typography;

const STORY_SECTIONS = [
  { key: 'origin', title: '出土背景', getContent: (s: any) => s.origin },
  { key: 'craftsmanship', title: '制作工艺', getContent: (s: any) => s.craftsmanship },
  { key: 'historical_context', title: '历史背景', getContent: (s: any) => s.historical_context },
  { key: 'cultural_significance', title: '文化价值', getContent: (s: any) => s.cultural_significance },
];

export default function StoryPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: artifact, isLoading: artifactLoading } = useQuery({
    queryKey: ['artifact', id],
    queryFn: () => artifactService.get(id!),
    enabled: !!id,
  });

  const { data: storyData, isLoading: storyLoading } = useQuery({
    queryKey: ['artifact-story', id],
    queryFn: () => storyService.getLatestStory(id!),
    enabled: !!id,
  });

  const generateMutation = useMutation({
    mutationFn: () => storyService.generate(id!, 'detailed'),
    onSuccess: () => {
      message.success('故事生成任务已提交');
      queryClient.invalidateQueries({ queryKey: ['artifact-story', id] });
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '生成失败');
    },
  });

  const handleGenerateStory = () => {
    if (!id) return;
    Modal.confirm({
      title: '确认生成',
      content: '将为该文物生成详细的AI故事，这可能需要几分钟时间。',
      onOk: () => generateMutation.mutate(),
    });
  };

  const handleReadAloud = () => {
    if (storyData?.content?.origin) {
      speechSynthesis.cancel();
      const fullText = [
        storyData.content.origin,
        storyData.content.craftsmanship,
        storyData.content.historical_context,
        storyData.content.cultural_significance,
      ].filter(Boolean).join('。');
      const utterance = new SpeechSynthesisUtterance(fullText);
      utterance.lang = 'zh-CN';
      speechSynthesis.speak(utterance);
      message.info('开始语音播报');
    }
  };

  useEffect(() => {
    return () => { speechSynthesis.cancel(); };
  }, []);

  const handleShare = () => {
    const url = window.location.href;
    if (navigator.share) {
      navigator.share({
        title: artifact?.name || '文物故事',
        text: `${artifact?.name}的详细历史故事`,
        url,
      }).catch(() => {});
    } else {
      navigator.clipboard.writeText(url).then(() => {
        message.success('链接已复制到剪贴板');
      }).catch(() => {
        message.error('复制失败');
      });
    }
  };

  if (artifactLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <Button
        onClick={() => navigate(-1)}
        style={{
          marginBottom: 24,
          borderColor: 'rgba(201, 169, 98, 0.3)',
          color: 'rgba(255, 255, 255, 0.6)',
        }}
      >
        ← 返回
      </Button>

      {/* Header Card */}
      <Card
        className="card-glass"
        style={{
          marginBottom: 32,
          background: 'linear-gradient(135deg, rgba(201, 169, 98, 0.08) 0%, rgba(20, 20, 31, 0.9) 100%)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <div style={{
              fontSize: 10,
              letterSpacing: '0.3em',
              color: 'rgba(201, 169, 98, 0.5)',
              marginBottom: 8,
            }}>
              THE STORY OF
            </div>
            <Title
              level={2}
              style={{
                color: '#C9A962',
                margin: 0,
                marginBottom: 12,
                fontFamily: '"Noto Serif SC", serif',
                letterSpacing: '0.05em',
              }}
            >
              {artifact?.name || '文物'}
            </Title>
            <Space size={[8, 8]}>
              {artifact?.dynasty && (
                <Tag
                  style={{
                    background: 'rgba(201, 169, 98, 0.15)',
                    border: '1px solid rgba(201, 169, 98, 0.3)',
                    color: '#C9A962',
                  }}
                >
                  {artifact.dynasty}
                </Tag>
              )}
              {artifact?.category && (
                <Tag
                  style={{
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    color: 'rgba(255, 255, 255, 0.6)',
                  }}
                >
                  {artifact.category}
                </Tag>
              )}
            </Space>
          </div>
          <Button
            icon={<EditOutlined />}
            onClick={handleGenerateStory}
            loading={generateMutation.isPending}
            className="btn-gold"
          >
            生成故事
          </Button>
        </div>
      </Card>

      {/* Story Content */}
      {storyLoading ? (
        <Card className="card-glass" style={{ textAlign: 'center', padding: 48 }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: 'rgba(255,255,255,0.4)' }}>加载中...</div>
        </Card>
      ) : !storyData ? (
        <Card className="card-glass" style={{ textAlign: 'center', padding: 64 }}>
          <div style={{ fontSize: 40, color: 'rgba(201, 169, 98, 0.2)', marginBottom: 16 }}>◇</div>
          <Empty
            description={
              <span style={{ color: 'rgba(255,255,255,0.4)' }}>
                暂无文物故事，点击上方"生成故事"按钮创建
              </span>
            }
          />
        </Card>
      ) : (
        <>
          {STORY_SECTIONS.map(({ key, title, getContent }) => {
            const content = getContent(storyData.content);
            if (!content) return null;
            return (
              <Card
                key={key}
                className="card-glass"
                style={{ marginBottom: 16 }}
                title={
                  <span style={{ color: '#C9A962', fontFamily: '"Noto Serif SC", serif', fontSize: 15 }}>
                    {title}
                  </span>
                }
              >
                <Paragraph
                  style={{
                    color: 'rgba(255, 255, 255, 0.8)',
                    lineHeight: 2,
                    fontSize: 15,
                    margin: 0,
                  }}
                >
                  {content}
                </Paragraph>
              </Card>
            );
          })}

          {/* Related Events */}
          {storyData.content.related_events && storyData.content.related_events.length > 0 && (
            <Card
              className="card-glass"
              style={{ marginBottom: 16 }}
              title={
                <span style={{ color: '#C9A962', fontFamily: '"Noto Serif SC", serif', fontSize: 15 }}>
                  相关历史事件
                </span>
              }
            >
              <Space wrap size={[8, 8]}>
                {storyData.content.related_events.map((event: string, i: number) => (
                  <Tag
                    key={i}
                    style={{
                      background: 'rgba(201, 169, 98, 0.1)',
                      border: '1px solid rgba(201, 169, 98, 0.25)',
                      color: '#C9A962',
                      padding: '4px 12px',
                    }}
                  >
                    {event}
                  </Tag>
                ))}
              </Space>
            </Card>
          )}

          {/* Similar Artifacts */}
          {storyData.content.similar_artifacts && storyData.content.similar_artifacts.length > 0 && (
            <Card
              className="card-glass"
              style={{ marginBottom: 16 }}
              title={
                <span style={{ color: '#C9A962', fontFamily: '"Noto Serif SC", serif', fontSize: 15 }}>
                  相似文物
                </span>
              }
            >
              <Space wrap size={[8, 8]}>
                {storyData.content.similar_artifacts.map((artifact: string, i: number) => (
                  <Tag
                    key={i}
                    style={{
                      background: 'rgba(255, 255, 255, 0.05)',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      color: 'rgba(255, 255, 255, 0.6)',
                      padding: '4px 12px',
                    }}
                  >
                    {artifact}
                  </Tag>
                ))}
              </Space>
            </Card>
          )}
        </>
      )}

      {/* Audio Player */}
      <Card
        className="card-glass"
        style={{
          marginTop: 24,
          textAlign: 'center',
          padding: '40px 32px',
        }}
      >
        {/* Decorative element */}
        <div style={{
          width: 60,
          height: 60,
          borderRadius: '50%',
          background: 'linear-gradient(135deg, rgba(201, 169, 98, 0.15) 0%, rgba(201, 169, 98, 0.05) 100%)',
          border: '1px solid rgba(201, 169, 98, 0.2)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 20px',
        }}>
          <SoundOutlined style={{ fontSize: 24, color: '#C9A962' }} />
        </div>

        <Title level={5} style={{ color: '#fff', marginBottom: 8 }}>
          语音播报
        </Title>
        <Paragraph style={{ color: 'rgba(255, 255, 255, 0.4)', marginBottom: 24 }}>
          点击播放按钮，收听文物故事语音讲解
        </Paragraph>
        <Space size={16}>
          <Button
            size="large"
            icon={<PlayCircleOutlined />}
            onClick={handleReadAloud}
            disabled={!storyData?.content?.origin}
            className="btn-gold"
          >
            播放
          </Button>
          <Button
            size="large"
            icon={<ShareAltOutlined />}
            onClick={handleShare}
            style={{
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(201, 169, 98, 0.3)',
              color: '#C9A962',
            }}
          >
            分享
          </Button>
        </Space>
      </Card>
    </div>
  );
}
