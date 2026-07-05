import type { Transaction } from "../types/api";

function formatCurrency(amount: string): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
  }).format(parseFloat(amount));
}

export function SettlementPlan({
  transactions,
  isAlreadySettled,
}: {
  transactions: Transaction[];
  isAlreadySettled: boolean;
}) {
  if (isAlreadySettled) {
    return (
      <div className="card p-8 text-center">
        <div className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-green-100 mb-3">
          <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
          </svg>
        </div>
        <p className="text-sm font-semibold text-gray-900 mb-1">Nothing to settle</p>
        <p className="text-sm text-gray-500">
          Everyone's balance is at zero. No payments needed.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="section-title">Suggested payments</h3>
          <p className="text-xs text-gray-500 mt-0.5">
            Minimum {transactions.length} payment{transactions.length !== 1 ? "s" : ""} to settle
            all balances — calculated to minimise the number of transactions.
          </p>
        </div>
      </div>

      {/* Transaction list */}
      <div className="card overflow-hidden">
        {/* Column headers */}
        <div className="grid grid-cols-[1fr_auto] px-5 py-2.5 border-b border-gray-100 bg-gray-50">
          <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Transfer</span>
          <span className="text-xs font-medium text-gray-500 uppercase tracking-wide text-right">Amount</span>
        </div>

        <ul className="divide-y divide-gray-100">
          {transactions.map((t, i) => (
            <li key={i} className="grid grid-cols-[1fr_auto] items-center px-5 py-4">
              {/* From → To */}
              <div className="flex items-center gap-2 min-w-0">
                {/* Step number */}
                <span className="flex-shrink-0 inline-flex items-center justify-center w-5 h-5 rounded-full bg-gray-100 text-[10px] font-semibold text-gray-500">
                  {i + 1}
                </span>

                <div className="flex items-center gap-1.5 min-w-0 flex-wrap">
                  <span className="text-sm font-medium text-gray-900 truncate">
                    {t.from_user_name}
                  </span>
                  <svg
                    className="w-3.5 h-3.5 text-gray-400 flex-shrink-0"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 8.25L21 12m0 0l-3.75 3.75M21 12H3" />
                  </svg>
                  <span className="text-sm font-medium text-gray-900 truncate">
                    {t.to_user_name}
                  </span>
                </div>
              </div>

              {/* Amount */}
              <span className="text-sm font-semibold text-gray-900 tabular-nums whitespace-nowrap">
                {formatCurrency(t.amount)}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <p className="text-xs text-gray-400 px-1">
        These are suggestions only. Mark payments as done by coordinating directly with your group.
      </p>
    </div>
  );
}
