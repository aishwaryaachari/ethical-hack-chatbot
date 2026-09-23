import { useState } from 'react';
import './styles.css';
import { AuthProvider, useAuth } from './auth';
import Login from './Login';
import Shell from './Shell';

function Gate() {
  const { user } = useAuth();
  const [mode, setMode] = useState('vulnerable');
  if (!user) return <Login />;
  return <Shell mode={mode} setMode={setMode} />;
}

export default function App() {
  return <AuthProvider><Gate /></AuthProvider>;
}
