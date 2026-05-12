import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, Row, Col, Input, Select, Spin, Typography, Badge, Pagination } from 'antd';
import { Link } from 'react-router-dom';
import { SearchOutlined, FilterOutlined } from '@ant-design/icons';
import { artifactService } from '@/services/artifactService';
import type { Artifact, ArtifactImage } from '@/types';

const { Title } = Typography;
const { Search } = Input;

const categories = [
  { value: '', label: '全部分类' },
  { value: '青铜器', label: '青铜器' },
  { value: '陶器', label: '陶器' },
  { value: '金银器', label: '金银器' },
  { value: '玉石器', label: '玉石器' },
  { value: '书画', label: '书画' },
];

export default function GalleryPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const pageSize = 12;

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['artifacts', page, search, category],
    queryFn: () =>
      artifactService.list({
        page,
        page_size: pageSize,
        search: search || undefined,
        category: category || undefined,
      }),
  });

  // Fetch images for all artifacts in the list
  const artifactIds = data?.items.map((a: Artifact) => a.id) || [];
  const { data: imagesMap } = useQuery({
    queryKey: ['artifacts-images', artifactIds],
    queryFn: async () => {
      const results = await Promise.all(
        artifactIds.map(async (id: string) => {
          const images = await artifactService.listImages(id);
          return { id, images };
        })
      );
      return Object.fromEntries(results.map(r => [r.id, r.images]));
    },
    enabled: artifactIds.length > 0,
  });

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 40 }}>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 12,
          marginBottom: 8,
          color: 'rgba(201, 169, 98, 0.5)',
          fontSize: 11,
          letterSpacing: '0.3em',
        }}>
          <div style={{ width: 20, height: 1, background: 'rgba(201, 169, 98, 0.3)' }} />
          COLLECTION
        </div>
        <Title
          level={2}
          style={{
            color: '#C9A962',
            margin: 0,
            fontFamily: '"Noto Serif SC", serif',
            letterSpacing: '0.1em',
            fontSize: 36,
          }}
        >
          文物库
        </Title>
      </div>

      {/* Filters */}
      <div
        className="card-glass"
        style={{
          display: 'flex',
          gap: 16,
          marginBottom: 32,
          flexWrap: 'wrap',
          alignItems: 'center',
          padding: '16px 20px',
        }}
      >
        <Search
          placeholder="搜索文物名称..."
          allowClear
          style={{ width: 280 }}
          onSearch={(value) => { setSearch(value); setPage(1); }}
          prefix={<SearchOutlined style={{ color: 'rgba(201, 169, 98, 0.5)' }} />}
          className="input-glass"
        />
        <Select
          placeholder="选择分类"
          options={categories}
          value={category}
          onChange={(val) => { setCategory(val); setPage(1); }}
          style={{ width: 150 }}
          suffixIcon={<FilterOutlined style={{ color: '#C9A962' }} />}
          className="input-glass"
        />
        <div style={{ color: 'rgba(255, 255, 255, 0.4)', marginLeft: 'auto', fontSize: 13 }}>
          共 <span style={{ color: '#C9A962', fontWeight: 500 }}>{data?.total || 0}</span> 件文物
        </div>
      </div>

      {/* Loading State */}
      {(isLoading || isFetching) && (
        <div style={{ textAlign: 'center', padding: 100 }}>
          <Spin size="large" />
        </div>
      )}

      {/* Artifact Grid */}
      {!isLoading && !isFetching && (
        <>
          <Row gutter={[24, 24]} className="stagger-children">
            {data?.items.map((artifact: Artifact) => {
              const artifactImages: ArtifactImage[] = imagesMap?.[artifact.id] || [];
              const primaryImage = artifactImages[0];
              return (
                <Col xs={24} sm={12} md={8} lg={6} key={artifact.id}>
                  <Link to={`/viewer/${artifact.id}`} style={{ textDecoration: 'none' }}>
                    <Card
                      hoverable
                      className="card-glass"
                      style={{
                        overflow: 'hidden',
                        cursor: 'pointer',
                      }}
                      styles={{
                        body: { padding: 0 },
                      }}
                      cover={
                        <div
                          style={{
                            height: 220,
                            position: 'relative',
                            overflow: 'hidden',
                            background: primaryImage?.thumbnail_url || primaryImage?.image_url
                              ? 'transparent'
                              : 'linear-gradient(135deg, rgba(201, 169, 98, 0.08) 0%, rgba(20, 20, 31, 0.9) 100%)',
                          }}
                        >
                          {primaryImage?.thumbnail_url || primaryImage?.image_url ? (
                            <img
                              src={primaryImage.thumbnail_url || primaryImage.image_url}
                              alt={artifact.name}
                              style={{
                                width: '100%',
                                height: '100%',
                                objectFit: 'cover',
                                transition: 'transform 0.4s ease',
                              }}
                              onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.05)'}
                              onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
                            />
                          ) : (
                            <div style={{
                              position: 'absolute',
                              inset: 0,
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                            }}>
                              <div style={{
                                width: 60,
                                height: 60,
                                border: '1px solid rgba(201, 169, 98, 0.2)',
                                borderRadius: '50%',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                color: 'rgba(201, 169, 98, 0.3)',
                                fontSize: 20,
                              }}>◆</div>
                            </div>
                          )}

                          {/* Category badge */}
                          <Badge
                            count={artifact.category || '未分类'}
                            style={{
                              position: 'absolute',
                              top: 12,
                              right: 12,
                              backgroundColor: 'rgba(10, 10, 15, 0.8)',
                              color: '#C9A962',
                              border: '1px solid rgba(201, 169, 98, 0.3)',
                              backdropFilter: 'blur(8px)',
                              fontSize: 11,
                              padding: '2px 10px',
                            }}
                          />

                          {/* Hover overlay */}
                          <div style={{
                            position: 'absolute',
                            inset: 0,
                            background: 'linear-gradient(180deg, transparent 40%, rgba(10, 10, 15, 0.9) 100%)',
                            opacity: 0,
                            transition: 'opacity 0.3s ease',
                          }}
                          onMouseEnter={(e) => (e.currentTarget.style.opacity = '1')}
                          onMouseLeave={(e) => (e.currentTarget.style.opacity = '0')}
                          />
                        </div>
                      }
                    >
                      <div style={{ padding: 16 }}>
                        <Title
                          level={5}
                          style={{
                            color: '#fff',
                            margin: 0,
                            marginBottom: 8,
                            fontFamily: '"Noto Serif SC", serif',
                            fontSize: 16,
                            fontWeight: 500,
                            letterSpacing: '0.02em',
                          }}
                          ellipsis={{ rows: 1 }}
                        >
                          {artifact.name}
                        </Title>
                        <div style={{
                          color: 'rgba(255, 255, 255, 0.45)',
                          fontSize: 12,
                          letterSpacing: '0.05em',
                          marginBottom: artifact.description ? 8 : 0,
                        }}>
                          {artifact.dynasty || '年代不详'} · {artifact.category || '未分类'}
                        </div>
                        {artifact.description && (
                          <div
                            style={{
                              color: 'rgba(255, 255, 255, 0.35)',
                              fontSize: 12,
                              lineHeight: 1.6,
                              display: '-webkit-box',
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: 'vertical',
                              overflow: 'hidden',
                            }}
                          >
                            {artifact.description}
                          </div>
                        )}
                      </div>
                    </Card>
                  </Link>
                </Col>
              );
            })}
          </Row>

          {/* Pagination */}
          {data && data.pages > 1 && (
            <div style={{ textAlign: 'center', marginTop: 48 }}>
              <Pagination
                current={page}
                pageSize={pageSize}
                total={data.total}
                onChange={handlePageChange}
                showSizeChanger={false}
                showTotal={(total) => `共 ${total} 件文物`}
              />
            </div>
          )}
        </>
      )}

      {/* Empty State */}
      {!isLoading && !isFetching && (!data?.items || data.items.length === 0) && (
        <div
          className="card-glass"
          style={{
            textAlign: 'center',
            padding: 100,
          }}
        >
          <div style={{
            color: 'rgba(201, 169, 98, 0.3)',
            fontSize: 48,
            marginBottom: 16,
            letterSpacing: '0.2em',
          }}>
            ◇
          </div>
          <div style={{ color: 'rgba(255, 255, 255, 0.5)', marginBottom: 8 }}>暂无文物数据</div>
          <div style={{ color: 'rgba(255, 255, 255, 0.3)', fontSize: 13 }}>
            点击上方"上传"按钮添加文物
          </div>
        </div>
      )}
    </div>
  );
}
