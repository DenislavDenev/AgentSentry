export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-4xl font-bold tracking-tight">AgentSentry</h1>
      <p className="text-gray-400 text-lg">
        Dashboard — arriving in Phase 5
      </p>
      <div className="mt-8 grid grid-cols-2 gap-4 text-sm text-gray-500 sm:grid-cols-4">
        {["AgentScout", "The Beacon", "Watchtower", "AgentSentry"].map(
          (module) => (
            <div
              key={module}
              className="rounded border border-gray-800 px-4 py-3 text-center"
            >
              {module}
            </div>
          )
        )}
      </div>
    </main>
  );
}
