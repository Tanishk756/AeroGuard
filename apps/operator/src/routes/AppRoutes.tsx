import React from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { AlertsPage } from '../pages/AlertsPage';
import { AnalyticsPage } from '../pages/AnalyticsPage';
import { ApiConsolePage } from '../pages/ApiConsolePage';
import { AuditLogPage } from '../pages/AuditLogPage';
import { DiagnosticsPage } from '../pages/DiagnosticsPage';
import { GeofencesPage } from '../pages/GeofencesPage';
import { HistoryPage } from '../pages/HistoryPage';
import { IntelligencePage } from '../pages/IntelligencePage';
import { LoginPage } from '../pages/LoginPage';
import { OverviewPage } from '../pages/OverviewPage';
import { RbacPage } from '../pages/RbacPage';
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
          path="intelligence"
          element={
            <ProtectedRoute requiredPermission="tracks.read">
              <IntelligencePage />
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
          path="geofences"
          element={
            <ProtectedRoute requiredAnyPermissions={['scenarios.read', 'scenarios.create', 'scenarios.update', 'scenarios.delete']}>
              <GeofencesPage />
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
        <Route
          path="audit"
          element={
            <ProtectedRoute requiredPermission="audit.read">
              <AuditLogPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="rbac"
          element={
            <ProtectedRoute requiredAnyPermissions={['roles.read', 'permissions.read', 'roles.create', 'roles.update', 'roles.delete', 'roles.assign']}>
              <RbacPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="diagnostics"
          element={
            <ProtectedRoute requiredPermission="system.read">
              <DiagnosticsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="developer"
          element={
            <ProtectedRoute requiredPermission="system.read">
              <ApiConsolePage />
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
