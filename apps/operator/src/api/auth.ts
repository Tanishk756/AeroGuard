import { CurrentUserResponse, LoginRequest } from '../types';
import { request } from './client';

export async function login(credentials: LoginRequest): Promise<CurrentUserResponse> {
  return request<CurrentUserResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(credentials),
  });
}

export async function logout(): Promise<{ message: string }> {
  return request<{ message: string }>('/auth/logout', {
    method: 'POST',
  });
}

export async function getMe(): Promise<CurrentUserResponse> {
  return request<CurrentUserResponse>('/me');
}
