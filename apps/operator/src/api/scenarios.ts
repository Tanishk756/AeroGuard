import { Scenario, ScenarioExecutionStatus, ScenarioPage } from '../types';
import { request } from './client';

export interface GetScenariosParams {
  status?: string;
  cursor?: string;
  limit?: number;
}

export async function getScenarios(params?: GetScenariosParams): Promise<ScenarioPage> {
  return request<ScenarioPage>('/scenarios', {
    params: params as Record<string, string | number | boolean | undefined>,
  });
}

export async function getScenarioDetail(scenarioId: string): Promise<Scenario> {
  return request<Scenario>(`/scenarios/${encodeURIComponent(scenarioId)}`);
}

export async function getScenarioStatus(scenarioId: string): Promise<ScenarioExecutionStatus> {
  return request<ScenarioExecutionStatus>(`/scenarios/${encodeURIComponent(scenarioId)}/status`);
}

export async function prepareScenario(scenarioId: string): Promise<Scenario> {
  return request<Scenario>(`/scenarios/${encodeURIComponent(scenarioId)}/prepare`, {
    method: 'POST',
  });
}

export async function startScenario(scenarioId: string): Promise<ScenarioExecutionStatus> {
  return request<ScenarioExecutionStatus>(`/scenarios/${encodeURIComponent(scenarioId)}/start`, {
    method: 'POST',
  });
}

export async function pauseScenario(scenarioId: string): Promise<ScenarioExecutionStatus> {
  return request<ScenarioExecutionStatus>(`/scenarios/${encodeURIComponent(scenarioId)}/pause`, {
    method: 'POST',
  });
}

export async function resumeScenario(scenarioId: string): Promise<ScenarioExecutionStatus> {
  return request<ScenarioExecutionStatus>(`/scenarios/${encodeURIComponent(scenarioId)}/resume`, {
    method: 'POST',
  });
}

export async function stepScenario(scenarioId: string, ticks = 1): Promise<ScenarioExecutionStatus> {
  return request<ScenarioExecutionStatus>(`/scenarios/${encodeURIComponent(scenarioId)}/step`, {
    method: 'POST',
    body: JSON.stringify({ ticks }),
  });
}

export async function stopScenario(scenarioId: string): Promise<ScenarioExecutionStatus> {
  return request<ScenarioExecutionStatus>(`/scenarios/${encodeURIComponent(scenarioId)}/stop`, {
    method: 'POST',
  });
}

export async function resetScenario(scenarioId: string): Promise<ScenarioExecutionStatus> {
  return request<ScenarioExecutionStatus>(`/scenarios/${encodeURIComponent(scenarioId)}/reset`, {
    method: 'POST',
  });
}

export async function deleteScenario(scenarioId: string): Promise<void> {
  return request<void>(`/scenarios/${encodeURIComponent(scenarioId)}`, {
    method: 'DELETE',
  });
}
