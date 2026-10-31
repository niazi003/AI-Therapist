// Chat Page Component
import { useEffect, useRef } from 'react';
import { useChat } from '../hooks/useChat';
import { ChatMessage } from '../components/ChatMessage';
import { ChatInput } from '../components/ChatInput';
interface ChatPageProps {
  onOpenSettings: () => void;
  onOpenCountrySettings: () => void;
  onLogout: () => void;
  countryCode: string | null;
}

export function ChatPage({
  onOpenSettings,
  onOpenCountrySettings,
  onLogout,
  countryCode,
}: ChatPageProps) {
  const { messages, isLoading, error, sendMessage } = useChat();
  const bottomRef = useRef<HTMLDivElement>(null);

  const countryName = (code: string) =>
    new Intl.DisplayNames(['en'], { type: 'region' }).of(code) ?? code;

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="chat-page">
      <header className="chat-header">
        <h1>🌱 Wellbeing Companion</h1>
        <nav aria-label="App navigation">
          <button
            onClick={onOpenCountrySettings}
            className="country-capsule"
            aria-label={countryCode
              ? `Crisis resources country: ${countryName(countryCode)}. Manage country settings`
              : 'Set country for crisis resources'}
          >
            <span className="country-capsule-icon" aria-hidden="true">📍</span>
            <span className="country-capsule-label">
              {countryCode ? countryName(countryCode) : 'Set country'}
            </span>
          </button>
          <button onClick={onOpenSettings} className="btn-nav">⚙️ Settings</button>
          <button onClick={onLogout} className="btn-nav">Logout</button>
        </nav>
      </header>

      <main className="chat-main">
        {messages.length === 0 ? (
          <div className="welcome-message">
            <div className="welcome-icon" aria-hidden="true">🌿</div>
            <h2>Welcome! 👋</h2>
            <p>I'm here to listen and help you think through what’s on your mind.</p>
            <p className="disclaimer">
              I’m an AI companion, not a therapist or emergency service.
            </p>
            <a
              href={
                countryCode
                  ? `https://findahelpline.com/countries/${countryCode.toLowerCase()}`
                  : 'https://findahelpline.com/'
              }
              target="_blank"
              rel="noopener noreferrer"
              className="urgent-help-link"
            >
              Need urgent help? Get crisis resources →
            </a>
          </div>
        ) : (
          <div className="message-list">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
          </div>
        )}

        {isLoading && (
          <div className="loading-indicator" aria-live="polite">
            <span className="dot-pulse" />
            <span>Thinking…</span>
          </div>
        )}

        {error && (
          <div className="error-banner" role="alert">
            ⚠️ {error}
          </div>
        )}

        <div ref={bottomRef} />
      </main>

      <footer className="chat-footer">
        <ChatInput
          onSend={sendMessage}
          disabled={isLoading}
          placeholder="Share what's on your mind…"
        />
      </footer>
    </div>
  );
}