import React, { useState } from 'react';
import { 
  RotateCw, 
  Cloud, 
  Moon, 
  Sun, 
  Menu, 
  Code2, 
  Play, 
  BookOpen, 
  Download,
  Settings,
  HelpCircle,
  ExternalLink,
  Check
} from 'lucide-react';
import { StreamlitTemplate } from '../types/streamlit';

interface StreamlitHeaderProps {
  currentTemplate: StreamlitTemplate;
  activeTab: 'preview' | 'code' | 'deploy';
  setActiveTab: (tab: 'preview' | 'code' | 'deploy') => void;
  isDark: boolean;
  toggleTheme: () => void;
  isRunning: boolean;
  triggerRerun: () => void;
  onOpenDeploy: () => void;
  onDownloadZip: () => void;
}

export const StreamlitHeader: React.FC<StreamlitHeaderProps> = ({
  currentTemplate,
  activeTab,
  setActiveTab,
  isDark,
  toggleTheme,
  isRunning,
  triggerRerun,
  onOpenDeploy,
  onDownloadZip
}) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2000);
  };

  return (
    <header className="sticky top-0 z-40 border-b transition-colors bg-white/95 dark:bg-[#0E1117]/95 backdrop-blur-md border-neutral-200 dark:border-neutral-800">
      <div className="flex items-center justify-between px-4 py-2.5 max-w-[1700px] mx-auto gap-4">
        {/* Left: Streamlit Brand Icon & App Title */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="flex items-center gap-2">
            {/* Authentic Streamlit Red Crown Logo SVG */}
            <svg 
              className="w-6 h-6 shrink-0 transition-transform hover:scale-105" 
              viewBox="0 0 24 24" 
              fill="none" 
              xmlns="http://www.w3.org/2000/svg"
            >
              <path 
                d="M12 2L15.5 9.5L23 10.5L17.5 15.5L19 23L12 19L5 23L6.5 15.5L1 10.5L8.5 9.5L12 2Z" 
                fill="#FF4B4B"
              />
            </svg>
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-sm tracking-tight text-neutral-900 dark:text-neutral-100">
                  streamlit
                </span>
                <span className="text-neutral-400 dark:text-neutral-600 text-xs">/</span>
                <span className="text-xs font-medium text-neutral-600 dark:text-neutral-400 truncate max-w-[180px] sm:max-w-[260px]">
                  {currentTemplate.name}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Center: Mode Switcher (Clean Segmented Tabs) */}
        <div className="flex items-center p-1 bg-neutral-100 dark:bg-neutral-900 rounded-lg border border-neutral-200/80 dark:border-neutral-800 shrink-0">
          <button
            onClick={() => setActiveTab('preview')}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all whitespace-nowrap ${
              activeTab === 'preview'
                ? 'bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 shadow-xs'
                : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-200'
            }`}
          >
            <Play className="w-3.5 h-3.5 text-[#FF4B4B]" />
            <span>Live App</span>
          </button>

          <button
            onClick={() => setActiveTab('code')}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all whitespace-nowrap ${
              activeTab === 'code'
                ? 'bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 shadow-xs'
                : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-200'
            }`}
          >
            <Code2 className="w-3.5 h-3.5 text-blue-500" />
            <span>Files & Code</span>
          </button>

          <button
            onClick={() => setActiveTab('deploy')}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all whitespace-nowrap ${
              activeTab === 'deploy'
                ? 'bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 shadow-xs'
                : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-200'
            }`}
          >
            <BookOpen className="w-3.5 h-3.5 text-emerald-500" />
            <span>Cloud Guide</span>
          </button>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2 shrink-0">
          {/* Rerun Button with spinning animation */}
          <button
            onClick={triggerRerun}
            disabled={isRunning}
            title="Rerun Streamlit App (R)"
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-md border border-neutral-200 dark:border-neutral-700 transition-colors"
          >
            <RotateCw className={`w-3.5 h-3.5 text-neutral-500 ${isRunning ? 'animate-spin text-[#FF4B4B]' : ''}`} />
            <span className="hidden md:inline">{isRunning ? 'Running...' : 'Rerun'}</span>
          </button>

          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            title={isDark ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
            className="p-1.5 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-md transition-colors"
          >
            {isDark ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4" />}
          </button>

          {/* Download Zip */}
          <button
            onClick={onDownloadZip}
            title="Download project files (.zip) for GitHub"
            className="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-md border border-neutral-200 dark:border-neutral-700 transition-colors"
          >
            <Download className="w-3.5 h-3.5 text-neutral-500" />
            <span>Download .zip</span>
          </button>

          {/* Primary Action: Deploy to Streamlit Community Cloud */}
          <button
            onClick={onOpenDeploy}
            className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-[#FF4B4B] hover:bg-[#E03A3A] active:scale-[0.98] rounded-md shadow-xs transition-all whitespace-nowrap"
          >
            <Cloud className="w-3.5 h-3.5" />
            <span>Deploy</span>
          </button>

          {/* Hamburger Menu */}
          <div className="relative">
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className="p-1.5 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-md transition-colors"
              aria-label="Settings and options"
            >
              <Menu className="w-4 h-4" />
            </button>

            {menuOpen && (
              <div 
                className="absolute right-0 mt-2 w-56 bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-lg shadow-lg py-1.5 z-50 text-xs"
                onMouseLeave={() => setMenuOpen(false)}
              >
                <div className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500">
                  Streamlit Environment
                </div>
                <button
                  onClick={() => {
                    triggerRerun();
                    setMenuOpen(false);
                  }}
                  className="w-full text-left px-3 py-2 flex items-center justify-between text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800"
                >
                  <span className="flex items-center gap-2">
                    <RotateCw className="w-3.5 h-3.5" />
                    <span>Clear cache & rerun</span>
                  </span>
                  <span className="text-[10px] text-neutral-400 font-mono">Ctrl+C</span>
                </button>
                <button
                  onClick={() => {
                    onOpenDeploy();
                    setMenuOpen(false);
                  }}
                  className="w-full text-left px-3 py-2 flex items-center gap-2 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800"
                >
                  <Settings className="w-3.5 h-3.5" />
                  <span>Deployment Settings</span>
                </button>
                <button
                  onClick={handleShare}
                  className="w-full text-left px-3 py-2 flex items-center gap-2 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800"
                >
                  {copiedLink ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <HelpCircle className="w-3.5 h-3.5" />}
                  <span>{copiedLink ? 'Link copied!' : 'Copy Applet URL'}</span>
                </button>
                <div className="my-1 border-t border-neutral-100 dark:border-neutral-800" />
                <a
                  href="https://share.streamlit.io"
                  target="_blank"
                  rel="noreferrer"
                  className="w-full text-left px-3 py-2 flex items-center justify-between text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800"
                >
                  <span className="flex items-center gap-2">
                    <Cloud className="w-3.5 h-3.5 text-[#FF4B4B]" />
                    <span>Streamlit Community Cloud</span>
                  </span>
                  <ExternalLink className="w-3 h-3 text-neutral-400" />
                </a>
                <a
                  href="https://docs.streamlit.io/deploy/streamlit-community-cloud"
                  target="_blank"
                  rel="noreferrer"
                  className="w-full text-left px-3 py-2 flex items-center justify-between text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800"
                >
                  <span className="flex items-center gap-2">
                    <BookOpen className="w-3.5 h-3.5 text-neutral-500" />
                    <span>Streamlit Cloud Docs</span>
                  </span>
                  <ExternalLink className="w-3 h-3 text-neutral-400" />
                </a>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
