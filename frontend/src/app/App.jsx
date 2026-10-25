import { Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import Analytics from './pages/Analytics';
import Coverage from './pages/Coverage';
import Dashboard from './pages/Dashboard';
import Issues from './pages/Issues';
import Login from './pages/Login';
import Maintenance from './pages/Maintenance';
import Monitoring from './pages/Monitoring';
import Units from './pages/Units';

function Protected({ children }) {
  if (!sessionStorage.getItem('urbansense_token')) {
    return <Navigate to="/login" replace />;
  }
  return <Layout>{children}</Layout>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="/login" element={<Login />} />
      <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
      <Route path="/monitoring" element={<Protected><Monitoring /></Protected>} />
      <Route path="/units" element={<Protected><Units /></Protected>} />
      <Route path="/issues" element={<Protected><Issues /></Protected>} />
      <Route path="/maintenance" element={<Protected><Maintenance /></Protected>} />
      <Route path="/analytics" element={<Protected><Analytics /></Protected>} />
      <Route path="/coverage" element={<Protected><Coverage /></Protected>} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
