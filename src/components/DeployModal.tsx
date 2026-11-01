import React, { useState } from 'react';
import { 
  Cloud, 
  Github, 
  Download, 
  Check, 
  Copy, 
  ExternalLink, 
  X, 
  CheckCircle2, 
  Terminal, 
  Key, 
  Sparkles,
  ArrowRight,
  ShieldCheck
} from 'lucide-react';
import { StreamlitTemplate } from '../types/streamlit';

interface DeployModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentTemplate: StreamlitTemplate;
  onDownloadZip: () => void;
  isFullPage?: boolean;
}

export const DeployModal: React.FC<DeployModalProps> = ({
  isOpen,
  onClose,
  currentTemplate,
  onDownloadZip,
  isFullPage = false
}) => {
  const [copiedStep, setCopiedStep] = useState<number | null>(null);

  if (!isOpen && !isFullPage) return null;

  const copyToClipboard = (text: string, stepId: number) => {
    navigator.clipboard.writeText(text);
    setCopiedStep(stepId);
    setTimeout(() => setCopiedStep(null), 2000);
  };

  const gitCommands = `# 1. Initialize git and commit your empty app files
git init
git add .
git commit -m "Initial commit for Streamlit Community Cloud"

# 2. Add your GitHub remote repository
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# 3. Push to GitHub
git push -u origin main`;

  const content = (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="p-6 bg-gradient-to-br from-[#FF4B4B]/10 via-[#FF4B4B]/5 to-transparent border border-[#FF4B4B]/20 rounded-xl space-y-2">
        <div className="flex items-center gap-2 text-[#FF4B4B]">
          <Cloud className="w-5 h-5" />
          <span className="text-xs font-semibold uppercase tracking-wider">
            Official Hosting Platform
          </span>
        </div>
        <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100">
          Deploy to Streamlit Community Cloud
        </h2>
        <p className="text-xs sm:text-sm text-neutral-600 dark:text-neutral-400 max-w-2xl leading-relaxed">
          Streamlit Community Cloud lets you share your Python apps with the world for free, directly from your GitHub repository. Follow this 4-step deployment checklist.
        </p>
      </div>

      {/* 4 Steps Checklist */}
      <div className="space-y-4">
        {/* Step 1: Download or Push Files */}
        <div className="p-5 bg-white dark:bg-[#151921] border border-neutral-200 dark:border-neutral-800 rounded-xl space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="w-6 h-6 rounded-full bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 font-bold text-xs flex items-center justify-center font-mono">
                1
              </span>
              <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                Get the App Files & Create GitHub Repository
              </h3>
            </div>
            <button
              onClick={onDownloadZip}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-[#FF4B4B] hover:bg-[#E03A3A] rounded-lg transition-colors shadow-xs"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download .zip</span>
            </button>
          </div>

          <p className="text-xs text-neutral-600 dark:text-neutral-400">
            Unzip the files into your project folder, create a new repository on <a href="https://github.com/new" target="_blank" rel="noreferrer" className="text-[#FF4B4B] hover:underline inline-flex items-center gap-0.5 font-medium">GitHub <ExternalLink className="w-2.5 h-2.5" /></a>, and push:
          </p>

          <div className="relative p-3 bg-[#0E1117] text-neutral-200 rounded-lg font-mono text-xs overflow-x-auto">
            <button
              onClick={() => copyToClipboard(gitCommands, 1)}
              className="absolute right-2 top-2 p-1.5 rounded bg-neutral-800 text-neutral-300 hover:text-white transition-colors"
              title="Copy git commands"
            >
              {copiedStep === 1 ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
            <pre className="text-[11px] leading-5">{gitCommands}</pre>
          </div>
        </div>

        {/* Step 2: Connect Streamlit Community Cloud */}
        <div className="p-5 bg-white dark:bg-[#151921] border border-neutral-200 dark:border-neutral-800 rounded-xl space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="w-6 h-6 rounded-full bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 font-bold text-xs flex items-center justify-center font-mono">
                2
              </span>
              <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                Open Streamlit Community Cloud
              </h3>
            </div>
            <a
              href="https://share.streamlit.io"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-neutral-900 dark:text-white bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 rounded-lg transition-colors border border-neutral-200 dark:border-neutral-700"
            >
              <span>share.streamlit.io</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>

          <p className="text-xs text-neutral-600 dark:text-neutral-400">
            Sign in with your GitHub account. Click the blue or red <strong className="text-neutral-900 dark:text-neutral-100">"New app"</strong> button in your dashboard.
          </p>
        </div>

        {/* Step 3: Configure Deployment Fields */}
        <div className="p-5 bg-white dark:bg-[#151921] border border-neutral-200 dark:border-neutral-800 rounded-xl space-y-3">
          <div className="flex items-center gap-3">
            <span className="w-6 h-6 rounded-full bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 font-bold text-xs flex items-center justify-center font-mono">
              3
            </span>
            <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
              Fill Deployment Settings
            </h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
            <div className="p-3 bg-neutral-50 dark:bg-neutral-900 rounded-lg border border-neutral-200 dark:border-neutral-800 text-xs">
              <span className="font-semibold text-neutral-700 dark:text-neutral-300">Repository</span>
              <div className="mt-1 font-mono text-[11px] text-[#FF4B4B] truncate">
                your-username/repo-name
              </div>
            </div>

            <div className="p-3 bg-neutral-50 dark:bg-neutral-900 rounded-lg border border-neutral-200 dark:border-neutral-800 text-xs">
              <span className="font-semibold text-neutral-700 dark:text-neutral-300">Branch</span>
              <div className="mt-1 font-mono text-[11px] text-neutral-800 dark:text-neutral-200">
                main
              </div>
            </div>

            <div className="p-3 bg-neutral-50 dark:bg-neutral-900 rounded-lg border border-neutral-200 dark:border-neutral-800 text-xs">
              <span className="font-semibold text-neutral-700 dark:text-neutral-300">Main file path</span>
              <div className="mt-1 font-mono text-[11px] text-emerald-600 dark:text-emerald-400 font-semibold">
                streamlit_app.py
              </div>
            </div>
          </div>
        </div>

        {/* Step 4: Secrets & Advanced Settings */}
        <div className="p-5 bg-white dark:bg-[#151921] border border-neutral-200 dark:border-neutral-800 rounded-xl space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="w-6 h-6 rounded-full bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 font-bold text-xs flex items-center justify-center font-mono">
                4
              </span>
              <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                Add Secrets (Optional) & Deploy!
              </h3>
            </div>
            <button
              onClick={() => copyToClipboard(currentTemplate.secretsToml, 4)}
              className="text-xs text-neutral-500 hover:text-neutral-900 dark:hover:text-neutral-200 flex items-center gap-1"
            >
              {copiedStep === 4 ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
              <span>Copy Secrets Example</span>
            </button>
          </div>

          <p className="text-xs text-neutral-600 dark:text-neutral-400">
            If your app requires API keys or database credentials, click <strong className="text-neutral-800 dark:text-neutral-200">"Advanced settings..."</strong> in the Streamlit Cloud modal and paste them into the <strong className="text-neutral-800 dark:text-neutral-200">Secrets</strong> box in TOML format. Then click <strong className="text-[#FF4B4B]">"Deploy!"</strong>.
          </p>

          <div className="p-3 bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800 rounded-lg flex items-center gap-2.5 text-xs text-emerald-800 dark:text-emerald-300">
            <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <span>Never commit secret keys directly to GitHub. Streamlit Community Cloud securely encrypts your secrets at runtime.</span>
          </div>
        </div>
      </div>

      {/* Pro Tips */}
      <div className="p-4 bg-neutral-50 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-xl space-y-2 text-xs">
        <h4 className="font-semibold text-neutral-800 dark:text-neutral-200 flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-amber-500" />
          <span>Streamlit Community Cloud Pro Tips:</span>
        </h4>
        <ul className="list-disc list-inside space-y-1 text-neutral-600 dark:text-neutral-400 pl-1">
          <li><strong>Custom Subdomain:</strong> After deploying, you can change your URL to something custom like <code className="font-mono text-[#FF4B4B]">https://my-empty-app.streamlit.app</code> in App settings.</li>
          <li><strong>Auto-Reboot:</strong> Every git push triggers a fast rebuild. If you ever get an error, you can reboot the app via the "Manage app" bottom-right toolbar.</li>
          <li><strong>Packages.txt:</strong> Need system libraries (e.g. OpenCV, ffmpeg, graphviz)? Just add a <code className="font-mono">packages.txt</code> file in your repo.</li>
        </ul>
      </div>
    </div>
  );

  if (isFullPage) {
    return (
      <main className="p-4 md:p-8 max-w-5xl mx-auto min-h-[calc(100vh-56px)]">
        {content}
      </main>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs overflow-y-auto">
      <div className="relative w-full max-w-3xl bg-white dark:bg-[#12161E] rounded-2xl border border-neutral-200 dark:border-neutral-800 shadow-2xl p-6 md:p-8 max-h-[90vh] overflow-y-auto">
        <button
          onClick={onClose}
          className="absolute right-5 top-5 p-1.5 text-neutral-400 hover:text-neutral-900 dark:hover:text-white rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
        {content}
      </div>
    </div>
  );
};
