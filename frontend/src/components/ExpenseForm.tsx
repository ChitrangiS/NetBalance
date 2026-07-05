import { useState, type FormEvent } from "react";
import type { GroupDetailResponse, SplitType } from "../types/api";
import * as expenseService from "../services/expenseService";

export function ExpenseForm({
  group,
  onCreated,
  onCancel,
}: {
  group: GroupDetailResponse;
  onCreated: () => void;
  onCancel: () => void;
}) {
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [selectedMembers, setSelectedMembers] = useState<Set<number>>(
    new Set(group.members.map((m) => m.user_id))
  );
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function toggleMember(userId: number) {
    setSelectedMembers((prev) => {
      const next = new Set(prev);
      next.has(userId) ? next.delete(userId) : next.add(userId);
      return next;
    });
  }

  function toggleAll() {
    if (selectedMembers.size === group.members.length) {
      setSelectedMembers(new Set());
    } else {
      setSelectedMembers(new Set(group.members.map((m) => m.user_id)));
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (selectedMembers.size === 0) {
      setError("Select at least one person to split with.");
      return;
    }

    setIsSubmitting(true);
    try {
      await expenseService.createExpense(group.id, {
        description,
        amount,
        split_type: "equal" as SplitType,
        split_with: Array.from(selectedMembers),
      });
      onCreated();
    } catch {
      setError("Failed to add expense. Check the amount and try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  const allSelected = selectedMembers.size === group.members.length;

  return (
    <div className="card p-5">
      <h3 className="section-title mb-4">Add an expense</h3>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Description */}
        <div>
          <label className="field-label" htmlFor="exp-description">
            Description <span className="text-red-500">*</span>
          </label>
          <input
            id="exp-description"
            type="text"
            required
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What was this for?"
            className="field-input"
          />
        </div>

        {/* Amount */}
        <div>
          <label className="field-label" htmlFor="exp-amount">
            Amount (₹) <span className="text-red-500">*</span>
          </label>
          <input
            id="exp-amount"
            type="number"
            required
            step="0.01"
            min="0.01"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0.00"
            className="field-input font-mono"
          />
        </div>

        {/* Split with */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="field-label mb-0">
              Split equally among
            </label>
            <button
              type="button"
              onClick={toggleAll}
              className="text-xs text-blue-600 hover:text-blue-800 font-medium"
            >
              {allSelected ? "Deselect all" : "Select all"}
            </button>
          </div>

          {/* Member list in a contained inset box */}
          <div className="border border-gray-200 rounded-md divide-y divide-gray-100 overflow-hidden">
            {group.members.map((m) => (
              <label
                key={m.user_id}
                className={`flex items-center gap-3 px-3 py-2.5 cursor-pointer transition-colors ${
                  selectedMembers.has(m.user_id) ? "bg-blue-50" : "bg-white hover:bg-gray-50"
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedMembers.has(m.user_id)}
                  onChange={() => toggleMember(m.user_id)}
                  className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                />
                <div className="min-w-0 flex-1">
                  <span className="text-sm font-medium text-gray-900">{m.full_name}</span>
                  <span className="ml-1.5 text-xs text-gray-400">{m.email}</span>
                </div>
                {m.role === "admin" && (
                  <span className="text-[10px] text-gray-400 font-medium">admin</span>
                )}
              </label>
            ))}
          </div>

          {selectedMembers.size > 0 && (
            <p className="text-xs text-gray-500 mt-1.5">
              {selectedMembers.size} of {group.members.length} selected
            </p>
          )}
        </div>

        {error && (
          <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md px-3 py-2">
            {error}
          </p>
        )}

        <div className="flex items-center gap-2 pt-1">
          <button type="submit" disabled={isSubmitting} className="btn-primary">
            {isSubmitting ? "Adding…" : "Add expense"}
          </button>
          <button type="button" onClick={onCancel} className="btn-secondary">
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
