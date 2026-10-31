// Login Page Component
import { useState } from 'react';

interface LoginPageProps {
  onLoginSuccess: () => void;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  isLoading: boolean;
  error: string | null;
}

export function LoginPage({ onLoginSuccess, login, register, isLoading, error }: LoginPageProps) {
  const [isRegistering, setIsRegistering] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (isRegistering) {
        await register(email, password, fullName || undefined);
      } else {
        await login(email, password);
      }
      onLoginSuccess();
    } catch {
      // Error is displayed via useAuth.error
    }
  };

  return (
    <div className="login-page">
      <div className="login-intro" aria-hidden="true">
        <span className="login-intro-mark">🌿</span>
        <p>A little space to pause, reflect, and find your next step.</p>
        <span className="login-intro-caption">Private, supportive conversations at your pace</span>
      </div>
      <div className="login-card">
        <div className="login-logo" aria-hidden="true">🌱</div>
        <p className="eyebrow">WELLBEING COMPANION</p>
        <h1>{isRegistering ? 'Create your account' : 'Welcome back'}</h1>
        <p className="subtitle">
          {isRegistering
            ? 'Create an account to begin your wellbeing journey.'
            : 'Sign in to continue your wellbeing journey.'}
        </p>

        <div className="disclaimer login-disclaimer">
          <strong>Before you begin</strong>
          <span>This AI companion offers general wellbeing support, not therapy or emergency care.</span>
        </div>

        <form onSubmit={handleSubmit}>
          {isRegistering && (
            <div className="form-group">
              <label htmlFor="fullName">Name (optional)</label>
              <input
                id="fullName"
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Your name"
                autoComplete="name"
              />
            </div>
          )}

          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="your@email.com"
              autoComplete="email"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              placeholder="Minimum 8 characters"
              autoComplete={isRegistering ? 'new-password' : 'current-password'}
            />
          </div>

          {error && <div className="error-message" role="alert">{error}</div>}

          <button type="submit" className="btn-primary btn-full" disabled={isLoading}>
            {isLoading ? 'Please wait…' : isRegistering ? 'Create Account' : 'Sign In'}
          </button>
        </form>

        <p className="switch-mode">
          {isRegistering ? 'Already have an account?' : "Don't have an account?"}{' '}
          <button
            type="button"
            className="btn-link"
            onClick={() => setIsRegistering(!isRegistering)}
          >
            {isRegistering ? 'Sign In' : 'Register'}
          </button>
        </p>
      </div>
    </div>
  );
}