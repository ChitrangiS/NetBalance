import { useState, type FormEvent, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import * as groupService from "../services/groupService";

type Tab = "create" | "join";

export function CreateGroupPage() {
  const [searchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState<Tab>(
    searchParams.get("tab") === "join" ? "join" : "create"
  );

  // Create form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  // Join form state
  const [inviteCode, setInviteCode] = useState("");

  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const navigate = useNavigate();

  // Sync tab from URL param (used by the dashboard "Join group" button)
  useEffect(() => {
    if (searchParams.get("tab") === "join") setActiveTab("join");
  }, [searchParams]);

  function handleTabChange(tab: Tab) {
    setActiveTab(tab);
    setError(null);
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const group = await groupService.createGroup({
        name,
        description: description.trim() || undefined,
      });
      navigate(`/groups/${group.id}`);
    } catch {
      setError("Failed to create group. Check your input and try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleJoin(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const group = await groupService.joinGroup({ invite_code: inviteCode.trim() });
      navigate(`/groups/${group.id}`);
    } catch {
      setError("Invalid invite code, or you are already a member of this group.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">

      {/* Back link */}
      <button
        onClick={() => navigate("/dashboard")}
        className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 mb-6 transition-colors"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
        </svg>
        Back to dashboard
      </button>

      <div className="max-w-md">
        <h1 className="text-xl font-semibold text-gray-900 mb-6">
          {activeTab === "create" ? "Create a group" : "Join a group"}
        </h1>

        {/* Tab switcher — underline style */}
        <div className="flex border-b border-gray-200 mb-6">
          {(["create", "join"] as Tab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => handleTabChange(tab)}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                activeTab === tab
                  ? "border-gray-900 text-gray-900"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              {tab === "create" ? "Create new" : "Join existing"}
            </button>
          ))}
        </div>

        {/* Create form */}
        {activeTab === "create" && (
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="field-label" htmlFor="group-name">
                Group name <span className="text-red-500">*</span>
              </label>
              <input
                id="group-name"
                type="text"
                required
                minLength={2}
                maxLength={100}
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Trip to Goa, Flat expenses"
                className="field-input"
              />
            </div>

            <div>
              <label className="field-label" htmlFor="group-description">
                Description
                <span className="ml-1 font-normal text-gray-400">(optional)</span>
              </label>
              <input
                id="group-description"
                type="text"
                maxLength={500}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What is this group for?"
                className="field-input"
              />
            </div>

            {error && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md px-3 py-2">
                {error}
              </p>
            )}

            <div className="flex items-center gap-2 pt-1">
              <button type="submit" disabled={isSubmitting} className="btn-primary">
                {isSubmitting ? "Creating…" : "Create group"}
              </button>
              <button
                type="button"
                onClick={() => navigate("/dashboard")}
                className="btn-secondary"
              >
                Cancel
              </button>
            </div>
          </form>
        )}

        {/* Join form */}
        {activeTab === "join" && (
          <form onSubmit={handleJoin} className="space-y-4">
            <div>
              <label className="field-label" htmlFor="invite-code">
                Invite code <span className="text-red-500">*</span>
              </label>
              <input
                id="invite-code"
                type="text"
                required
                value={inviteCode}
                onChange={(e) => setInviteCode(e.target.value)}
                placeholder="Paste the invite code here"
                className="field-input font-mono tracking-wide"
                autoComplete="off"
                spellCheck={false}
              />
              <p className="mt-1.5 text-xs text-gray-500">
                Ask a group admin to share their invite code with you.
              </p>
            </div>

            {error && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md px-3 py-2">
                {error}
              </p>
            )}

            <div className="flex items-center gap-2 pt-1">
              <button type="submit" disabled={isSubmitting} className="btn-primary">
                {isSubmitting ? "Joining…" : "Join group"}
              </button>
              <button
                type="button"
                onClick={() => navigate("/dashboard")}
                className="btn-secondary"
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
