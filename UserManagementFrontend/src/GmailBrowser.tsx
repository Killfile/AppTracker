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

const GmailBrowser: React.FC<GmailBrowserProps> = ({ jwt }) => {
  const [messages, setMessages] = useState<GmailMessage[]>([]);
  const [nextPageToken, setNextPageToken] = useState<string | undefined>(undefined);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<GmailMessage | null>(null);
  const [pageTokens, setPageTokens] = useState<string[]>([]);

  const fetchMessages = (pageToken?: string) => {
    setLoading(true);
    setError(null);
    let url = `${API_URL}/api/gmail/messages?maxResults=10`;
    if (pageToken) url += `&pageToken=${pageToken}`;
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
  }, [jwt]);

  const handleNext = () => {
    if (nextPageToken) {
      fetchMessages(nextPageToken);
      setPageTokens((prev) => [...prev, nextPageToken]);
    }
  };
  const handlePrev = () => {
    if (pageTokens.length > 1) {
      const prevTokens = [...pageTokens];
      prevTokens.pop();
      const prevToken = prevTokens[prevTokens.length - 1];
      fetchMessages(prevToken);
      setPageTokens(prevTokens);
    }
  };

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: 24 }}>
      <h2>Gmail Message Browser</h2>
      {loading && <div>Loading...</div>}
      {error && <div style={{ color: 'red' }}>{error}</div>}
      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 16 }}>
        <thead>
          <tr style={{ background: '#f0f0f0' }}>
            <th style={{ textAlign: 'left', padding: 8 }}>Subject</th>
            <th style={{ textAlign: 'left', padding: 8 }}>From</th>
            <th style={{ textAlign: 'left', padding: 8 }}>Date</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {messages.map((msg) => (
            <tr key={msg.id} style={{ borderBottom: '1px solid #eee' }}>
              <td style={{ padding: 8 }}>{getHeader(msg.payload, 'Subject')}</td>
              <td style={{ padding: 8 }}>{getHeader(msg.payload, 'From')}</td>
              <td style={{ padding: 8 }}>{formatDate(msg.internalDate)}</td>
              <td style={{ padding: 8 }}>
                <button onClick={() => setSelected(msg)} style={{ fontSize: 14, padding: '4px 12px' }}>
                  Details
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <button onClick={handlePrev} disabled={pageTokens.length <= 1}>
          Previous
        </button>
        <button onClick={handleNext} disabled={!nextPageToken}>
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
          <div style={{ background: '#fff', padding: 32, borderRadius: 8, minWidth: 400, maxWidth: 600, maxHeight: '80vh', overflowY: 'auto' }} onClick={e => e.stopPropagation()}>
            <h3>Email Details</h3>
            <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontSize: 14 }}>{JSON.stringify(selected, null, 2)}</pre>
            <button onClick={() => setSelected(null)} style={{ marginTop: 16 }}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default GmailBrowser;
