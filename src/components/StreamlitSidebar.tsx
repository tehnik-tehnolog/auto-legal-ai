import React from 'react';
import { 
  ChevronLeft, 
  ChevronRight, 
  Layers, 
  CheckCircle2, 
  Terminal,
  FileCode2,
  Sparkles
} from 'lucide-react';
import { StreamlitTemplate, TemplateId } from '../types/streamlit';
import { TEMPLATES } from '../data/templates';

interface StreamlitSidebarProps {
  isExpanded: boolean;
  setIsExpanded: (expanded: boolean) => void;
  selectedTemplateId: TemplateId;
  onSelectTemplate: (template: StreamlitTemplate) => void;
  // Live widget state values
  userName: string;
  setUserName: (name: string) => void;
  appMode: string;
  setAppMode: (mode: string) => void;
  multiplier: number;
  setMultiplier: (val: number) => void;
  enableBalloons: boolean;
  setEnableBalloons: (enabled: boolean) => void;
  onOpenDeploy: () => void;
}

export const StreamlitSidebar: React.FC<StreamlitSidebarProps> = ({
  isExpanded,
  setIsExpanded,
  selectedTemplateId,
  onSelectTemplate,
  userName,
  setUserName,
  appMode,
  setAppMode,
  multiplier,
  setMultiplier,
  enableBalloons,
  setEnableBalloons,
  onOpenDeploy
}) => {
  return (
    <>
      {/* Floating expand button when collapsed */}
      {!isExpanded && (
        <button
          onClick={() => setIsExpanded(true)}
          title="Expand sidebar"
          className="fixed left-0 top-16 z-30 p-1.5 bg-white dark:bg-neutral-900 border-r border-y border-neutral-200 dark:border-neutral-800 rounded-r-md shadow-xs text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      )}

      {/* Sidebar container */}
      <aside
        className={`fixed inset-y-0 left-0 z-30 flex flex-col pt-14 border-r transition-all duration-200 bg-[#F8F9FA] dark:bg-[#1A1D24] border-neutral-200 dark:border-neutral-800 ${
          isExpanded ? 'w-72 sm:w-80 translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Sidebar Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-200/80 dark:border-neutral-800/80">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400">
              st.sidebar
            </span>
          </div>
          <button
            onClick={() => setIsExpanded(false)}
            title="Collapse sidebar"
            className="p-1 rounded text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 hover:bg-neutral-200/60 dark:hover:bg-neutral-800 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
        </div>

        {/* Scrollable Sidebar Body */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-6">
          {/* Template Switcher */}
          <div className="space-y-2">
            <label className="flex items-center gap-1.5 text-xs font-semibold text-neutral-800 dark:text-neutral-200">
              <Layers className="w-3.5 h-3.5 text-[#FF4B4B]" />
              <span>Empty Starter Template</span>
            </label>
            <div className="space-y-1.5">
              {TEMPLATES.map((tmpl) => {
                const isActive = tmpl.id === selectedTemplateId;
                return (
                  <button
                    key={tmpl.id}
                    onClick={() => onSelectTemplate(tmpl)}
                    className={`w-full text-left p-2.5 rounded-lg border transition-all text-xs ${
                      isActive
                        ? 'bg-white dark:bg-neutral-800/90 border-[#FF4B4B]/40 shadow-xs'
                        : 'bg-white/60 dark:bg-neutral-900/40 border-neutral-200/80 dark:border-neutral-800 hover:bg-white dark:hover:bg-neutral-800/60'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className={`font-medium ${isActive ? 'text-[#FF4B4B]' : 'text-neutral-800 dark:text-neutral-200'}`}>
                        {tmpl.name}
                      </span>
                      <span className="text-[10px] text-neutral-500 dark:text-neutral-400">
                        {tmpl.badge}
                      </span>
                    </div>
                    <p className="mt-1 text-[11px] text-neutral-500 dark:text-neutral-400 line-clamp-2">
                      {tmpl.summary}
                    </p>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="border-t border-neutral-200 dark:border-neutral-800" />

          {/* Interactive Streamlit Widgets Demo Controls */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400">
                Interactive Widgets
              </span>
              <span className="text-[10px] text-neutral-400">Live Sync</span>
            </div>

            {/* st.text_input */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-neutral-700 dark:text-neutral-300">
                st.text_input("User Name")
              </label>
              <input
                type="text"
                value={userName}
                onChange={(e) => setUserName(e.target.value)}
                className="w-full px-3 py-1.5 text-xs bg-white dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-700 rounded-md focus:outline-none focus:ring-1 focus:ring-[#FF4B4B] focus:border-[#FF4B4B] text-neutral-900 dark:text-neutral-100"
                placeholder="Enter your name"
              />
            </div>

            {/* st.selectbox */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-neutral-700 dark:text-neutral-300">
                st.selectbox("Choose view")
              </label>
              <select
                value={appMode}
                onChange={(e) => setAppMode(e.target.value)}
                className="w-full px-2.5 py-1.5 text-xs bg-white dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-700 rounded-md focus:outline-none focus:ring-1 focus:ring-[#FF4B4B] text-neutral-900 dark:text-neutral-100"
              >
                <option value="Overview">Overview</option>
                <option value="Data Preview">Data Preview</option>
                <option value="Cloud Deployment Guide">Cloud Deployment Guide</option>
              </select>
            </div>

            {/* st.slider */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <label className="font-medium text-neutral-700 dark:text-neutral-300">
                  st.slider("Multiplier")
                </label>
                <span className="font-mono text-neutral-600 dark:text-neutral-400 tabular-nums">
                  {multiplier}x
                </span>
              </div>
              <input
                type="range"
                min="1"
                max="10"
                value={multiplier}
                onChange={(e) => setMultiplier(Number(e.target.value))}
                className="w-full accent-[#FF4B4B] cursor-pointer"
              />
            </div>

            {/* st.checkbox */}
            <label className="flex items-center gap-2 cursor-pointer select-none text-xs text-neutral-700 dark:text-neutral-300">
              <input
                type="checkbox"
                checked={enableBalloons}
                onChange={(e) => setEnableBalloons(e.target.checked)}
                className="rounded accent-[#FF4B4B] cursor-pointer"
              />
              <span>Enable st.balloons() celebration</span>
            </label>
          </div>

          <div className="border-t border-neutral-200 dark:border-neutral-800" />

          {/* Cloud Readiness Checklist */}
          <div className="p-3 bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-lg space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-neutral-900 dark:text-neutral-100">
                Cloud Readiness
              </span>
              <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" />
                Valid
              </span>
            </div>
            <div className="space-y-1 text-[11px] text-neutral-500 dark:text-neutral-400">
              <div className="flex items-center gap-1.5">
                <span className="text-emerald-500 font-mono">✓</span>
                <span>streamlit_app.py entrypoint</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-emerald-500 font-mono">✓</span>
                <span>requirements.txt included</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-emerald-500 font-mono">✓</span>
                <span>.streamlit/config.toml ready</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-emerald-500 font-mono">✓</span>
                <span>.gitignore prevents key leaks</span>
              </div>
            </div>
            <button
              onClick={onOpenDeploy}
              className="w-full mt-2 py-1.5 text-center text-xs font-medium text-[#FF4B4B] hover:text-[#E03A3A] hover:bg-neutral-50 dark:hover:bg-neutral-800/80 rounded border border-[#FF4B4B]/30 transition-colors"
            >
              View Deploy Checklist
            </button>
          </div>
        </div>

        {/* Sidebar Footer info */}
        <div className="px-4 py-3 border-t border-neutral-200/80 dark:border-neutral-800 text-[11px] text-neutral-400 dark:text-neutral-500 flex items-center justify-between">
          <span>Streamlit Community Cloud</span>
          <span className="font-mono">Python 3.11</span>
        </div>
      </aside>
    </>
  );
};
