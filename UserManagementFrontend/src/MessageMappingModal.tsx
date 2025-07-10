import React, { useState } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, MenuItem, CircularProgress } from '@mui/material';

interface Company {
  id: number;
  name: string;
}
interface Application {
  id: number;
  title: string;
  date_applied: string;
  company_id: number;
  user_id: number;
}
interface MessageMappingModalProps {
  open: boolean;
  onClose: () => void;
  jwt: string;
  gmailMessage: any;
  onMapped: () => void;
}

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
const ACTION_TYPES = [
  'EMAIL_SENT', 'CALL', 'INTERVIEW', 'FOLLOW_UP', 'REJECTED', 'OTHER'
];

const MessageMappingModal: React.FC<MessageMappingModalProps> = ({ open, onClose, jwt, gmailMessage, onMapped }) => {
  // Company
  const [companyQuery, setCompanyQuery] = useState('');
  const [companyResults, setCompanyResults] = useState<Company[]>([]);
  const [companyLoading, setCompanyLoading] = useState(false);
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null);
  // Application
  const [appQuery, setAppQuery] = useState('');
  const [appResults, setAppResults] = useState<Application[]>([]);
  const [appLoading, setAppLoading] = useState(false);
  const [selectedApp, setSelectedApp] = useState<Application | null>(null);
  // Action
  const [selectedAction, setSelectedAction] = useState('');
  // State
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');


  /**
   * Extracts the plain text message body from a Gmail message object.
   * Handles multipart and base64url decoding.
   */
  function getMessageBody(gmailMessage: any): string {
    if (!gmailMessage?.payload) return '';

    // Helper to decode base64url
    const decode = (str: string) => {
      try {
        // Gmail uses base64url (replace -/_)
        const b64 = str.replace(/-/g, '+').replace(/_/g, '/');
        // Pad with '=' if needed
        const pad = b64.length % 4 === 0 ? '' : '='.repeat(4 - (b64.length % 4));
        return decodeURIComponent(escape(window.atob(b64 + pad)));
      } catch {
        return '';
      }
    };

    // Recursively search for 'text/plain' part
    function findPlainTextPart(payload: any): string | null {
      if (!payload) return null;
      if (payload.mimeType === 'text/plain' && payload.body?.data) {
        return decode(payload.body.data);
      }
      if (payload.parts && Array.isArray(payload.parts)) {
        for (const part of payload.parts) {
          const result = findPlainTextPart(part);
          if (result) return result;
        }
      }
      return null;
    }

    // Try to get plain text, fallback to HTML if needed
    const plain = findPlainTextPart(gmailMessage.payload);
    if (plain) return plain;

    // Fallback: try to get 'text/html' part
    function findHtmlPart(payload: any): string | null {
      if (!payload) return null;
      if (payload.mimeType === 'text/html' && payload.body?.data) {
        return decode(payload.body.data);
      }
      if (payload.parts && Array.isArray(payload.parts)) {
        for (const part of payload.parts) {
          const result = findHtmlPart(part);
          if (result) return result;
        }
      }
      return null;
    }
    const html = findHtmlPart(gmailMessage.payload);
    return html || '';
  }

  // --- Company Typeahead ---
  const searchCompanies = async (q: string) => {
    setCompanyLoading(true);
    setCompanyQuery(q);
    setSelectedCompany(null);
    setSelectedApp(null);
    setAppQuery('');
    setAppResults([]);
    try {
      const res = await fetch(`${API_URL}/api/companies?q=${encodeURIComponent(q)}`, {
        headers: { Authorization: `Bearer ${jwt}` }
      });
      const data = await res.json();
      setCompanyResults(data);
    } catch {
      setCompanyResults([]);
    }
    setCompanyLoading(false);
  };
  const createCompany = async (name: string) => {
    setCompanyLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/companies`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${jwt}` },
        body: JSON.stringify({ name })
      });
      const data = await res.json();
      setSelectedCompany(data);
      setCompanyResults([data]);
    } catch {
      setError('Failed to create company');
    }
    setCompanyLoading(false);
  };

  // --- Application Typeahead ---
  const searchApps = async (q: string) => {
    if (!selectedCompany) return;
    setAppLoading(true);
    setAppQuery(q);
    setSelectedApp(null);
    try {
      const res = await fetch(`${API_URL}/api/applications?q=${encodeURIComponent(q)}`, {
        headers: { Authorization: `Bearer ${jwt}` }
      });
      const data = await res.json();
      setAppResults(data.filter((a: Application) => a.company_id === selectedCompany.id));
    } catch {
      setAppResults([]);
    }
    setAppLoading(false);
  };
  const createApp = async (title: string) => {
    if (!selectedCompany) return;
    setAppLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/applications`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${jwt}` },
        body: JSON.stringify({ title, date_applied: new Date().toISOString().slice(0,10), company_id: selectedCompany.id })
      });
      const data = await res.json();
      setSelectedApp(data);
      setAppResults([data]);
    } catch {
      setError('Failed to create application');
    }
    setAppLoading(false);
  };

  // --- Save Mapping ---
  const handleSave = async () => {
    if (!selectedCompany || !selectedApp || !selectedAction) return;
    setSaving(true);
    setError('');

    try {
      // 1. Extract sender email from gmailMessage
      console.log('Extracting sender email from Gmail message...');
      const fromHeader = gmailMessage.payload?.headers?.find((h:any) => h.name.toLowerCase() === 'from');
      let senderEmail = '';
      if (fromHeader) {
        const match = fromHeader.value.match(/<(.+?)>/);
        senderEmail = match ? match[1].toLowerCase() : fromHeader.value.toLowerCase();
        senderEmail = senderEmail.replace(/^"|"$/g, '').trim();
      }
      if (!senderEmail) throw new Error('Could not extract sender email');

      // 2. Upsert email address
      console.log('Searching for email address:', senderEmail);
      const upsertRequest = await fetch(`${API_URL}/api/email_address`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${jwt}` },
        body: JSON.stringify({ email: senderEmail})
      });
      if (!upsertRequest.ok) {
        throw new Error('Failed to upsert email address');
      }
      const upsertData = await upsertRequest.json();
      console.log('Upserted email address:', upsertData);
      let emailAddressId = upsertData.id;
      if (!emailAddressId) throw new Error('Could not resolve email address ID');

      let upsert = false;
      let msgRes = null;
     
      // 3. Upsert message
      msgRes = await fetch(`${API_URL}/api/messages/upsert`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${jwt}` },
        body: JSON.stringify({
          subject: gmailMessage.payload ? gmailMessage.payload.headers.find((h:any) => h.name==='Subject')?.value : '',
          date_received: new Date(Number(gmailMessage.internalDate)).toISOString().slice(0,10),
          message_body: getMessageBody(gmailMessage),
          gmail_message_id: gmailMessage.id,
          user_id: null, // backend will use JWT
          company_id: selectedCompany.id,
          email_address_id: emailAddressId
        })
      });
      
      
      const msgData = await msgRes.json();
      // 5. Create Action
      console.log('Creating action record for message:', msgData.id);
      await fetch(`${API_URL}/api/actions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${jwt}` },
        body: JSON.stringify({
          date_logged: new Date().toISOString().slice(0,10),
          type: selectedAction,
          application_id: selectedApp.id,
          message_id: msgData.id
        })
      });
      onMapped();
      onClose();
    } catch (e: any) {
      setError('Failed to save mapping: ' + (e?.message || ''));
    }
    setSaving(false);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Map Email to Application</DialogTitle>
      <DialogContent>
        {/* Company Typeahead */}
        <div style={{ marginBottom: 24 }}>
          <TextField
            label="Company"
            value={selectedCompany ? selectedCompany.name : companyQuery}
            onChange={e => searchCompanies(e.target.value)}
            fullWidth
            disabled={!!selectedCompany}
            InputProps={{
              endAdornment: companyLoading && <CircularProgress size={20} />
            }}
            autoFocus
          />
          {!selectedCompany && companyQuery && !companyLoading && companyResults.length === 0 && (
            <Button onClick={() => createCompany(companyQuery)} color="primary" style={{ marginTop: 8 }}>Create "{companyQuery}"</Button>
          )}
          {!selectedCompany && companyResults.map(c => (
            <Button key={c.id} onClick={() => { setSelectedCompany(c); setCompanyQuery(c.name); }} style={{ marginTop: 8, marginRight: 8 }}>{c.name}</Button>
          ))}
          {selectedCompany && (
            <Button onClick={() => { setSelectedCompany(null); setCompanyQuery(''); setSelectedApp(null); setAppQuery(''); setAppResults([]); }} color="secondary" style={{ marginTop: 8 }}>Change</Button>
          )}
        </div>
        {/* Application Typeahead */}
        <div style={{ marginBottom: 24 }}>
          <TextField
            label="Application"
            value={selectedApp ? selectedApp.title : appQuery}
            onChange={e => searchApps(e.target.value)}
            fullWidth
            disabled={!selectedCompany || !!selectedApp}
            InputProps={{
              endAdornment: appLoading && <CircularProgress size={20} />
            }}
          />
          {!selectedApp && appQuery && !appLoading && appResults.length === 0 && selectedCompany && (
            <Button onClick={() => createApp(appQuery)} color="primary" style={{ marginTop: 8 }}>Create "{appQuery}"</Button>
          )}
          {!selectedApp && appResults.map(a => (
            <Button key={a.id} onClick={() => { setSelectedApp(a); setAppQuery(a.title); }} style={{ marginTop: 8, marginRight: 8 }}>{a.title}</Button>
          ))}
          {selectedApp && (
            <Button onClick={() => { setSelectedApp(null); setAppQuery(''); }} color="secondary" style={{ marginTop: 8 }}>Change</Button>
          )}
        </div>
        {/* Action Dropdown */}
        <div style={{ marginBottom: 24 }}>
          <TextField
            select
            label="Action"
            value={selectedAction}
            onChange={e => setSelectedAction(e.target.value)}
            fullWidth
            disabled={!selectedApp}
          >
            {ACTION_TYPES.map(type => (
              <MenuItem key={type} value={type}>{type.replace('_', ' ')}</MenuItem>
            ))}
          </TextField>
        </div>
        {error && <div style={{ color: 'red', marginBottom: 8 }}>{error}</div>}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} color="secondary">Cancel</Button>
        <Button onClick={handleSave} color="primary" variant="contained" disabled={!selectedCompany || !selectedApp || !selectedAction || saving}>
          {saving ? <CircularProgress size={20} /> : 'Save'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default MessageMappingModal;
