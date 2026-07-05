// ── Auth ──────────────────────────────────────────────────────────────────────

export interface UserResponse {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface RegisterRequest {
  email: string;
  full_name: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

// ── Groups ────────────────────────────────────────────────────────────────────

export type MemberRole = "admin" | "member";

export interface MemberResponse {
  user_id: number;
  full_name: string;
  email: string;
  role: MemberRole;
  joined_at: string;
}

export interface GroupResponse {
  id: number;
  name: string;
  description: string | null;
  invite_code: string;
  created_by: number;
  member_count: number;
  created_at: string;
}

export interface GroupDetailResponse extends GroupResponse {
  members: MemberResponse[];
}

export interface CreateGroupRequest {
  name: string;
  description?: string;
}

export interface JoinGroupRequest {
  invite_code: string;
}

// ── Expenses ──────────────────────────────────────────────────────────────────

export type SplitType = "equal" | "exact" | "percentage";

export interface SplitInput {
  user_id: number;
  amount?: string;
  percentage?: string;
}

export interface SplitResponse {
  id: number;
  user_id: number;
  amount: string;
  percentage: string | null;
}

export interface ExpenseResponse {
  id: number;
  group_id: number;
  paid_by: number;
  paid_by_name: string;
  amount: string;
  description: string;
  notes: string | null;
  split_type: SplitType;
  splits: SplitResponse[];
  created_at: string;
}

export interface ExpenseSummary {
  id: number;
  group_id: number;
  paid_by: number;
  paid_by_name: string;
  amount: string;
  description: string;
  split_type: SplitType;
  created_at: string;
}

export interface CreateExpenseRequest {
  description: string;
  amount: string;
  split_type: SplitType;
  split_with: number[];
  notes?: string;
  splits?: SplitInput[];
}

// ── Balances ──────────────────────────────────────────────────────────────────

export interface MemberBalance {
  user_id: number;
  full_name: string;
  email: string;
  total_paid: string;
  total_owed: string;
  net_balance: string;
}

export interface GroupBalanceResponse {
  group_id: number;
  balances: MemberBalance[];
  is_settled: boolean;
}

// ── Settlements ───────────────────────────────────────────────────────────────

export interface Transaction {
  from_user_id: number;
  from_user_name: string;
  to_user_id: number;
  to_user_name: string;
  amount: string;
}

export interface SettlementPlanResponse {
  group_id: number;
  transactions: Transaction[];
  transaction_count: number;
  is_already_settled: boolean;
}

// ── Generic API error shape (FastAPI's default error format) ───────────────────

export interface ApiErrorDetail {
  detail: string;
}