import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import type {
  GroupDetailResponse,
  ExpenseSummary,
  GroupBalanceResponse,
  SettlementPlanResponse,
} from "../types/api";
import * as groupService from "../services/groupService";
import * as expenseService from "../services/expenseService";
import * as balanceService from "../services/balanceService";
import { useAuth } from "../context/AuthContext";
import { ExpenseList } from "../components/ExpenseList";
import { ExpenseForm } from "../components/ExpenseForm";
import { BalanceSummary } from "../components/BalanceSummary";
import { SettlementPlan } from "../components/SettlementPlan";

type Tab = "expenses" | "balances" | "settle";

const TAB_LABELS: Record<Tab, string> = {
  expenses: "Expenses",
  balances: "Balances",
  settle: "Settle up",
};

export function GroupDetailPage() {
  const { groupId } = useParams<{ groupId: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [group, setGroup] = useState<GroupDetailResponse | null>(null);
  const [expenses, setExpenses] = useState<ExpenseSummary[]>([]);
  const [balances, setBalances] = useState<GroupBalanceResponse | null>(null);
  const [settlement, setSettlement] = useState<SettlementPlanResponse | null>(null);

  const [activeTab, setActiveTab] = useState<Tab>("expenses");
  const [showExpenseForm, setShowExpenseForm] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [codeCopied, setCodeCopied] = useState(false);

  const id = Number(groupId);

  const fetchAll = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [groupData, expensesData, balancesData, settlementData] = await Promise.all([
        groupService.getGroup(id),
        expenseService.listExpenses(id),
        balanceService.getGroupBalances(id),
        balanceService.getSettlementPlan(id),
      ]);
      setGroup(groupData);
      setExpenses(expensesData);
      setBalances(balancesData);
      setSettlement(settlementData);
    } catch {
      setError("Failed to load group data.");
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  function handleExpenseCreated() {
    setShowExpenseForm(false);
    fetchAll();
  }

  function copyInviteCode() {
    if (!group) return;
    navigator.clipboard.writeText(group.invite_code).then(() => {
      setCodeCopied(true);
      setTimeout(() => setCodeCopied(false), 2000);
    });
  }

  // ── Loading skeleton ────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-100 rounded w-1/4" />
          <div className="h-4 bg-gray-100 rounded w-1/6" />
          <div className="h-px bg-gray-200 mt-6" />
          <div className="space-y-3 mt-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="card p-4 h-14" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error || !group || !balances || !settlement || !user) {
    return (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        <div className="card p-5 border-red-200 bg-red-50">
          <p className="text-sm text-red-700">{error ?? "Something went wrong."}</p>
          <button onClick={() => navigate("/dashboard")} className="btn-secondary mt-3 text-xs">
            Back to dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">

      {/* Back link */}
      <button
        onClick={() => navigate("/dashboard")}
        className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 mb-5 transition-colors"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
        </svg>
        Dashboard
      </button>

      {/* Group header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-6">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">{group.name}</h1>
          {group.description && (
            <p className="text-sm text-gray-500 mt-0.5">{group.description}</p>
          )}

          {/* Meta row */}
          <div className="flex flex-wrap items-center gap-2 mt-2 text-xs text-gray-500">
            <span>
              {group.member_count} {group.member_count === 1 ? "member" : "members"}
            </span>
            <span className="text-gray-300">·</span>
            {/* Invite code — copyable */}
            <button
              onClick={copyInviteCode}
              title="Click to copy invite code"
              className="inline-flex items-center gap-1 font-mono bg-gray-100 hover:bg-gray-200 text-gray-600 px-2 py-0.5 rounded transition-colors text-[11px] tracking-wide"
            >
              {group.invite_code}
              {codeCopied ? (
                <svg className="w-3 h-3 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
              ) : (
                <svg className="w-3 h-3 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 011.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 00-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 01-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 00-3.375-3.375h-1.5a1.125 1.125 0 01-1.125-1.125v-1.5a3.375 3.375 0 00-3.375-3.375H9.75" />
                </svg>
              )}
            </button>
            {codeCopied && <span className="text-green-600 font-medium">Copied!</span>}
          </div>
        </div>
      </div>

      {/* Tab bar — underline style */}
      <div className="flex border-b border-gray-200 mb-6">
        {(Object.keys(TAB_LABELS) as Tab[]).map((tab) => (
          <button
            key={tab}
            onClick={() => { setActiveTab(tab); setShowExpenseForm(false); }}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
              activeTab === tab
                ? "border-gray-900 text-gray-900"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            {TAB_LABELS[tab]}
            {/* Badge for balances tab when unsettled */}
            {tab === "balances" && balances && !balances.is_settled && (
              <span className="ml-1.5 inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-amber-100 text-amber-700">
                open
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "expenses" && (
        <div className="space-y-4">
          {!showExpenseForm && (
            <div className="flex justify-end">
              <button
                onClick={() => setShowExpenseForm(true)}
                className="btn-primary"
              >
                + Add expense
              </button>
            </div>
          )}

          {showExpenseForm && (
            <ExpenseForm
              group={group}
              onCreated={handleExpenseCreated}
              onCancel={() => setShowExpenseForm(false)}
            />
          )}

          <ExpenseList expenses={expenses} />
        </div>
      )}

      {activeTab === "balances" && (
        <BalanceSummary
          balances={balances.balances}
          isSettled={balances.is_settled}
          currentUserId={user.id}
        />
      )}

      {activeTab === "settle" && (
        <SettlementPlan
          transactions={settlement.transactions}
          isAlreadySettled={settlement.is_already_settled}
        />
      )}
    </div>
  );
}
