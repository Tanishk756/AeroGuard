import React from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { AlertsPage } from '../pages/AlertsPage';
import { AnalyticsPage } from '../pages/AnalyticsPage';
import { HistoryPage } from '../pages/HistoryPage';
import { LoginPage } from '../pages/LoginPage';
import { OverviewPage } from '../pages/OverviewPage';
import { ReplayPage } from '../pages/ReplayPage';
import { ScenariosPage } from '../pages/ScenariosPage';
import { SensorsPage } from '../pages/SensorsPage';
import { ThreatsPage } from '../pages/ThreatsPage';
import { TracksPage } from '../pages/TracksPage';
import { ProtectedRoute } from './ProtectedRoute';

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      {/* Public Login Route */}
      <Route path="/login" element={<LoginPage />} />

      {/* Authenticated Application Routes */}
      <Route
        path="/app"
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/app/overview" replace />} />
        <Route path="overview" element={<OverviewPage />} />
        <Route
          path="tracks"
          element={
            <ProtectedRoute requiredPermission="tracks.read">
              <TracksPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="sensors"
          element={
            <ProtectedRoute requiredPermission="sensors.read">
              <SensorsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="alerts"
          element={
            <ProtectedRoute requiredPermission="alerts.read">
              <AlertsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="threats"
          element={
            <ProtectedRoute requiredPermission="threats.read">
              <ThreatsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="history"
          element={
            <ProtectedRoute requiredAnyPermissions={['sensors.read', 'tracks.read', 'alerts.read', 'threats.read']}>
              <HistoryPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="scenarios"
          element={
            <ProtectedRoute requiredAnyPermissions={['scenarios.read', 'scenarios.run', 'scenarios.create']}>
              <ScenariosPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="replay"
          element={
            <ProtectedRoute requiredAnyPermissions={['scenarios.read', 'tracks.read', 'scenarios.run']}>
              <ReplayPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="analytics"
          element={
            <ProtectedRoute requiredAnyPermissions={['sensors.read', 'tracks.read', 'alerts.read', 'threats.read']}>
              <AnalyticsPage />
            </ProtectedRoute>
          }
        />
      </Route>

      {/* Default Catch-all */}
      <Route path="/" element={<Navigate to="/app/overview" replace />} />
      <Route path="*" element={<Navigate to="/app/overview" replace />} />
    </Routes>
  );
};
