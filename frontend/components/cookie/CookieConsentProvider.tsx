"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  acceptAll as persistAcceptAll,
  canUseAnalytics,
  canUseMarketing,
  CONSENT_OPEN_SETTINGS_EVENT,
  CONSENT_UPDATED_EVENT,
  getConsent,
  hasAnswered,
  rejectNonEssential as persistReject,
  setConsent,
  type ConsentState,
} from "@/lib/cookie-consent";
import { CookieBanner } from "@/components/cookie/CookieBanner";
import { CookieSettings } from "@/components/cookie/CookieSettings";

type CookieConsentContextValue = {
  consent: ConsentState;
  answered: boolean;
  analyticsAllowed: boolean;
  marketingAllowed: boolean;
  settingsOpen: boolean;
  openSettings: () => void;
  closeSettings: () => void;
  acceptAll: () => void;
  rejectNonEssential: () => void;
  saveChoices: (choices: {
    analytics: boolean;
    marketing: boolean;
  }) => void;
};

const CookieConsentContext = createContext<CookieConsentContextValue | null>(
  null,
);

export function useCookieConsent(): CookieConsentContextValue {
  const ctx = useContext(CookieConsentContext);
  if (!ctx) {
    throw new Error("useCookieConsent must be used within CookieConsentProvider");
  }
  return ctx;
}

/** Safe hook for optional gating outside provider (defaults to denied). */
export function useMarketingConsent(): boolean {
  const [allowed, setAllowed] = useState(false);
  useEffect(() => {
    setAllowed(canUseMarketing());
    function onUpdate(event: Event) {
      const detail = (event as CustomEvent<ConsentState>).detail;
      setAllowed(detail ? detail.marketing : canUseMarketing());
    }
    window.addEventListener(CONSENT_UPDATED_EVENT, onUpdate);
    return () => window.removeEventListener(CONSENT_UPDATED_EVENT, onUpdate);
  }, []);
  return allowed;
}

export function CookieConsentProvider({ children }: { children: ReactNode }) {
  const [consent, setConsentState] = useState<ConsentState>(() => getConsent());
  const [answered, setAnswered] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setConsentState(getConsent());
    setAnswered(hasAnswered());
    setHydrated(true);

    function onUpdate(event: Event) {
      const detail = (event as CustomEvent<ConsentState>).detail;
      setConsentState(detail ?? getConsent());
      setAnswered(true);
    }
    function onOpenSettings() {
      setSettingsOpen(true);
    }

    window.addEventListener(CONSENT_UPDATED_EVENT, onUpdate);
    window.addEventListener(CONSENT_OPEN_SETTINGS_EVENT, onOpenSettings);
    return () => {
      window.removeEventListener(CONSENT_UPDATED_EVENT, onUpdate);
      window.removeEventListener(CONSENT_OPEN_SETTINGS_EVENT, onOpenSettings);
    };
  }, []);

  const openSettings = useCallback(() => setSettingsOpen(true), []);
  const closeSettings = useCallback(() => setSettingsOpen(false), []);

  const acceptAll = useCallback(() => {
    setConsentState(persistAcceptAll());
    setAnswered(true);
    setSettingsOpen(false);
  }, []);

  const rejectNonEssential = useCallback(() => {
    setConsentState(persistReject());
    setAnswered(true);
    setSettingsOpen(false);
  }, []);

  const saveChoices = useCallback(
    (choices: { analytics: boolean; marketing: boolean }) => {
      setConsentState(setConsent(choices));
      setAnswered(true);
      setSettingsOpen(false);
    },
    [],
  );

  const value = useMemo(
    () => ({
      consent,
      answered,
      analyticsAllowed: canUseAnalytics(consent),
      marketingAllowed: canUseMarketing(consent),
      settingsOpen,
      openSettings,
      closeSettings,
      acceptAll,
      rejectNonEssential,
      saveChoices,
    }),
    [
      consent,
      answered,
      settingsOpen,
      openSettings,
      closeSettings,
      acceptAll,
      rejectNonEssential,
      saveChoices,
    ],
  );

  return (
    <CookieConsentContext.Provider value={value}>
      {children}
      {hydrated && !answered ? (
        <CookieBanner
          onAcceptAll={acceptAll}
          onReject={rejectNonEssential}
          onCustomize={openSettings}
        />
      ) : null}
      {hydrated && settingsOpen ? (
        <CookieSettings
          consent={consent}
          onClose={closeSettings}
          onSave={saveChoices}
          onAcceptAll={acceptAll}
          onReject={rejectNonEssential}
        />
      ) : null}
    </CookieConsentContext.Provider>
  );
}
