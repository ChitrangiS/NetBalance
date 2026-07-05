import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { GroupResponse } from "../types/api";
import * as groupService from "../services/groupService";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function DashboardPage() {
  const [groups, setGroups] = useState<GroupResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    async function fetchGroups() {
      try {
        const data = await groupService.listMyGroups();
        setGroups(data);
      } catch {
        setError("Failed to load your groups. Please refresh and try again.");
      } finally {
        setIsLoading(false);
      }
    }
    fetchGroups();
  }, []);

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">

      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Your Groups</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Manage shared expenses across all your groups.
          </p>
        </div>

        {/* Action buttons — both always visible */}
        <div className="flex items-center gap-2">
          <Link to="/groups/new?tab=join" className="btn-secondary">
            Join group
          </Link>
          <Link to="/groups/new" className="btn-primary">
            + New group
          </Link>
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="card p-5 animate-pulse"
            >
              <div className="h-4 bg-gray-100 rounded w-1/3 mb-2" />
              <div className="h-3 bg-gray-100 rounded w-1/5" />
            </div>
          ))}
        </div>
      )}

      {/* Error */}
      {!isLoading && error && (
        <div className="card p-5 border-red-200 bg-red-50">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !error && groups.length === 0 && (
        <div className="card p-12 text-center">
          {/* Simple icon — no external deps */}
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-gray-100 mb-4">
            <svg
              className="w-6 h-6 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z"
              />
            </svg>
          </div>
          <h2 className="text-base font-semibold text-gray-900 mb-1">
            No groups yet
          </h2>
          <p className="text-sm text-gray-500 mb-6 max-w-xs mx-auto">
            Create a group to start tracking shared expenses, or join one using an invite code.
          </p>
          <div className="flex items-center justify-center gap-2">
            <Link to="/groups/new?tab=join" className="btn-secondary">
              Join a group
            </Link>
            <Link to="/groups/new" className="btn-primary">
              Create a group
            </Link>
          </div>
        </div>
      )}

      {/* Group list */}
      {!isLoading && !error && groups.length > 0 && (
        <div className="space-y-2">
          {groups.map((group) => (
            <GroupCard key={group.id} group={group} />
          ))}
        </div>
      )}
    </div>
  );
}

function GroupCard({ group }: { group: GroupResponse }) {
  return (
    <Link
      to={`/groups/${group.id}`}
      className="card flex items-center justify-between p-5 hover:border-gray-300 hover:shadow-md transition-all duration-150 group"
    >
      {/* Left: name + meta */}
      <div className="min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <h2 className="text-sm font-semibold text-gray-900 truncate group-hover:text-gray-700">
            {group.name}
          </h2>
          {group.description && (
            <span className="hidden sm:block text-xs text-gray-400 truncate max-w-xs">
              — {group.description}
            </span>
          )}
        </div>

        {/* Meta row */}
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
            </svg>
            {group.member_count} {group.member_count === 1 ? "member" : "members"}
          </span>

          <span className="text-gray-300">·</span>

          <span>Created {formatDate(group.created_at)}</span>

          <span className="text-gray-300">·</span>

          {/* Invite code as a subtle badge */}
          <span className="font-mono bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded text-[10px] tracking-wide">
            {group.invite_code}
          </span>
        </div>
      </div>

      {/* Right: chevron */}
      <svg
        className="w-4 h-4 text-gray-400 flex-shrink-0 ml-4 group-hover:text-gray-600 transition-colors"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
      </svg>
    </Link>
  );
}
