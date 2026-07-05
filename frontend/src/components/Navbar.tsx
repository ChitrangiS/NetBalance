import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function Navbar() {
  const { user, isAuthenticated, logout } = useAuth();

  return (
    <header className="bg-white border-b border-gray-200">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">

        {/* Brand */}
        <Link
          to="/"
          className="flex items-center gap-2.5 text-gray-900 hover:text-gray-700 transition-colors"
        >
          {/* Simple monogram mark — no SVG dependencies */}
          <span className="inline-flex items-center justify-center w-7 h-7 rounded-md bg-gray-900 text-white text-xs font-bold tracking-tight select-none">
            NB
          </span>
          <span className="text-sm font-semibold tracking-tight">NetBalance</span>
        </Link>

        {/* Right side */}
        {isAuthenticated && (
          <div className="flex items-center gap-3">
            {/* User identifier — subtle, not a CTA */}
            <span className="hidden sm:block text-sm text-gray-500">
              {user?.email}
            </span>

            <div className="h-4 w-px bg-gray-200" aria-hidden="true" />

            <button
              onClick={logout}
              className="btn-ghost text-gray-500 hover:text-gray-900"
            >
              Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
