import apiClient from "./apiClient";
import type {
  GroupResponse,
  GroupDetailResponse,
  CreateGroupRequest,
  JoinGroupRequest,
} from "../types/api";

export async function createGroup(data: CreateGroupRequest): Promise<GroupDetailResponse> {
  const response = await apiClient.post<GroupDetailResponse>("/groups/", data);
  return response.data;
}

export async function joinGroup(data: JoinGroupRequest): Promise<GroupDetailResponse> {
  const response = await apiClient.post<GroupDetailResponse>("/groups/join", data);
  return response.data;
}

export async function listMyGroups(): Promise<GroupResponse[]> {
  const response = await apiClient.get<GroupResponse[]>("/groups/");
  return response.data;
}

export async function getGroup(groupId: number): Promise<GroupDetailResponse> {
  const response = await apiClient.get<GroupDetailResponse>(`/groups/${groupId}`);
  return response.data;
}