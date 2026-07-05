import apiClient from "./apiClient";
import type { ExpenseResponse, ExpenseSummary, CreateExpenseRequest } from "../types/api";

export async function createExpense(
  groupId: number,
  data: CreateExpenseRequest
): Promise<ExpenseResponse> {
  const response = await apiClient.post<ExpenseResponse>(`/groups/${groupId}/expenses/`, data);
  return response.data;
}

export async function listExpenses(groupId: number): Promise<ExpenseSummary[]> {
  const response = await apiClient.get<ExpenseSummary[]>(`/groups/${groupId}/expenses/`);
  return response.data;
}

export async function deleteExpense(groupId: number, expenseId: number): Promise<void> {
  await apiClient.delete(`/groups/${groupId}/expenses/${expenseId}`);
}