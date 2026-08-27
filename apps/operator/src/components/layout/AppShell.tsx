import React from 'react';
import { Outlet } from 'react-router-dom';
import { useDesktopEnvironment } from '../../hooks/useDesktopEnvironment';
import { DesktopTitlebar } from '../desktop/DesktopTitlebar';
import { AppFooter } from './AppFooter';
import { AppHeader } from './AppHeader';
import { AppSidebar } from './AppSidebar';

export const AppShell: React.FC = () => {
  const { isDesktop } = useDesktopEnvironment();

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
      {isDesktop && <DesktopTitlebar />}
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
