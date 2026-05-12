import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import {
  Card,
  Form,
  Input,
  Select,
  Upload,
  Button,
  Typography,
  Steps,
  message,
  Row,
  Col,
  Modal,
  Space,
} from 'antd';
import { UploadOutlined, InboxOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { artifactService } from '@/services/artifactService';

const { Title, Text } = Typography;
const { TextArea } = Input;
const { Dragger } = Upload;

const viewTypes = [
  { value: 'front', label: '正面' },
  { value: 'side_left', label: '左侧' },
  { value: 'side_right', label: '右侧' },
  { value: 'back', label: '背面' },
  { value: 'top', label: '顶面' },
  { value: 'bottom', label: '底面' },
];

const categories = [
  { value: '青铜器', label: '青铜器' },
  { value: '陶器', label: '陶器' },
  { value: '金银器', label: '金银器' },
  { value: '玉石器', label: '玉石器' },
  { value: '书画', label: '书画' },
  { value: '其他', label: '其他' },
];

export default function UploadPage() {
  const [form] = Form.useForm();
  const [currentStep, setCurrentStep] = useState(0);
  const [uploadedImages, setUploadedImages] = useState<Record<string, string>>({});
  const uploadedCount = Object.keys(uploadedImages).length;
  const [artifactId, setArtifactId] = useState<string | null>(null);
  const [pendingFiles, setPendingFiles] = useState<{ file: File; viewType: string }[]>([]);
  const [viewTypeModalVisible, setViewTypeModalVisible] = useState(false);
  const navigate = useNavigate();

  const createMutation = useMutation({
    mutationFn: artifactService.create,
    onSuccess: (data) => {
      setArtifactId(data.id);
      setCurrentStep(1);
      message.success('文物信息已保存');
    },
    onError: () => {
      message.error('创建失败，请重试');
    },
  });

  const uploadMutation = useMutation({
    mutationFn: ({ file, viewType }: { file: File; viewType: string }) =>
      artifactService.uploadImage(artifactId!, file, viewType),
    onSuccess: (data) => {
      setUploadedImages((prev) => ({ ...prev, [data.view_type!]: data.id }));
      message.success(`已上传 ${data.view_type}`);
    },
    onError: () => {
      message.error('上传失败');
    },
  });

  const onFinish = (values: any) => {
    createMutation.mutate(values);
  };

  const beforeUpload = (file: File, fileList: File[]) => {
    const viewType = fileList.indexOf(file) === 0 ? 'front' : '';
    setPendingFiles(prev => [...prev, { file, viewType }]);
    return false;
  };

  const handleConfirmUpload = () => {
    const validFiles = pendingFiles.filter(p => p.viewType);
    if (validFiles.length === 0) {
      message.error('请至少选择一个视角');
      return;
    }
    setViewTypeModalVisible(false);
    validFiles.forEach(({ file, viewType }) => {
      uploadMutation.mutate({ file, viewType });
    });
    setPendingFiles([]);
  };

  const steps = [
    { title: '填写信息', icon: <InboxOutlined /> },
    { title: '上传图像', icon: <UploadOutlined /> },
    { title: '完成', icon: <CheckCircleOutlined /> },
  ];

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
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
          UPLOAD
        </div>
        <Title level={2} style={{
          color: '#C9A962',
          margin: 0,
          fontFamily: '"Noto Serif SC", serif',
          letterSpacing: '0.1em',
          fontSize: 36,
        }}>
          上传文物
        </Title>
      </div>

      <Steps
        current={currentStep}
        items={steps}
        style={{ marginBottom: 48 }}
        size="small"
      />

      {/* Step 1: Artifact Info */}
      {currentStep === 0 && (
        <Card className="card-glass" style={{ padding: 8 }}>
          <Form form={form} layout="vertical" onFinish={onFinish}>
            <Form.Item
              name="name"
              label={<Text style={{ color: 'rgba(255, 255, 255, 0.7)' }}>文物名称</Text>}
              rules={[{ required: true, message: '请输入文物名称' }]}
            >
              <Input
                placeholder="如：错金银四龙四凤铜方案座"
                size="large"
                className="input-glass"
              />
            </Form.Item>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="dynasty" label={<Text style={{ color: 'rgba(255, 255, 255, 0.7)' }}>朝代</Text>}>
                  <Input placeholder="如：战国" size="large" className="input-glass" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="category" label={<Text style={{ color: 'rgba(255, 255, 255, 0.7)' }}>分类</Text>}>
                  <Select
                    placeholder="选择分类"
                    size="large"
                    options={categories}
                    className="input-glass"
                  />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item name="description" label={<Text style={{ color: 'rgba(255, 255, 255, 0.7)' }}>描述</Text>}>
              <TextArea rows={4} placeholder="简要描述此文物..." className="input-glass" />
            </Form.Item>

            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                size="large"
                loading={createMutation.isPending}
                className="btn-gold"
              >
                保存并继续
              </Button>
            </Form.Item>
          </Form>
        </Card>
      )}

      {/* Step 2: Upload Images */}
      {currentStep === 1 && (
        <Card className="card-glass" style={{ padding: 8 }}>
          <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
            上传多视图图像
          </Title>
          <Text style={{ color: 'rgba(255, 255, 255, 0.5)', display: 'block', marginBottom: 24 }}>
            请上传至少4张文物图像（正面、侧面、背面等），以获得最佳的3D重建效果
          </Text>

          <Dragger
            multiple
            accept="image/*"
            beforeUpload={beforeUpload}
            showUploadList={false}
            disabled={uploadMutation.isPending}
            onChange={({ fileList }) => {
              if (fileList.length > 0 && pendingFiles.length > 0) {
                setViewTypeModalVisible(true);
              }
            }}
            style={{
              background: 'rgba(201, 169, 98, 0.03)',
              border: '2px dashed rgba(201, 169, 98, 0.2)',
              borderRadius: 16,
              padding: 32,
            }}
          >
            <div style={{ textAlign: 'center' }}>
              <div style={{
                width: 64,
                height: 64,
                borderRadius: '50%',
                background: 'linear-gradient(135deg, rgba(201, 169, 98, 0.15) 0%, rgba(201, 169, 98, 0.05) 100%)',
                border: '1px solid rgba(201, 169, 98, 0.2)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 20px',
              }}>
                <UploadOutlined style={{ fontSize: 28, color: '#C9A962' }} />
              </div>
              <p style={{ color: '#fff', fontSize: 16, marginBottom: 8 }}>
                点击或拖拽图像到此区域上传
              </p>
              <p style={{ color: 'rgba(255, 255, 255, 0.4)', fontSize: 13 }}>
                支持 JPG、PNG、WEBP 格式，建议分辨率 2048×2048
              </p>
            </div>
          </Dragger>

          {uploadedCount > 0 && (
            <div style={{ marginTop: 32 }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                marginBottom: 16,
              }}>
                <CheckCircleOutlined style={{ color: '#C9A962', fontSize: 18 }} />
                <Title level={5} style={{ color: '#fff', margin: 0 }}>
                  已上传 {uploadedCount} 张图像
                </Title>
              </div>
              <Row gutter={[12, 12]}>
                {Object.entries(uploadedImages).map(([viewType, id]) => (
                  <Col span={6} key={id}>
                    <Card
                      size="small"
                      style={{
                        background: 'rgba(201, 169, 98, 0.08)',
                        border: '1px solid rgba(201, 169, 98, 0.2)',
                        textAlign: 'center',
                      }}
                    >
                      <CheckCircleOutlined style={{ color: '#C9A962', fontSize: 20, marginBottom: 4 }} />
                      <div style={{ color: '#fff', fontSize: 12 }}>{viewType}</div>
                    </Card>
                  </Col>
                ))}
              </Row>
            </div>
          )}

          <div style={{ marginTop: 32, display: 'flex', gap: 12 }}>
            <Button onClick={() => setCurrentStep(0)}>
              上一步
            </Button>
            <Button
              type="primary"
              disabled={uploadedCount < 4}
              onClick={() => setCurrentStep(2)}
              className="btn-gold"
            >
              完成
            </Button>
          </div>
        </Card>
      )}

      {/* Step 3: Complete */}
      {currentStep === 2 && (
        <Card
          className="card-glass"
          style={{
            textAlign: 'center',
            padding: 64,
          }}
        >
          <div style={{
            width: 80,
            height: 80,
            borderRadius: '50%',
            background: 'linear-gradient(135deg, rgba(201, 169, 98, 0.2) 0%, rgba(201, 169, 98, 0.05) 100%)',
            border: '1px solid rgba(201, 169, 98, 0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 24px',
          }}>
            <CheckCircleOutlined style={{ fontSize: 36, color: '#C9A962' }} />
          </div>
          <Title level={3} style={{ color: '#fff', marginBottom: 12 }}>
            上传完成！
          </Title>
          <Text style={{ color: 'rgba(255, 255, 255, 0.5)', display: 'block', marginBottom: 32 }}>
            文物信息已保存，现在可以开始3D重建
          </Text>
          <Space size={16}>
            <Button size="large" onClick={() => navigate(`/viewer/${artifactId}`)}>
              查看文物
            </Button>
            <Button
              type="primary"
              size="large"
              onClick={() => navigate('/gallery')}
              className="btn-gold"
            >
              返回文物库
            </Button>
          </Space>
        </Card>
      )}

      {/* View Type Selection Modal */}
      <Modal
        title={<span style={{ color: '#C9A962', fontFamily: '"Noto Serif SC", serif' }}>选择图像视角</span>}
        open={viewTypeModalVisible}
        onOk={handleConfirmUpload}
        onCancel={() => { setViewTypeModalVisible(false); setPendingFiles([]); }}
        okText="确认上传"
        cancelText="取消"
        centered
        styles={{
          content: {
            background: 'rgba(14, 14, 22, 0.95)',
            backdropFilter: 'blur(20px)',
            border: '1px solid rgba(201, 169, 98, 0.2)',
            borderRadius: 16,
          },
          header: { borderBottom: '1px solid rgba(201, 169, 98, 0.1)' },
          body: { padding: '24px' },
        }}
      >
        <div style={{ maxHeight: 400, overflow: 'auto' }}>
          {pendingFiles.map((pf, idx) => (
            <div
              key={idx}
              style={{
                marginBottom: 12,
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: '8px 12px',
                background: 'rgba(255, 255, 255, 0.02)',
                borderRadius: 8,
              }}
            >
              <span style={{
                color: 'rgba(255, 255, 255, 0.7)',
                flex: 1,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                fontSize: 13,
              }}>
                {pf.file.name}
              </span>
              <Select
                placeholder="选择视角"
                value={pf.viewType || undefined}
                onChange={(val) => {
                  setPendingFiles(prev =>
                    prev.map((p, i) => i === idx ? { ...p, viewType: val } : p)
                  );
                }}
                options={viewTypes}
                style={{ width: 120 }}
                size="small"
              />
            </div>
          ))}
        </div>
      </Modal>
    </div>
  );
}
