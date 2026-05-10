import { Navigate, Route, Routes } from "react-router-dom"
import { Sidebar } from "@/components/nav/Sidebar"
import { PrivacyBlur } from "@/components/ui/PrivacyBlur"
import OverviewPage from "@/pages/OverviewPage"
import SessionsPage from "@/pages/SessionsPage"
import SessionDetailPage from "@/pages/SessionDetailPage"
import ProjectsPage from "@/pages/ProjectsPage"
import ProjectDetailPage from "@/pages/ProjectDetailPage"
import PromptsPage from "@/pages/PromptsPage"
import ToolsPage from "@/pages/ToolsPage"
import TipsPage from "@/pages/TipsPage"
import SettingsPage from "@/pages/SettingsPage"

export default function App() {
  return (
    <div className="flex h-screen overflow-hidden bg-gray-950 text-gray-100 antialiased">
      <PrivacyBlur />
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-6">
        <Routes>
          <Route path="/" element={<Navigate to="/overview" replace />} />
          <Route path="/overview" element={<OverviewPage />} />
          <Route path="/sessions" element={<SessionsPage />} />
          <Route path="/sessions/:id" element={<SessionDetailPage />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/:slug" element={<ProjectDetailPage />} />
          <Route path="/prompts" element={<PromptsPage />} />
          <Route path="/tools" element={<ToolsPage />} />
          <Route path="/tips" element={<TipsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  )
}
