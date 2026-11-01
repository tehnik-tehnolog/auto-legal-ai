import React, { useState, useMemo } from 'react';
import confetti from 'canvas-confetti';
import { 
  Copy, 
  Check, 
  ExternalLink, 
  Search, 
  Download, 
  ChevronDown, 
  ChevronUp, 
  Sparkles,
  ArrowUpRight,
  TrendingUp,
  Server,
  Cpu,
  Info,
  CheckCircle2,
  AlertTriangle,
  Send,
  User,
  Bot
} from 'lucide-react';
import { StreamlitTemplate } from '../types/streamlit';

interface StreamlitMainViewProps {
  currentTemplate: StreamlitTemplate;
  isSidebarExpanded: boolean;
  userName: string;
  appMode: string;
  multiplier: number;
  enableBalloons: boolean;
  onOpenDeploy: () => void;
  onSwitchTab: (tab: 'code' | 'deploy') => void;
}

export const StreamlitMainView: React.FC<StreamlitMainViewProps> = ({
  currentTemplate,
  isSidebarExpanded,
  userName,
  appMode,
  multiplier,
  enableBalloons,
  onOpenDeploy,
  onSwitchTab
}) => {
  const [buttonClicked, setButtonClicked] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [copiedCode, setCopiedCode] = useState(false);
  const [expanderOpen, setExpanderOpen] = useState(false);
  const [tableSearch, setTableSearch] = useState('');
  const [chatMessages, setChatMessages] = useState([
    { role: 'assistant', text: 'Hello! I am your Streamlit assistant running inside this empty app starter.' }
  ]);
  const [chatInput, setChatInput] = useState('');

  // Sample data points calculated dynamically from multiplier
  const chartData = useMemo(() => {
    const quarters = ['Q1', 'Q2', 'Q3', 'Q4'];
    return quarters.map((q, idx) => ({
      quarter: q,
      value: Math.round((28 + idx * 14 + Math.sin(idx + 1) * 10) * multiplier),
      growth: Math.round((4.2 + idx * 2.8) * 10) / 10
    }));
  }, [multiplier]);

  const maxChartValue = Math.max(...chartData.map(d => d.value), 100);

  // Sample table rows
  const tableRows = useMemo(() => {
    return [
      { id: 101, module: 'streamlit_app.py', status: 'Active', latency: `${(12 * multiplier).toFixed(1)}ms`, tier: 'Production' },
      { id: 102, module: 'requirements.txt', status: 'Pinned', latency: '0.0ms', tier: 'Core' },
      { id: 103, module: 'config.toml', status: 'Loaded', latency: '1.2ms', tier: 'Theme' },
      { id: 104, module: 'secrets.toml', status: 'Secure', latency: '0.8ms', tier: 'Encrypted' },
      { id: 105, module: 'Community Cloud Prober', status: 'Ready', latency: '4.5ms', tier: 'Cloud' },
    ].filter(r => r.module.toLowerCase().includes(tableSearch.toLowerCase()) || r.status.toLowerCase().includes(tableSearch.toLowerCase()));
  }, [multiplier, tableSearch]);

  const triggerBalloons = () => {
    confetti({
      particleCount: 80,
      spread: 70,
      origin: { y: 0.6 },
      colors: ['#FF4B4B', '#FF7A00', '#FFB800', '#2BD465', '#249CFF', '#9E44FF']
    });
  };

  const handleButtonClick = () => {
    setButtonClicked(true);
    if (enableBalloons) {
      triggerBalloons();
    }
    showToast('st.toast("Button interaction triggered! App state refreshed.")');
  };

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  const handleCopyCode = () => {
    navigator.clipboard.writeText(currentTemplate.pythonCode);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userText = chatInput;
    setChatMessages(prev => [...prev, { role: 'user', text: userText }]);
    setChatInput('');

    setTimeout(() => {
      setChatMessages(prev => [
        ...prev,
        { role: 'assistant', text: `Echo from Streamlit session_state: "${userText}". You can connect any LLM API (Gemini, OpenAI, Anthropic) in your deployed Community Cloud app!` }
      ]);
    }, 400);
  };

  return (
    <main
      className={`min-h-[calc(100vh-56px)] transition-all duration-200 p-6 md:p-10 ${
        isSidebarExpanded ? 'lg:pl-88' : 'pl-6 md:pl-10'
      }`}
    >
      <div className="max-w-5xl mx-auto space-y-8">
        {/* Streamlit Top Status Alert Banner */}
        <div className="flex items-center justify-between p-3.5 bg-neutral-50 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-lg text-xs">
          <div className="flex items-center gap-2.5 text-neutral-700 dark:text-neutral-300">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span className="font-semibold text-neutral-900 dark:text-neutral-100">
              Streamlit Community Cloud Ready
            </span>
            <span className="text-neutral-400">·</span>
            <span className="text-neutral-500 dark:text-neutral-400 hidden sm:inline">
              Entrypoint: <code className="text-[#FF4B4B] font-mono">streamlit_app.py</code>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onSwitchTab('code')}
              className="text-xs text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 hover:underline flex items-center gap-1"
            >
              <span>View Source</span>
            </button>
            <span className="text-neutral-300 dark:text-neutral-700">|</span>
            <button
              onClick={onOpenDeploy}
              className="text-xs font-medium text-[#FF4B4B] hover:text-[#E03A3A] hover:underline flex items-center gap-1"
            >
              <span>Deploy to Cloud</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Minimal Template Specific View */}
        {currentTemplate.id === 'minimal' && (
          <div className="space-y-6 bg-white dark:bg-[#151921] p-8 rounded-xl border border-neutral-200/80 dark:border-neutral-800 shadow-xs max-w-2xl mx-auto">
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100 flex items-center gap-2">
                <span>🎈</span>
                <span>Minimal Streamlit App</span>
              </h1>
              <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
                This is the cleanest, ultralight baseline starter app (~15 lines of Python) for Streamlit Community Cloud.
              </p>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold text-neutral-700 dark:text-neutral-300">
                st.text_input("What is your name?")
              </label>
              <input
                type="text"
                value={userName}
                readOnly
                className="w-full px-3 py-2 text-sm bg-neutral-50 dark:bg-neutral-800/60 border border-neutral-300 dark:border-neutral-700 rounded-md text-neutral-900 dark:text-neutral-100"
              />
              <p className="text-xs text-neutral-500">
                Hello, <strong className="text-neutral-800 dark:text-neutral-200">{userName || 'World'}</strong>!
              </p>
            </div>

            <div>
              <button
                onClick={handleButtonClick}
                className="px-4 py-2 text-xs font-semibold text-white bg-[#FF4B4B] hover:bg-[#E03A3A] active:scale-[0.98] rounded-md transition-all shadow-xs"
              >
                Say Hello
              </button>
            </div>

            {buttonClicked && (
              <div className="p-3 bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 rounded-lg flex items-center gap-2.5 text-xs text-emerald-800 dark:text-emerald-300">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <span>Greetings, {userName}! Your empty app is responding properly.</span>
              </div>
            )}
          </div>
        )}

        {/* Chatbot Template Specific View */}
        {currentTemplate.id === 'chat' && (
          <div className="space-y-6 max-w-3xl mx-auto">
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100 flex items-center gap-2">
                <span>💬</span>
                <span>Chatbot Starter Template</span>
              </h1>
              <p className="mt-1 text-xs sm:text-sm text-neutral-500 dark:text-neutral-400">
                Powered by Streamlit's native <code className="text-[#FF4B4B]">st.chat_message</code> and <code className="text-[#FF4B4B]">st.chat_input</code>.
              </p>
            </div>

            {/* Chat Container */}
            <div className="bg-white dark:bg-[#151921] border border-neutral-200 dark:border-neutral-800 rounded-xl p-4 sm:p-6 space-y-4 min-h-[380px] flex flex-col justify-between shadow-xs">
              <div className="space-y-3.5 overflow-y-auto max-h-[460px] pr-1">
                {chatMessages.map((msg, i) => (
                  <div
                    key={i}
                    className={`flex items-start gap-3 text-xs sm:text-sm ${
                      msg.role === 'user' ? 'justify-end' : 'justify-start'
                    }`}
                  >
                    {msg.role === 'assistant' && (
                      <div className="w-7 h-7 rounded-full bg-[#FF4B4B]/10 text-[#FF4B4B] flex items-center justify-center shrink-0 mt-0.5">
                        <Bot className="w-4 h-4" />
                      </div>
                    )}
                    <div
                      className={`p-3 rounded-lg max-w-[82%] leading-relaxed ${
                        msg.role === 'user'
                          ? 'bg-[#FF4B4B] text-white'
                          : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200'
                      }`}
                    >
                      {msg.text}
                    </div>
                    {msg.role === 'user' && (
                      <div className="w-7 h-7 rounded-full bg-neutral-200 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-300 flex items-center justify-center shrink-0 mt-0.5">
                        <User className="w-4 h-4" />
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Chat Input form */}
              <form onSubmit={handleSendMessage} className="pt-2 border-t border-neutral-100 dark:border-neutral-800">
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    placeholder="Type your message here..."
                    className="flex-1 px-3.5 py-2 text-xs sm:text-sm bg-neutral-50 dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-700 rounded-lg focus:outline-none focus:ring-1 focus:ring-[#FF4B4B] text-neutral-900 dark:text-neutral-100"
                  />
                  <button
                    type="submit"
                    className="p-2 sm:px-4 sm:py-2 text-xs font-semibold text-white bg-[#FF4B4B] hover:bg-[#E03A3A] rounded-lg transition-colors flex items-center gap-1.5"
                  >
                    <Send className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">Send</span>
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Standard / Data Analytics View */}
        {(currentTemplate.id === 'starter' || currentTemplate.id === 'data') && (
          <>
            {/* Header Area (st.title & st.write) */}
            <div className="space-y-2">
              <div className="flex items-baseline gap-2">
                <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100">
                  {currentTemplate.id === 'data' ? '📊 Data Analytics Starter' : '🎈 Streamlit Empty Starter App'}
                </h1>
              </div>
              <p className="text-sm text-neutral-600 dark:text-neutral-400 max-w-3xl leading-relaxed">
                Welcome to your empty Streamlit application! This template is pre-configured with the standard directory structure, requirements, and theme settings ready for instant deployment on <strong className="text-neutral-900 dark:text-neutral-100">Streamlit Community Cloud</strong>.
              </p>
            </div>

            {/* st.columns: Metric Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-4 bg-white dark:bg-[#151921] border border-neutral-200 dark:border-neutral-800 rounded-xl shadow-xs space-y-1">
                <div className="flex items-center justify-between text-xs text-neutral-500 dark:text-neutral-400">
                  <span>Server Status</span>
                  <Server className="w-3.5 h-3.5 text-neutral-400" />
                </div>
                <div className="text-2xl font-bold font-mono tracking-tight text-neutral-900 dark:text-neutral-100 tabular-nums">
                  Online
                </div>
                <div className="flex items-center gap-1 text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
                  <TrendingUp className="w-3 h-3" />
                  <span>Healthy (Community Cloud ready)</span>
                </div>
              </div>

              <div className="p-4 bg-white dark:bg-[#151921] border border-neutral-200 dark:border-neutral-800 rounded-xl shadow-xs space-y-1">
                <div className="flex items-center justify-between text-xs text-neutral-500 dark:text-neutral-400">
                  <span>Python Runtime</span>
                  <Cpu className="w-3.5 h-3.5 text-neutral-400" />
                </div>
                <div className="text-2xl font-bold font-mono tracking-tight text-neutral-900 dark:text-neutral-100 tabular-nums">
                  3.11
                </div>
                <div className="text-[11px] text-neutral-500 dark:text-neutral-400">
                  Streamlit v1.40.0+
                </div>
              </div>

              <div className="p-4 bg-white dark:bg-[#151921] border border-neutral-200 dark:border-neutral-800 rounded-xl shadow-xs space-y-1">
                <div className="flex items-center justify-between text-xs text-neutral-500 dark:text-neutral-400">
                  <span>Compute Factor</span>
                  <Sparkles className="w-3.5 h-3.5 text-[#FF4B4B]" />
                </div>
                <div className="text-2xl font-bold font-mono tracking-tight text-neutral-900 dark:text-neutral-100 tabular-nums">
                  {multiplier * 42} ops
                </div>
                <div className="text-[11px] text-emerald-600 dark:text-emerald-400 font-mono">
                  +{multiplier}x (reactive to sidebar slider)
                </div>
              </div>
            </div>

            {/* st.info Callout */}
            <div className="p-4 bg-blue-50/70 dark:bg-blue-950/20 border border-blue-200/80 dark:border-blue-900/40 rounded-xl flex items-start gap-3 text-xs sm:text-sm text-blue-900 dark:text-blue-200">
              <Info className="w-4 h-4 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <span className="font-semibold">Greeting for {userName}:</span>
                <p className="text-blue-800 dark:text-blue-300 text-xs">
                  This empty app is running live. Open the <strong className="font-semibold">Files & Code</strong> tab to see the generated Python script, or click <strong className="font-semibold">Deploy</strong> to publish directly to Streamlit Community Cloud.
                </p>
              </div>
            </div>

            {/* st.button & Balloons Action Row */}
            <div className="flex flex-wrap items-center gap-3 p-4 bg-white dark:bg-[#151921] border border-neutral-200 dark:border-neutral-800 rounded-xl">
              <button
                onClick={handleButtonClick}
                className="px-4 py-2 text-xs font-semibold text-white bg-[#FF4B4B] hover:bg-[#E03A3A] active:scale-[0.98] rounded-md transition-all shadow-xs flex items-center gap-1.5"
              >
                <span>🚀 Click to test Streamlit interaction</span>
              </button>

              <button
                onClick={triggerBalloons}
                className="px-3.5 py-2 text-xs font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 border border-neutral-300 dark:border-neutral-700 rounded-md transition-colors flex items-center gap-1.5"
              >
                <span>🎈 Trigger st.balloons()</span>
              </button>

              <span className="text-xs text-neutral-500">
                Active view: <strong className="text-neutral-800 dark:text-neutral-200">{appMode}</strong>
              </span>
            </div>

            {/* Interactive Visual Chart (Simulating st.line_chart / st.bar_chart) */}
            <div className="p-5 bg-white dark:bg-[#151921] border border-neutral-200 dark:border-neutral-800 rounded-xl space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                    📈 st.line_chart(sample_data)
                  </h3>
                  <p className="text-xs text-neutral-500">
                    Dynamically rendered with metric multiplier ({multiplier}x)
                  </p>
                </div>
                <div className="text-xs font-mono text-neutral-400 tabular-nums">
                  max: {maxChartValue}
                </div>
              </div>

              {/* Chart Visualization Bars / Lines */}
              <div className="h-44 flex items-end gap-6 sm:gap-12 px-4 pt-4 border-b border-neutral-200 dark:border-neutral-800">
                {chartData.map((item) => {
                  const heightPercent = Math.min(100, Math.max(15, (item.value / maxChartValue) * 100));
                  return (
                    <div key={item.quarter} className="flex-1 flex flex-col items-center gap-2 group h-full justify-end">
                      <div className="text-[11px] font-mono text-neutral-500 dark:text-neutral-400 tabular-nums opacity-0 group-hover:opacity-100 transition-opacity">
                        {item.value}
                      </div>
                      <div
                        style={{ height: `${heightPercent}%` }}
                        className="w-full bg-gradient-to-t from-[#FF4B4B] to-[#FF7A00] rounded-t transition-all duration-300 hover:brightness-110"
                      />
                      <span className="text-xs font-medium text-neutral-600 dark:text-neutral-400">
                        {item.quarter}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Dataframe Explorer: st.dataframe */}
            <div className="p-5 bg-white dark:bg-[#151921] border border-neutral-200 dark:border-neutral-800 rounded-xl space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                    📋 st.dataframe(app_manifest)
                  </h3>
                  <p className="text-xs text-neutral-500">
                    Interactive tabular view with search filter
                  </p>
                </div>
                <div className="relative w-full sm:w-64">
                  <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-neutral-400" />
                  <input
                    type="text"
                    value={tableSearch}
                    onChange={(e) => setTableSearch(e.target.value)}
                    placeholder="Search modules..."
                    className="w-full pl-8 pr-3 py-1.5 text-xs bg-neutral-50 dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-700 rounded-md focus:outline-none focus:ring-1 focus:ring-[#FF4B4B]"
                  />
                </div>
              </div>

              {/* Table */}
              <div className="overflow-x-auto border border-neutral-200 dark:border-neutral-800 rounded-lg">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-neutral-50 dark:bg-neutral-900/80 border-b border-neutral-200 dark:border-neutral-800 text-neutral-600 dark:text-neutral-400 font-medium">
                      <th className="py-2.5 px-3">ID</th>
                      <th className="py-2.5 px-3">File / Module</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3 text-right">Execution Latency</th>
                      <th className="py-2.5 px-3">Cloud Tier</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-100 dark:divide-neutral-800/60 font-mono">
                    {tableRows.map((row) => (
                      <tr key={row.id} className="hover:bg-neutral-50/80 dark:hover:bg-neutral-800/40 transition-colors">
                        <td className="py-2.5 px-3 text-neutral-400 tabular-nums">#{row.id}</td>
                        <td className="py-2.5 px-3 font-semibold text-neutral-800 dark:text-neutral-200 font-sans">
                          {row.module}
                        </td>
                        <td className="py-2.5 px-3 font-sans">
                          <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                            {row.status}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right text-neutral-700 dark:text-neutral-300 tabular-nums">
                          {row.latency}
                        </td>
                        <td className="py-2.5 px-3 font-sans text-neutral-500">
                          {row.tier}
                        </td>
                      </tr>
                    ))}
                    {tableRows.length === 0 && (
                      <tr>
                        <td colSpan={5} className="py-6 text-center text-xs text-neutral-400">
                          No matching modules found.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* st.expander */}
            <div className="border border-neutral-200 dark:border-neutral-800 rounded-xl overflow-hidden bg-white dark:bg-[#151921]">
              <button
                onClick={() => setExpanderOpen(!expanderOpen)}
                className="w-full px-5 py-3.5 flex items-center justify-between text-left text-xs font-semibold text-neutral-800 dark:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-neutral-800/50 transition-colors"
              >
                <span>ℹ️ st.expander("How does Streamlit Community Cloud run this app?")</span>
                {expanderOpen ? <ChevronUp className="w-4 h-4 text-neutral-400" /> : <ChevronDown className="w-4 h-4 text-neutral-400" />}
              </button>

              {expanderOpen && (
                <div className="px-5 py-4 border-t border-neutral-100 dark:border-neutral-800 text-xs text-neutral-600 dark:text-neutral-400 space-y-2 leading-relaxed">
                  <p>
                    Streamlit Community Cloud is a free, managed hosting service for Streamlit applications. When you link your GitHub repository:
                  </p>
                  <ul className="list-disc list-inside space-y-1 pl-1 text-neutral-700 dark:text-neutral-300">
                    <li>It provisions a container running Debian Linux and Python 3.11+.</li>
                    <li>It automatically executes <code className="font-mono text-[#FF4B4B]">pip install -r requirements.txt</code>.</li>
                    <li>It starts your app with <code className="font-mono text-[#FF4B4B]">streamlit run streamlit_app.py</code>.</li>
                    <li>Every push to your GitHub branch triggers automatic instant redeployments!</li>
                  </ul>
                </div>
              )}
            </div>

            {/* st.code block */}
            <div className="p-5 bg-white dark:bg-[#151921] border border-neutral-200 dark:border-neutral-800 rounded-xl space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-neutral-700 dark:text-neutral-300">
                  st.code("streamlit_app.py", language="python")
                </span>
                <button
                  onClick={handleCopyCode}
                  className="flex items-center gap-1 text-xs text-neutral-500 hover:text-neutral-900 dark:hover:text-neutral-200"
                >
                  {copiedCode ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedCode ? 'Copied' : 'Copy'}</span>
                </button>
              </div>

              <div className="p-3 bg-[#0E1117] text-neutral-200 rounded-lg font-mono text-xs overflow-x-auto max-h-48">
                <pre>{currentTemplate.pythonCode.slice(0, 480)}...</pre>
              </div>
            </div>
          </>
        )}

        {/* Floating Toast Notification */}
        {toastMessage && (
          <div className="fixed bottom-6 right-6 z-50 p-3 bg-neutral-900 text-white text-xs rounded-lg shadow-xl border border-neutral-700 animate-in fade-in slide-in-from-bottom-2">
            {toastMessage}
          </div>
        )}
      </div>
    </main>
  );
};
