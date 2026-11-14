import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  AlertCircle,
  ArrowRight,
  AudioLines,
  Check,
  ChevronRight,
  CircleHelp,
  Code2,
  Download,
  Eye,
  FileAudio,
  FileImage,
  FileVideo,
  Fingerprint,
  Info,
  Layers3,
  LockKeyhole,
  Menu,
  RefreshCw,
  ScanFace,
  Shield,
  ShieldAlert,
  UploadCloud,
  Video,
  X,
  XCircle,
} from "lucide-react";
import { analyzeMedia, API_DOCS_URL, checkBackend } from "./api";
import { findingCopy } from "./copy";
import { formatModelScore, presentModel } from "./modelPresentation";
import { SpatialMetrics } from "./SpatialMetrics";
import type { AnalysisReport, Evidence, MediaKind, Severity } from "./types";

type Stage = "idle" | "analyzing" | "complete" | "error";

const categoryLabels: Record<Evidence["category"], string> = {
  integrity: "File checks",
  metadata: "File details",
  visual: "Image checks",
  model: "Model checks",
  provenance: "Source history",
};

const severityIcons: Record<Severity, typeof Info> = {
  info: Info,
  low: CircleHelp,
  medium: AlertCircle,
  high: ShieldAlert,
};

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const unit = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** unit).toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`;
}

function fileKind(file: File): MediaKind {
  if (file.type.startsWith("image/")) return "image";
  if (file.type.startsWith("video/")) return "video";
  if (file.type.startsWith("audio/")) return "audio";
  return "unknown";
}

function Brand() {
  return (
    <a className="brand" href="#top" aria-label="VeriSight home">
      <span className="brand-word">VERI<span>/</span>SIGHT</span>
      <span className="brand-sub">Look a little closer</span>
    </a>
  );
}

function Header() {
  const [open, setOpen] = useState(false);
  return (
    <header className="site-header">
      <div className="shell nav-wrap">
        <Brand />
        <button className="mobile-menu" onClick={() => setOpen((value) => !value)} aria-label="Toggle navigation">
          {open ? <X size={21} /> : <Menu size={21} />}
        </button>
        <nav className={open ? "nav open" : "nav"} aria-label="Main navigation">
          <a href="#analyze" onClick={() => setOpen(false)}><i>01</i> Check a file</a>
          <a href="#method" onClick={() => setOpen(false)}><i>02</i> How it works</a>
          <a href="#responsibility" onClick={() => setOpen(false)}><i>03</i> What to know</a>
          <a className="nav-cta" href={API_DOCS_URL} target="_blank" rel="noreferrer">
            <Code2 size={14} /> For developers
          </a>
        </nav>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="hero" id="top">
      <div className="shell hero-content">
        <div className="hero-copy-block">
          <div className="eyebrow"><span>SEE BEYOND THE SURFACE</span><b>PHOTO · VIDEO · AUDIO</b></div>
          <h1>Every frame<br /><em>leaves a trace.</em></h1>
          <p className="hero-copy">
            Could this picture be AI-generated? Get an experimental model’s assessment, with clear explanations of what it can and can’t tell you.
          </p>
          <div className="hero-actions">
            <a href="#analyze" className="button primary">Check your file <ArrowRight size={15} /></a>
            <a href="#method" className="button ghost"><span>How it works</span><span>↓</span></a>
          </div>
          <div className="hero-facts">
            <span><b>A</b> IMAGE</span>
            <span><b>V</b> VIDEO</span>
            <span><b>W</b> AUDIO</span>
            <span className="hero-fact-end">NO FILES KEPT</span>
          </div>
        </div>
        <div className="hero-plate" aria-label="Illustrated landscape with a magnified view of its pixels. A design illustration, not an analysis result.">
          <div className="plate-head"><span>THERE’S MORE TO THE PICTURE</span><b>ILLUSTRATION</b></div>
          <div className="picture-study" aria-hidden="true">
            <svg viewBox="0 0 640 720" preserveAspectRatio="xMidYMid meet">
              <defs>
                <linearGradient id="study-sky" x2="0" y2="1"><stop stopColor="#d0b99a"/><stop offset="1" stopColor="#f1dfbe"/></linearGradient>
                <pattern id="pixel-grid" width="22" height="22" patternUnits="userSpaceOnUse"><path d="M22 0H0V22" fill="none" stroke="#f4e5cf" strokeWidth="1" opacity=".35"/></pattern>
                <clipPath id="landscape-clip"><rect x="62" y="120" width="496" height="340"/></clipPath>
                <clipPath id="zoom-clip"><circle cx="443" cy="476" r="116"/></clipPath>
              </defs>
              <rect x="82" y="100" width="496" height="360" fill="none" stroke="#80796a" opacity=".5" transform="rotate(7 330 280)"/>
              <rect x="48" y="106" width="524" height="390" fill="#ece2cf" transform="rotate(-3 310 300)"/>
              <g clipPath="url(#landscape-clip)">
                <rect x="62" y="120" width="496" height="340" fill="url(#study-sky)"/>
                <circle cx="414" cy="209" r="48" fill="#f7e9cc"/>
                <path d="M40 380L190 214L302 345L388 262L580 410V470H40Z" fill="#929488"/>
                <path d="M94 385L238 277L370 411L498 307L582 385V470H40Z" fill="#555f59"/>
                <path d="M40 444Q192 348 306 408T580 390V470H40Z" fill="#2b3935"/>
                <path d="M289 460Q341 414 314 399Q287 385 324 367" fill="none" stroke="#d1baa0" strokeWidth="9"/>
              </g>
              <rect x="281" y="304" width="62" height="62" fill="none" stroke="#ef4a32" strokeWidth="2"/>
              <path d="M343 335L414 386M312 366L348 440" stroke="#ef4a32" strokeWidth="1" strokeDasharray="4 5"/>
              <circle cx="443" cy="476" r="126" fill="#171714" stroke="#ef4a32" strokeWidth="2"/>
              <g clipPath="url(#zoom-clip)">
                <rect x="320" y="350" width="250" height="250" fill="#929488"/>
                <path d="M320 394H364V416H386V438H430V460H452V482H496V504H562V610H320Z" fill="#555f59"/>
                <path d="M320 526H364V504H408V526H452V548H518V526H562V610H320Z" fill="#2b3935"/>
                <path d="M408 600V570H430V548H452V526H430V504H408V482H430V460H452" stroke="#d1baa0" strokeWidth="20" fill="none"/>
                <rect x="320" y="350" width="250" height="250" fill="url(#pixel-grid)"/>
              </g>
              <path d="M78 530V556H278" fill="none" stroke="#7a756a"/>
              <text x="78" y="580" fill="#bfb7a8" fontSize="12" fontFamily="monospace">A closer look.</text>
              <text x="78" y="602" fill="#777267" fontSize="10" fontFamily="monospace">Small details. Useful clues.</text>
            </svg>
          </div>
          <div className="plate-foot"><span>LOOK CLOSER. ASK QUESTIONS.</span><span>EXAMPLE ARTWORK</span></div>
        </div>
      </div>
    </section>
  );
}

interface UploadPanelProps {
  stage: Stage;
  file: File | null;
  elapsed: number;
  error: string;
  onFile: (file: File) => void;
  onClear: () => void;
}

function BackendStatus() {
  const [message, setMessage] = useState("Checking backend connection…");
  const [checking, setChecking] = useState(true);
  const [offline, setOffline] = useState(false);
  const check = async () => {
    setChecking(true);
    try {
      setMessage(await checkBackend());
      setOffline(false);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Backend unavailable.");
      setOffline(true);
    } finally { setChecking(false); }
  };
  useEffect(() => { void check(); }, []);
  return <div className={`backend-status ${offline ? "offline" : ""}`} role="status">
    <span>{checking ? "Checking backend connection…" : message}</span>
    <button className="text-button" disabled={checking} onClick={() => void check()}><RefreshCw size={14} /> Re-check connection</button>
  </div>;
}

function UploadPanel({ stage, file, elapsed, error, onFile, onClear }: UploadPanelProps) {
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const kind = file ? fileKind(file) : "unknown";
  const FileIcon = kind === "image" ? FileImage : kind === "video" ? FileVideo : FileAudio;

  const acceptFile = (candidate?: File) => {
    if (candidate) onFile(candidate);
  };

  return (
    <div className="upload-card">
      {stage === "analyzing" && file ? (
        <div className="analysis-progress" aria-live="polite">
          <div className="file-chip large">
            <span className="file-icon"><FileIcon size={24} /></span>
            <div><strong>{file.name}</strong><small>{formatBytes(file.size)} · {file.type || "unknown type"}</small></div>
          </div>
          <div className="scan-visual">
            <div className="scan-core"><ScanFace size={42} strokeWidth={1.25} /><span className="scan-line" /></div>
            <span className="orbit orbit-one" /><span className="orbit orbit-two" />
          </div>
          <h3>Taking a closer look</h3>
          <p>Detailed image checks can take 1–2 minutes on this computer. Keep this page open.</p>
          <div className="progress-track" role="progressbar" aria-label="Image analysis in progress"><span className="indeterminate" /></div>
          <div className="progress-label"><span>{elapsed}s elapsed</span><span>Waiting for the complete result</span></div>
        </div>
      ) : (
        <>
          <div
            className={`drop-zone ${dragging ? "dragging" : ""}`}
            onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
            onDragOver={(event) => event.preventDefault()}
            onDragLeave={(event) => { event.preventDefault(); setDragging(false); }}
            onDrop={(event) => { event.preventDefault(); setDragging(false); acceptFile(event.dataTransfer.files[0]); }}
            onClick={() => input.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") input.current?.click(); }}
          >
            <input
              ref={input}
              type="file"
              accept="image/*,video/*,audio/*,.mkv,.m4a"
              onChange={(event) => acceptFile(event.target.files?.[0])}
              hidden
            />
            <span className="drop-index">YOUR FILE GOES HERE</span>
            <span className="upload-icon"><UploadCloud size={30} strokeWidth={1.5} /></span>
            <h3>Drop a file.<br />Let’s take a look.</h3>
            <p>Drop a file here or <span>select from device →</span></p>
            <small>UP TO 100 MB · YOUR FILE ISN’T KEPT AFTER THE CHECK</small>
            <div className="media-pills">
              <span><FileImage size={13} /> JPG / PNG / WEBP</span>
              <span><Video size={13} /> MP4 / MOV / WEBM</span>
              <span><AudioLines size={13} /> MP3 / WAV</span>
            </div>
          </div>
          {error && <div className="error-message" role="alert"><XCircle size={17} /> <span>{error}</span></div>}
          {stage === "error" && file && (
            <div className="upload-retry"><button className="retry-link" onClick={() => onFile(file)}><RefreshCw size={14} /> Retry this file</button><button className="retry-link" onClick={onClear}>Choose another file</button></div>
          )}
        </>
      )}
    </div>
  );
}

function TrustRail() {
  return (
    <div className="trust-rail">
      <div><b>01</b><Fingerprint size={19} /><span><strong>A unique file ID</strong>Recognize the same file</span></div>
      <div><b>02</b><Layers3 size={19} /><span><strong>More than one check</strong>Look at several clues</span></div>
      <div><b>03</b><Activity size={19} /><span><strong>Clear explanations</strong>See what each clue means</span></div>
      <div><b>04</b><LockKeyhole size={19} /><span><strong>Your file stays yours</strong>We don’t keep a copy</span></div>
    </div>
  );
}

function MediaPreview({ file }: { file: File }) {
  const [url, setUrl] = useState("");
  useEffect(() => {
    const objectUrl = URL.createObjectURL(file);
    setUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);
  const kind = fileKind(file);
  if (!url) return null;
  if (kind === "image") return <img src={url} alt="Uploaded media preview" />;
  if (kind === "video") return <video src={url} controls aria-label="Uploaded video preview" />;
  if (kind === "audio") return <div className="audio-preview"><FileAudio size={44} /><audio src={url} controls /></div>;
  return <div className="audio-preview"><Shield size={44} /><span>Preview unavailable</span></div>;
}

function ModelRechecks({ report }: { report: AnalysisReport }) {
  const presentation = presentModel(report.detection);
  return (
    <div className="model-rechecks">
      <span className="result-label">RESIZING & COMPRESSION CHECK</span>
      <h3>{presentation.recheckTitle}</h3>
      <p>{presentation.recheckDescription}</p>
      {presentation.checks.length > 0 && <><p className="score-key">AI-class output · 0–100 scale, not confidence</p><dl className="model-comparisons">{presentation.checks.map(check => <div key={check.key}><dt>{check.name}</dt><dd><strong>{formatModelScore(check.value)} <small>/100</small></strong><span>{check.preference === "neither class" ? "Even outputs" : `Favors ${check.preference}`}</span></dd></div>)}</dl>{presentation.checks.length > 1 && <p>Re-check range: <strong>{((Math.max(...presentation.checks.map(c => c.value)) - Math.min(...presentation.checks.map(c => c.value))) * 100).toFixed(2)} points</strong></p>}</>}
    </div>
  );
}

function EvidenceCard({ item }: { item: Evidence }) {
  const Icon = severityIcons[item.severity];
  const copy = findingCopy[item.id] ?? item;
  return (
    <article className={`evidence-card severity-${item.severity}`}>
      <span className="evidence-icon"><Icon size={18} /></span>
      <div className="evidence-body">
        <div className="evidence-heading"><h4>{copy.title}</h4><span>{categoryLabels[item.category]}</span></div>
        <p>{copy.description}</p>
        {item.observed && <details className="technical-detail"><summary>Technical details</summary><code>{item.observed}</code></details>}
      </div>
    </article>
  );
}

function Results({ report, file, onReset }: { report: AnalysisReport; file: File; onReset: () => void }) {
  const [filter, setFilter] = useState<Evidence["category"] | "all">("all");
  const filtered = report.evidence.filter((item) => filter === "all" || item.category === filter);
  const presentation = presentModel(report.detection);
  const verdictIcon = report.verdict === "suspicious" ? ShieldAlert : report.verdict === "review" ? AlertCircle : CircleHelp;
  const VerdictIcon = verdictIcon;

  const download = () => {
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `verisight-${report.analysis_id.slice(0, 8)}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section className="results" aria-live="polite">
      <div className="results-toolbar">
        <div><span className="success-dot"><Check size={13} /></span><strong>Analysis complete</strong><small>{report.processing_ms} ms · Engine {report.engine_version}</small></div>
        <div><button className="text-button" onClick={download}><Download size={15} /> Download report</button><button className="button compact" onClick={onReset}><RefreshCw size={15} /> Check another file</button></div>
      </div>

      <div className="verdict-panel model-result-panel">
        <div className={`verdict-copy verdict-${report.verdict}`}>
          <span className="verdict-icon"><VerdictIcon size={23} /></span>
          <div><small>EXPERIMENTAL MODEL RESULT</small><h2>{presentation.title}</h2><p>{presentation.description}</p></div>
        </div>
        <ModelRechecks report={report} />
      </div>

      {!report.limitations.neural_detector_available && (
        <div className="coverage-warning"><AlertCircle size={18} /><div><strong>AI detection did not run</strong><span>{report.detection.message}</span></div></div>
      )}
      {report.detection.status === "complete" && <div className="model-info"><p><strong>How to read this:</strong> This is an experimental AI-generation classifier. Its outputs are not confidence estimates; it can be wrong. It does not detect face swaps or verify authenticity.</p><details><summary>View raw outputs and model limitations</summary>{presentation.checks.map(check => <p key={check.key}>{check.name}: AI-class output {check.value.toFixed(6)} (0–1 scale)</p>)}<p>{report.detection.model_id} · revision {report.detection.revision?.slice(0, 12)}</p>{report.limitations.notes.map(note => <p key={note}>{note}</p>)}</details></div>}

      <SpatialMetrics analysis={report.spatial_analysis} />
      <div className="report-grid">
        <div className="evidence-section">
          <div className="section-heading"><div><span>Your results, explained</span><h3>{filtered.length} {filtered.length === 1 ? "check" : "checks"} explained</h3></div><small>Findings and gaps in coverage</small></div>
          <div className="filter-row">
            {(["all", "integrity", "metadata", "visual", "provenance", "model"] as const).map((category) => (
              <button key={category} className={filter === category ? "active" : ""} onClick={() => setFilter(category)}>
                {category === "all" ? "All checks" : categoryLabels[category]}
              </button>
            ))}
          </div>
          <div className="evidence-list">
            {filtered.map((item) => <EvidenceCard item={item} key={item.id} />)}
            {!filtered.length && <div className="empty-filter">No results for this type of check.</div>}
          </div>
        </div>

        <aside className="media-sidebar">
          <div className="preview-card"><MediaPreview file={file} /><span className="preview-badge">{report.media.media_kind}</span></div>
          <div className="detail-card">
            <div className="detail-title"><span>Media details</span><Fingerprint size={17} /></div>
            <dl>
              <div><dt>File</dt><dd title={report.media.filename}>{report.media.filename}</dd></div>
              <div><dt>Size</dt><dd>{formatBytes(report.media.size_bytes)}</dd></div>
              <div><dt>Type</dt><dd>{report.media.mime_type}</dd></div>
              {report.media.dimensions && <div><dt>Dimensions</dt><dd>{report.media.dimensions}</dd></div>}
              {report.media.software && <div><dt>Software</dt><dd>{report.media.software}</dd></div>}
              <div className="hash-row"><dt>Unique file ID (SHA-256)</dt><dd>{report.media.sha256}</dd></div>
            </dl>
          </div>
          <div className="limitations-card"><strong><Info size={15} /> Keep in mind</strong><p>A low score doesn’t prove a file is real. Check where it came from and compare it with the original when you can.</p></div>
        </aside>
      </div>
    </section>
  );
}

function Method() {
  const steps = [
    { number: "01", icon: Fingerprint, title: "Read your file", text: "We identify the file type and create a unique ID so you can recognize this exact file again." },
    { number: "02", icon: Layers3, title: "Look for clues", text: "We check saved file details and, for images, look for unusual patterns that may come from editing." },
    { number: "03", icon: Activity, title: "Check for consistency", text: "We re-check images after resizing and compression. If the model changes its mind sharply, we flag the result as unreliable." },
    { number: "04", icon: Eye, title: "Show you why", text: "You get a breakdown of what we found, what it could mean, and which checks weren’t available." },
  ];
  return (
    <section className="method-section" id="method">
      <div className="shell">
        <div className="section-kicker">HOW IT WORKS</div>
        <div className="method-intro"><h2>A closer look.<br />A clearer explanation.</h2><p>Photos are checked by a trained AI-image model when it’s available. File details are shown separately. Video, audio, and face-swap detection aren’t supported yet.</p></div>
        <div className="method-grid">
          {steps.map(({ number, icon: Icon, title, text }, index) => (
            <article key={number}><div className="method-top"><span>{number}</span><Icon size={22} /></div><h3>{title}</h3><p>{text}</p>{index < steps.length - 1 && <ChevronRight className="step-arrow" size={20} />}</article>
          ))}
        </div>
      </div>
    </section>
  );
}

function Responsibility() {
  return (
    <section className="responsibility" id="responsibility">
      <div className="shell responsibility-grid">
        <div><span className="section-kicker">WHAT TO KNOW</span><h2>There’s always<br /><em>more to the story.</em></h2></div>
        <div className="principles">
          <p><b>1</b><span><strong>Start with the original</strong>A screenshot or forwarded copy can lose useful details. Use the original file if you have it.</span></p>
          <p><b>2</b><span><strong>Check the source</strong>Look at who shared it, where it first appeared, and whether other sources agree.</span></p>
          <p><b>3</b><span><strong>Leave room for mistakes</strong>Real files can look unusual too. Use these results as a starting point for a closer look.</span></p>
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer><div className="shell footer-row"><Brand /><p>A little more context.<br />A better-informed view.</p><span>EARLY VERSION<br />BUILT TO HELP YOU LOOK CLOSER</span></div></footer>
  );
}

export default function App() {
  const [stage, setStage] = useState<Stage>("idle");
  const [file, setFile] = useState<File | null>(null);
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [error, setError] = useState("");
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (stage !== "analyzing") return;
    const started = Date.now();
    const timer = window.setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000);
    return () => window.clearInterval(timer);
  }, [stage]);

  const handleFile = async (candidate: File) => {
    if (candidate.size > 100 * 1024 * 1024) {
      setError("That file is larger than the 100 MB analysis limit.");
      setStage("error");
      return;
    }
    setFile(candidate);
    setReport(null);
    setError("");
    setElapsed(0);
    setStage("analyzing");
    try {
      const result = await analyzeMedia(candidate);
      window.setTimeout(() => {
        setReport(result);
        setStage("complete");
        window.setTimeout(() => document.getElementById("report")?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
      }, 350);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unexpected analysis error.");
      setStage("error");
    }
  };

  const reset = () => {
    setStage("idle"); setFile(null); setReport(null); setError(""); setElapsed(0);
    document.getElementById("analyze")?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <>
      <Header />
      <main>
        <Hero />
        <section className="analyze-section" id="analyze">
          <div className="shell">
            <div className="intake-layout">
              <div className="analyze-heading"><span className="section-kicker">CHECK A FILE</span><h2>What would you<br />like to check?</h2><p>Upload an image for an AI-generation check. Video and audio uploads show file details only; deepfake detection for these isn’t available yet.</p><div className="intake-note"><span>YOU CAN UPLOAD</span><b>PHOTOS<br />VIDEOS<br />AUDIO</b></div></div>
              <UploadPanel stage={stage} file={file} elapsed={elapsed} error={error} onFile={handleFile} onClear={reset} />
            </div>
            <TrustRail />
            <BackendStatus key={stage} />
          </div>
        </section>
        {stage === "complete" && report && file && <div className="shell" id="report"><Results report={report} file={file} onReset={reset} /></div>}
        <Method />
        <Responsibility />
      </main>
      <Footer />
    </>
  );
}
