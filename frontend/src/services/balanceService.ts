import apiClient from "./apiClient";
import type { GroupBalanceResponse, SettlementPlanResponse } from "../types/api";

export async function getGroupBalances(groupId: number): Promise<GroupBalanceResponse> {
  const response = await apiClient.get<GroupBalanceResponse>(`/groups/${groupId}/balances/`);
  return response.data;
}

export async function getSettlementPlan(groupId: number): Promise<SettlementPlanResponse> {
  const response = await apiClient.get<SettlementPlanResponse>(`/groups/${groupId}/settlements/`);
  return response.data;
}