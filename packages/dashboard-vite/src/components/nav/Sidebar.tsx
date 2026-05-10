import { Link, useLocation } from "react-router-dom"

const NAV = [
  { href: "/overview", label: "Overview" },
  { href: "/sessions", label: "Sessions" },
  { href: "/projects", label: "Projects" },
  { href: "/tools", label: "Tools" },
  { href: "/prompts", label: "Prompts" },
  { href: "/tips", label: "Tips" },
  { href: "/settings", label: "Settings" },
]

export function Sidebar() {
  const { pathname } = useLocation()

  return (
    <aside className="flex h-screen w-48 flex-shrink-0 flex-col border-r border-gray-800 bg-gray-950">
      <div className="px-4 py-5">
        <span className="text-sm font-bold tracking-widest text-indigo-400 uppercase">
          AgentSentry
        </span>
      </div>

      <nav className="flex flex-col gap-0.5 px-2">
        {NAV.map(({ href, label }) => {
          const active = pathname === href || pathname.startsWith(href + "/")
          return (
            <Link
              key={href}
              to={href}
              className={[
                "rounded px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-indigo-900/60 text-indigo-300 font-medium"
                  : "text-gray-400 hover:bg-gray-800 hover:text-gray-100",
              ].join(" ")}
            >
              {label}
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}
