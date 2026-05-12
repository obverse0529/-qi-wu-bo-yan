import { useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { Layout as AntLayout, Menu, Button, Typography, Modal } from 'antd';
import {
  HomeOutlined,
  AppstoreOutlined,
  UploadOutlined,
  UserOutlined,
  ApiOutlined,
} from '@ant-design/icons';

const { Header, Content, Footer } = AntLayout;
const { Title } = Typography;

const menuItems = [
  { key: '/', icon: <HomeOutlined />, label: <Link to="/">首页</Link> },
  { key: '/gallery', icon: <AppstoreOutlined />, label: <Link to="/gallery">文物库</Link> },
  { key: '/knowledge-graph', icon: <ApiOutlined />, label: <Link to="/knowledge-graph">知识图谱</Link> },
  { key: '/upload', icon: <UploadOutlined />, label: <Link to="/upload">上传</Link> },
  { key: '/admin', icon: <UserOutlined />, label: <Link to="/admin">管理</Link> },
];

export function Layout() {
  const location = useLocation();
  const [aboutVisible, setAboutVisible] = useState(false);

  return (
    <AntLayout className="bg-museum" style={{ minHeight: '100vh', background: 'transparent' }}>
      {/* Noise overlay */}
      <div className="noise-overlay" />

      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(10, 10, 15, 0.75)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          borderBottom: '1px solid rgba(201, 169, 98, 0.15)',
          padding: '0 32px',
          position: 'sticky',
          top: 0,
          zIndex: 100,
          height: 72,
        }}
      >
        <Link to="/" style={{ textDecoration: 'none' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {/* Decorative diamond */}
            <span style={{
              color: '#C9A962',
              fontSize: 10,
              animation: 'pulse-glow 2.5s ease-in-out infinite',
            }}>◆</span>
            <Title
              level={4}
              style={{
                color: '#C9A962',
                margin: 0,
                fontFamily: '"Noto Serif SC", serif',
                letterSpacing: '0.15em',
                fontWeight: 500,
              }}
            >
              启物博言
            </Title>
            <span style={{
              color: 'rgba(255, 255, 255, 0.3)',
              fontSize: 12,
              fontFamily: '"Cinzel", serif',
              letterSpacing: '0.3em',
            }}>
              QIWU BOYAN
            </span>
          </div>
        </Link>

        <Menu
          mode="horizontal"
          selectedKeys={[location.pathname]}
          items={menuItems}
          style={{
            background: 'transparent',
            border: 'none',
            flex: 1,
            justifyContent: 'center',
          }}
          theme="dark"
        />

        <Button
          ghost
          onClick={() => setAboutVisible(true)}
          style={{
            borderColor: 'rgba(201, 169, 98, 0.5)',
            color: '#C9A962',
            fontSize: 13,
            height: 36,
            paddingLeft: 16,
            paddingRight: 16,
          }}
        >
          关于
        </Button>
      </Header>

      <Content
        style={{
          padding: '40px 24px',
          maxWidth: 1400,
          margin: '0 auto',
          width: '100%',
        }}
      >
        <div className="animate-fade-in">
          <Outlet />
        </div>
      </Content>

      <Footer
        style={{
          textAlign: 'center',
          background: 'transparent',
          color: 'rgba(255, 255, 255, 0.35)',
          borderTop: '1px solid rgba(201, 169, 98, 0.08)',
          padding: '32px 24px',
        }}
      >
        {/* Decorative line */}
        <div style={{
          width: 60,
          height: 1,
          background: 'linear-gradient(90deg, transparent, rgba(201, 169, 98, 0.4), transparent)',
          margin: '0 auto 24px',
        }} />

        <div style={{
          fontFamily: '"Noto Serif SC", serif',
          letterSpacing: '0.1em',
          color: 'rgba(201, 169, 98, 0.6)',
          fontSize: 14,
          marginBottom: 8,
        }}>
          启物博言智慧博物馆系统
        </div>
        <div style={{
          fontFamily: '"Cinzel", serif',
          letterSpacing: '0.2em',
          fontSize: 10,
          color: 'rgba(255, 255, 255, 0.25)',
          textTransform: 'uppercase',
        }}>
          Heritage Reimagined · 2026
        </div>
        <div style={{ marginTop: 16, fontSize: 12 }}>
          让文物活起来 · 传承中华文化
        </div>
      </Footer>

      <Modal
        title={null}
        open={aboutVisible}
        onCancel={() => setAboutVisible(false)}
        footer={null}
        width={480}
        centered
        closeIcon={null}
        style={{ top: 20 }}
        styles={{
          content: {
            background: 'rgba(14, 14, 22, 0.95)',
            backdropFilter: 'blur(20px)',
            border: '1px solid rgba(201, 169, 98, 0.2)',
            borderRadius: 16,
            padding: 0,
            overflow: 'hidden',
          },
          body: { padding: '32px' },
        }}
      >
        {/* Header bar */}
        <div style={{
          background: 'linear-gradient(135deg, rgba(201, 169, 98, 0.15) 0%, rgba(201, 169, 98, 0.05) 100%)',
          padding: '24px 32px',
          borderBottom: '1px solid rgba(201, 169, 98, 0.15)',
        }}>
          <div style={{
            fontFamily: '"Cinzel", serif',
            fontSize: 10,
            letterSpacing: '0.3em',
            color: 'rgba(201, 169, 98, 0.6)',
            marginBottom: 8,
          }}>
            MUSEUM NOIR
          </div>
          <Title
            level={3}
            style={{
              color: '#C9A962',
              margin: 0,
              fontFamily: '"Noto Serif SC", serif',
              letterSpacing: '0.1em',
            }}
          >
            关于系统
          </Title>
        </div>

        <div style={{ padding: '28px 32px', lineHeight: 2 }}>
          <p style={{ color: 'rgba(255,255,255,0.9)', fontSize: 15, marginBottom: 16 }}>
            <strong style={{ color: '#C9A962' }}>启物博言智慧博物馆系统</strong>
          </p>
          <p style={{ color: 'rgba(255,255,255,0.65)', fontSize: 14, marginBottom: 12 }}>
            基于多视图图像的智能文物3D重建与AI解读系统
          </p>
          <div style={{
            height: 1,
            background: 'linear-gradient(90deg, transparent, rgba(201, 169, 98, 0.2), transparent)',
            margin: '20px 0',
          }} />
          <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: 13, marginBottom: 8 }}>
            集成腾讯混元3D模型
          </p>
          <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: 13, marginBottom: 8 }}>
            Google Gemma大语言模型
          </p>
          <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: 13, marginBottom: 8 }}>
            Neo4j知识图谱 · Milvus向量检索
          </p>
          <div style={{
            marginTop: 24,
            padding: '16px',
            background: 'rgba(201, 169, 98, 0.05)',
            borderRadius: 8,
            border: '1px solid rgba(201, 169, 98, 0.1)',
          }}>
            <p style={{
              color: 'rgba(255,255,255,0.4)',
              fontSize: 12,
              fontFamily: '"Cinzel", serif',
              letterSpacing: '0.1em',
              margin: 0,
              textAlign: 'center',
            }}>
              让文物活起来 · 传承中华文化
            </p>
          </div>
        </div>
      </Modal>
    </AntLayout>
  );
}
