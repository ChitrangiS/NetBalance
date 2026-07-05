import type { MemberBalance } from "../types/api";

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
  }).format(Math.abs(amount));
}

export function BalanceSummary({
  balances,
  isSettled,
  currentUserId,
}: {
  balances: MemberBalance[];
  isSettled: boolean;
  currentUserId: number;
}) {
  // Settled-up shortcut
  if (isSettled) {
    return (
      <div className="card p-8 text-center">
        <div className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-green-100 mb-3">
          <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
          </svg>
        </div>
        <p className="text-sm font-semibold text-gray-900 mb-1">All settled up</p>
        <p className="text-sm text-gray-500">Every member's balance is at zero.</p>
      </div>
    );
  }

  const owed = balances.filter((b) => parseFloat(b.net_balance) > 0.005);
  const owes = balances.filter((b) => parseFloat(b.net_balance) < -0.005);
  const settled = balances.filter((b) => Math.abs(parseFloat(b.net_balance)) <= 0.005);

  return (
    <div className="space-y-4">

      {/* People who are owed money */}
      {owed.length > 0 && (
        <div className="card overflow-hidden">
          <div className="px-5 py-2.5 border-b border-gray-100 bg-green-50 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-500 flex-shrink-0" />
            <span className="text-xs font-medium text-green-800 uppercase tracking-wide">
              Owed money
            </span>
          </div>
          <ul className="divide-y divide-gray-100">
            {owed.map((b) => (
              <BalanceRow key={b.user_id} balance={b} currentUserId={currentUserId} />
            ))}
          </ul>
        </div>
      )}

      {/* People who owe money */}
      {owes.length > 0 && (
        <div className="card overflow-hidden">
          <div className="px-5 py-2.5 border-b border-gray-100 bg-red-50 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-red-400 flex-shrink-0" />
            <span className="text-xs font-medium text-red-800 uppercase tracking-wide">
              Owes money
            </span>
          </div>
          <ul className="divide-y divide-gray-100">
            {owes.map((b) => (
              <BalanceRow key={b.user_id} balance={b} currentUserId={currentUserId} />
            ))}
          </ul>
        </div>
      )}

      {/* Settled members */}
      {settled.length > 0 && (
        <div className="card overflow-hidden">
          <div className="px-5 py-2.5 border-b border-gray-100 bg-gray-50 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-gray-300 flex-shrink-0" />
            <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
              Settled
            </span>
          </div>
          <ul className="divide-y divide-gray-100">
            {settled.map((b) => (
              <BalanceRow key={b.user_id} balance={b} currentUserId={currentUserId} />
            ))}
          </ul>
        </div>
      )}

      {/* Totals footnote */}
      <p className="text-xs text-gray-400 text-right px-1">
        Paid vs. owed across all expenses in this group.
      </p>
    </div>
  );
}

function BalanceRow({
  balance,
  currentUserId,
}: {
  balance: MemberBalance;
  currentUserId: number;
}) {
  const net = parseFloat(balance.net_balance);
  const paid = parseFloat(balance.total_paid);
  const owed = parseFloat(balance.total_owed);
  const isMe = balance.user_id === currentUserId;
  const isOwed = net > 0.005;
  const isOwing = net < -0.005;

  return (
    <li className="grid grid-cols-[1fr_auto] items-center px-5 py-3.5">
      {/* Left: name + paid/owed breakdown */}
      <div className="min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="text-sm font-medium text-gray-900">{balance.full_name}</span>
          {isMe && (
            <span className="text-[10px] font-medium text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded-full">
              you
            </span>
          )}
        </div>
        <p className="text-xs text-gray-500 mt-0.5 tabular-nums">
          Paid {new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", minimumFractionDigits: 2 }).format(paid)}
          {" · "}
          Share {new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", minimumFractionDigits: 2 }).format(owed)}
        </p>
      </div>

      {/* Right: net amount */}
      <div className="text-right">
        {Math.abs(net) <= 0.005 ? (
          <span className="text-xs font-medium text-gray-400">—</span>
        ) : (
          <>
            <span
              className={`text-sm font-semibold tabular-nums ${
                isOwed ? "text-green-700" : "text-red-600"
              }`}
            >
              {isOwed ? "+" : "−"}{formatCurrency(net)}
            </span>
            <p className={`text-[10px] font-medium mt-0.5 ${isOwed ? "text-green-600" : "text-red-500"}`}>
              {isOwed ? "is owed" : "owes"}
            </p>
          </>
        )}
      </div>
    </li>
  );
}
