import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { ArrowRight, KeyRound, Loader2, ShieldCheck } from "lucide-react";
import { ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";
import { BrandMark } from "../components/ui";

const DEMO = [
  { username: "engineer", role: "Engineer", decision: "Which component is underperforming?" },
  { username: "operations", role: "Operations", decision: "What do I fix first today?" },
  { username: "cfo", role: "CFO", decision: "Is the investment case holding?" },
  { username: "presenter", role: "Presenter", decision: "All three truths, side by side" },
];

function ArrayIllustration() {
  // Rows of fixed-tilt tables receding toward the horizon, with a string inverter skid.
  const rows = Array.from({ length: 6 }, (_, i) => i);
  return (
    <svg viewBox="0 70 520 240" className="h-full w-full" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <defs>
        <linearGradient id="pv" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#3d8be6" />
          <stop offset="1" stopColor="#1c5cab" />
        </linearGradient>
      </defs>
      <circle cx="430" cy="110" r="22" fill="#fab219" opacity="0.95" />
      <circle cx="430" cy="110" r="36" fill="#fab219" opacity="0.12" />
      <path d="M0 150 H520" stroke="#2b5a8f" strokeWidth="1" />
      {rows.map((i) => {
        const y = 160 + i * i * 3.2 + i * 14;
        const h = 6 + i * 3.2;
        const inset = 120 - i * 22;
        return (
          <g key={i}>
            <path d={`M${inset} ${y + h} L${inset + 14} ${y} H${520 - inset + 14} L${520 - inset} ${y + h} Z`} fill="url(#pv)" />
            <path d={`M${inset + 7} ${y + h / 2} H${520 - inset + 7}`} stroke="#9ec5f4" strokeOpacity="0.45" strokeWidth="0.8" />
            {Array.from({ length: 10 }, (_, k) => {
              const x = inset + 14 + ((520 - 2 * inset) / 10) * k;
              return <path key={k} d={`M${x} ${y} L${x - 14} ${y + h}`} stroke="#9ec5f4" strokeOpacity="0.35" strokeWidth="0.8" />;
            })}
          </g>
        );
      })}
      <rect x="452" y="248" width="44" height="26" rx="2" fill="#dfe4eb" />
      <rect x="458" y="254" width="14" height="14" fill="#4a5668" />
      <rect x="476" y="254" width="14" height="5" fill="#0ca30c" />
    </svg>
  );
}

export default function LoginPage() {
  const { session, login } = useAuth();
  const nav = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (session) return <Navigate to={session.home} replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const s = await login(username, password);
      nav(s.home, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError && err.status === 401 ? "Username or password is incorrect." : "Cannot reach the API.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-full lg:grid-cols-[1.1fr_1fr]">
      <div className="relative hidden flex-col gap-8 overflow-hidden bg-steel-900 p-10 text-white lg:flex">
        <div className="relative flex items-center gap-3">
          <BrandMark size={34} />
          <div>
            <p className="text-[15px] font-semibold">Three Truths</p>
            <p className="text-[12px] text-steel-300">Solar performance assurance</p>
          </div>
        </div>
        <div className="relative my-auto max-w-[520px]">
          <p className="text-[28px] font-semibold leading-tight">One asset. One evidence chain. Three decision-ready truths.</p>
          <p className="mt-3 max-w-md text-[14px] leading-relaxed text-steel-200">
            The engineer, the O&amp;M manager and the CFO read the same plant from one model. Each view is enforced on the
            server — and nobody can quietly move the target.
          </p>
          <div className="mt-6 aspect-[520/240] overflow-hidden rounded-xl border border-white/10 bg-gradient-to-b from-[#123864] to-[#0d2a4b]">
            <ArrayIllustration />
          </div>
          <div className="mt-4 grid grid-cols-3 gap-3 text-[12px]">
            {[
              ["60 MWp", "Thar-1 fixed tilt"],
              ["35,136", "15-min intervals"],
              ["P50 frozen", "baseline v1"],
            ].map(([a, b]) => (
              <div key={a} className="rounded-lg border border-white/15 bg-white/5 px-3 py-2 backdrop-blur-sm">
                <p className="text-[15px] font-semibold">{a}</p>
                <p className="text-steel-300">{b}</p>
              </div>
            ))}
          </div>
        </div>
        <p className="relative text-[11px] text-steel-300">Monitoring only — no command path to equipment.</p>
      </div>

      <div className="flex items-center justify-center bg-plane px-6 py-10">
        <div className="w-full max-w-[400px]">
          <div className="mb-6 flex items-center gap-3 lg:hidden">
            <BrandMark size={32} />
            <p className="text-[16px] font-semibold">Three Truths</p>
          </div>
          <h1 className="text-[22px] font-semibold tracking-tight">Sign in</h1>
          <p className="mt-1 text-[13.5px] text-ink-3">Your role decides which truth you see.</p>
          <form onSubmit={submit} className="card mt-6 space-y-4 p-5">
            <label className="block" htmlFor="username">
              <span className="label">Username</span>
              <input
                id="username"
                name="username"
                className="input mt-1.5"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoFocus
                required
              />
            </label>
            <label className="block" htmlFor="password">
              <span className="label">Password</span>
              <input
                id="password"
                name="password"
                className="input mt-1.5"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>
            {error && (
              <p className="rounded-md border border-critical/30 bg-critical-bg px-3 py-2 text-[13px] text-critical-ink" role="alert">
                {error}
              </p>
            )}
            <button className="btn-primary w-full py-2.5" disabled={busy}>
              {busy ? <Loader2 size={16} className="animate-spin" /> : <KeyRound size={15} />} Sign in
            </button>
            <p className="flex items-center gap-1.5 text-[11.5px] text-ink-4">
              <ShieldCheck size={13} /> Role and plant scope are carried in a signed token and enforced by the API.
            </p>
          </form>

          <div className="mt-6">
            <p className="label mb-2">Demo accounts</p>
            <div className="grid grid-cols-2 gap-2">
              {DEMO.map((d) => (
                <button
                  key={d.username}
                  type="button"
                  className="card group px-3 py-2.5 text-left transition hover:border-brand-500"
                  onClick={() => {
                    setUsername(d.username);
                    setPassword(`thar1-${d.username}`);
                  }}
                >
                  <span className="flex items-center justify-between text-[13px] font-semibold text-ink">
                    {d.role}
                    <ArrowRight size={13} className="text-ink-4 transition group-hover:translate-x-0.5 group-hover:text-brand-600" />
                  </span>
                  <span className="mt-0.5 block text-[11.5px] leading-snug text-ink-3">{d.decision}</span>
                </button>
              ))}
            </div>
            <p className="mt-2 text-[11px] text-ink-4">Click a card to fill its demo credentials (password: thar1-&lt;username&gt;).</p>
          </div>
        </div>
      </div>
    </div>
  );
}
