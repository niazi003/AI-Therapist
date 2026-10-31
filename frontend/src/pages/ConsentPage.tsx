// Consent Page Component
import { useState, useEffect } from 'react';
import { consentApi } from '../api/client';
import type { Consent } from '../types';

interface ConsentPageProps {
  onConsentComplete: () => void;
}

export function ConsentPage({ onConsentComplete }: ConsentPageProps) {
  const [consents, setConsents] = useState<Consent[]>([]);
  const [requiredPurposes, setRequiredPurposes] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    loadConsents();
  }, []);

  const loadConsents = async () => {
    setLoadError(null);
    try {
      const [consentList, required] = await Promise.all([
        consentApi.get(),
        consentApi.getRequired(),
      ]);
      setConsents(consentList);
      setRequiredPurposes(required.purposes);
    } catch {
      setLoadError('Failed to load consent settings. Please refresh to try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleConsentChange = async (purpose: string, granted: boolean) => {
    setIsSaving(true);
    setSaveError(null);
    try {
      await consentApi.update(purpose, granted);
      setConsents(prev =>
        prev.map(c => c.purpose === purpose ? { ...c, granted } : c)
      );
    } catch {
      await loadConsents();
      setSaveError('Could not save this consent choice. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const hasRequiredConsent = () =>
    consents.some(c => c.purpose === 'ai_processing' && c.granted);

  if (isLoading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner" />
        <p>Loading consent settings…</p>
      </div>
    );
  }

  return (
    <div className="consent-page">
      <div className="consent-card">
        <h1>📋 Consent Settings</h1>
        <p className="subtitle">
          Choose what you’re comfortable sharing. You can update these choices later in Settings.
        </p>

        {loadError && <p className="error-message" role="alert">{loadError}</p>}
        {saveError && <p className="error-message" role="alert">{saveError}</p>}

        <div className="consent-list">
          {Object.entries(requiredPurposes).map(([purpose, description]) => {
            const consent = consents.find(c => c.purpose === purpose);
            const isGranted = consent?.granted ?? false;
            const isRequired = purpose === 'ai_processing';
            const label = purpose.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

            return (
              <div key={purpose} className="consent-item">
                <div className="consent-info">
                  <h3>
                    {label}
                    {isRequired && <span className="required"> *Required</span>}
                  </h3>
                  <p>{description}</p>
                </div>
                <label className="toggle" aria-label={`${label}${isRequired ? ' (required)' : ''}`}>
                  <input
                    type="checkbox"
                    checked={isGranted}
                    onChange={(e) => handleConsentChange(purpose, e.target.checked)}
                    disabled={isSaving}
                    aria-label={`${label}${isRequired ? ' (required)' : ''}`}
                  />
                  <span className="slider" />
                </label>
              </div>
            );
          })}
        </div>

        <div className="consent-actions">
          <button
            className="btn-primary btn-full"
            onClick={onConsentComplete}
            disabled={!hasRequiredConsent() || isSaving}
          >
            {isSaving ? 'Saving…' : 'Continue to Chat'}
          </button>
        </div>

        <p className="consent-note">
          You can change your consent settings at any time from the settings menu.
          Your privacy is important to us.
        </p>
      </div>
    </div>
  );
}