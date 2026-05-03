"use client"

import { useEffect } from "react"

/**
 * Listens for Cmd+B / Ctrl+B and toggles the `blur-sensitive` class on <body>.
 * Elements marked with the `sensitive` class will be blurred when active.
 */
export function PrivacyBlur() {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "b" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        document.body.classList.toggle("blur-sensitive")
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [])

  return null
}
