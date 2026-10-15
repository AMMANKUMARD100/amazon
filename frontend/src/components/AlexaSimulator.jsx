import React, { useState, useEffect, useRef } from 'react';
import { 
  Bot, 
  Send, 
  Mic, 
  MicOff, 
  Sparkles, 
  Radio, 
  Terminal, 
  CheckCircle2, 
  Calendar, 
  AlertCircle,
  Minimize2,
  Maximize2
} from 'lucide-react';
import api from '../services/api';

const AlexaSimulator = ({ onTaskAction }) => {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([
    {
      sender: 'alexa',
      text: "Hello! I am your CampusMate Alexa+ assistant. How can I help you manage your study schedule, pending tasks, or lecture attendance today?",
      card: { title: "Alexa+ Ready", content: "Ask me: 'What are my pending tasks?' or 'Add task Math homework due 2026-10-28'" },
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [inputUtterance, setInputUtterance] = useState('');
  const [loading, setLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isExpanded, setIsExpanded] = useState(true);
  const [activeTraceId, setActiveTraceId] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendUtterance = async (utteranceToSend) => {
    const text = utteranceToSend || inputUtterance;
    if (!text.trim() || loading) return;

    const userMsg = {
      sender: 'user',
      text: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    setInputUtterance('');
    setLoading(true);

    try {
      const response = await api.post('/alexa/simulate', {
        utterance: text,
        session_id: sessionId,
        device: "Echo Show 10 (Simulated)"
      });

      const alexaRes = response.data;
      if (alexaRes?.sessionAttributes?.session_id) {
        setSessionId(alexaRes.sessionAttributes.session_id);
      }

      const speech = alexaRes?.response?.outputSpeech?.text || "I've processed your request.";
      const card = alexaRes?.response?.card;
      const simulation = alexaRes?.simulation;

      const alexaMsg = {
        sender: 'alexa',
        text: speech,
        card: card,
        simulation: simulation,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setMessages(prev => [...prev, alexaMsg]);

      // Trigger task refresh in parent dashboard if a task action was executed
      if (simulation?.action_executed && onTaskAction) {
        onTaskAction(simulation.action_executed);
      }
    } catch (err) {
      console.error(err);
      setMessages(prev => [
        ...prev,
        {
          sender: 'alexa',
          text: "I'm having trouble connecting to the concierge agent right now. Please verify backend service is running.",
          card: { title: "Connection Notice", content: "Failed to simulate request." },
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const sampleUtterances = [
    "What are my pending tasks?",
    "Check my attendance percentage",
    "What classes do I have today?",
    "Add task Physics Lab due 2026-10-30",
    "Complete task Physics Lab"
  ];

  return (
    <div className="glass-panel flex flex-col h-[520px] rounded-2xl overflow-hidden border border-slate-200/80 dark:border-slate-800/80 shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3.5 bg-gradient-to-r from-cyan-600/10 via-brand-500/10 to-indigo-600/10 border-b border-slate-200/60 dark:border-slate-800/60">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-tr from-cyan-500 to-brand-500 rounded-xl text-white shadow-md shadow-brand-500/20">
            <Radio size={18} className="animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-sm text-slate-800 dark:text-white">
                Alexa+ Assistant Simulator
              </h3>
              <span className="text-[10px] font-semibold px-2 py-0.5 bg-cyan-500/20 text-cyan-700 dark:text-cyan-300 rounded-full border border-cyan-500/30">
                Hackathon Track
              </span>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              Simulated voice & text multimodal interaction
            </p>
          </div>
        </div>

        <button 
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition"
          title={isExpanded ? "Collapse" : "Expand"}
        >
          {isExpanded ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
        </button>
      </div>

      {isExpanded && (
        <>
          {/* Quick Prompts Bar */}
          <div className="px-4 py-2 bg-slate-50/70 dark:bg-slate-900/40 border-b border-slate-200/40 dark:border-slate-800/40 flex items-center gap-2 overflow-x-auto no-scrollbar">
            <span className="text-[10px] font-bold text-slate-400 shrink-0 uppercase tracking-wider flex items-center gap-1">
              <Sparkles size={12} className="text-amber-500" /> Prompts:
            </span>
            {sampleUtterances.map((sample, idx) => (
              <button
                key={idx}
                onClick={() => handleSendUtterance(sample)}
                disabled={loading}
                className="text-[11px] whitespace-nowrap px-2.5 py-1 rounded-lg bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 hover:border-brand-500 hover:text-brand-500 transition shadow-xs"
              >
                {sample}
              </button>
            ))}
          </div>

          {/* Messages History */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((m, idx) => (
              <div 
                key={idx} 
                className={`flex flex-col ${m.sender === 'user' ? 'items-end' : 'items-start'}`}
              >
                <div className={`flex items-start gap-2.5 max-w-[85%] ${m.sender === 'user' ? 'flex-row-reverse' : ''}`}>
                  <div className={`p-1.5 rounded-xl shrink-0 mt-0.5 ${
                    m.sender === 'user' 
                      ? 'bg-brand-500 text-white' 
                      : 'bg-cyan-500/20 text-cyan-600 dark:text-cyan-400'
                  }`}>
                    {m.sender === 'user' ? <Terminal size={14} /> : <Bot size={14} />}
                  </div>

                  <div>
                    <div className={`px-4 py-3 rounded-2xl text-xs leading-relaxed ${
                      m.sender === 'user'
                        ? 'bg-brand-500 text-white rounded-br-xs'
                        : 'bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-100 rounded-bl-xs border border-slate-200/50 dark:border-slate-700/50'
                    }`}>
                      {m.text}
                    </div>

                    {/* Alexa Visual Card (Multimodal Simulation) */}
                    {m.card && m.sender === 'alexa' && (
                      <div className="mt-2 p-3 bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800/80 shadow-xs text-xs">
                        <div className="flex items-center gap-1.5 font-bold text-slate-800 dark:text-white text-[11px] mb-1">
                          <CheckCircle2 size={13} className="text-emerald-500" />
                          {m.card.title}
                        </div>
                        <p className="text-slate-600 dark:text-slate-400 text-[11px]">
                          {m.card.text || m.card.content}
                        </p>
                        {m.simulation && (
                          <div className="mt-1.5 pt-1.5 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-[9px] text-slate-400">
                            <span>Mode: {m.simulation.mode}</span>
                            {m.simulation.action_executed && (
                              <span className="font-mono text-brand-500">
                                tool:{m.simulation.action_executed}
                              </span>
                            )}
                          </div>
                        )}

                        {/* What the assistant did panel */}
                        {m.simulation?.tool_traces && m.simulation.tool_traces.length > 0 && (
                          <div className="mt-2 pt-2 border-t border-slate-100 dark:border-slate-800">
                            <button
                              type="button"
                              onClick={() => setActiveTraceId(activeTraceId === idx ? null : idx)}
                              className="text-[10px] text-indigo-500 hover:text-indigo-600 font-medium flex items-center gap-1"
                            >
                              <Sparkles size={11} />
                              {activeTraceId === idx ? 'Hide Assistant Execution Trace' : 'What the assistant did (Trace)'}
                            </button>
                            {activeTraceId === idx && (
                              <div className="mt-1.5 p-2 bg-slate-950 text-slate-200 rounded-lg font-mono text-[9px] overflow-x-auto max-h-36">
                                {m.simulation.tool_traces.map((trace, tIdx) => (
                                  <div key={tIdx} className="mb-2 pb-1 border-b border-slate-800 last:border-none last:mb-0">
                                    <div className="text-emerald-400 font-bold">Tool: {trace.tool_name}</div>
                                    <div className="text-slate-400">Args: {JSON.stringify(trace.input)}</div>
                                    <div className="text-sky-300">Success: {String(trace.output?.success)}</div>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}

                    <span className="text-[9px] text-slate-400 mt-1 block px-1">
                      {m.timestamp}
                    </span>
                  </div>
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex items-center gap-2 text-slate-400 text-xs py-2 px-3 bg-slate-100/50 dark:bg-slate-800/50 rounded-xl w-fit">
                <div className="w-3.5 h-3.5 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
                <span>Alexa is thinking & executing tools...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Utterance Input Bar */}
          <form 
            onSubmit={(e) => { e.preventDefault(); handleSendUtterance(); }}
            className="p-3 bg-white dark:bg-slate-900 border-t border-slate-200/60 dark:border-slate-800/60 flex items-center gap-2"
          >
            <button
              type="button"
              onClick={() => setIsListening(!isListening)}
              className={`p-2.5 rounded-xl transition ${
                isListening 
                  ? 'bg-red-500 text-white animate-pulse' 
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-500 hover:text-slate-800 dark:hover:text-white'
              }`}
              title="Simulate Microphone Speech Input"
            >
              {isListening ? <MicOff size={18} /> : <Mic size={18} />}
            </button>

            <input
              type="text"
              value={inputUtterance}
              onChange={(e) => setInputUtterance(e.target.value)}
              placeholder="Type an utterance (e.g. 'Alexa, add task Lab Report due 2026-10-28')..."
              className="flex-1 px-4 py-2.5 text-xs bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-100 rounded-xl border border-slate-200 dark:border-slate-700 focus:outline-none focus:border-brand-500"
              disabled={loading}
            />

            <button
              type="submit"
              disabled={loading || !inputUtterance.trim()}
              className="p-2.5 bg-brand-500 hover:bg-brand-600 disabled:opacity-50 text-white rounded-xl transition shadow-md shadow-brand-500/20"
            >
              <Send size={18} />
            </button>
          </form>
        </>
      )}
    </div>
  );
};

export default AlexaSimulator;
