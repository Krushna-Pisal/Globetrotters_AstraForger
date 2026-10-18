import { useMemo, useState, type ReactNode } from "react";
import { Eye, Info, MapPin, RotateCcw, Save, ShieldAlert } from "lucide-react";
import { AppShell } from "../components/AppShell";
import { Notice } from "../components/ui";
import { useAuth } from "../lib/auth";

// UI mock (not wired to the API): prefilled with the synthetic Thar-1 values from configs/plant/thar1.yaml.
const DEFAULTS = {
  name: "Thar-1 (fictional demo plant)",
  plantId: "THAR1",
  lat: "27.54",
  lon: "71.91",
  tz: "Asia/Kolkata",
  cod: "2023-04-01",
  dcKwp: "60000",
  acKw: "50000",
  contractedKw: "50000",
  mounting: "fixed",
  tilt: "25",
  azimuth: "180",
  albedo: "0.25",
  transposition: "perez",
  gamma: "-0.35",
  tempModel: "sapm_open_rack_glass_polymer",
  degradation: "0.5",
  invCount: "20",
  invAcKw: "2500",
  invDcKwp: "3000",
  invEta: "98",
  invModel: "pvwatts",
  mismatch: "1.5",
  dcWiring: "1.5",
  lid: "1.0",
  exportLoss: "1.5",
  aSoiling: "2.0",
  aAvailability: "1.0",
  aCurtailment: "0.0",
  aGrid: "0.0",
  weatherPrimary: "open_meteo",
  weatherFallback: "nasa_power",
  tmy: "pvgis_era5",
  interval: "15",
  downscale: "clearsky_index",
  modelVersion: "perf-1.0",
  meterId: "MTR-DP",
  wsId: "WS-01",
};
type Cfg = typeof DEFAULTS;

const BLOCKS = [
  { id: "B1", inverters: ["INV-01", "INV-02", "INV-03", "INV-04", "INV-05"] },
  { id: "B2", inverters: ["INV-06", "INV-07", "INV-08", "INV-09", "INV-10"] },
  { id: "B3", inverters: ["INV-11", "INV-12", "INV-13", "INV-14", "INV-15"] },
  { id: "B4", inverters: ["INV-16", "INV-17", "INV-18", "INV-19", "INV-20"] },
];
const STATUS_CODES = [
  { scope: "Inverter", code: "RUNNING", category: "normal", cause: "—", controllable: "—" },
  { scope: "Inverter", code: "WAIT_GRID", category: "normal (plant offline)", cause: "—", controllable: "—" },
  { scope: "Inverter", code: "CURTAILED", category: "normal (following setpoint)", cause: "—", controllable: "—" },
  { scope: "Inverter", code: "FAULT_OVERTEMP", category: "equipment outage", cause: "IGBT_OVERTEMP", controllable: "yes" },
  { scope: "Inverter", code: "FAULT_GRID_ISOLATION", category: "equipment outage", cause: "ISO_FAULT", controllable: "yes" },
  { scope: "Inverter", code: "OFFLINE", category: "equipment outage", cause: "INVERTER_OFFLINE", controllable: "yes" },
  { scope: "Plant", code: "OFFLINE", category: "grid unavailability", cause: "LINE_OUTAGE", controllable: "no" },
  { scope: "Plant", code: "CURTAILED", category: "curtailment", cause: "SLDC_BACKDOWN", controllable: "no" },
];
const SECTIONS = [
  ["site", "Site & identity"],
  ["capacity", "Capacity"],
  ["array", "Array geometry"],
  ["modules", "Modules"],
  ["inverters", "Inverters"],
  ["hierarchy", "Hierarchy"],
  ["structural", "Structural losses"],
  ["assumed", "Baseline-assumed losses"],
  ["weather", "Weather & model"],
  ["metering", "Metering & sensors"],
  ["status", "SCADA status codes"],
] as const;

export default function ConfigPage() {
  const { session } = useAuth();
  const editable = session?.role === "presenter";
  const [cfg, setCfg] = useState<Cfg>(DEFAULTS);
  const [toast, setToast] = useState<string | null>(null);
  const dirty = useMemo(() => (Object.keys(DEFAULTS) as (keyof Cfg)[]).filter((k) => cfg[k] !== DEFAULTS[k]).length, [cfg]);
  const set = (k: keyof Cfg) => (v: string) => setCfg((c) => ({ ...c, [k]: v }));
  const f = (k: keyof Cfg) => ({ value: cfg[k], onChange: set(k), disabled: !editable, changed: cfg[k] !== DEFAULTS[k] });

  // Display-only helpers for configuration inputs (not plant metrics).
  const ratio = Number(cfg.acKw) > 0 ? (Number(cfg.dcKwp) / Number(cfg.acKw)).toFixed(2) : "—";
  const az = Number(cfg.azimuth);
  const southZero = Number.isFinite(az) ? (((az - 180 + 540) % 360) - 180).toFixed(0) : "—";

  return (
    <AppShell title="Plant configuration" decision="The plant description the expected-output model runs on: site, array, equipment and loss register.">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <span className="inline-flex items-center gap-1.5 rounded-md border border-line bg-surface px-2.5 py-1 text-[12px] text-ink-2">
          <Info size={13} className="text-ink-4" /> Source <span className="font-mono">configs/plant/thar1.yaml</span>
        </span>
        {editable ? (
          <span className="inline-flex items-center gap-1.5 rounded-md border border-brand-100 bg-brand-50 px-2.5 py-1 text-[12px] font-medium text-brand-700">
            <ShieldAlert size={13} /> Editing as presenter (admin)
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 rounded-md border border-line bg-steel-50 px-2.5 py-1 text-[12px] font-medium text-ink-3">
            <Eye size={13} /> Read-only for your role
          </span>
        )}
        {editable && (
          <div className="ml-auto flex items-center gap-2">
            {dirty > 0 && <span className="text-[12px] text-warning-ink">{dirty} unsaved change{dirty > 1 ? "s" : ""}</span>}
            <button className="btn-ghost" disabled={!dirty} onClick={() => setCfg(DEFAULTS)}>
              <RotateCcw size={14} /> Reset
            </button>
            <button
              className="btn-primary"
              disabled={!dirty}
              onClick={() => {
                setToast("Mock only — the configuration is not connected to the backend yet, nothing was saved.");
                window.setTimeout(() => setToast(null), 4500);
              }}
            >
              <Save size={14} /> Save configuration
            </button>
          </div>
        )}
      </div>
      {toast && (
        <div className="mb-4">
          <Notice tone="warn">{toast}</Notice>
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-[200px_1fr]">
        <nav className="hidden lg:block">
          <div className="sticky top-[84px] space-y-0.5">
            <p className="label px-2 pb-2">Sections</p>
            {SECTIONS.map(([id, label]) => (
              <a key={id} href={`#${id}`} className="block rounded-md px-2 py-1.5 text-[13px] text-ink-2 hover:bg-surface hover:text-brand-700">
                {label}
              </a>
            ))}
          </div>
        </nav>

        <div className="space-y-4">
          <Section id="site" title="Site & identity" note="Location drives solar position; timezone sets the local day and month boundaries.">
            <Grid>
              <Field label="Plant name" wide {...f("name")} />
              <Field label="Plant ID" mono {...f("plantId")} />
              <Field label="Latitude" unit="° N" type="number" {...f("lat")} />
              <Field label="Longitude" unit="° E" type="number" {...f("lon")} />
              <SelectField label="Timezone" options={[["Asia/Kolkata", "Asia/Kolkata (UTC+05:30)"]]} {...f("tz")} />
              <Field label="Commercial operation date" type="date" hint="Start of degradation" {...f("cod")} />
            </Grid>
            <div className="mt-4 flex items-center gap-3 rounded-lg border border-line bg-steel-50 px-3 py-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
                <MapPin size={17} />
              </span>
              <div className="text-[12.5px]">
                <p className="font-medium text-ink">
                  {cfg.lat}° N, {cfg.lon}° E · Bhadla solar zone, Rajasthan (assumed site)
                </p>
                <p className="text-ink-3">Fictional plant; weather is real 2024 reanalysis for these coordinates.</p>
              </div>
            </div>
          </Section>

          <Section id="capacity" title="Capacity" note="CUF in the PPA is measured on the contracted AC capacity.">
            <Grid>
              <Field label="DC capacity" unit="kWp" type="number" {...f("dcKwp")} />
              <Field label="AC capacity" unit="kW" type="number" {...f("acKw")} />
              <Field label="Contracted AC capacity" unit="kW" type="number" hint="CUF basis" {...f("contractedKw")} />
              <ReadOnly label="DC/AC ratio" value={ratio} hint="Above 1.0 clips on clear noons" />
            </Grid>
          </Section>

          <Section id="array" title="Array geometry" note="Plane-of-array irradiance comes from these values via the transposition model.">
            <Grid>
              <SelectField label="Mounting" options={[["fixed", "Fixed tilt"], ["single_axis", "Single-axis tracker"]]} {...f("mounting")} />
              <Field label="Tilt" unit="°" type="number" {...f("tilt")} />
              <Field label="Azimuth (pvlib)" unit="°" type="number" hint="180 = south" {...f("azimuth")} />
              <ReadOnly label="Azimuth (Open-Meteo / PVGIS)" value={`${southZero}°`} hint="0 = south — converted, never mixed" />
              <Field label="Ground albedo" type="number" {...f("albedo")} />
              <SelectField label="Transposition model" options={[["perez", "Perez"], ["haydavies", "Hay–Davies"], ["isotropic", "Isotropic"]]} {...f("transposition")} />
            </Grid>
          </Section>

          <Section id="modules" title="Modules">
            <Grid>
              <Field label="Temperature coefficient (P)" unit="%/°C" type="number" {...f("gamma")} />
              <SelectField
                label="Cell temperature model"
                options={[
                  ["sapm_open_rack_glass_polymer", "SAPM · open rack, glass/polymer"],
                  ["sapm_open_rack_glass_glass", "SAPM · open rack, glass/glass"],
                  ["pvsyst_freestanding", "PVsyst · free-standing"],
                ]}
                {...f("tempModel")}
              />
              <Field label="Annual degradation" unit="%/yr" type="number" hint="Applied in both expected output and baseline" {...f("degradation")} />
            </Grid>
          </Section>

          <Section id="inverters" title="Inverters" note="All inverters share one model in this plant.">
            <Grid>
              <Field label="Inverter count" type="number" {...f("invCount")} />
              <Field label="AC rating per inverter" unit="kW" type="number" {...f("invAcKw")} />
              <Field label="DC per inverter" unit="kWp" type="number" {...f("invDcKwp")} />
              <Field label="Nominal efficiency" unit="%" type="number" {...f("invEta")} />
              <SelectField label="Inverter model" options={[["pvwatts", "PVWatts"], ["sandia", "Sandia (CEC)"]]} {...f("invModel")} />
            </Grid>
          </Section>

          <Section id="hierarchy" title="Hierarchy" note="Plant → block → inverter. Asset ids are referenced by every event and metric." bodyClass="p-0">
            <table className="tbl">
              <thead>
                <tr>
                  <th className="w-24">Block</th>
                  <th>Inverters</th>
                  <th className="w-40 text-right">DC / AC</th>
                </tr>
              </thead>
              <tbody>
                {BLOCKS.map((b) => (
                  <tr key={b.id}>
                    <td className="font-mono font-semibold text-ink">{b.id}</td>
                    <td>
                      <div className="flex flex-wrap gap-1.5">
                        {b.inverters.map((i) => (
                          <span key={i} className="rounded border border-line bg-steel-50 px-1.5 py-0.5 font-mono text-[11.5px] text-ink-2">
                            {i}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="num text-right">15,000 kWp / 12,500 kW</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>

          <Section id="structural" title="Structural losses" note="Design losses applied in BOTH expected output and the baseline — never attributed as variance.">
            <Grid>
              <Field label="Module mismatch" unit="%" type="number" {...f("mismatch")} />
              <Field label="DC wiring" unit="%" type="number" {...f("dcWiring")} />
              <Field label="LID & nameplate" unit="%" type="number" {...f("lid")} />
              <Field label="Export to delivery point" unit="%" type="number" hint="Transformer + line to MTR-DP" {...f("exportLoss")} />
            </Grid>
          </Section>

          <Section id="assumed" title="Baseline-assumed losses" note="Used for P50 only. Attribution reports actual − assumed for each.">
            <Notice tone="warn">The approved baseline is frozen. Changing these values creates a new baseline version; v1 stays visible.</Notice>
            <div className="mt-3">
              <Grid>
                <Field label="Soiling" unit="%" type="number" {...f("aSoiling")} />
                <Field label="Availability" unit="%" type="number" {...f("aAvailability")} />
                <Field label="Curtailment" unit="%" type="number" {...f("aCurtailment")} />
                <Field label="Grid unavailability" unit="%" type="number" {...f("aGrid")} />
              </Grid>
            </div>
          </Section>

          <Section id="weather" title="Weather & model inputs" note="Fetched once and cached; everything after runs offline.">
            <Grid>
              <SelectField label="Primary weather" options={[["open_meteo", "Open-Meteo archive (ERA5)"], ["nasa_power", "NASA POWER hourly"]]} {...f("weatherPrimary")} />
              <SelectField label="Fallback weather" options={[["nasa_power", "NASA POWER hourly"], ["none", "None"]]} {...f("weatherFallback")} />
              <SelectField label="Baseline TMY" options={[["pvgis_era5", "PVGIS TMY (ERA5, 2005–2023)"], ["pvgis_sarah3", "PVGIS TMY (SARAH3 — not available at 71.9° E)"]]} {...f("tmy")} />
              <SelectField label="Interval" options={[["15", "15 minutes"], ["60", "60 minutes"]]} {...f("interval")} />
              <SelectField label="Hourly → 15-min downscaling" options={[["clearsky_index", "Clear-sky index"], ["linear", "Linear"]]} {...f("downscale")} />
              <ReadOnly label="Model version" value={cfg.modelVersion} hint="Changing inputs writes new expected-output rows" />
            </Grid>
          </Section>

          <Section id="metering" title="Metering & sensors">
            <Grid>
              <Field label="Delivery-point meter" mono hint="Settlement boundary" {...f("meterId")} />
              <Field label="Weather station" mono {...f("wsId")} />
            </Grid>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {["POA irradiance", "GHI", "Module temperature", "Ambient temperature", "Wind speed", "Precipitation"].map((q) => (
                <span key={q} className="rounded-full border border-line bg-steel-50 px-2 py-0.5 text-[11.5px] text-ink-2">
                  {q}
                </span>
              ))}
            </div>
          </Section>

          <Section id="status" title="SCADA status codes" note="How reported status codes map to events. Detection never reads the scenario file." bodyClass="p-0">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Scope</th>
                  <th>Status code</th>
                  <th>Category</th>
                  <th>Cause code</th>
                  <th>Controllable</th>
                </tr>
              </thead>
              <tbody>
                {STATUS_CODES.map((r) => (
                  <tr key={r.scope + r.code}>
                    <td>{r.scope}</td>
                    <td className="font-mono text-[12.5px] font-medium text-ink">{r.code}</td>
                    <td>{r.category}</td>
                    <td className="font-mono text-[12.5px]">{r.cause}</td>
                    <td>{r.controllable}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>
        </div>
      </div>
    </AppShell>
  );
}

function Section({ id, title, note, children, bodyClass = "p-4" }: { id: string; title: string; note?: string; children: ReactNode; bodyClass?: string }) {
  return (
    <section id={id} className="card scroll-mt-24">
      <header className="card-head">
        <div>
          <h2 className="card-title">{title}</h2>
          {note && <p className="mt-0.5 text-[12px] text-ink-3">{note}</p>}
        </div>
      </header>
      <div className={bodyClass}>{children}</div>
    </section>
  );
}

function Grid({ children }: { children: ReactNode }) {
  return <div className="grid gap-x-4 gap-y-3.5 sm:grid-cols-2 xl:grid-cols-3">{children}</div>;
}

type FieldProps = {
  label: string;
  value: string;
  onChange: (v: string) => void;
  disabled: boolean;
  changed: boolean;
  unit?: string;
  hint?: string;
  type?: string;
  mono?: boolean;
  wide?: boolean;
};

function Field({ label, value, onChange, disabled, changed, unit, hint, type = "text", mono, wide }: FieldProps) {
  return (
    <label className={`block ${wide ? "sm:col-span-2 xl:col-span-2" : ""}`}>
      <span className="label flex items-center gap-1.5">
        {label}
        {changed && <span className="h-1.5 w-1.5 rounded-full bg-warning" title="Changed" />}
      </span>
      <div className="relative mt-1.5">
        <input
          type={type}
          step="any"
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
          className={`input disabled:cursor-default disabled:bg-steel-50 disabled:text-ink-2 ${unit ? "pr-14" : ""} ${mono ? "font-mono" : ""}`}
        />
        {unit && <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-[12px] text-ink-4">{unit}</span>}
      </div>
      {hint && <span className="mt-1 block text-[11.5px] text-ink-4">{hint}</span>}
    </label>
  );
}

function SelectField({ label, value, onChange, disabled, changed, options }: FieldProps & { options: [string, string][] }) {
  return (
    <label className="block">
      <span className="label flex items-center gap-1.5">
        {label}
        {changed && <span className="h-1.5 w-1.5 rounded-full bg-warning" title="Changed" />}
      </span>
      <select
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className="input mt-1.5 disabled:cursor-default disabled:bg-steel-50 disabled:text-ink-2"
      >
        {options.map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
    </label>
  );
}

function ReadOnly({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div>
      <span className="label">{label}</span>
      <div className="mt-1.5 rounded-md border border-dashed border-line-strong bg-steel-50 px-3 py-2 font-medium text-ink-2">{value}</div>
      {hint && <span className="mt-1 block text-[11.5px] text-ink-4">{hint}</span>}
    </div>
  );
}
