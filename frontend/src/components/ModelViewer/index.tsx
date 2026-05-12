import { Suspense, useRef, useState, useCallback, useImperativeHandle, forwardRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Environment, useGLTF, Center, Html, useProgress } from '@react-three/drei';
import * as THREE from 'three';

export interface ModelViewer3DHandle {
  screenshot: () => string | null;
  zoomIn: () => void;
  zoomOut: () => void;
  resetView: () => void;
  toggleFullscreen: () => void;
}

interface ModelViewerProps {
  modelUrl?: string;
  className?: string;
}

function Loader() {
  const { progress } = useProgress();
  return (
    <Html center>
      <div style={{
        color: '#C9A962',
        textAlign: 'center',
        background: 'rgba(0,0,0,0.7)',
        padding: '20px 40px',
        borderRadius: '12px',
        border: '1px solid rgba(201, 169, 98, 0.3)',
      }}>
        <div style={{ fontSize: 24, marginBottom: 8 }}>⚙️</div>
        <div style={{ fontSize: 14, marginBottom: 8 }}>加载中... {progress.toFixed(0)}%</div>
        <div style={{
          width: 200,
          height: 4,
          background: 'rgba(255,255,255,0.1)',
          borderRadius: 2,
          overflow: 'hidden',
        }}>
          <div style={{
            width: `${progress}%`,
            height: '100%',
            background: '#C9A962',
            transition: 'width 0.3s',
          }} />
        </div>
      </div>
    </Html>
  );
}

function Model({ url }: { url: string }) {
  const { scene } = useGLTF(url);
  const ref = useRef<THREE.Group>(null);

  useFrame((_, delta) => {
    if (ref.current) {
      ref.current.rotation.y += delta * 0.1;
    }
  });

  return <primitive ref={ref} object={scene} />;
}

function PlaceholderModel() {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame((_, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += delta * 0.5;
    }
  });

  return (
    <mesh ref={meshRef} castShadow receiveShadow>
      <dodecahedronGeometry args={[1.5, 0]} />
      <meshStandardMaterial
        color="#C9A962"
        roughness={0.3}
        metalness={0.8}
      />
    </mesh>
  );
}

function Scene({
  modelUrl,
  autoRotate,
  controlsRef,
}: {
  modelUrl?: string;
  autoRotate: boolean;
  controlsRef: React.MutableRefObject<any>;
}) {
  return (
    <>
      <Suspense fallback={<Loader />}>
        <Center>
          {modelUrl ? <Model url={modelUrl} /> : <PlaceholderModel />}
        </Center>
        <Environment preset="studio" />
      </Suspense>
      <OrbitControls
        ref={controlsRef}
        enableDamping
        dampingFactor={0.05}
        minDistance={1}
        maxDistance={20}
        autoRotate={autoRotate}
        autoRotateSpeed={0.5}
        target={[0, 0, 0]}
      />
      <ambientLight intensity={0.4} />
      <directionalLight
        position={[10, 10, 5]}
        intensity={1}
        castShadow
        shadow-mapSize={[1024, 1024]}
      />
      <pointLight position={[-10, -10, -5]} intensity={0.5} color="#C9A962" />
      <spotLight
        position={[0, 10, 0]}
        angle={0.3}
        penumbra={0.8}
        intensity={0.5}
        castShadow
      />
    </>
  );
}

export const ModelViewer3D = forwardRef<ModelViewer3DHandle, ModelViewerProps>(
  ({ modelUrl, className }, ref) => {
    const [autoRotate, setAutoRotate] = useState(!modelUrl);
    const containerRef = useRef<HTMLDivElement>(null);
    const controlsRef = useRef<any>(null);
    const glRef = useRef<any>(null);

    const screenshot = useCallback(() => {
      const gl = glRef.current;
      if (!gl) return null;
      return gl.domElement.toDataURL('image/png');
    }, []);

    const zoomIn = useCallback(() => {
      const controls = controlsRef.current;
      if (controls?.object) {
        const cur = controls.object.position.length();
        const dir = controls.object.position.clone().normalize();
        controls.object.position.copy(dir.multiplyScalar(Math.max(cur * 0.8, 1)));
        controls.update();
      }
    }, []);

    const zoomOut = useCallback(() => {
      const controls = controlsRef.current;
      if (controls?.object) {
        const cur = controls.object.position.length();
        const dir = controls.object.position.clone().normalize();
        controls.object.position.copy(dir.multiplyScalar(Math.min(cur * 1.25, 20)));
        controls.update();
      }
    }, []);

    const resetView = useCallback(() => {
      const controls = controlsRef.current;
      if (controls) {
        controls.target.set(0, 0, 0);
        controls.object.position.set(0, 2, 5);
        controls.update();
      }
    }, []);

    const toggleFullscreen = useCallback(() => {
      const el = containerRef.current;
      if (!el) return;
      if (!document.fullscreenElement) {
        el.requestFullscreen?.();
      } else {
        document.exitFullscreen?.();
      }
    }, []);

    useImperativeHandle(ref, () => ({
      screenshot,
      zoomIn,
      zoomOut,
      resetView,
      toggleFullscreen,
    }), [screenshot, zoomIn, zoomOut, resetView, toggleFullscreen]);

    return (
      <div ref={containerRef} className={className} style={{ width: '100%', height: '100%', position: 'relative' }}>
        <Canvas
          camera={{ position: [0, 2, 5], fov: 45 }}
          gl={{
            antialias: true,
            toneMapping: THREE.ACESFilmicToneMapping,
            toneMappingExposure: 1.0,
          }}
          shadows
          style={{ background: 'linear-gradient(180deg, #1a1a2e 0%, #0a0a0f 100%)' }}
          onCreated={({ gl }) => {
            gl.setPixelRatio(window.devicePixelRatio);
            glRef.current = gl;
          }}
        >
          <Scene modelUrl={modelUrl} autoRotate={autoRotate} controlsRef={controlsRef} />
        </Canvas>

        {/* Controls overlay */}
        <div
          style={{
            position: 'absolute',
            bottom: 16,
            left: 16,
            display: 'flex',
            gap: 8,
          }}
        >
          <ControlButton
            onClick={() => setAutoRotate(!autoRotate)}
            active={autoRotate}
            title={autoRotate ? '停止旋转' : '自动旋转'}
          >
            🔄
          </ControlButton>
        </div>

        {/* Info overlay */}
        <div
          style={{
            position: 'absolute',
            top: 16,
            left: 16,
            color: 'rgba(255,255,255,0.5)',
            fontSize: 12,
            pointerEvents: 'none',
          }}
        >
          {modelUrl ? '3D 模型已加载' : '占位模型 (请上传文物图像进行3D重建)'}
        </div>
      </div>
    );
  }
);

ModelViewer3D.displayName = 'ModelViewer3D';

function ControlButton({
  children,
  onClick,
  active,
  title,
}: {
  children: React.ReactNode;
  onClick: () => void;
  active?: boolean;
  title: string;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      style={{
        width: 40,
        height: 40,
        borderRadius: 10,
        border: active ? '1px solid #C9A962' : '1px solid rgba(201, 169, 98, 0.25)',
        background: active ? 'rgba(201, 169, 98, 0.2)' : 'rgba(10, 10, 15, 0.7)',
        backdropFilter: 'blur(10px)',
        color: active ? '#C9A962' : 'rgba(255, 255, 255, 0.7)',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 16,
        transition: 'all 0.2s ease',
        boxShadow: active ? '0 0 15px rgba(201, 169, 98, 0.2)' : 'none',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = '#C9A962';
        e.currentTarget.style.color = '#C9A962';
        e.currentTarget.style.boxShadow = '0 0 15px rgba(201, 169, 98, 0.15)';
      }}
      onMouseLeave={(e) => {
        if (!active) {
          e.currentTarget.style.borderColor = 'rgba(201, 169, 98, 0.25)';
          e.currentTarget.style.color = 'rgba(255, 255, 255, 0.7)';
          e.currentTarget.style.boxShadow = 'none';
        }
      }}
    >
      {children}
    </button>
  );
}

export default ModelViewer3D;
