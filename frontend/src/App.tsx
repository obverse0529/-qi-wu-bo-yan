import { Routes, Route } from 'react-router-dom';
import { Layout } from './components/common/Layout';
import HomePage from './pages/Home';
import GalleryPage from './pages/Gallery';
import UploadPage from './pages/Upload';
import ViewerPage from './pages/Viewer';
import StoryPage from './pages/Story';
import KnowledgeGraphPage from './pages/KnowledgeGraph';
import AdminPage from './pages/Admin';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="gallery" element={<GalleryPage />} />
        <Route path="upload" element={<UploadPage />} />
        <Route path="viewer/:id" element={<ViewerPage />} />
        <Route path="story/:id" element={<StoryPage />} />
        <Route path="knowledge-graph" element={<KnowledgeGraphPage />} />
        <Route path="admin" element={<AdminPage />} />
      </Route>
    </Routes>
  );
}

export default App;
