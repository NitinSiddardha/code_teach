import React, { useState, useEffect } from 'react';
import Editor from 'react-simple-code-editor';
import { highlight, languages } from 'prismjs';
import 'prismjs/components/prism-python';
import 'prismjs/themes/prism-tomorrow.css';
import { 
  Zap, 
  Terminal, 
  BookOpen, 
  Trophy, 
  ChevronRight, 
  Send, 
  AlertCircle,
  HelpCircle,
  TrendingDown,
  TrendingUp,
  RotateCcw
} from 'lucide-react';

const API_BASE = "http://localhost:8000/api";

function App() {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(false);
  const [code, setCode] = useState("");
  const [topic, setTopic] = useState("Python Variables");
  const [level, setLevel] = useState("beginner");
  const [responses, setResponses] = useState([]);
  const [profile, setProfile] = useState({
    total_tasks: 0,
    confidence_streak: 0,
    mastered_concepts: []
  });

  // Start Session
  const initSession = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/session/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic, level })
      });
      const data = await res.json();
      setResponses([data]);
      if (data.starter_code) setCode(data.starter_code);
      setSession(true);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Submit Code
  const handleSubmit = async () => {
    if (!code.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/session/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code })
      });
      const data = await res.json();
      setResponses(prev => [...prev, data]);
      if (data.starter_code) setCode(data.starter_code);
      
      // Rough profile update from response
      if (data.profile) setProfile(data.profile);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Send Signal
  const handleSignal = async (signal, detail = null) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/session/signal`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ signal, detail })
      });
      const data = await res.json();
      setResponses(prev => [...prev, data]);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const lastResponse = responses[responses.length - 1];

  if (!session) {
    return (
      <div className="app-container" style={{justifyContent: 'center', alignItems: 'center'}}>
        <div className="glass-card" style={{maxWidth: '500px', width: '100%', textAlign: 'center'}}>
          <Zap size={48} color="var(--accent-primary)" style={{marginBottom: '20px'}}/>
          <h1 style={{marginBottom: '10px'}}>code.teach Premium</h1>
          <p style={{color: 'var(--text-dim)', marginBottom: '30px'}}>Your AI-powered coding journey starts here.</p>
          
          <div style={{textAlign: 'left', marginBottom: '20px'}}>
            <label className="stat-label">Topic</label>
            <input 
              className="glass-card" 
              style={{width: '100%', marginTop: '5px', padding: '12px', background: 'rgba(255,255,255,0.05)'}}
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
            />
          </div>

          <div style={{textAlign: 'left', marginBottom: '30px'}}>
            <label className="stat-label">Level</label>
            <select 
              className="glass-card" 
              style={{width: '100%', marginTop: '5px', padding: '12px', background: 'rgba(255,255,255,0.05)'}}
              value={level}
              onChange={(e) => setLevel(e.target.value)}
            >
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </div>

          <button className="btn-primary" onClick={initSession} disabled={loading}>
            {loading ? "Preparing Lesson..." : "Begin Learning"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      <header>
        <div className="logo"><Terminal size={24} style={{display:'inline', marginRight:'10px', verticalAlign:'middle'}}/> code.teach</div>
        <div style={{display:'flex', gap: '20px'}}>
          <div className="stat-item" style={{alignItems:'flex-end'}}>
            <span className="stat-value"><Trophy size={16} /> {profile.confidence_streak}</span>
            <span className="stat-label">Streak</span>
          </div>
          <div className="stat-item" style={{alignItems:'flex-end'}}>
            <span className="stat-value">{profile.total_tasks}</span>
            <span className="stat-label">Tasks</span>
          </div>
        </div>
      </header>

      <div className="layout">
        <aside className="sidebar">
          <div className="glass-card chat-bubbles" style={{flexGrow: 1, overflowY: 'auto'}}>
            {responses.map((res, i) => (
              <div key={i} className="bubble teacher">
                {res.message}
                {res.mode && <div style={{marginTop: '10px'}}><span className={`badge badge-${res.mode}`}>{res.mode}</span></div>}
              </div>
            ))}
            {loading && <div className="stat-label">Teacher is thinking...</div>}
          </div>
          
          <div className="glass-card">
            <h4 style={{marginBottom:'15px', display:'flex', alignItems:'center', gap:'8px'}}><AlertCircle size={16}/> Signals</h4>
            <div style={{display:'grid', gridTemplateColumns: '1fr 1fr', gap: '8px'}}>
              <button className="btn-signal" onClick={() => handleSignal("too_hard")}><TrendingDown size={14}/> Too Hard</button>
              <button className="btn-signal" onClick={() => handleSignal("too_easy")}><TrendingUp size={14}/> Too Easy</button>
              <button className="btn-signal" onClick={() => handleSignal("lost_concept")}><HelpCircle size={14}/> Lost</button>
              <button className="btn-signal" onClick={() => handleSignal("more_practice")}><RotateCcw size={14}/> Practice</button>
            </div>
          </div>
        </aside>

        <main className="main-content">
          {lastResponse && lastResponse.task && (
            <div className="bubble task">
              <h3 style={{marginBottom:'10px', color: 'var(--accent-primary)'}}>Current Task</h3>
              <p>{lastResponse.task}</p>
              {lastResponse.concept_tested && (
                <div style={{marginTop:'15px', fontSize:'0.75rem', color:'var(--text-dim)'}}>
                  Concept: <strong>{lastResponse.concept_tested}</strong>
                </div>
              )}
            </div>
          )}

          <div className="editor-wrapper">
            <div className="editor-header">
              <span>main.py</span>
              <span style={{color: 'var(--text-dim)'}}>Python 3.12</span>
            </div>
            <div className="editor-inner">
              <Editor
                value={code}
                onValueChange={code => setCode(code)}
                highlight={code => highlight(code, languages.python)}
                padding={20}
                className="code-editor-content"
                style={{
                  fontFamily: '"Fira Code", "Fira Mono", monospace',
                  fontSize: 14,
                  minHeight: '400px',
                  color: '#e6edf3'
                }}
              />
            </div>
            <div className="editor-footer">
              <button className="btn-primary" onClick={handleSubmit} disabled={loading}>
                {loading ? "Evaluating..." : <><Send size={16} /> Submit Code</>}
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
