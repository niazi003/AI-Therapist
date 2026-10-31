// Chat Message Component
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message } from '../hooks/useChat';

interface ChatMessageProps {
  message: Message;
}

const workflowLabel: Record<string, string> = {
  routine: '💬 Routine',
  follow_up: '❓ Follow-up',
  urgent: '⚠️ Urgent',
  review_unavailable: '⚠️ Safety check unavailable',
  professional_referral: '🧭 Professional support',
};

function formatAssistantContent(content: string): string {
  let formatted = content
    .replace(/\r\n?/g, '\n')
    .replace(/<br\s*\/?>/gi, '  \n');

  if (/\|\s*:?-{3,}:?\s*\|/.test(formatted)) {
    formatted = formatted
      .replace(/(\*\*[^*\n]+\*\*:)\s*\|/g, '$1\n|')
      .replace(/\s*\|\s*\|\s*/g, '\n|')
      .replace(/\s*\|\|\s*/g, '\n|');
  }

  return formatted;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const isUrgent = message.workflow === 'urgent';
  const isSafetyUnavailable = message.workflow === 'review_unavailable';
  const supportCountryCode = message.supportUrl?.match(/\/countries\/([a-z]{2})$/i)?.[1];
  const supportCountryName = supportCountryCode
    ? new Intl.DisplayNames(['en'], { type: 'region' }).of(supportCountryCode.toUpperCase())
    : null;

  return (
    <div
      className={[
        'message',
        `message-${message.role}`,
        isUrgent ? 'message-crisis' : '',
        isSafetyUnavailable && !isUser ? 'message-safety-warning' : '',
      ].filter(Boolean).join(' ')}
    >
      <div className="message-content">
        {isUser ? (
          message.content
        ) : (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              table: ({ children }) => (
                <div className="message-table">
                  <table>{children}</table>
                </div>
              ),
            }}
          >
            {formatAssistantContent(message.content)}
          </ReactMarkdown>
        )}
      </div>
      {message.serviceUnavailable && message.supportUrl && (
        <aside className="service-unavailable-card">
          <strong>Human support is still available</strong>
          <a href={message.supportUrl} target="_blank" rel="noopener noreferrer">
            {supportCountryName
              ? `Find mental health support in ${supportCountryName}`
              : 'Find mental health support by country'}
          </a>
          <span>
            Browse current helplines and support options.
          </span>
        </aside>
      )}
      {message.workflow && !isUser && !message.serviceUnavailable && workflowLabel[message.workflow] && (
        <div className={`workflow-badge workflow-${message.workflow}`}>
          {workflowLabel[message.workflow]}
        </div>
      )}
      {isUrgent && isUser && (
        <div className="workflow-badge workflow-urgent">⚠️ Safety concern</div>
      )}
    </div>
  );
}