import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { SystemProvider } from './context/SystemContext';
import { AppRoutes } from './routes/AppRoutes';
import './styles/globals.css';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <SystemProvider>
          <AppRoutes />
        </SystemProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
