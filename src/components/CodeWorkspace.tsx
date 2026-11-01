import React, { useState } from 'react';
import { 
  FileCode, 
  FileText, 
  Settings2, 
  KeyRound, 
  Eye, 
  Copy, 
  Check, 
  Download, 
  RotateCcw,
  Sparkles,
  Info
} from 'lucide-react';
import { StreamlitTemplate } from '../types/streamlit';

interface CodeWorkspaceProps {
  currentTemplate: StreamlitTemplate;
  isSidebarExpanded: boolean;
  pythonCode: string;
  setPythonCode: (code: string) => void;
  onDownloadZip: () => void;
  onSwitchToPreview: () => void;
}

type ActiveFileName = 'streamlit_app.py' | 'requirements.txt' | 'config.toml' | 'secrets.toml' | '.gitignore' | 'README.md';

export const CodeWorkspace: React.FC<CodeWorkspaceProps> = ({
  currentTemplate,
  isSidebarExpanded,
  pythonCode,
  setPythonCode,
  onDownloadZip,
  onSwitchToPreview
}) => {
  const [activeFile, setActiveFile] = useState<ActiveFileName>('streamlit_app.py');
  const [copied, setCopied] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  const getFileContent = (file: ActiveFileName): string => {
    switch (file) {
      case 'streamlit_app.py':
        return pythonCode;
      case 'requirements.txt':
        return currentTemplate.requirements;
      case 'config.toml':
        return currentTemplate.configToml;
      case 'secrets.toml':
        return currentTemplate.secretsToml;
      case '.gitignore':
        return currentTemplate.gitignore;
      case 'README.md':
        return currentTemplate.readme;
    }
  };

  const currentContent = getFileContent(activeFile);

  const handleCopy = () => {
    navigator.clipboard.writeText(currentContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleReset = () => {
    setPythonCode(currentTemplate.pythonCode);
  };

  const files = [
    { name: 'streamlit_app.py' as ActiveFileName, icon: FileCode, label: 'Main Entrypoint' },
    { name: 'requirements.txt' as ActiveFileName, icon: FileText, label: 'Dependencies' },
    { name: 'config.toml' as ActiveFileName, icon: Settings2, label: '.streamlit/config' },
    { name: 'secrets.toml' as ActiveFileName, icon: KeyRound, label: 'Secrets (Example)' },
    { name: '.gitignore' as ActiveFileName, icon: FileText, label: 'Git Rules' },
    { name: 'README.md' as ActiveFileName, icon: FileText, label: 'Documentation' },
  ];

  const lineCount = currentContent.split('\n').length;

  return (
    <main
      className={`min-h-[calc(100vh-56px)] transition-all duration-200 p-4 md:p-8 ${
        isSidebarExpanded ? 'lg:pl-88' : 'pl-4 md:pl-8'
      }`}
    >
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Top Info Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 bg-white dark:bg-[#151921] border border-neutral-200 dark:border-neutral-800 rounded-xl shadow-xs">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100 flex items-center gap-2">
              <FileCode className="w-5 h-5 text-[#FF4B4B]" />
              <span>Project Files for Streamlit Community Cloud</span>
            </h1>
            <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
              These files represent the exact GitHub repository files required to deploy your app on <code className="text-[#FF4B4B] font-mono">share.streamlit.io</code>.
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={onDownloadZip}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-[#FF4B4B] hover:bg-[#E03A3A] rounded-lg transition-colors shadow-xs"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download Project .zip</span>
            </button>

            <button
              onClick={onSwitchToPreview}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 border border-neutral-300 dark:border-neutral-700 rounded-lg transition-colors"
            >
              <Eye className="w-3.5 h-3.5" />
              <span>Test Live App</span>
            </button>
          </div>
        </div>

        {/* File Tabs & Editor Box */}
        <div className="bg-[#0E1117] border border-neutral-800 rounded-xl overflow-hidden shadow-md">
          {/* File Tabs Bar */}
          <div className="flex items-center justify-between px-3 py-2 bg-[#161B22] border-b border-neutral-800 overflow-x-auto gap-2">
            <div className="flex items-center gap-1">
              {files.map((file) => {
                const Icon = file.icon;
                const isActive = activeFile === file.name;
                return (
                  <button
                    key={file.name}
                    onClick={() => setActiveFile(file.name)}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-mono transition-colors whitespace-nowrap ${
                      isActive
                        ? 'bg-[#0E1117] text-white border border-neutral-700 font-semibold'
                        : 'text-neutral-400 hover:text-neutral-200 hover:bg-neutral-800/50'
                    }`}
                  >
                    <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-[#FF4B4B]' : 'text-neutral-500'}`} />
                    <span>{file.name}</span>
                  </button>
                );
              })}
            </div>

            {/* Actions for current file */}
            <div className="flex items-center gap-2 shrink-0">
              {activeFile === 'streamlit_app.py' && (
                <button
                  onClick={handleReset}
                  title="Reset python code to template initial code"
                  className="flex items-center gap-1 text-[11px] text-neutral-400 hover:text-neutral-200 px-2 py-1 rounded hover:bg-neutral-800 transition-colors"
                >
                  <RotateCcw className="w-3 h-3" />
                  <span>Reset</span>
                </button>
              )}

              <button
                onClick={handleCopy}
                className="flex items-center gap-1 text-xs text-neutral-300 hover:text-white px-2.5 py-1 bg-neutral-800 hover:bg-neutral-700 rounded transition-colors"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied!' : 'Copy File'}</span>
              </button>
            </div>
          </div>

          {/* Code Viewer / Editor Area with Line Numbers */}
          <div className="relative font-mono text-xs text-neutral-200 flex">
            {/* Line numbers gutter */}
            <div className="select-none py-4 px-3 text-right text-neutral-600 bg-[#0A0D12] border-r border-neutral-800/80 font-mono text-xs min-w-[44px]">
              {Array.from({ length: lineCount }).map((_, i) => (
                <div key={i} className="leading-6">
                  {i + 1}
                </div>
              ))}
            </div>

            {/* Code Content */}
            <div className="flex-1 overflow-x-auto p-4">
              {activeFile === 'streamlit_app.py' ? (
                <textarea
                  value={pythonCode}
                  onChange={(e) => setPythonCode(e.target.value)}
                  className="w-full h-[520px] bg-transparent text-neutral-100 font-mono text-xs leading-6 resize-none focus:outline-none border-0"
                  spellCheck={false}
                />
              ) : (
                <pre className="text-neutral-100 font-mono text-xs leading-6 min-h-[300px]">
                  {currentContent}
                </pre>
              )}
            </div>
          </div>

          {/* Bottom Bar Info */}
          <div className="flex items-center justify-between px-4 py-2 bg-[#161B22] border-t border-neutral-800 text-[11px] text-neutral-400 font-mono">
            <span>
              {activeFile === 'streamlit_app.py' ? 'Editing enabled · Changes reflect in zip download' : 'Read-only view'}
            </span>
            <span>UTF-8 · Python 3.11</span>
          </div>
        </div>

        {/* Tip Box */}
        <div className="p-4 bg-neutral-50 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-xl flex items-start gap-3 text-xs text-neutral-600 dark:text-neutral-400">
          <Info className="w-4 h-4 text-[#FF4B4B] shrink-0 mt-0.5" />
          <p className="leading-relaxed">
            <strong className="text-neutral-800 dark:text-neutral-200">Community Cloud Convention:</strong> Streamlit Community Cloud looks for either <code className="text-[#FF4B4B] font-mono">streamlit_app.py</code> or <code className="text-[#FF4B4B] font-mono">app.py</code> at the root of your GitHub repository. Having <code className="text-[#FF4B4B] font-mono">requirements.txt</code> in the root ensures all dependencies install automatically.
          </p>
        </div>
      </div>
    </main>
  );
};
