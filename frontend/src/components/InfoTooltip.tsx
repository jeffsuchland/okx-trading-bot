import { useState } from 'react'

interface InfoTooltipProps {
  title: string
  children: React.ReactNode
}

export default function InfoTooltip({ title, children }: InfoTooltipProps) {
  const [open, setOpen] = useState(false)

  return (
    <span className="relative inline-flex items-center">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="ml-1.5 w-4 h-4 rounded-full bg-gray-700 hover:bg-gray-600 text-gray-400 hover:text-white text-[10px] font-bold inline-flex items-center justify-center transition-colors flex-shrink-0"
        aria-label={`Info about ${title}`}
      >
        i
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute left-6 top-0 z-50 w-72 bg-gray-800 border border-gray-700 rounded-lg shadow-xl p-4 text-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="font-semibold text-white text-xs uppercase tracking-wider">{title}</span>
              <button
                onClick={() => setOpen(false)}
                className="text-gray-400 hover:text-white text-xs"
              >
                ✕
              </button>
            </div>
            <div className="text-gray-300 text-xs leading-relaxed">{children}</div>
          </div>
        </>
      )}
    </span>
  )
}
