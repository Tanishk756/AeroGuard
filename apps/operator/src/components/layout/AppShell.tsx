import React from 'react';
import { Outlet } from 'react-router-dom';
import { AppFooter } from './AppFooter';
import { AppHeader } from './AppHeader';
import { AppSidebar } from './AppSidebar';

export const AppShell: React.FC = () => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        width: '100vw',
        overflow: 'hidden',
        backgroundColor: 'var(--bg-canvas)',
      }}
    >
      <AppHeader />
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <AppSidebar />
        <main
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'auto',
            backgroundColor: 'var(--bg-canvas)',
          }}
        >
          <Outlet />
        </main>
      </div>
      <AppFooter />
    </div>
  );
};
