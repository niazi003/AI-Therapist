// Main App Component
import { useState, useEffect } from 'react';
import { useAuth } from './hooks/useAuth';
import { LoginPage } from './pages/LoginPage';
import { ConsentPage } from './pages/ConsentPage';
import { ChatPage } from './pages/ChatPage';
import { memoryApi } from './api/client';
import type { MemoryBlock } from './types';
import {
  clearCountryCode,
  confirmCountryCode,
  detectCountryFromIp,
  getCountryCode,
} from './services/location';

type AppState = 'login' | 'consent' | 'chat' | 'settings';

function App() {
  const { isAuthenticated, isLoading, error, login, register, logout } = useAuth();
  const [appState, setAppState] = useState<AppState>('login');
  const [memories, setMemories] = useState<MemoryBlock[]>([]);
  const [memError, setMemError] = useState<string | null>(null);
  const [isLoadingMemories, setIsLoadingMemories] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [countryCode, setCountryCode] = useState(() => getCountryCode());
  const [countryCandidate, setCountryCandidate] = useState<string | null>(null);
  const [isLocatingCountry, setIsLocatingCountry] = useState(false);
  const [countryError, setCountryError] = useState<string | null>(null);
  const [showCountryPrompt, setShowCountryPrompt] = useState(false);

  const countryName = (code: string) =>
    new Intl.DisplayNames(['en'], { type: 'region' }).of(code) ?? code;

  // Sync appState with authentication status
  useEffect(() => {
    if (!isAuthenticated && appState !== 'login') {
      setAppState('login');
    }
  }, [isAuthenticated, appState]);

  useEffect(() => {
    if (
      isAuthenticated &&
      appState === 'chat' &&
      !countryCode &&
      sessionStorage.getItem('country_prompt_dismissed') !== 'true'
    ) {
      setShowCountryPrompt(true);
    }
  }, [isAuthenticated, appState, countryCode]);

  const dismissCountryPrompt = () => {
    sessionStorage.setItem('country_prompt_dismissed', 'true');
    setShowCountryPrompt(false);
  };

  const handleCountryLookup = async () => {
    setCountryError(null);
    setIsLocatingCountry(true);
    try {
      setCountryCandidate(await detectCountryFromIp());
    } catch (lookupError) {
      setCountryError(
        lookupError instanceof Error
          ? lookupError.message
          : 'Could not estimate a country. You can try again or skip.'
      );
    } finally {
      setIsLocatingCountry(false);
    }
  };

  const handleConfirmCountry = () => {
    if (!countryCandidate) return;
    confirmCountryCode(countryCandidate);
    setCountryCode(countryCandidate);
    setCountryCandidate(null);
    setCountryError(null);
    dismissCountryPrompt();
  };

  const handleForgetCountry = () => {
    clearCountryCode();
    setCountryCode(null);
    setCountryCandidate(null);
    setCountryError(null);
    dismissCountryPrompt();
  };

  const handleLoginSuccess = () => {
    setAppState('consent');
  };

  const handleConsentComplete = () => {
    setAppState('chat');
  };

  const handleOpenSettings = async () => {
    setMemError(null);
    setIsLoadingMemories(true);
    setAppState('settings');
    try {
      const mems = await memoryApi.get();
      setMemories(mems);
    } catch {
      setMemories([]);
      setMemError('Could not load memories.');
    } finally {
      setIsLoadingMemories(false);
    }
  };

  const handleCloseSettings = () => {
    setAppState('chat');
  };

  const handleLogout = () => {
    logout();
    setAppState('login');
  };

  const handleDeleteAllMemory = async () => {
    if (!window.confirm('Are you sure you want to delete all memory? This cannot be undone.')) return;
    setIsDeleting(true);
    try {
      await memoryApi.deleteAll();
      setMemories([]);
      setMemError(null);
    } catch {
      setMemError('Failed to delete memory. Please try again.');
    } finally {
      setIsDeleting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner" />
        <p>Loading…</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <LoginPage
        onLoginSuccess={handleLoginSuccess}
        login={login}
        register={register}
        isLoading={isLoading}
        error={error}
      />
    );
  }

  switch (appState) {
    case 'consent':
      return <ConsentPage onConsentComplete={handleConsentComplete} />;

    case 'settings':
      return (
        <div className="settings-page">
          <div className="settings-header">
            <div>
              <p className="eyebrow">YOUR SPACE</p>
              <h1>Settings</h1>
              <p className="settings-intro">Manage what the companion remembers and how your account works.</p>
            </div>
            <button className="btn-secondary settings-back" onClick={handleCloseSettings}>
              ← Back to chat
            </button>
          </div>

          <div className="settings-section">
            <h2>Crisis resource country</h2>
            <p className="settings-help">
              {countryCode
                ? `Your approximate country is set to ${countryName(countryCode)}. It is stored in this browser and used to tailor crisis-resource links; it does not identify your exact location.`
                : 'Set an approximate country to tailor crisis-resource links. This is optional and does not determine your exact location.'}
            </p>
            {countryCandidate ? (
              <div className="country-settings-actions">
                <p>IP lookup suggests {countryName(countryCandidate)}. Is that correct?</p>
                <button className="btn-primary" onClick={handleConfirmCountry}>Confirm country</button>
                <button className="btn-secondary" onClick={() => setCountryCandidate(null)}>Cancel</button>
              </div>
            ) : (
              <div className="settings-actions">
                <button
                  className="btn-secondary"
                  onClick={handleCountryLookup}
                  disabled={isLocatingCountry}
                >
                  {isLocatingCountry
                    ? 'Estimating…'
                    : countryCode
                      ? 'Update country'
                      : 'Estimate country from IP'}
                </button>
                {countryCode && (
                  <button className="btn-danger" onClick={handleForgetCountry}>
                    Forget country
                  </button>
                )}
              </div>
            )}
            {countryError && <p className="error-message" role="alert">{countryError}</p>}
            <details className="location-privacy">
              <summary>How country estimation works</summary>
              <p>
                If you choose IP lookup, your public IP is sent to ipwho.is through
                our backend to estimate a country. The result is not your exact
                location. It is only saved after you confirm it, and you can forget
                it here at any time.
              </p>
            </details>
          </div>

          <div className="settings-section">
            <h2>Memory</h2>
            <p className="settings-help">
              These notes help personalize future conversations. You can remove them at any time.
            </p>
            {memError && <p className="error-message">{memError}</p>}
            {isLoadingMemories ? (
              <p className="empty-state">Loading memories…</p>
            ) : memories.length === 0 ? (
              <p className="empty-state">No memories stored.</p>
            ) : (
              <div className="memory-list">
                {memories.map((mem) => (
                  <div key={mem.id} className="memory-item">
                    <h4>{mem.memory_type}</h4>
                    <p>{mem.content}</p>
                  </div>
                ))}
              </div>
            )}
            <div className="settings-actions">
              <button
                onClick={handleDeleteAllMemory}
                className="btn-danger"
                disabled={isDeleting}
              >
                {isDeleting ? 'Deleting…' : 'Delete All Memory'}
              </button>
            </div>
          </div>

          <div className="settings-section">
            <h2>Consent</h2>
            <p className="settings-help">Review or change which data uses you’ve agreed to.</p>
            <div className="settings-actions">
              <button className="btn-secondary" onClick={() => setAppState('consent')}>
                Manage Consent
              </button>
            </div>
          </div>

          <div className="settings-section">
            <h2>Account</h2>
            <p className="settings-help">Return to the conversation or sign out of this account.</p>
            <div className="settings-actions">
              <button className="btn-secondary" onClick={handleCloseSettings}>
                Back to Chat
              </button>
              <button className="btn-danger" onClick={handleLogout}>
                Logout
              </button>
            </div>
          </div>
        </div>
      );

    case 'chat':
    default:
      return (
        <>
          <ChatPage
            onOpenSettings={handleOpenSettings}
            onOpenCountrySettings={handleOpenSettings}
            onLogout={handleLogout}
            countryCode={countryCode}
          />
          {showCountryPrompt && !countryCode && (
            <div className="country-prompt-backdrop">
              <section
                className="country-prompt"
                role="dialog"
                aria-modal="true"
                aria-labelledby="country-prompt-title"
                aria-describedby="country-prompt-description"
              >
                <p className="eyebrow">OPTIONAL SETUP</p>
                <h2 id="country-prompt-title">Tailor crisis resources</h2>
                <p id="country-prompt-description">
                  Choose an approximate country to show relevant crisis-support
                  links. You can skip this and set it later from the country
                  capsule at the top of the chat.
                </p>
                {countryCandidate ? (
                  <div className="country-settings-actions">
                    <p>IP lookup suggests {countryName(countryCandidate)}. Is that correct?</p>
                    <button className="btn-primary btn-full" onClick={handleConfirmCountry}>
                      Confirm {countryName(countryCandidate)}
                    </button>
                    <button className="btn-secondary btn-full" onClick={() => setCountryCandidate(null)}>
                      Choose again
                    </button>
                    <button className="btn-link country-prompt-skip" onClick={dismissCountryPrompt}>
                      Skip for now
                    </button>
                  </div>
                ) : (
                  <>
                    <button
                      className="btn-primary btn-full"
                      onClick={handleCountryLookup}
                      disabled={isLocatingCountry}
                    >
                      {isLocatingCountry ? 'Estimating country…' : 'Estimate my country'}
                    </button>
                    <button
                      className="btn-link country-prompt-skip"
                      onClick={dismissCountryPrompt}
                    >
                      Skip for now
                    </button>
                  </>
                )}
                {countryError && <p className="error-message" role="alert">{countryError}</p>}
                <details className="location-privacy">
                  <summary>Privacy details</summary>
                  <p>
                    Estimation sends your public IP to ipwho.is through our backend.
                    The result may be wrong, is not your exact location, and is only
                    saved if you confirm it.
                  </p>
                </details>
              </section>
            </div>
          )}
        </>
      );
  }
}

export default App;