import React, { useEffect, useState } from 'react';
import logo from './logo.svg';
import './App.css';
import GmailBrowser from './GmailBrowser';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

function App() {
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showGmail, setShowGmail] = useState(false);

  // Helper to get JWT from localStorage
  const getJWT = () => localStorage.getItem('jwt');

  // On mount, check for JWT and fetch user
  useEffect(() => {
    const jwt = getJWT();
    if (!jwt) {
      setLoading(false);
      return;
    }
    fetch(`${API_URL}/users`, {
      headers: { Authorization: `Bearer ${jwt}` },
    })
      .then(async (res) => {
        if (res.status === 200) {
          const data = await res.json();
          if (data.users && data.users.length > 0) {
            setUser(data.users[0]);
          }
        } else {
          localStorage.removeItem('jwt');
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  // Listen for JWT from backend after OAuth
  useEffect(() => {
    // If redirected back with JWT in URL (after OAuth)
    const params = new URLSearchParams(window.location.search);
    const jwt = params.get('jwt');
    const userStr = params.get('user');
    if (jwt) {
      localStorage.setItem('jwt', jwt);
      if (userStr) {
        try {
          setUser(JSON.parse(decodeURIComponent(userStr)));
        } catch {}
      }
      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  const handleGoogleLogin = () => {
    window.location.href = `${API_URL}/login`;
  };

  const handleLogout = () => {
    localStorage.removeItem('jwt');
    setUser(null);
    window.location.href = `${API_URL}/logout`;
  };

  const handleShowGmail = () => {
    setShowGmail(true);
  };

  if (loading) return <div>Loading...</div>;

  if (!user) {
    return (
      <div className="App">
        <h1>AppTracker User Management</h1>
        <button onClick={handleGoogleLogin} style={{ fontSize: 18, padding: '10px 20px' }}>
          Sign in with Google
        </button>
      </div>
    );
  }

  if (showGmail) {
    return (
      <div className="App">
        <button onClick={handleLogout} style={{ float: 'right', fontSize: 16, padding: '8px 16px' }}>
          Logout
        </button>
        <GmailBrowser jwt={getJWT()} />
      </div>
    );
  }

  return (
    <div className="App">
      <h1>Welcome, {user.username}!</h1>
      <p>This is the landing page. You are logged in.</p>
      <button onClick={handleShowGmail} style={{ fontSize: 16, padding: '8px 16px', marginRight: 10 }}>
        Go to Gmail Message Browser
      </button>
      <button onClick={handleLogout} style={{ fontSize: 16, padding: '8px 16px' }}>
        Logout
      </button>
    </div>
  );
}

export default App;
