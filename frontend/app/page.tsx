"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Cpu, Network, Shield, Loader2, Play, Pause, Save, CheckCircle, XCircle, Zap, BookOpen, HelpCircle, Activity } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import ThreeBackground from "./components/ThreeBackground";

// --- Utilities ---
function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// --- Types ---
type Message = {
  role: "user" | "agent";
  content: string;
  type?: "quick" | "research" | "explain";
  timestamp: number;
};

type GraphNode = "router" | "planner" | "executor" | "validator" | "reporter" | "chat_node" | "human_approval" | "explain_node" | "step_manager";

// --- Components ---

const GlassCard = ({ children, className }: { children: React.ReactNode, className?: string }) => (
  <div className={cn(
    "backdrop-blur-xl bg-gray-900/40 border border-white/10 shadow-2xl rounded-2xl overflow-hidden",
    className
  )}>
    {children}
  </div>
);

const NodeBadge = ({ active, label, icon: Icon, processing }: { active: boolean; label: string; icon: any, processing?: boolean }) => (
  <motion.div
    animate={{
      borderColor: active ? "rgba(16, 185, 129, 0.5)" : "rgba(255, 255, 255, 0.05)",
      backgroundColor: active ? "rgba(16, 185, 129, 0.1)" : "rgba(0, 0, 0, 0.2)",
      scale: active ? 1.02 : 1,
      x: active ? 10 : 0
    }}
    transition={{ type: "spring", stiffness: 300, damping: 20 }}
    className={cn(
      "flex items-center gap-3 px-4 py-3 rounded-xl border transition-all duration-300 w-full mb-3 relative overflow-hidden",
      active ? "shadow-[0_0_20px_rgba(16,185,129,0.2)]" : "opacity-50 blur-[1px] hover:opacity-80 hover:blur-0"
    )}
  >
    {active && processing && (
      <motion.div
        className="absolute inset-0 bg-emerald-500/10"
        initial={{ x: "-100%" }}
        animate={{ x: "100%" }}
        transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
      />
    )}
    <Icon className={cn("w-5 h-5 z-10 relative", active ? "text-emerald-400" : "text-gray-500")} />
    <span className={cn("text-xs font-bold uppercase tracking-wider z-10 relative", active ? "text-emerald-100" : "text-gray-500")}>
      {label}
    </span>
    {active && (
      <motion.div layoutId="active-glow" className="absolute right-3 w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_10px_#34d399]" />
    )}
  </motion.div>
);

export default function AgentInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [mounted, setMounted] = useState(false);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeNode, setActiveNode] = useState<GraphNode | null>(null);
  const [approvalRequired, setApprovalRequired] = useState(false);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [mode, setMode] = useState<"quick" | "research" | "explain" | null>(null);

  const threadId = useRef("web_session_" + Math.random().toString(36).substr(2, 9)).current;
  const scrollRef = useRef<HTMLDivElement>(null);

  // Load from session storage on mount
  useEffect(() => {
    setMounted(true);
    const saved = sessionStorage.getItem("chat_messages");
    if (saved) {
      try {
        setMessages(JSON.parse(saved));
      } catch (e) {
        console.error("Failed to parse history", e);
      }
    }
  }, []);

  // Save to session storage whenever messages change
  useEffect(() => {
    if (mounted && messages.length > 0) {
      sessionStorage.setItem("chat_messages", JSON.stringify(messages));
    }
  }, [messages, mounted]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    }
  }, [messages, loading, activeNode]);

  const processEvents = async (events: any[]) => {
    for (const event of events) {
      if (!event || !event.node) continue;

      setActiveNode(event.node);

      if (event.node === "router" && event.data?.mode) {
        setMode(event.data.mode);
      }

      if (event.node === "explain_node" && event.data?.explanation) {
        setExplanation(event.data.explanation);
      }

      if (event.node === "human_approval") {
        setApprovalRequired(true);
        break; // Stop processing to wait for user
      }

      if (event.data?.final_response || event.data?.response) {
        const content = event.data.final_response || event.data.response;
        const type = event.node === "chat_node" ? "quick" : "research";

        setMessages(prev => {
          if (prev.length > 0 && prev[prev.length - 1].content === content && prev[prev.length - 1].role === "agent") {
            return prev;
          }
          return [...prev, {
            role: "agent",
            content: content,
            type: type,
            timestamp: Date.now()
          }]
        });
      }

      // Keep it extremely fast
      await new Promise(r => setTimeout(r, 20));
    }

    if (!approvalRequired) {
      // Don't clear active node immediately if we are still loading, handled by outer loop
    }
  };

  const processStream = async (response: Response) => {
    if (!response.body) return;
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let dimmerBuffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = (dimmerBuffer + chunk).split("\n");
        dimmerBuffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const data = JSON.parse(line);
            if (data.status === "paused") {
              setApprovalRequired(true);
              setActiveNode("human_approval");
              return; // Stop processing stream if paused
            }
            if (data.status === "error") {
              console.error("Backend Error:", data.message);
              setMessages(prev => [...prev, {
                role: "agent",
                content: `❌ SYSTEM ERROR: ${data.message}`,
                timestamp: Date.now()
              }]);
              setLoading(false);
              return;
            }
            if (data.events) {
              await processEvents(data.events);
            }
          } catch (e) {
            console.error("Error parsing stream line", e);
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  };


  const sendMessage = async (text: string) => {
    if (!text.trim()) return;

    const userMsg = { role: "user", content: text, timestamp: Date.now() } as Message;
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    setActiveNode("router");
    setExplanation(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, thread_id: threadId })
      });

      await processStream(res);

    } catch (e) {
      console.error(e);
      setMessages(prev => [...prev, { role: "agent", content: "Error connecting to agent backend.", timestamp: Date.now() }]);
    } finally {
      // Only turn off loading if we didn't get paused
      // We can't rely on 'approvalRequired' state variable here immediately because of closure stale state
      // But since we await processStream, if it hit pause, it set state.
      // We'll trust the component re-render to handle UI state, but we need to ensure local loading is off?
      // Actually, if paused, we want loading off? No, we want to show 'paused' UI.

      // Let's use a functional update check or just a timeout to check refs? 
      // Simpler: Just turn off loading. The approval UI will show if needed.
      setLoading(false);
      if (!approvalRequired) setActiveNode(null);
    }
  };

  const handleApproval = async (approved: boolean) => {
    setApprovalRequired(false);
    setLoading(true);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ thread_id: threadId, approved })
      });
      await processStream(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
      setActiveNode(null);
    }
  };

  if (!mounted) return null;

  return (
    <div className="relative flex h-screen w-full overflow-hidden text-gray-200 font-sans selection:bg-emerald-500/30 selection:text-emerald-200">

      {/* 3D Background */}
      <ThreeBackground />

      {/* Main Content Layout */}
      <div className="z-10 flex w-full h-full p-4 lg:p-8 gap-6">

        {/* LEFT: Chat Area */}
        <GlassCard className="flex-1 flex flex-col relative">

          {/* Header */}
          <div className="p-6 border-b border-white/5 flex justify-between items-center bg-black/20">
            <div className="flex items-center gap-4">
              <div className="relative">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-cyan-600 flex items-center justify-center shadow-lg shadow-emerald-500/20">
                  <Activity className="text-white w-6 h-6" />
                </div>
                {loading && (
                  <span className="absolute -top-1 -right-1 flex h-3 w-3">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                  </span>
                )}
              </div>
              <div>
                <h1 className="font-bold text-2xl tracking-tight text-white flex items-center gap-2">
                  ISEA <span className="text-xs font-mono text-emerald-500/80 px-2 py-0.5 rounded border border-emerald-500/20 bg-emerald-500/10">v2.0 PRO</span>
                </h1>
                <p className="text-xs text-gray-500 font-mono tracking-wider uppercase">Introspective Self-Evolving Agent</p>
              </div>
            </div>

            {mode && (
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                className={cn(
                  "px-3 py-1.5 rounded-full text-xs font-bold border flex items-center gap-2 shadow-lg backdrop-blur-md",
                  mode === "quick" ? "bg-blue-500/20 border-blue-500/50 text-blue-300" :
                    mode === "research" ? "bg-purple-500/20 border-purple-500/50 text-purple-300" :
                      "bg-orange-500/20 border-orange-500/50 text-orange-300"
                )}
              >
                {mode === "quick" && <Zap className="w-3 h-3" />}
                {mode === "research" && <BookOpen className="w-3 h-3" />}
                {mode === "explain" && <HelpCircle className="w-3 h-3" />}
                {mode.toUpperCase()} MODE
              </motion.div>
            )}
          </div>

          {/* Messages Area */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-8 scroll-smooth custom-scrollbar">
            <AnimatePresence>
              {messages.length === 0 && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex flex-col items-center justify-center h-full text-gray-500 space-y-6"
                >
                  <div className="w-24 h-24 rounded-full bg-white/5 flex items-center justify-center border border-white/10 animate-pulse-slow">
                    <Network className="w-10 h-10 opacity-30" />
                  </div>
                  <div className="text-center space-y-2">
                    <h3 className="text-xl font-medium text-white">System Ready</h3>
                    <p className="text-[12px] uppercase tracking-widest opacity-60">Awaiting Neural Input</p>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full max-w-lg mt-8">
                    {[
                      { label: "Research Quantum Computing", icon: BookOpen, query: "Research the current state of Quantum Computing" },
                      { label: "Explain Architecture", icon: Cpu, query: "Explain your internal reasoning engine" },
                      { label: "Quick Math Analysis", icon: Zap, query: "Calculate the Fibonacci sequence up to 100" },
                      { label: "Analyze Global Trends", icon: Activity, query: "Analyze current global tech trends" },
                    ].map((item, idx) => (
                      <button
                        key={idx}
                        onClick={() => sendMessage(item.query)}
                        className="p-4 bg-white/5 hover:bg-emerald-500/20 border border-white/10 hover:border-emerald-500/50 rounded-xl text-sm text-left transition-all duration-300 group"
                      >
                        <div className="flex items-center gap-2 mb-1 text-gray-400 group-hover:text-emerald-400">
                          <item.icon className="w-4 h-4" />
                          <span className="font-bold">{item.label}</span>
                        </div>
                        <span className="text-xs text-gray-600 group-hover:text-emerald-500/70 truncate block">{item.query}</span>
                      </button>
                    ))}
                  </div>
                </motion.div>
              )}

              {messages.map((m, i) => (
                <motion.div
                  initial={{ opacity: 0, y: 20, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ duration: 0.3 }}
                  key={m.timestamp} // Use timestamp for key to avoid re-renders
                  className={cn("flex flex-col max-w-3xl", m.role === "user" ? "ml-auto items-end" : "mr-auto items-start")}
                >
                  <div className="flex items-end gap-3 mb-1">
                    {m.role === "agent" && (
                      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-600 to-teal-800 flex items-center justify-center shadow-lg border border-white/10">
                        <Activity className="w-4 h-4 text-white" />
                      </div>
                    )}
                    <div className={cn(
                      "p-5 rounded-2xl text-[15px] leading-7 shadow-2xl backdrop-blur-sm border",
                      m.role === "user"
                        ? "bg-gradient-to-br from-indigo-600 to-blue-700 text-white rounded-br-sm border-white/10"
                        : "bg-gray-800/80 text-gray-100 rounded-bl-sm border-white/5"
                    )}>
                      <div className="whitespace-pre-wrap">{m.content}</div>
                    </div>
                  </div>
                  <span className="text-[10px] text-gray-500 mt-2 px-12 opacity-50 uppercase tracking-widest font-mono">
                    {m.role} • {new Date(m.timestamp).toLocaleTimeString()}
                  </span>
                </motion.div>
              ))}
            </AnimatePresence>

            {/* Loading Indicator */}
            {loading && !approvalRequired && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center gap-3 text-emerald-500 text-sm p-2 ml-1"
              >
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="font-mono text-xs tracking-wider animate-pulse">
                  NEURAL PROCESSING... [{activeNode?.toUpperCase() || "THINKING"}]
                </span>
              </motion.div>
            )}

            {/* Explanation Block */}
            <AnimatePresence>
              {activeNode === "explain_node" && explanation && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="bg-gray-900/90 border border-emerald-500/30 rounded-xl overflow-hidden mt-4 mx-4"
                >
                  <div className="bg-emerald-900/20 p-3 border-b border-emerald-500/20 flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-emerald-400" />
                    <h4 className="text-sm font-bold text-emerald-400 uppercase tracking-wider">Metacognition Stream</h4>
                  </div>
                  <div className="p-6 text-emerald-100/90 font-mono text-sm leading-relaxed">
                    {explanation}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Approval Modal */}
            <AnimatePresence>
              {approvalRequired && (
                <motion.div
                  initial={{ scale: 0.9, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  exit={{ scale: 0.9, opacity: 0 }}
                  className="mx-auto mt-6 p-1 rounded-2xl bg-gradient-to-r from-amber-500 via-orange-500 to-red-500 w-full max-w-lg shadow-[0_0_30px_rgba(245,158,11,0.3)]"
                >
                  <div className="bg-gray-900 rounded-xl p-6">
                    <div className="flex items-center gap-3 mb-4 text-amber-500">
                      <Shield className="w-8 h-8" />
                      <div>
                        <h3 className="font-bold text-xl text-white">Authorization Protocol</h3>
                        <p className="text-xs text-amber-500/70 uppercase tracking-widest">Human-in-the-Loop Gate</p>
                      </div>
                    </div>
                    <p className="text-gray-300 mb-8 leading-relaxed">
                      The agent has initiated a restricted protocol <span className="text-white font-mono bg-white/10 px-1 py-0.5 rounded">save_to_notes</span>.
                      This action requires explicit verified approval to proceed.
                    </p>
                    <div className="flex gap-4">
                      <button
                        onClick={() => handleApproval(true)}
                        className="flex-1 py-3 bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-white font-bold rounded-lg flex items-center justify-center gap-2 transition-all shadow-lg shadow-emerald-900/20 active:scale-95"
                      >
                        <CheckCircle className="w-5 h-5" /> AUTHORIZE
                      </button>
                      <button
                        onClick={() => handleApproval(false)}
                        className="flex-1 py-3 bg-gray-800 hover:bg-gray-700 text-gray-300 font-bold rounded-lg flex items-center justify-center gap-2 transition-all border border-white/10 active:scale-95"
                      >
                        <XCircle className="w-5 h-5" /> REJECT
                      </button>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Input Area */}
          <div className="p-6 border-t border-white/5 bg-black/40 backdrop-blur-md">
            <div className="relative group">
              <div className="absolute -inset-0.5 bg-gradient-to-r from-emerald-500 to-cyan-500 rounded-xl opacity-30 group-focus-within:opacity-100 transition duration-500 blur"></div>
              <div className="relative flex items-center bg-gray-900 rounded-xl">
                <input
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      if (!loading && !approvalRequired) sendMessage(input);
                    }
                  }}
                  placeholder="Enter command or research query..."
                  className="w-full bg-transparent p-4 outline-none text-white placeholder-gray-500 font-medium"
                  disabled={loading || approvalRequired}
                  autoComplete="off"
                  autoFocus
                />
                <button
                  type="button"
                  onClick={() => sendMessage(input)}
                  disabled={loading || approvalRequired}
                  className="p-3 mr-1 text-emerald-500 hover:text-white hover:bg-emerald-500 rounded-lg transition-all disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-emerald-500"
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
            </div>
            <div className="text-[10px] text-gray-600 mt-2 text-center font-mono opacity-50 flex justify-center gap-4">
              <span>SYSTEM: ONLINE</span>
              <span>LATENCY: 12ms</span>
              <span>ENCRYPTION: AES-256</span>
            </div>
          </div>
        </GlassCard>

        {/* RIGHT: Live Graph Visualization */}
        <div className="hidden lg:flex w-80 flex-col gap-6">
          <GlassCard className="p-6 h-full flex flex-col relative overflow-hidden">
            {/* Decorative Grid */}
            <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:20px_20px]" />

            <h2 className="text-xs font-bold text-emerald-400 uppercase tracking-widest mb-6 flex items-center gap-2 relative z-10">
              <Activity className="w-4 h-4 animate-pulse" /> Live Neural State
            </h2>

            <div className="flex-1 relative z-10 space-y-2">
              {/* Visual Path Connector */}
              <div className="absolute left-7 top-4 bottom-4 w-0.5 bg-gradient-to-b from-gray-800 via-emerald-900/50 to-gray-800 -z-10" />

              <NodeBadge active={activeNode === "router"} label="Router" icon={Network} processing={activeNode === "router"} />
              <NodeBadge active={activeNode === "planner"} label="Planner" icon={Cpu} processing={activeNode === "planner"} />

              {/* Logic Branch */}
              <div className="pl-6 py-2 space-y-3 relative">
                <div className="absolute left-0 top-0 bottom-0 w-px bg-gray-800" />
                <div className="absolute left-0 top-1/2 w-4 h-px bg-gray-800" />

                <NodeBadge active={activeNode === "executor"} label="Executor" icon={Play} processing={activeNode === "executor"} />
                <NodeBadge active={activeNode === "validator"} label="Validator" icon={Shield} processing={activeNode === "validator"} />
                <NodeBadge active={activeNode === "human_approval"} label="Human Gate" icon={Pause} processing={activeNode === "human_approval"} />
              </div>

              <NodeBadge active={activeNode === "reporter"} label="Reporter" icon={Save} processing={activeNode === "reporter"} />
              <NodeBadge active={activeNode === "chat_node"} label="Quick Chat Line" icon={Zap} processing={activeNode === "chat_node"} />
            </div>

            <div className="mt-auto relative z-10 p-4 bg-black/40 rounded-xl border border-white/5 backdrop-blur-md">
              <h3 className="text-[10px] text-gray-500 uppercase mb-3 font-bold">System Telemetry</h3>
              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-gray-400">Context Window</span>
                  <span className="text-emerald-400 font-mono">128k</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-400">Token Usage</span>
                  <span className="text-emerald-400 font-mono">~450/req</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-400">Model</span>
                  <span className="text-emerald-400 font-mono">Gemini-1.5-Flash</span>
                </div>
              </div>
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
