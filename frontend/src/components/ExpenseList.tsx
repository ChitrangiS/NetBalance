import type { ExpenseSummary } from "../types/api";

function formatCurrency(amount: string): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
  }).format(parseFloat(amount));
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
  });
}

export function ExpenseList({ expenses }: { expenses: ExpenseSummary[] }) {
  if (expenses.length === 0) {
    return (
      <div className="card p-10 text-center">
        <p className="text-sm font-medium text-gray-700 mb-1">No expenses yet</p>
        <p className="text-sm text-gray-500">
          Add the first expense using the button above.
        </p>
      </div>
    );
  }

  return (
    <div className="card overflow-hidden">
      {/* Column header */}
      <div className="grid grid-cols-[1fr_auto] px-5 py-2.5 border-b border-gray-100 bg-gray-50">
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Expense</span>
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide text-right">Amount</span>
      </div>

      <ul className="divide-y divide-gray-100">
        {expenses.map((e) => (
          <li key={e.id} className="grid grid-cols-[1fr_auto] items-center px-5 py-3.5 hover:bg-gray-50 transition-colors">
            {/* Left: description + meta */}
            <div className="min-w-0 pr-4">
              <p className="text-sm font-medium text-gray-900 truncate">{e.description}</p>
              <p className="text-xs text-gray-500 mt-0.5">
                Paid by <span className="text-gray-700">{e.paid_by_name}</span>
                <span className="mx-1.5 text-gray-300">·</span>
                {formatDate(e.created_at)}
                <span className="mx-1.5 text-gray-300">·</span>
                <span className="capitalize">{e.split_type} split</span>
              </p>
            </div>

            {/* Right: amount */}
            <span className="text-sm font-semibold text-gray-900 tabular-nums whitespace-nowrap">
              {formatCurrency(e.amount)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
