import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import { 
  ShieldAlert, 
  Search, 
  Database, 
  Settings, 
  Plus, 
  Edit3, 
  Trash2, 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  RefreshCw, 
  ChevronLeft, 
  ChevronRight,
  Info,
  Menu,
  MessageSquare,
  Send,
  LogOut,
  User,
  Mail,
  Lock,
  Key
} from 'lucide-react';

function App() {
  const [activeTab, setActiveTab] = useState(() => {
    const saved = localStorage.getItem('kizilelma_auth');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        return parsed.role === 'admin' ? 'admin' : 'analiz';
      } catch (e) {}
    }
    return 'analiz';
  });
  const [backendStatus, setBackendStatus] = useState({
    status: 'checking',
    records: 0,
    engine_version: '3.0.0-Elite',
    uptime: 'unknown',
    context_depth: 0,
    cache_status: 'checking',
    dynamic_records: 0
  });

  // Check Backend Status periodically
  const checkStatus = async () => {
    try {
      const res = await fetch('http://127.0.0.1:5000/api/status');
      if (res.ok) {
        const data = await res.json();
        setBackendStatus({
          status: 'online',
          records: data.records,
          engine_version: data.engine_version,
          uptime: data.uptime,
          context_depth: data.context_depth,
          cache_status: data.cache_status,
          dynamic_records: data.dynamic_records
        });
      } else {
        setBackendStatus(prev => ({ ...prev, status: 'offline', cache_status: 'disabled' }));
      }
    } catch (err) {
      setBackendStatus(prev => ({ ...prev, status: 'offline', cache_status: 'disabled' }));
    }
  };

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 15000);
    
    // Detect reload to bypass cache
    try {
      const navEntries = performance.getEntriesByType("navigation");
      if (navEntries.length > 0 && navEntries[0].type === "reload") {
        sessionStorage.setItem("kizilelma_bypass_cache_once", "true");
        console.log("⚡ Ctrl+F5 or reload detected, cache bypass armed.");
      }
    } catch (e) {
      console.warn("Navigation performance API not supported", e);
    }
    
    return () => clearInterval(interval);
  }, []);

  // ----------------------------------------------------
  // TAB 1: CONTINUOUS CHAT LOGIC (Gemini-like)
  // ----------------------------------------------------
  const [query, setQuery] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [messages, setMessages] = useState([]);
  const [chatHistory, setChatHistory] = useState([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const messagesEndRef = useRef(null);

  // Load chat history from localStorage on mount
  useEffect(() => {
    const savedHistory = localStorage.getItem('kizilelma_chat_history');
    if (savedHistory) {
      try {
        setChatHistory(JSON.parse(savedHistory));
      } catch (e) {
        console.error("Could not parse chat history", e);
      }
    }
  }, []);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const startNewChat = () => {
    if (messages.length > 0) {
      // Save current chat to history if not empty
      const title = messages[0].text.substring(0, 30) + "...";
      const newHistory = [{ id: Date.now(), title, messages }, ...chatHistory];
      setChatHistory(newHistory);
      localStorage.setItem('kizilelma_chat_history', JSON.stringify(newHistory));
    }
    setMessages([]);
  };

  const loadHistoryItem = (historyItem) => {
    setMessages(historyItem.messages);
  };

  const deleteHistoryItem = (e, id) => {
    e.stopPropagation();
    const newHistory = chatHistory.filter(item => item.id !== id);
    setChatHistory(newHistory);
    localStorage.setItem('kizilelma_chat_history', JSON.stringify(newHistory));
  };

  const handleSendMessage = async (e, forcedQuery = null) => {
    if (e) e.preventDefault();
    const activeQuery = forcedQuery || query;
    if (!activeQuery.trim()) return;
    
    const userText = activeQuery.trim();
    
    if (!forcedQuery) {
      const newUserMsg = { id: Date.now(), role: 'user', text: userText };
      setMessages(prev => [...prev, newUserMsg]);
      setQuery('');
    }
    
    setChatLoading(true);

    // Önbellek baypas kontrolü
    let forceRefresh = false;
    if (sessionStorage.getItem("kizilelma_bypass_cache_once") === "true") {
      forceRefresh = true;
      sessionStorage.removeItem("kizilelma_bypass_cache_once");
    }
    if (forcedQuery) {
      forceRefresh = true;
    }

    try {
      const res = await fetch('http://127.0.0.1:5000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query: userText,
          force_refresh: forceRefresh
        })
      });
      
      if (res.ok) {
        const data = await res.json();
        const newAiMsg = { id: Date.now() + 1, role: 'ai', result: data, originalQuery: userText };
        
        if (forcedQuery) {
          setMessages(prev => {
            const updated = [...prev];
            for (let i = updated.length - 1; i >= 0; i--) {
              if (updated[i].role === 'ai' && (updated[i].originalQuery === userText || updated[i].result?.source === data.source)) {
                updated[i] = newAiMsg;
                break;
              }
            }
            return updated;
          });
        } else {
          setMessages(prev => [...prev, newAiMsg]);
        }
        checkStatus(); // Refresh status
      } else {
        setMessages(prev => [...prev, { id: Date.now() + 1, role: 'error', text: 'Analiz sırasında sunucu hatası oluştu.' }]);
      }
    } catch (err) {
      setMessages(prev => [...prev, { id: Date.now() + 1, role: 'error', text: 'Sunucuya bağlanılamadı. Lütfen backend uygulamasının çalıştığından emin olun.' }]);
    } finally {
      setChatLoading(false);
    }
  };

  // Handle Enter key for textarea
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Helper to render SVGs for metrics inside chat
  const CircularProgress = ({ value, label, color }) => {
    const radius = 20;
    const circumference = 2 * Math.PI * radius;
    const strokeDashoffset = circumference - (value / 100) * circumference;

    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <svg width="50" height="50" style={{ transform: 'rotate(-90deg)' }}>
          <circle cx="25" cy="25" r={radius} fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="4" />
          <circle cx="25" cy="25" r={radius} fill="none" stroke={color} strokeWidth="4" strokeDasharray={circumference} strokeDashoffset={strokeDashoffset} style={{ transition: 'stroke-dashoffset 0.8s ease' }} />
        </svg>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{label}</span>
          <span style={{ fontWeight: 'bold' }}>%{value}</span>
        </div>
      </div>
    );
  };

  // ----------------------------------------------------
  // AUTHENTICATION LOGIC
  // ----------------------------------------------------
  const [auth, setAuth] = useState(() => {
    const saved = localStorage.getItem('kizilelma_auth');
    return saved ? JSON.parse(saved) : null;
  });
  
  const [authMode, setAuthMode] = useState('login'); // login, register, verify
  const [authForm, setAuthForm] = useState({ email: '', password: '', code: '', firstName: '', lastName: '' });
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState('');
  const [authSuccess, setAuthSuccess] = useState('');

  const logout = () => {
    setAuth(null);
    localStorage.removeItem('kizilelma_auth');
    setActiveTab('analiz');
  };

  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError('');
    setAuthSuccess('');

    try {
      let endpoint = '';
      let payload = {};

      if (authMode === 'login') {
        endpoint = '/api/auth/login';
        payload = { email: authForm.email, password: authForm.password };
      } else if (authMode === 'register') {
        endpoint = '/api/auth/register';
        payload = { email: authForm.email, password: authForm.password, first_name: authForm.firstName, last_name: authForm.lastName };
      } else if (authMode === 'verify') {
        endpoint = '/api/auth/verify';
        payload = { email: authForm.email, code: authForm.code };
      }

      const res = await fetch(`http://127.0.0.1:5000${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (res.ok) {
        if (authMode === 'login') {
          const authData = { token: data.access_token, role: data.role, email: authForm.email, firstName: data.first_name, lastName: data.last_name };
          setAuth(authData);
          localStorage.setItem('kizilelma_auth', JSON.stringify(authData));
          if (data.role === 'admin') setActiveTab('admin');
          else setActiveTab('analiz');
        } else if (authMode === 'register') {
          setAuthSuccess(data.message);
          setAuthMode('verify');
        } else if (authMode === 'verify') {
          setAuthSuccess(data.message);
          setAuthMode('login');
        }
      } else {
        setAuthError(data.detail || 'Bir hata oluştu.');
      }
    } catch (err) {
      setAuthError('Sunucuya bağlanılamadı.');
    } finally {
      setAuthLoading(false);
    }
  };

  const getAuthHeaders = () => {
    return auth ? { 'Authorization': `Bearer ${auth.token}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' };
  };

  // ----------------------------------------------------
  // TAB 2: ADMIN KNOWLEDGE BASE LOGIC
  // ----------------------------------------------------
  const [records, setRecords] = useState([]);
  const [recordsLoading, setRecordsLoading] = useState(false);
  const [recordsSearch, setRecordsSearch] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalRecords, setTotalRecords] = useState(0);
  const [adminSort, setAdminSort] = useState('newest');
  const limit = 50; // Increased limit for better pagination visibility

  const fetchRecords = async () => {
    if (activeTab !== 'admin') return;
    setRecordsLoading(true);
    try {
      const res = await fetch(`http://127.0.0.1:5000/api/veri?page=${page}&limit=${limit}&sort=${adminSort}`, {
        headers: getAuthHeaders()
      });
      if (res.ok) {
        const data = await res.json();
        setRecords(data.data);
        setTotalPages(data.total_pages);
        setTotalRecords(data.total);
      }
    } catch (err) {
      console.error("Failed to fetch records:", err);
    } finally {
      setRecordsLoading(false);
    }
  };

  useEffect(() => {
    fetchRecords();
  }, [activeTab, page, adminSort]);

  // Search filter locally for better responsiveness
  const filteredRecords = records.filter(r => 
    r.text.toLowerCase().includes(recordsSearch.toLowerCase())
  );

  // CRUD State and handlers
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState(null);

  // Form inputs
  const [formText, setFormText] = useState('');
  const [formLabel, setFormLabel] = useState(1);
  const [formAuthority, setFormAuthority] = useState(0.85);
  const [crudLoading, setCrudLoading] = useState(false);

  const openEditModal = (rec) => {
    setSelectedRecord(rec);
    setFormText(rec.text);
    setFormLabel(rec.label);
    setFormAuthority(rec.authority);
    setShowEditModal(true);
  };

  const handleAddSubmit = async (e) => {
    e.preventDefault();
    setCrudLoading(true);
    try {
      const res = await fetch('http://127.0.0.1:5000/api/inject', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          text: formText,
          label: parseInt(formLabel),
          authority: parseFloat(formAuthority)
        })
      });
      if (res.ok) {
        setShowAddModal(false);
        setFormText('');
        setFormLabel(1);
        setFormAuthority(0.85);
        fetchRecords();
        checkStatus();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setCrudLoading(false);
    }
  };

  const handleEditSubmit = async (e) => {
    e.preventDefault();
    setCrudLoading(true);
    try {
      const res = await fetch(`http://127.0.0.1:5000/api/admin/veri/${selectedRecord.id}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          text: formText,
          label: parseInt(formLabel),
          authority: parseFloat(formAuthority)
        })
      });
      if (res.ok) {
        setShowEditModal(false);
        setSelectedRecord(null);
        setFormText('');
        fetchRecords();
        checkStatus();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setCrudLoading(false);
    }
  };

  const handleDelete = async (recordId) => {
    if (!window.confirm("Bu kaydı veritabanından kalıcı olarak silmek istediğinizden emin misiniz?")) return;
    try {
      const res = await fetch(`http://127.0.0.1:5000/api/admin/veri/${recordId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });
      if (res.ok) {
        fetchRecords();
        checkStatus();
      }
    } catch (err) {
      console.error(err);
    }
  };

  if (!auth) {
    return (
      <div className="app-layout" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: 'var(--bg-main)' }}>
        <div className="auth-container" style={{ width: '100%', maxWidth: '450px', padding: '2.5rem', background: 'var(--bg-card)', borderRadius: '16px', border: '1px solid var(--border-color)', boxShadow: 'var(--shadow-main)', transition: 'all 0.3s ease' }}>
          <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
            <img src="/logo.png" alt="KızılelmAI Logo" style={{ width: '120px', height: 'auto', marginBottom: '1rem', borderRadius: '50%' }} />
            <h2 style={{ fontSize: '1.75rem', marginBottom: '0.5rem', fontWeight: 'bold' }}>
              {authMode === 'login' ? "KızılelmAI'ye Giriş Yapın" : authMode === 'register' ? "Yeni Hesap Oluşturun" : "Hesabınızı Doğrulayın"}
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
              {authMode === 'login' ? "Sistemi kullanmak için lütfen kimliğinizi doğrulayın." : authMode === 'register' ? "Bilgilerinizi eksiksiz doldurunuz." : "Mailinize gelen 6 haneli kodu giriniz."}
            </p>
          </div>
          
          <form onSubmit={handleAuthSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {authMode === 'register' && (
              <div style={{ display: 'flex', gap: '1rem' }}>
                <div className="form-group" style={{ flex: 1 }}>
                  <label>İsim</label>
                  <input type="text" className="form-input" required value={authForm.firstName} onChange={e => setAuthForm({...authForm, firstName: e.target.value})} />
                </div>
                <div className="form-group" style={{ flex: 1 }}>
                  <label>Soyisim</label>
                  <input type="text" className="form-input" required value={authForm.lastName} onChange={e => setAuthForm({...authForm, lastName: e.target.value})} />
                </div>
              </div>
            )}

            <div className="form-group">
              <label><Mail size={14} style={{ display: 'inline', marginRight: '5px' }} /> Email Adresi / Kullanıcı Adı</label>
              <input type="text" className="form-input" required value={authForm.email} onChange={e => setAuthForm({...authForm, email: e.target.value})} />
            </div>
            
            {authMode !== 'verify' && (
              <div className="form-group">
                <label><Key size={14} style={{ display: 'inline', marginRight: '5px' }} /> Şifre</label>
                <input type="password" className="form-input" required minLength="4" value={authForm.password} onChange={e => setAuthForm({...authForm, password: e.target.value})} />
              </div>
            )}

            {authMode === 'verify' && (
              <div className="form-group">
                <label>6 Haneli Doğrulama Kodu</label>
                <input type="text" className="form-input" required maxLength="6" placeholder="Örn: 123456" value={authForm.code} onChange={e => setAuthForm({...authForm, code: e.target.value})} />
              </div>
            )}

            {authError && <div style={{ color: 'var(--color-fake)', fontSize: '0.85rem', padding: '0.75rem', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.2)' }}>{authError}</div>}
            {authSuccess && <div style={{ color: 'var(--color-real)', fontSize: '0.85rem', padding: '0.75rem', background: 'rgba(16, 185, 129, 0.1)', borderRadius: '8px', border: '1px solid rgba(16, 185, 129, 0.2)' }}>{authSuccess}</div>}

            <button type="submit" className="admin-action-btn" disabled={authLoading} style={{ width: '100%', justifyContent: 'center', marginTop: '1rem', padding: '0.75rem', fontSize: '1rem', fontWeight: 'bold' }}>
              {authLoading ? <div className="spinner" /> : (authMode === 'login' ? 'Giriş Yap' : authMode === 'register' ? 'Kayıt Ol' : 'Kodu Onayla')}
            </button>
          </form>

          <div style={{ textAlign: 'center', marginTop: '1.5rem', fontSize: '0.95rem' }}>
            {authMode === 'login' ? (
              <span style={{ color: 'var(--text-secondary)' }}>Hesabınız yok mu? <a href="#" onClick={(e) => { e.preventDefault(); setAuthMode('register'); setAuthError(''); setAuthSuccess(''); }} style={{ color: 'var(--accent-orange)', fontWeight: 'bold' }}>Kayıt Ol</a></span>
            ) : authMode === 'register' ? (
              <span style={{ color: 'var(--text-secondary)' }}>Zaten hesabınız var mı? <a href="#" onClick={(e) => { e.preventDefault(); setAuthMode('login'); setAuthError(''); setAuthSuccess(''); }} style={{ color: 'var(--accent-orange)', fontWeight: 'bold' }}>Giriş Yap</a></span>
            ) : (
              <span style={{ color: 'var(--text-secondary)' }}><a href="#" onClick={(e) => { e.preventDefault(); setAuthMode('login'); setAuthError(''); setAuthSuccess(''); }} style={{ color: 'var(--accent-orange)', fontWeight: 'bold' }}>Giriş Ekranına Dön</a></span>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-layout">
      {/* SIDEBAR */}
      <aside className={`sidebar ${!sidebarOpen ? 'closed' : ''}`}>
        <div className="sidebar-header">
          <button className="menu-toggle" onClick={() => setSidebarOpen(false)}>
            <Menu size={24} />
          </button>
          <img src="/logo.png" alt="Logo" style={{ width: '40px', height: '40px', borderRadius: '50%', objectFit: 'cover' }} />
        </div>
        
        <div style={{ padding: '1rem' }}>
          <button className="new-chat-btn" onClick={startNewChat}>
            <Plus size={18} /> Yeni Doğrulama
          </button>
        </div>

        <div className="chat-history-list">
          <div style={{ padding: '0 1rem', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.5rem', fontWeight: '600' }}>Geçmiş Sorgular</div>
          {chatHistory.map(item => (
            <div key={item.id} className="history-item" onClick={() => loadHistoryItem(item)}>
              <MessageSquare size={16} />
              <span style={{ flex: 1 }}>{item.title}</span>
              <button 
                className="action-icon-btn delete" 
                style={{ padding: '4px', background: 'transparent' }}
                onClick={(e) => deleteHistoryItem(e, item.id)}
              >
                <Trash2 size={14} color="var(--text-muted)" />
              </button>
            </div>
          ))}
          {chatHistory.length === 0 && (
            <div style={{ padding: '1rem', color: 'var(--text-muted)', fontSize: '0.85rem', textAlign: 'center' }}>
              Henüz geçmiş bulunmuyor.
            </div>
          )}
        </div>
      </aside>

      {/* MAIN CONTENT */}
      <main className="main-content">
        {/* TOP NAVIGATION (Tabs) */}
        <header className="top-nav">
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            {!sidebarOpen && (
              <button className="menu-toggle" onClick={() => setSidebarOpen(true)}>
                <Menu size={24} />
              </button>
            )}
            <div className="logo-text">
              <h1 style={{ fontSize: '1.2rem' }}>KızılelmAI</h1>
            </div>
          </div>

          <nav className="nav-tabs">
            {auth.role !== 'admin' && (
              <>
                <button className={`tab-btn ${activeTab === 'analiz' ? 'active' : ''}`} onClick={() => setActiveTab('analiz')}>
                  <ShieldAlert size={16} /> Doğrulama Modu
                </button>
                <button className={`tab-btn ${activeTab === 'status' ? 'active' : ''}`} onClick={() => setActiveTab('status')}>
                  <Settings size={16} /> Sistem Durumu
                </button>
              </>
            )}
            {auth.role === 'admin' && (
              <button className={`tab-btn ${activeTab === 'admin' ? 'active' : ''}`} onClick={() => setActiveTab('admin')}>
                <Database size={16} /> Yönetim Paneli
              </button>
            )}
          </nav>

          {auth && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', color: 'var(--text-secondary)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <User size={16} color="var(--accent-orange)" />
                <span style={{ fontSize: '0.95rem', fontWeight: '500' }}>
                  {auth.firstName ? `Merhaba ${auth.firstName} ${auth.lastName}` : auth.email}
                </span>
                <span style={{ fontSize: '0.7rem', background: 'var(--accent-orange)', color: '#000', padding: '2px 6px', borderRadius: '10px', fontWeight: 'bold' }}>{auth.role}</span>
              </div>
              <button onClick={logout} className="action-icon-btn delete" title="Çıkış Yap">
                <LogOut size={18} />
              </button>
            </div>
          )}
        </header>

        {/* TAB 1: NEWS ANALYSIS (Chat UI) */}
        {activeTab === 'analiz' && (
          <>
            {messages.length === 0 ? (
              <div className="empty-state">
                <img src="/logo.png" alt="KızılelmAI Logo" style={{ width: '80px', height: '80px', borderRadius: '50%', objectFit: 'cover', marginBottom: '1.5rem', boxShadow: 'var(--shadow-neon)' }} />
                <h2 className="empty-title">Neyi doğrulamak istersiniz?</h2>
                <p className="empty-subtitle">KızılelmAI, haberleri ve iddiaları resmi ve güvenilir kaynaklardan saniyeler içinde teyit eder.</p>
              </div>
            ) : (
              <div className="chat-container">
                {messages.map((msg) => (
                  <div key={msg.id} className={`message-wrapper ${msg.role}`}>
                    <div className="message-avatar">
                      {msg.role === 'user' ? 'S' : <img src="/logo.png" alt="Bot" style={{ width: '100%', height: '100%', borderRadius: '50%', objectFit: 'cover' }} />}
                    </div>
                    {msg.role === 'user' ? (
                      <div className="message-bubble">{msg.text}</div>
                    ) : msg.role === 'error' ? (
                      <div className="message-bubble" style={{ color: 'var(--color-fake)' }}>{msg.text}</div>
                    ) : (
                      <div className="message-bubble" style={{ position: 'relative' }}>
                        {msg.originalQuery && (
                          <button 
                            onClick={() => handleSendMessage(null, msg.originalQuery)}
                            className="action-icon-btn refresh"
                            style={{ 
                              position: 'absolute', 
                              top: '12px', 
                              right: '12px', 
                              background: 'transparent',
                              border: 'none',
                              color: 'var(--text-muted)',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px',
                              fontSize: '0.8rem'
                            }}
                            title="Önbelleği temizle ve yeniden sorgula"
                          >
                            <RefreshCw size={12} className={chatLoading ? 'spin' : ''} />
                            <span>Yenile</span>
                          </button>
                        )}
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', fontWeight: 'bold' }}>
                          {msg.result.status === 'ONAY' && <CheckCircle size={20} color="var(--color-real)" />}
                          {msg.result.status === 'RED' && <XCircle size={20} color="var(--color-fake)" />}
                          {msg.result.status === 'UYARI' && <AlertTriangle size={20} color="var(--color-fake)" />}
                          {msg.result.status === 'KISMI' && <Info size={20} color="var(--color-partial)" />}
                          {msg.result.status === 'RET' && <Info size={20} color="var(--color-info)" />}
                          <span style={{ 
                            color: msg.result.status === 'ONAY' ? 'var(--color-real)' : 
                                   msg.result.status === 'KISMI' ? 'var(--color-partial)' : 
                                   msg.result.status === 'RET' ? 'var(--color-info)' : 'var(--color-fake)'
                          }}>
                            {msg.result.msg}
                          </span>
                        </div>
                        <div style={{ marginBottom: '1.5rem', lineHeight: '1.6' }}>
                          {msg.result.description}
                        </div>
                        
                        {msg.result.status !== 'RET' && (
                          <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '12px', border: '1px solid var(--border-color)', marginBottom: '1rem' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
                              <span>Vektörel Kaynak Eşleşmesi</span>
                              <span style={{ color: 'var(--accent-orange)', fontWeight: 'bold' }}>{msg.result.source_channel || 'Doğrulanmış Kaynak'}</span>
                            </div>
                            <div style={{ fontStyle: 'italic', color: 'var(--text-secondary)' }}>"{msg.result.source}"</div>
                          </div>
                        )}

                        <div style={{ display: 'flex', gap: '2rem', marginTop: '1rem', borderTop: '1px solid var(--border-color)', paddingTop: '1rem' }}>
                           <CircularProgress 
                            value={msg.result.confidence} 
                            label="Güven" 
                            color={msg.result.status === 'ONAY' ? 'var(--color-real)' : msg.result.status === 'KISMI' ? 'var(--color-partial)' : msg.result.status === 'RET' ? 'var(--color-info)' : 'var(--color-fake)'} 
                          />
                          <CircularProgress 
                            value={msg.result.risk} 
                            label="Risk" 
                            color={msg.result.risk > 70 ? 'var(--color-fake)' : msg.result.risk > 40 ? 'var(--color-partial)' : 'var(--color-real)'} 
                          />
                        </div>
                      </div>
                    )}
                  </div>
                ))}
                {chatLoading && (
                  <div className="message-wrapper ai">
                     <div className="message-avatar">
                        <img src="/logo.png" alt="Bot" style={{ width: '100%', height: '100%', borderRadius: '50%', objectFit: 'cover' }} />
                     </div>
                     <div className="message-bubble">
                        <div className="spinner" style={{ width: '20px', height: '20px', borderColor: 'var(--accent-orange) transparent transparent transparent' }} />
                     </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            )}
            
            <div className="input-area">
              <div className="chat-input-wrapper">
                <textarea 
                  className="chat-input"
                  placeholder="Doğrulamak istediğiniz haberi veya iddiayı buraya yazın..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  rows={1}
                />
                <button 
                  className="chat-submit-btn" 
                  onClick={handleSendMessage}
                  disabled={!query.trim() || chatLoading}
                >
                  <Send size={18} />
                </button>
              </div>
              <div style={{ textAlign: 'center', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.75rem' }}>
                KızılelmAI resmi kaynaklardan doğrulama yapar. Kritik kararlar almadan önce kontrol ediniz.
              </div>
            </div>
          </>
        )}

        {/* TAB 2: ADMIN PANEL */}
        {activeTab === 'admin' && (
          <div className="glass-card" style={{ margin: '2rem', display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
            
            {auth.role !== 'admin' ? (
              <div className="empty-state">
                <AlertTriangle size={64} color="var(--color-fake)" />
                <h2 className="empty-title">Yetkisiz Erişim</h2>
                <p className="empty-subtitle">Sadece yetkili yöneticiler bu alana erişebilir.</p>
              </div>
            ) : (
              <>
                <div className="admin-header">
              <div className="admin-search-box">
                <Search size={18} style={{ position: 'absolute', left: '12px', top: '10px', color: 'var(--text-secondary)' }} />
                <input 
                  type="text" 
                  className="search-input" 
                  placeholder="Kayıtlar içinde yerel arama..." 
                  value={recordsSearch}
                  onChange={(e) => setRecordsSearch(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginLeft: 'auto', marginRight: '1rem' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Sıralama:</span>
                <select 
                  className="form-input" 
                  style={{ width: 'auto', padding: '0.4rem 1rem' }}
                  value={adminSort}
                  onChange={(e) => { setAdminSort(e.target.value); setPage(1); }}
                >
                  <option value="newest">En Yeniler</option>
                  <option value="oldest">En Eskiler (ID)</option>
                </select>
              </div>

              <button className="admin-action-btn" onClick={() => setShowAddModal(true)}>
                <Plus size={18} /> Yeni Bilgi Aşıla
              </button>
            </div>

            {recordsLoading ? (
              <div className="loader-container">
                <div className="spinner" style={{ width: '40px', height: '40px' }} />
                <span>Kayıtlar veritabanından yükleniyor...</span>
              </div>
            ) : (
              <>
                <div className="table-wrapper" style={{ overflowY: 'auto', flex: 1, minHeight: '400px', borderBottom: '1px solid var(--border-color)', marginBottom: '1rem' }}>
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th style={{ width: '80px' }}>ID</th>
                        <th>Haber Bilgisi / Referans Metin</th>
                        <th style={{ width: '130px' }}>Güvenilirlik</th>
                        <th style={{ width: '130px' }}>Kaynak Otoritesi</th>
                        <th style={{ width: '100px' }}>İşlemler</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredRecords.map((rec) => (
                        <tr key={rec.id}>
                          <td>#{rec.id}</td>
                          <td title={rec.text}>{rec.text}</td>
                          <td>
                            <span className={`table-badge ${rec.label === 1 ? 'real' : 'fake'}`}>
                              {rec.label === 1 ? 'Gerçek (REAL)' : 'Yalan (FAKE)'}
                            </span>
                          </td>
                          <td>%{Math.round(rec.authority * 100)}</td>
                          <td>
                            <div className="actions-cell">
                              <button className="action-icon-btn edit" onClick={() => openEditModal(rec)} title="Düzenle">
                                <Edit3 size={16} />
                              </button>
                              <button className="action-icon-btn delete" onClick={() => handleDelete(rec.id)} title="Kalıcı Sil">
                                <Trash2 size={16} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                      {filteredRecords.length === 0 && (
                        <tr>
                          <td colSpan="5" style={{ textAlignment: 'center', color: 'var(--text-secondary)', padding: '2rem' }}>
                            Arama kriterine uygun veya kayıtlı herhangi bir veri bulunamadı.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>

                <div className="pagination">
                  <span className="pagination-info">
                    Toplam <strong>{totalRecords}</strong> kayıttan <strong>{filteredRecords.length}</strong> tanesi listeleniyor
                  </span>

                  <div className="pagination-controls" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <button 
                      className="pag-btn" 
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page === 1}
                    >
                      <ChevronLeft size={18} />
                    </button>
                    <span className="page-num">{page} / {totalPages}</span>
                    <button 
                      className="pag-btn" 
                      onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                    >
                      <ChevronRight size={18} />
                    </button>
                    
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginLeft: '1rem', borderLeft: '1px solid var(--border-color)', paddingLeft: '1rem' }}>
                      <input 
                        type="number" 
                        min="1" 
                        max={totalPages}
                        className="form-input" 
                        style={{ width: '60px', padding: '0.2rem 0.5rem', textAlign: 'center' }} 
                        placeholder="Git"
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            const val = parseInt(e.target.value);
                            if (val >= 1 && val <= totalPages) {
                              setPage(val);
                              e.target.value = '';
                            }
                          }
                        }}
                      />
                    </div>

                    <button className="pag-btn" onClick={fetchRecords} title="Yenile" style={{ marginLeft: '0.5rem' }}>
                      <RefreshCw size={16} />
                    </button>
                  </div>
                </div>
              </>
            )}
          </>
        )}
      </div>
    )}

        {/* TAB 3: SYSTEM STATUS */}
        {activeTab === 'status' && (
          <div className="analysis-panel" style={{ margin: '2rem' }}>
            <div className="glass-card status-grid">
              
              <div className="glass-card status-card">
                <div className="status-icon-wrapper">
                  <Database size={24} />
                </div>
                <div className="status-info">
                  <span className="status-label">Toplam Veri Kaydı</span>
                  <span className="status-value">{backendStatus.records} satır</span>
                </div>
              </div>

              <div className="glass-card status-card">
                <div className="status-icon-wrapper">
                  <RefreshCw size={24} />
                </div>
                <div className="status-info">
                  <span className="status-label">Dinamik Aşılanan Veri</span>
                  <span className="status-value">{backendStatus.dynamic_records} satır</span>
                </div>
              </div>

              <div className="glass-card status-card">
                <div className="status-icon-wrapper">
                  <ShieldAlert size={24} />
                </div>
                <div className="status-info">
                  <span className="status-label">Önbellek (Redis Cache)</span>
                  <span className="status-value" style={{ color: backendStatus.cache_status === 'active' ? 'var(--color-real)' : 'var(--text-secondary)' }}>
                    {backendStatus.cache_status === 'active' ? 'AKTİF' : 'DEVRE DIŞI'}
                  </span>
                </div>
              </div>

              <div className="glass-card status-card">
                <div className="status-icon-wrapper">
                  <Settings size={24} />
                </div>
                <div className="status-info">
                  <span className="status-label">Analiz Motor Sürümü</span>
                  <span className="status-value">{backendStatus.engine_version}</span>
                </div>
              </div>

            </div>

            <div className="glass-card">
              <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '1rem' }}>Katman 1-10 Entegrasyon Raporu</h3>
              <p style={{ lineHeight: '1.6', color: 'var(--text-secondary)' }}>
                KızılelmAI analiz motoru, gelen iddiaları PostgreSQL ve Redis katmanları üzerinden süzgeçten geçirmektedir. 
                Vektörel arama (pgvector) ve anahtar kelime eşleşmesi (BM25) hibrit olarak çalışmakta, Sniper re-ranker 
                modeli en uygun kaynakları belirlemektedir. Niyet analizi, akıllı fark analizi (tarih, sayı, unvan farkları) 
                ve çok kaynaklı konsensüs kontrolleri FastAPI arka plan servisleri tarafından asenkron olarak işletilmektedir.
              </p>
            </div>
          </div>
        )}

      </main>

      {/* MODALS */}
      {/* 1. ADD FACT MODAL */}
      {showAddModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Yeni Bilgi Aşılama (Katman 10)</h3>
              <button className="modal-close-btn" onClick={() => setShowAddModal(false)}>×</button>
            </div>
            <form onSubmit={handleAddSubmit}>
              <div className="modal-body">
                <div className="form-group">
                  <label>Haber / Doğrulanmış Cümle Metni</label>
                  <textarea 
                    className="form-textarea" 
                    placeholder="Örn: Vali deprem bölgesinde incelemelerde bulundu ve hasar tespit çalışmalarını başlattı."
                    required
                    value={formText}
                    onChange={(e) => setFormText(e.target.value)}
                  />
                </div>
                
                <div className="form-group">
                  <label>Güvenilirlik Durumu (Label)</label>
                  <select className="form-select" value={formLabel} onChange={(e) => setFormLabel(e.target.value)}>
                    <option value={1}>Gerçek Bilgi (REAL)</option>
                    <option value={0}>Yalan / Asılsız İddia (FAKE)</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Kaynak Güvenilirlik Derecesi (Authority: 0.0 - 1.0)</label>
                  <input 
                    type="number" 
                    step="0.01" 
                    min="0" 
                    max="1" 
                    className="form-input" 
                    required
                    value={formAuthority}
                    onChange={(e) => setFormAuthority(e.target.value)}
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={() => setShowAddModal(false)}>İptal</button>
                <button type="submit" className="admin-action-btn" disabled={crudLoading}>
                  {crudLoading ? <div className="spinner" /> : 'Aşıla'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 2. EDIT FACT MODAL */}
      {showEditModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Bilgi Düzenleme (#{selectedRecord?.id})</h3>
              <button className="modal-close-btn" onClick={() => setShowEditModal(false)}>×</button>
            </div>
            <form onSubmit={handleEditSubmit}>
              <div className="modal-body">
                <div className="form-group">
                  <label>Haber / Cümle Metni</label>
                  <textarea 
                    className="form-textarea" 
                    required
                    value={formText}
                    onChange={(e) => setFormText(e.target.value)}
                  />
                </div>
                
                <div className="form-group">
                  <label>Güvenilirlik Durumu</label>
                  <select className="form-select" value={formLabel} onChange={(e) => setFormLabel(e.target.value)}>
                    <option value={1}>Gerçek Bilgi (REAL)</option>
                    <option value={0}>Yalan / Asılsız İddia (FAKE)</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Kaynak Güvenilirlik Derecesi (0.0 - 1.0)</label>
                  <input 
                    type="number" 
                    step="0.01" 
                    min="0" 
                    max="1" 
                    className="form-input" 
                    required
                    value={formAuthority}
                    onChange={(e) => setFormAuthority(e.target.value)}
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={() => setShowEditModal(false)}>İptal</button>
                <button type="submit" className="admin-action-btn" disabled={crudLoading}>
                  {crudLoading ? <div className="spinner" /> : 'Güncelle'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}

export default App;
