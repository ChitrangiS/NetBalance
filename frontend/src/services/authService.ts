import apiClient from "./apiClient";
import type { RegisterRequest, LoginRequest, TokenResponse, UserResponse } from "../types/api";

export async function register(data: RegisterRequest): Promise<UserResponse> {
  const response = await apiClient.post<UserResponse>("/auth/register", data);
  return response.data;
}

export async function login(data: LoginRequest): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>("/auth/login", data);
  return response.data;
}

export async function getCurrentUser(): Promise<UserResponse> {
  const response = await apiClient.get<UserResponse>("/auth/me");
  return response.data;
}