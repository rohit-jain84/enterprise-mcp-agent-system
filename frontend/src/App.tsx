import { Routes, Route } from 'react-router-dom';
import Layout from './components/common/Layout';
import ChatPage from './pages/ChatPage';
import ApprovalQueuePage from './pages/ApprovalQueuePage';
import SessionHistoryPage from './pages/SessionHistoryPage';
import SettingsPage from './pages/SettingsPage';
import LoginPage from './pages/LoginPage';
import { useAuthStore } from './stores/authStore';

function App() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<ChatPage />} />
        <Route path="/approvals" element={<ApprovalQueuePage />} />
        <Route path="/history" element={<SessionHistoryPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </Layout>
  );
}

export default App;
