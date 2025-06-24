import React, { useEffect, useState } from 'react';

interface GmailBrowserProps {
  jwt: string | null;
}

interface GmailMessage {
  id: string;
  snippet?: string;
  payload?: any;
  internalDate?: string;
}

interface GmailListMessagesResponse {
  messages: GmailMessage[];
  nextPageToken?: string;
  resultSizeEstimate?: number;
}

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

const getHeader = (payload: any, name: string) => {
  if (!payload || !payload.headers) return '';
  const header = payload.headers.find((h: any) => h.name.toLowerCase() === name.toLowerCase());
  return header ? header.value : '';
};

const formatDate = (internalDate?: string) => {
  if (!internalDate) return '';
  const date = new Date(Number(internalDate));
  return date.toLocaleString();
};

const palette = {
  emerald: '#23ce6b',
  gunmetal: '#272d2d',
  ghostWhite: '#f6f8ff',
  purpureus: '#a846a0',
  davysGray: '#50514f',
};

const GmailBrowser: React.FC<GmailBrowserProps> = ({ jwt }) => {
  const [messages, setMessages] = useState<GmailMessage[]>([]);
  const [nextPageToken, setNextPageToken] = useState<string | undefined>(undefined);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<GmailMessage | null>(null);
  const [pageTokens, setPageTokens] = useState<string[]>([]);
  const [search, setSearch] = useState('');
  const [searching, setSearching] = useState(false);
  const [searchActive, setSearchActive] = useState(false);

  const fetchMessages = (pageToken?: string, searchQuery?: string) => {
    setLoading(true);
    setError(null);
    let url = `${API_URL}/api/gmail/messages?maxResults=10`;
    if (pageToken) url += `&pageToken=${pageToken}`;
    if (searchQuery) url += `&q=${encodeURIComponent(searchQuery)}`;
    fetch(url, {
      headers: { Authorization: `Bearer ${jwt}` },
    })
      .then(async (res) => {
        if (res.status === 200) {
          const data: GmailListMessagesResponse = await res.json();
          setMessages(data.messages || []);
          setNextPageToken(data.nextPageToken);
        } else {
          setError('Failed to fetch messages');
        }
        setLoading(false);
      })
      .catch(() => {
        setError('Failed to fetch messages');
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchMessages();
    setPageTokens(['']);
    setSearch('');
    setSearchActive(false);
  }, [jwt]);

  const handleNext = () => {
    if (nextPageToken) {
      fetchMessages(nextPageToken, searchActive ? search : undefined);
      setPageTokens((prev) => [...prev, nextPageToken]);
    }
  };
  const handlePrev = () => {
    if (pageTokens.length > 1) {
      const prevTokens = [...pageTokens];
      prevTokens.pop();
      const prevToken = prevTokens[prevTokens.length - 1];
      fetchMessages(prevToken, searchActive ? search : undefined);
      setPageTokens(prevTokens);
    }
  };

  const handleSearch = () => {
    if (!search.trim()) {
      handleClear();
      return;
    }
    setSearchActive(true);
    setPageTokens(['']);
    fetchMessages(undefined, search);
  };

  const handleClear = () => {
    setSearch('');
    setSearchActive(false);
    setPageTokens(['']);
    fetchMessages();
  };

  const getSender = (payload: any) => {
    const from = getHeader(payload, 'From');
    if (!from) return { name: '', email: '' };
    const match = from.match(/^(.*?)(?:\s*<(.+?)>)?$/);
    if (match) {
      return {
        name: match[2] ? match[1].replace(/"/g, '').trim() : '',
        email: match[2] || match[1]
      };
    }
    return { name: '', email: from };
  };

  const getBody = (payload: any): string => {
    // Try to find the 'text/html' or 'text/plain' part
    const findPart = (part: any, mime: string): any => {
      if (!part) return null;
      if (part.mimeType === mime && part.body && part.body.data) return part.body.data;
      if (part.parts) {
        for (const p of part.parts) {
          const found = findPart(p, mime);
          if (found) return found;
        }
      }
      return null;
    };
    let data = findPart(payload, 'text/html') || findPart(payload, 'text/plain');
    if (!data && payload.body && payload.body.data) data = payload.body.data;
    if (!data) return '';
    try {
      // Gmail uses URL-safe base64 (replace -_/)
      const b64 = data.replace(/-/g, '+').replace(/_/g, '/');
      const decoded = atob(b64);
      // If HTML, return as is, else wrap in <pre>
      if (findPart(payload, 'text/html')) return decoded;
      return `<pre style='margin:0'>${decoded}</pre>`;
    } catch {
      return '';
    }
  };

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: 24, background: palette.ghostWhite, borderRadius: 16, boxShadow: '0 2px 12px rgba(39,45,45,0.08)' }}>
      <h2 style={{ color: palette.purpureus, fontWeight: 700, letterSpacing: 1 }}>Gmail Message Browser</h2>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 16, gap: 8 }}>
        <input
          type="text"
          placeholder="Search messages..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') handleSearch(); }}
          style={{ flex: 1, padding: '10px 14px', borderRadius: 8, border: `1px solid ${palette.davysGray}`, fontSize: 16, background: palette.ghostWhite }}
        />
        <button
          onClick={handleClear}
          disabled={!searchActive}
          style={{
            background: searchActive ? palette.davysGray : '#ccc',
            color: '#fff',
            border: 'none',
            borderRadius: 8,
            padding: '10px 18px',
            fontWeight: 600,
            cursor: searchActive ? 'pointer' : 'not-allowed',
            marginRight: 4
          }}
        >
          Clear
        </button>
        <button
          onClick={handleSearch}
          style={{
            background: palette.emerald,
            color: '#fff',
            border: 'none',
            borderRadius: 8,
            padding: '10px 18px',
            fontWeight: 600,
            cursor: 'pointer',
            boxShadow: '0 2px 6px rgba(35,206,107,0.08)'
          }}
        >
          Search
        </button>
      </div>
      {loading && <div>Loading...</div>}
      {error && <div style={{ color: palette.purpureus, fontWeight: 600 }}>{error}</div>}
      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 16, background: '#fff', borderRadius: 12, overflow: 'hidden', boxShadow: '0 1px 4px rgba(80,81,79,0.06)' }}>
        <thead>
          <tr style={{ background: palette.gunmetal, color: palette.ghostWhite }}>
            <th style={{ textAlign: 'left', padding: 12, fontWeight: 700 }}>Subject</th>
            <th style={{ textAlign: 'left', padding: 12, fontWeight: 700 }}>From</th>
            <th style={{ textAlign: 'left', padding: 12, fontWeight: 700 }}>Date</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {messages.map((msg) => (
            <tr key={msg.id} style={{ borderBottom: `1px solid ${palette.ghostWhite}` }}>
              <td style={{ padding: 12 }}>{getHeader(msg.payload, 'Subject')}</td>
              <td style={{ padding: 12 }}>{getHeader(msg.payload, 'From')}</td>
              <td style={{ padding: 12 }}>{formatDate(msg.internalDate)}</td>
              <td style={{ padding: 12 }}>
                <button onClick={() => setSelected(msg)} style={{ fontSize: 14, padding: '4px 12px', background: palette.purpureus, color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}>
                  Details
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <button onClick={handlePrev} disabled={pageTokens.length <= 1} style={{ background: palette.gunmetal, color: palette.ghostWhite, border: 'none', borderRadius: 8, padding: '10px 18px', fontWeight: 600, cursor: pageTokens.length <= 1 ? 'not-allowed' : 'pointer' }}>
          Previous
        </button>
        <button onClick={handleNext} disabled={!nextPageToken} style={{ background: palette.gunmetal, color: palette.ghostWhite, border: 'none', borderRadius: 8, padding: '10px 18px', fontWeight: 600, cursor: !nextPageToken ? 'not-allowed' : 'pointer' }}>
          Next
        </button>
      </div>
      {selected && (
        <div style={{
          position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', background: 'rgba(0,0,0,0.4)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}
          onClick={() => setSelected(null)}
        >
          <div style={{ background: '#fff', padding: 0, borderRadius: 8, minWidth: 400, maxWidth: 600, maxHeight: '80vh', overflow: 'hidden', boxShadow: '0 2px 12px rgba(39,45,45,0.12)', display: 'flex', flexDirection: 'column' }} onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', background: palette.gunmetal, color: palette.ghostWhite, padding: '20px 28px 12px 28px', borderTopLeftRadius: 8, borderTopRightRadius: 8 }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: 18 }}>{getHeader(selected.payload, 'Subject')}</div>
                <div style={{ fontSize: 15, marginTop: 4 }}>
                  <span style={{ fontWeight: 500 }}>{getSender(selected.payload).name}</span>
                  {getSender(selected.payload).name && ' '}
                  <span style={{ color: palette.purpureus }}>{`<${getSender(selected.payload).email}>`}</span>
                </div>
              </div>
              <div style={{ fontSize: 14, color: palette.davysGray, marginLeft: 16, minWidth: 120, textAlign: 'right' }}>
                {formatDate(selected.internalDate)}
              </div>
            </div>
            <div style={{ flex: 1, overflowY: 'auto', background: palette.ghostWhite, padding: 28 }}>
              <div dangerouslySetInnerHTML={{ __html: getBody(selected.payload) }} style={{ fontSize: 15, color: palette.gunmetal }} />
            </div>
            <div style={{ padding: 20, borderTop: `1px solid ${palette.ghostWhite}`, display: 'flex', justifyContent: 'flex-end', background: '#fff', borderBottomLeftRadius: 8, borderBottomRightRadius: 8 }}>
              <button onClick={() => setSelected(null)} style={{ background: palette.emerald, color: '#fff', border: 'none', borderRadius: 8, padding: '10px 18px', fontWeight: 600, cursor: 'pointer' }}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default GmailBrowser;
