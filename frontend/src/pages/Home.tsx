import { useQuery } from '@tanstack/react-query';
import { Button, Card, Row, Col, Typography, Space, Spin } from 'antd';
import { Link } from 'react-router-dom';
import { ArrowRightOutlined, ScanOutlined, ReadOutlined, ExperimentOutlined } from '@ant-design/icons';
import { artifactService } from '@/services/artifactService';
import { ragService } from '@/services/ragService';
import { kgService } from '@/services/kgService';

const { Title, Paragraph } = Typography;

const features = [
  {
    icon: <ScanOutlined style={{ fontSize: 40, color: '#C9A962' }} />,
    title: '多视图3D重建',
    description: '上传文物多视图图像，系统基于腾讯混元3D模型自动重建高精度3D模型',
  },
  {
    icon: <ReadOutlined style={{ fontSize: 40, color: '#C9A962' }} />,
    title: '智能文物解读',
    description: '基于Google Gemma大语言模型，生成文物完整历史故事和背景知识',
  },
  {
    icon: <ExperimentOutlined style={{ fontSize: 40, color: '#C9A962' }} />,
    title: '沉浸式展示',
    description: 'WebGL 3D渲染技术，支持交互式旋转、缩放、材质切换',
  },
];

function AnimatedNumber({ value, suffix = '' }: { value: number; suffix?: string }) {
  return (
    <span>
      {value}{suffix}
    </span>
  );
}

export default function HomePage() {
  const { data: artifactsData, isLoading: artifactsLoading } = useQuery({
    queryKey: ['home-artifacts-count'],
    queryFn: async () => {
      const data = await artifactService.list({ page_size: 1 });
      return data.total;
    },
  });

  const { data: ragData } = useQuery({
    queryKey: ['home-rag-count'],
    queryFn: () => ragService.getStatistics(),
  });

  const { data: kgData } = useQuery({
    queryKey: ['home-kg-count'],
    queryFn: () => kgService.getStatistics(),
  });

  const isLoading = artifactsLoading;

  return (
    <div style={{ position: 'relative' }}>
      {/* Hero Section */}
      <div
        style={{
          textAlign: 'center',
          padding: '60px 0 80px',
          position: 'relative',
        }}
      >
        {/* Decorative elements */}
        <div style={{
          position: 'absolute',
          top: '20%',
          left: '10%',
          width: 200,
          height: 200,
          background: 'radial-gradient(circle, rgba(201, 169, 98, 0.08) 0%, transparent 70%)',
          filter: 'blur(40px)',
          pointerEvents: 'none',
        }} />
        <div style={{
          position: 'absolute',
          bottom: '10%',
          right: '10%',
          width: 300,
          height: 300,
          background: 'radial-gradient(circle, rgba(201, 169, 98, 0.05) 0%, transparent 70%)',
          filter: 'blur(60px)',
          pointerEvents: 'none',
        }} />

        {/* Ornament */}
        <div
          className="animate-fade-in"
          style={{
            color: '#C9A962',
            opacity: 0.4,
            fontSize: 12,
            letterSpacing: '0.5em',
            marginBottom: 24,
          }}
        >
          ◆ ◆ ◆
        </div>

        {/* Main title */}
        <Title
          className="animate-fade-in-up"
          style={{
            fontSize: 64,
            fontFamily: '"Noto Serif SC", serif',
            color: '#C9A962',
            marginBottom: 20,
            letterSpacing: '0.08em',
            lineHeight: 1.2,
            textShadow: '0 0 60px rgba(201, 169, 98, 0.3)',
          }}
        >
          启物博言，以通古意
        </Title>

        {/* Subtitle */}
        <Paragraph
          className="animate-fade-in-up"
          style={{
            fontSize: 18,
            color: 'rgba(255, 255, 255, 0.6)',
            maxWidth: 560,
            margin: '0 auto 40px',
            lineHeight: 1.8,
            letterSpacing: '0.02em',
            animationDelay: '0.15s',
          }}
        >
          基于多视图图像的智能文物3D重建与AI解读系统
          <br />
          让文物活起来，让历史触手可及
        </Paragraph>

        {/* CTA buttons */}
        <Space
          size={20}
          className="animate-fade-in-up"
          style={{ animationDelay: '0.25s' }}
        >
          <Link to="/upload">
            <Button
              size="large"
              className="btn-gold"
              style={{
                height: 52,
                paddingLeft: 32,
                paddingRight: 32,
                fontSize: 15,
                borderRadius: 8,
                fontWeight: 500,
              }}
              icon={<ArrowRightOutlined style={{ fontSize: 16 }} />}
              iconPosition="end"
            >
              开始体验
            </Button>
          </Link>
          <Link to="/gallery">
            <Button
              size="large"
              ghost
              className="btn-ghost-gold"
              style={{
                height: 52,
                paddingLeft: 32,
                paddingRight: 32,
                fontSize: 15,
                borderRadius: 8,
              }}
            >
              浏览文物库
            </Button>
          </Link>
        </Space>

        {/* Decorative line */}
        <div style={{
          width: 1,
          height: 60,
          background: 'linear-gradient(180deg, rgba(201, 169, 98, 0.4), transparent)',
          margin: '60px auto 0',
        }} />
      </div>

      {/* Features */}
      <Row
        gutter={[32, 32]}
        style={{
          maxWidth: 1200,
          margin: '0 auto',
          position: 'relative',
        }}
        className="stagger-children"
      >
        {features.map((feature, index) => (
          <Col xs={24} md={8} key={index}>
            <Card
              className="card-glass"
              style={{
                height: '100%',
                cursor: 'default',
              }}
              styles={{
                body: {
                  padding: '36px 32px',
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  textAlign: 'center',
                },
              }}
            >
              {/* Icon container */}
              <div
                style={{
                  width: 80,
                  height: 80,
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, rgba(201, 169, 98, 0.15) 0%, rgba(201, 169, 98, 0.05) 100%)',
                  border: '1px solid rgba(201, 169, 98, 0.2)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: 24,
                  position: 'relative',
                }}
              >
                {/* Glow effect */}
                <div style={{
                  position: 'absolute',
                  inset: -4,
                  borderRadius: '50%',
                  background: 'radial-gradient(circle, rgba(201, 169, 98, 0.1) 0%, transparent 70%)',
                }} />
                {feature.icon}
              </div>

              <Title
                level={4}
                style={{
                  color: '#fff',
                  marginBottom: 12,
                  fontWeight: 500,
                  letterSpacing: '0.05em',
                }}
              >
                {feature.title}
              </Title>
              <Paragraph
                style={{
                  color: 'rgba(255, 255, 255, 0.55)',
                  lineHeight: 1.8,
                  margin: 0,
                  fontSize: 14,
                }}
              >
                {feature.description}
              </Paragraph>
            </Card>
          </Col>
        ))}
      </Row>

      {/* Stats Section */}
      <div
        style={{
          marginTop: 100,
          padding: '64px 0',
          background: 'linear-gradient(180deg, rgba(201, 169, 98, 0.03) 0%, transparent 100%)',
          borderTop: '1px solid rgba(201, 169, 98, 0.08)',
          borderBottom: '1px solid rgba(201, 169, 98, 0.08)',
        }}
      >
        {/* Section ornament */}
        <div style={{
          textAlign: 'center',
          marginBottom: 48,
        }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 16,
            color: 'rgba(201, 169, 98, 0.4)',
            fontSize: 10,
            letterSpacing: '0.4em',
          }}>
            <div style={{ width: 40, height: 1, background: 'rgba(201, 169, 98, 0.3)' }} />
            统计数据
            <div style={{ width: 40, height: 1, background: 'rgba(201, 169, 98, 0.3)' }} />
          </div>
        </div>

        {isLoading ? (
          <div style={{ textAlign: 'center', padding: 48 }}>
            <Spin size="large" />
          </div>
        ) : (
          <Row
            gutter={[80, 48]}
            justify="center"
            style={{ maxWidth: 900, margin: '0 auto' }}
          >
            <Col xs={24} sm={8} style={{ textAlign: 'center' }}>
              <div
                style={{
                  fontSize: 56,
                  fontWeight: 300,
                  fontFamily: '"Cinzel", serif',
                  color: '#C9A962',
                  letterSpacing: '0.05em',
                  lineHeight: 1,
                  marginBottom: 12,
                  textShadow: '0 0 40px rgba(201, 169, 98, 0.3)',
                }}
              >
                <AnimatedNumber value={artifactsData ?? 0} />
              </div>
              <div style={{
                color: 'rgba(255, 255, 255, 0.4)',
                fontSize: 13,
                letterSpacing: '0.15em',
                textTransform: 'uppercase',
              }}>
                馆藏文物
              </div>
              <div style={{
                width: 30,
                height: 1,
                background: 'linear-gradient(90deg, transparent, rgba(201, 169, 98, 0.3), transparent)',
                margin: '16px auto 0',
              }} />
            </Col>
            <Col xs={24} sm={8} style={{ textAlign: 'center' }}>
              <div
                style={{
                  fontSize: 56,
                  fontWeight: 300,
                  fontFamily: '"Cinzel", serif',
                  color: '#C9A962',
                  letterSpacing: '0.05em',
                  lineHeight: 1,
                  marginBottom: 12,
                  textShadow: '0 0 40px rgba(201, 169, 98, 0.3)',
                }}
              >
                <AnimatedNumber value={ragData?.count ?? 0} />
              </div>
              <div style={{
                color: 'rgba(255, 255, 255, 0.4)',
                fontSize: 13,
                letterSpacing: '0.15em',
                textTransform: 'uppercase',
              }}>
                史料文献
              </div>
              <div style={{
                width: 30,
                height: 1,
                background: 'linear-gradient(90deg, transparent, rgba(201, 169, 98, 0.3), transparent)',
                margin: '16px auto 0',
              }} />
            </Col>
            <Col xs={24} sm={8} style={{ textAlign: 'center' }}>
              <div
                style={{
                  fontSize: 56,
                  fontWeight: 300,
                  fontFamily: '"Cinzel", serif',
                  color: '#C9A962',
                  letterSpacing: '0.05em',
                  lineHeight: 1,
                  marginBottom: 12,
                  textShadow: '0 0 40px rgba(201, 169, 98, 0.3)',
                }}
              >
                <AnimatedNumber
                  value={kgData?.node_counts
                    ? Object.values(kgData.node_counts).reduce((a: number, b: number) => a + b, 0)
                    : 0}
                />
              </div>
              <div style={{
                color: 'rgba(255, 255, 255, 0.4)',
                fontSize: 13,
                letterSpacing: '0.15em',
                textTransform: 'uppercase',
              }}>
                图谱节点
              </div>
              <div style={{
                width: 30,
                height: 1,
                background: 'linear-gradient(90deg, transparent, rgba(201, 169, 98, 0.3), transparent)',
                margin: '16px auto 0',
              }} />
            </Col>
          </Row>
        )}
      </div>

      {/* Bottom ornament */}
      <div style={{
        textAlign: 'center',
        paddingTop: 80,
        paddingBottom: 20,
        color: 'rgba(201, 169, 98, 0.3)',
        fontSize: 10,
        letterSpacing: '0.5em',
      }}>
        ◆ ◆ ◆
      </div>
    </div>
  );
}
