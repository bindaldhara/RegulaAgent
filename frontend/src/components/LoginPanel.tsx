import { motion } from "motion/react";
import { useState } from "react";
import {
  loginEmail,
  requestPhoneOtp,
  signOut,
  signUpEmail,
  updateConsent,
  verifyPhoneOtp,
} from "../api/auth";
import { clearAccessToken } from "../lib/authStorage";
import { supabaseConfigured } from "../lib/supabase";
import {
  profileContactLabel,
  profileNameWithContact,
} from "../lib/profileContact";
import { fadeUp, staggerContainer } from "../motion/presets";
import type { PatientProfile } from "../types/auth";
import { GlassCard } from "./GlassCard";

type Tab = "email" | "phone";

interface LoginPanelProps {
  patient: PatientProfile | null;
  onAuthenticated: (patient: PatientProfile, options?: { resetChat?: boolean }) => void;
  onLogout: () => void;
  onNewConversation: () => void;
}

export function LoginPanel({
  patient,
  onAuthenticated,
  onLogout,
  onNewConversation,
}: LoginPanelProps) {
  const [tab, setTab] = useState<Tab>("email");
  const [emailMode, setEmailMode] = useState<"signin" | "signup">("signin");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleEmailSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!fullName.trim()) {
      setError("Please enter your name");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const profile =
        emailMode === "signup"
          ? await signUpEmail(email, password, fullName.trim())
          : await loginEmail(email, password, fullName.trim());
      onAuthenticated(profile, { resetChat: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleRequestOtp() {
    setError(null);
    setLoading(true);
    try {
      await requestPhoneOtp(phone);
      setOtpSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send code");
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyOtp(e: React.FormEvent) {
    e.preventDefault();
    if (!fullName.trim()) {
      setError("Please enter your name");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const profile = await verifyPhoneOtp(phone, otp, fullName.trim());
      onAuthenticated(profile, { resetChat: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleConsentChange(granted: boolean) {
    if (!patient) return;
    setError(null);
    setLoading(true);
    try {
      const updated = await updateConsent(granted);
      onAuthenticated(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update consent");
    } finally {
      setLoading(false);
    }
  }

  async function handleLogout() {
    await signOut();
    clearAccessToken();
    onLogout(); /* clears chat + patient in App */
  }

  if (!supabaseConfigured) {
    return (
      <GlassCard className="p-4" glow="violet">
        <p className="text-sm text-amber-200/90">
          Supabase is not configured. Set <code className="text-xs">VITE_SUPABASE_URL</code> and{" "}
          <code className="text-xs">VITE_SUPABASE_ANON_KEY</code> in your environment.
        </p>
      </GlassCard>
    );
  }

  return (
    <GlassCard className="p-4" glow="violet">
      <motion.div variants={staggerContainer(0.06)} initial="hidden" animate="visible">
        <motion.div className="mb-3 flex items-center justify-between" variants={fadeUp}>
          <h2 className="text-xs font-semibold uppercase tracking-wider text-ms-muted">Sign in</h2>
          <button
            type="button"
            onClick={onNewConversation}
            className="text-xs font-medium text-violet-300 hover:text-violet-200"
          >
            New chat
          </button>
        </motion.div>

        {patient ? (
          <motion.div className="space-y-3" variants={fadeUp}>
            <div className="rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-3 py-2.5">
              <p className="text-sm font-medium text-emerald-100">{profileNameWithContact(patient)}</p>
              <p className="mt-0.5 text-xs text-emerald-200/70">
                Signed in with {profileContactLabel(patient).toLowerCase()}
              </p>
              <p className="mt-1 text-[11px] text-emerald-200/60">Identity verified for this session</p>
            </div>

            <label
              className={`flex cursor-pointer items-start gap-3 rounded-xl border px-3 py-2.5 ${
                patient.consent_granted
                  ? "border-violet-400/30 bg-violet-500/10"
                  : "border-white/10 bg-black/20"
              }`}
            >
              <input
                type="checkbox"
                checked={patient.consent_granted}
                disabled={loading}
                onChange={(e) => handleConsentChange(e.target.checked)}
                className="mt-0.5 h-4 w-4 accent-violet-500"
              />
              <span>
                <span className="block text-sm text-zinc-200">I agree to schedule on my behalf</span>
                <span className="mt-0.5 block text-[11px] text-zinc-500">
                  Required before booking or canceling appointments
                </span>
              </span>
            </label>

            <button
              type="button"
              onClick={handleLogout}
              className="w-full rounded-xl border border-white/10 py-2 text-xs text-zinc-400 hover:border-white/20 hover:text-zinc-200"
            >
              Sign out
            </button>
          </motion.div>
        ) : (
          <>
            <motion.p className="mb-3 text-xs leading-relaxed text-zinc-500" variants={fadeUp}>
              Sign in with Supabase (email or phone). Your name is saved for this account.
            </motion.p>

            <motion.label className="mb-3 block" variants={fadeUp}>
              <span className="text-[10px] font-medium uppercase tracking-wider text-ms-muted">
                Your name
              </span>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="e.g. Jane Doe"
                autoComplete="name"
                className="mt-1.5 w-full rounded-xl border border-white/10 bg-black/40 px-3 py-2.5 text-sm outline-none focus:border-violet-400/35"
                required
              />
            </motion.label>

            <motion.div className="mb-3 flex gap-1 rounded-xl bg-black/30 p-1" variants={fadeUp}>
              {(["email", "phone"] as Tab[]).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTab(t)}
                  className={`flex-1 rounded-lg py-1.5 text-xs font-medium capitalize ${
                    tab === t ? "ms-pill-active text-white" : "text-zinc-500"
                  }`}
                >
                  {t === "email" ? "Email" : "Phone OTP"}
                </button>
              ))}
            </motion.div>

            {tab === "email" ? (
              <motion.form onSubmit={handleEmailSubmit} className="space-y-2" variants={fadeUp}>
                <div className="mb-2 flex gap-2 text-[11px]">
                  <button
                    type="button"
                    onClick={() => setEmailMode("signin")}
                    className={emailMode === "signin" ? "text-violet-300" : "text-zinc-500"}
                  >
                    Sign in
                  </button>
                  <span className="text-zinc-600">·</span>
                  <button
                    type="button"
                    onClick={() => setEmailMode("signup")}
                    className={emailMode === "signup" ? "text-violet-300" : "text-zinc-500"}
                  >
                    Create account
                  </button>
                </div>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Email"
                  className="w-full rounded-xl border border-white/10 bg-black/40 px-3 py-2.5 text-sm outline-none focus:border-violet-400/35"
                  required
                />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Password"
                  className="w-full rounded-xl border border-white/10 bg-black/40 px-3 py-2.5 text-sm outline-none focus:border-violet-400/35"
                  required
                />
                <button
                  type="submit"
                  disabled={loading}
                  className="ms-gradient-cta w-full rounded-xl py-2.5 text-sm font-semibold disabled:opacity-50"
                >
                  {emailMode === "signup" ? "Create account" : "Sign in"}
                </button>
              </motion.form>
            ) : (
              <motion.form onSubmit={handleVerifyOtp} className="space-y-2" variants={fadeUp}>
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+15551234567"
                  className="w-full rounded-xl border border-white/10 bg-black/40 px-3 py-2.5 text-sm outline-none focus:border-violet-400/35"
                  required
                />
                <button
                  type="button"
                  onClick={handleRequestOtp}
                  disabled={loading}
                  className="w-full rounded-xl border border-white/10 py-2 text-xs text-zinc-300 hover:bg-white/5"
                >
                  Send verification code
                </button>
                {otpSent && (
                  <p className="text-[11px] text-amber-200/80">
                    Enter the SMS code from Supabase (enable Phone provider in your project).
                  </p>
                )}
                <input
                  value={otp}
                  onChange={(e) => setOtp(e.target.value)}
                  placeholder="6-digit code"
                  className="w-full rounded-xl border border-white/10 bg-black/40 px-3 py-2.5 text-sm outline-none focus:border-violet-400/35"
                  required
                />
                <button
                  type="submit"
                  disabled={loading}
                  className="ms-gradient-cta w-full rounded-xl py-2.5 text-sm font-semibold disabled:opacity-50"
                >
                  Verify & sign in
                </button>
              </motion.form>
            )}
          </>
        )}

        {error && <p className="mt-2 text-xs text-rose-300">{error}</p>}
      </motion.div>
    </GlassCard>
  );
}
