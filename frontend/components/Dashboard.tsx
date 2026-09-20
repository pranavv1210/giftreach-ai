"use client";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Building2,
  Users,
  Send,
  Mail,
  Waypoints,
  Bot,
  Plug,
  Settings,
  ScrollText,
  Search,
  Plus,
  ShieldAlert,
  Pause,
  Play,
  Check,
  ChevronRight,
  X,
  Eye,
  ExternalLink,
} from "lucide-react";
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const NAV = [
  ["overview", "Overview", LayoutDashboard],
  ["companies", "Companies", Building2],
  ["contacts", "Contacts", Users],
  ["campaigns", "Discovery", Send],
  ["email-review", "Bulk review", Mail],
  ["pipeline", "Pipeline", Waypoints],
  ["agent", "Agent control", Bot],
  ["integrations", "Integrations", Plug],
  ["settings", "Settings", Settings],
  ["activity", "Activity logs", ScrollText],
] as const;
type Obj = Record<string, any>;
type Action = (p: string, b?: Obj, m?: string) => Promise<any>;
export default function Dashboard({ section }: { section: string }) {
  const router = useRouter(),
    [data, setData] = useState<any>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const api = useCallback(
    async (path: string, opts: RequestInit = {}) => {
      const csrf = sessionStorage.getItem("csrf") || "";
      const r = await fetch(`${API}${path}`, {
        credentials: "include",
        ...opts,
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrf,
          ...opts.headers,
        },
      });
      if (r.status === 401) {
        router.push("/");
        throw new Error("Session expired");
      }
      const d = await r.json().catch(() => ({}));
      if (!r.ok)
        throw new Error(
          typeof d.detail === "string"
            ? d.detail
            : "Action could not be completed",
        );
      return d;
    },
    [router],
  );
  const load = useCallback(async () => {
    setError("");
    try {
      const map: Obj = {
        overview: "/api/overview",
        companies: "/api/companies",
        contacts: "/api/contacts",
        campaigns: "/api/discovery-campaigns",
        "email-review": "/api/review",
        pipeline: "/api/drafts",
        agent: "/api/agent",
        integrations: "/api/integrations",
        settings: "/api/agent",
        activity: "/api/activity",
      };
      setData(await api(map[section] || "/api/overview"));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load");
    }
  }, [api, section]);
  useEffect(() => {
    load();
  }, [load]);
  async function action(path: string, body?: Obj, method = "POST") {
    setBusy(true);
    setError("");
    try {
      const result = await api(path, {
        method,
        body: body ? JSON.stringify(body) : undefined,
      });
      await load();
      return result;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
      throw e;
    } finally {
      setBusy(false);
    }
  }
  const title = NAV.find((n) => n[0] === section)?.[1] || "Overview";
  return (
    <div className="shell">
      <aside>
        <a className="brand" href="/overview">
          <span>G</span>
          <strong>GiftReach</strong>
        </a>
        <nav>
          {NAV.map(([id, label, Icon]) => (
            <a
              key={id}
              href={`/${id}`}
              className={section === id ? "active" : ""}
            >
              <Icon size={17} />
              {label}
            </a>
          ))}
        </nav>
        <div className="rail-foot">
          <span className="status-dot" />
          Guardrails active<small>Approval required to send</small>
        </div>
      </aside>
      <main className="workspace">
        <header className="top">
          <div>
            <p>Corporate gifting outreach</p>
            <h1>{title}</h1>
          </div>
          <div className="top-actions">
            <div className="avatar">PV</div>
          </div>
        </header>
        {error && (
          <div className="alert">
            {error}
            <button onClick={load}>Try again</button>
          </div>
        )}
        <section className="content">
          {data === null ? (
            <div className="loading">Loading workspace…</div>
          ) : (
            <View section={section} data={data} action={action} busy={busy} />
          )}
        </section>
      </main>
    </div>
  );
}
function View({
  section,
  data,
  action,
  busy,
}: {
  section: string;
  data: any;
  action: Action;
  busy: boolean;
}) {
  if (section === "campaigns")
    return <Campaigns data={data} action={action} busy={busy} />;
  if (section === "email-review")
    return <Review data={data} action={action} busy={busy} />;
  if (section === "overview")
    return (
      <>
        <div className="agent-strip">
          <div>
            <span className="pulse" />
            <p>Agent mode</p>
            <strong>{data.agent.mode.replaceAll("_", " ")}</strong>
          </div>
          <p>
            {data.agent.paused
              ? "Operations are paused."
              : "Create a discovery campaign, then review every qualified draft in one queue."}
          </p>
          <a href="/campaigns">
            Start discovery <ChevronRight size={16} />
          </a>
        </div>
        <div className="metrics">
          {[
            ["Companies", data.companies],
            ["Contacts", data.contacts],
            ["Verified", data.verified],
            ["Awaiting review", data.drafts],
            ["Sent", data.sent],
            ["Replies", data.replies],
            ["Bounces", data.bounces],
            ["Interested", data.interested],
          ].map(([k, v]) => (
            <article key={k}>
              <span>{k}</span>
              <strong>{v}</strong>
            </article>
          ))}
        </div>
        <Empty
          title="Build a prospect list automatically"
          copy="Set geography, industries, roles, and limits. GiftReach will search permitted sources and preserve every source URL."
          action="Create discovery campaign"
          href="/campaigns"
        />
      </>
    );
  if (section === "companies")
    return (
      <>
        <PageTools />
        <Table
          headers={[
            "Company",
            "Industry",
            "Location",
            "Score",
            "Contacts",
            "State",
          ]}
          rows={data.map((x: Obj) => [
            x.name,
            x.industry || "Not recorded",
            `${x.city}, ${x.district}`,
            `${x.score}/100`,
            x.contact_count,
            x.suppressed ? "Suppressed" : "Eligible",
          ])}
        />
        {!data.length && (
          <Empty
            title="No companies discovered"
            copy="Start a discovery campaign. Manual company entry remains available through the API."
          />
        )}
      </>
    );
  if (section === "contacts")
    return (
      <>
        <PageTools />
        <Table
          headers={[
            "Contact",
            "Company",
            "Role",
            "Verification",
            "Source",
            "State",
          ]}
          rows={data.map((x: Obj) => [
            x.name || x.email,
            x.company,
            x.title || "Not recorded",
            x.verification_status,
            x.sources[0]?.source_type || "Missing",
            x.suppressed ? "Suppressed" : "Eligible",
          ])}
        />
        {!data.length && (
          <Empty
            title="No contacts discovered"
            copy="Campaign research checks permitted public pages for relevant business contacts."
          />
        )}
      </>
    );
  if (section === "pipeline") {
    const stages = [
      "DRAFT",
      "APPROVED",
      "SENT",
      "REPLIED",
      "INTERESTED",
      "BOUNCED",
      "SUPPRESSED",
    ];
    return (
      <div className="pipeline">
        {stages.map((s) => (
          <article key={s}>
            <div>
              <span>{s}</span>
              <strong>{data.filter((d: Obj) => d.status === s).length}</strong>
            </div>
            {data
              .filter((d: Obj) => d.status === s)
              .map((d: Obj) => (
                <p key={d.id}>{d.subject}</p>
              ))}
          </article>
        ))}
      </div>
    );
  }
  if (section === "agent")
    return (
      <>
        <div className="control-hero">
          <div>
            <span className={data.kill_switch ? "danger-dot" : "pulse"} />
            <p>Current mode</p>
            <h2>{data.mode.replaceAll("_", " ")}</h2>
          </div>
          <button
            className="danger"
            disabled={busy}
            onClick={() => action("/api/agent/emergency-stop")}
          >
            <ShieldAlert size={18} />
            Emergency stop
          </button>
        </div>
        <div className="controls">
          <article>
            <h3>Operating mode</h3>
            <p>
              RESEARCH discovers contacts. DRAFT also prepares policy-checked
              messages.
            </p>
            <select
              value={data.mode}
              onChange={(e) =>
                action("/api/agent", { mode: e.target.value }, "PATCH")
              }
            >
              <option>OFF</option>
              <option>RESEARCH</option>
              <option>DRAFT</option>
              <option>CONTROLLED_AUTOPILOT</option>
            </select>
          </article>
          <article>
            <h3>Global operation</h3>
            <p>Pause all persistent jobs without losing their state.</p>
            <button
              onClick={() =>
                action("/api/agent", { paused: !data.paused }, "PATCH")
              }
            >
              {data.paused ? <Play size={16} /> : <Pause size={16} />}{" "}
              {data.paused ? "Resume" : "Pause"}
            </button>
          </article>
          <article>
            <h3>Sending</h3>
            <p>
              Bulk sending always requires approval and explicit confirmation.
            </p>
            <button
              onClick={() =>
                action(
                  "/api/agent",
                  { sending_paused: !data.sending_paused },
                  "PATCH",
                )
              }
            >
              {data.sending_paused ? "Resume sending" : "Pause sending"}
            </button>
          </article>
        </div>
      </>
    );
  if (section === "integrations")
    return (
      <div className="integrations">
        {Object.entries(data).map(([k, v]: [string, any]) => (
          <article key={k}>
            <div className={`integration-icon ${v.status}`}>
              <Plug size={18} />
            </div>
            <div>
              <h3>{k[0].toUpperCase() + k.slice(1)}</h3>
              <p>{v.email || v.status.replaceAll("_", " ")}</p>
            </div>
            {k === "gmail" && v.status !== "connected" ? (
              <button
                onClick={async () => {
                  const d = await action("/api/gmail/connect");
                  location.href = d.authorization_url;
                }}
              >
                Connect
              </button>
            ) : (
              <span>
                {v.status === "connected"
                  ? "Ready"
                  : v.status === "mock"
                    ? "Fallback"
                    : "Setup needed"}
              </span>
            )}
          </article>
        ))}
      </div>
    );
  if (section === "settings")
    return (
      <div className="settings-grid">
        <article>
          <h3>Approved catalogue</h3>
          <p>Generation is restricted to these categories.</p>
          <div className="chips">
            {data.approved_categories.map((x: string) => (
              <span key={x}>{x}</span>
            ))}
          </div>
        </article>
        <article>
          <h3>Sending safeguards</h3>
          <label>
            Daily maximum
            <input value={data.daily_limit} readOnly />
          </label>
          <label>
            Hourly maximum
            <input value={data.hourly_limit} readOnly />
          </label>
        </article>
        <article>
          <h3>Required signature</h3>
          <pre>Pranav V.{`\n`}Corporate Gifting</pre>
        </article>
      </div>
    );
  if (section === "activity")
    return (
      <div className="activity">
        {data.map((x: Obj) => (
          <article key={x.id}>
            <span className="event-dot" />
            <div>
              <strong>{x.message}</strong>
              <p>
                {x.event} · {new Date(x.created_at).toLocaleString()}
              </p>
            </div>
          </article>
        ))}
        {!data.length && (
          <Empty
            title="No activity recorded"
            copy="Discovery, provider failures, approvals, and sends appear here."
          />
        )}
      </div>
    );
  return (
    <Empty title="Nothing here yet" copy="This workspace is ready for data." />
  );
}
function Campaigns({
  data,
  action,
  busy,
}: {
  data: Obj[];
  action: Action;
  busy: boolean;
}) {
  const [open, setOpen] = useState(false);
  async function create(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    await action("/api/discovery-campaigns", {
      name: f.get("name"),
      cities: String(f.get("cities"))
        .split(",")
        .map((x) => x.trim())
        .filter(Boolean),
      districts: String(f.get("districts"))
        .split(",")
        .map((x) => x.trim())
        .filter(Boolean),
      industries: String(f.get("industries"))
        .split(",")
        .map((x) => x.trim())
        .filter(Boolean),
      company_sizes: Array.from(f.getAll("sizes")),
      contact_roles: String(f.get("roles"))
        .split(",")
        .map((x) => x.trim())
        .filter(Boolean),
      score_threshold: Number(f.get("score")),
      max_companies: Number(f.get("max")),
      max_contacts_per_company: Number(f.get("contacts")),
        provider: f.get("provider"),
      generate_drafts: f.get("drafts") === "on",
    });
    setOpen(false);
  }
  return (
    <>
      {open && (
        <div className="panel">
          <div className="panel-head">
            <div>
              <h2>New discovery campaign</h2>
              <p>
                Search permitted public sources without manual company entry.
              </p>
            </div>
            <button className="icon" onClick={() => setOpen(false)}>
              <X />
            </button>
          </div>
          <form className="campaign-form" onSubmit={create}>
            <label>
              Campaign name
              <input
                name="name"
                required
                placeholder="Bengaluru technology prospects"
              />
            </label>
            <label>
              Cities
              <input name="cities" defaultValue="Bengaluru" />
            </label>
            <label>
              Districts
              <input name="districts" defaultValue="Bengaluru Urban" />
            </label>
            <label>
              Industries
              <input
                name="industries"
                placeholder="Software, Consulting, Healthcare"
              />
            </label>
            <label>
              Discovery provider
              <select name="provider" defaultValue="overpass">
                <option value="overpass">OpenStreetMap — free, no key</option>
                <option value="brave">Brave Search — optional key</option>
              </select>
            </label>
            <label className="wide">
              Target roles
              <input
                name="roles"
                defaultValue="HR Manager, People Operations, Employee Engagement, Administration, Procurement"
              />
            </label>
            <fieldset>
              <legend>Company sizes</legend>
              {["Small", "Mid-sized", "Large"].map((s) => (
                <label key={s}>
                  <input type="checkbox" name="sizes" value={s} />
                  {s}
                </label>
              ))}
            </fieldset>
            <label>
              Minimum score
              <input
                name="score"
                type="number"
                min="0"
                max="100"
                defaultValue="40"
              />
            </label>
            <label>
              Maximum companies
              <input
                name="max"
                type="number"
                min="1"
                max="200"
                defaultValue="25"
              />
            </label>
            <label>
              Contacts per company
              <input
                name="contacts"
                type="number"
                min="1"
                max="10"
                defaultValue="3"
              />
            </label>
            <label className="check">
              <input name="drafts" type="checkbox" defaultChecked />
              Generate drafts in DRAFT mode
            </label>
            <div className="form-actions">
              <button
                type="button"
                className="secondary"
                onClick={() => setOpen(false)}
              >
                Cancel
              </button>
              <button disabled={busy}>Create campaign</button>
            </div>
          </form>
        </div>
      )}
      <div className="tools">
        <div>
          <strong>{data.length} campaigns</strong>
            <p>Free OpenStreetMap or optional Brave Search + official websites</p>
        </div>
        <button onClick={() => setOpen(true)}>
          <Plus size={16} />
          New campaign
        </button>
      </div>
      <div className="campaign-list">
        {data.map((c) => (
          <article key={c.id}>
            <div className="campaign-state">
              <span className={`state ${c.status.toLowerCase()}`} />
              <div>
                <strong>{c.name}</strong>
                <p>
                  {c.cities.join(", ")} ·{" "}
                  {c.industries.join(", ") || "All industries"}
                </p>
              </div>
            </div>
            <div>
              <span>Companies</span>
              <strong>
                {c.discovered_count}/{c.max_companies}
              </strong>
            </div>
            <div>
              <span>Qualified contacts</span>
              <strong>{c.qualified_count}</strong>
            </div>
            <div>
              <span>Status</span>
              <strong>{c.status}</strong>
              {c.error_message && (
                <em title={c.error_message}>Provider error</em>
              )}
            </div>
            <div className="row-actions">
              {!["RUNNING", "QUEUED"].includes(c.status) && (
                <button
                  disabled={busy}
                  onClick={() =>
                    action(`/api/discovery-campaigns/${c.id}/start`)
                  }
                >
                  Start
                </button>
              )}
              {["RUNNING", "QUEUED"].includes(c.status) && (
                <button
                  className="secondary"
                  onClick={() =>
                    action(`/api/discovery-campaigns/${c.id}/pause`)
                  }
                >
                  Pause
                </button>
              )}
            </div>
          </article>
        ))}
      </div>
      {!data.length && (
        <Empty
          title="Create your first search campaign"
          copy="Choose a narrow audience first. OpenStreetMap discovery needs no API key."
        />
      )}
    </>
  );
}
function Review({
  data,
  action,
  busy,
}: {
  data: Obj[];
  action: Action;
  busy: boolean;
}) {
  const [selected, setSelected] = useState<number[]>([]),
    [preview, setPreview] = useState<Obj | null>(null),
    [sendPlan, setSendPlan] = useState<Obj | null>(null);
  const reviewable = data.filter((x) => x.draft_id);
  const toggle = (id: number) =>
    setSelected((s) =>
      s.includes(id) ? s.filter((x) => x !== id) : [...s, id],
    );
  async function plan() {
    setSendPlan(
      await action("/api/review/bulk/preview-send", { draft_ids: selected }),
    );
  }
  return (
    <>
      <div className="review-toolbar">
        <div>
          <label className="check">
            <input
              type="checkbox"
              checked={
                reviewable.length > 0 &&
                reviewable.every((x) => selected.includes(x.draft_id))
              }
              onChange={(e) =>
                setSelected(
                  e.target.checked ? reviewable.map((x) => x.draft_id) : [],
                )
              }
            />
            Select all drafts
          </label>
          <span>{selected.length} selected</span>
        </div>
        <div>
          <button
            className="secondary"
            disabled={!selected.length || busy}
            onClick={() =>
              action("/api/review/bulk/reject", { draft_ids: selected })
            }
          >
            Reject
          </button>
          <button
            disabled={!selected.length || busy}
            onClick={() =>
              action("/api/review/bulk/approve", { draft_ids: selected })
            }
          >
            <Check size={16} />
            Approve selected
          </button>
          <button disabled={!selected.length || busy} onClick={plan}>
            Review send
          </button>
        </div>
      </div>
      <div className="review-table">
        <table>
          <thead>
            <tr>
              <th></th>
              <th>Company and contact</th>
              <th>Email evidence</th>
              <th>Score</th>
              <th>Draft</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {data.map((x) => (
              <tr key={x.prospect_id}>
                <td>
                  <input
                    type="checkbox"
                    disabled={!x.draft_id}
                    checked={selected.includes(x.draft_id)}
                    onChange={() => toggle(x.draft_id)}
                  />
                </td>
                <td>
                  <strong>{x.company}</strong>
                  <span>
                    {x.contact || "Public role address"} ·{" "}
                    {x.title || "Role not stated"}
                  </span>
                  <small>
                    {x.city} · {x.industry || "Industry unconfirmed"}
                  </small>
                </td>
                <td>
                  <strong>{x.email}</strong>
                  <span className="badge">{x.verification_status}</span>
                  <a href={x.source_url} target="_blank">
                    {x.source_type} <ExternalLink size={11} />
                  </a>
                  {![
                    "MX_VALID",
                    "PROVIDER_VERIFIED",
                    "MANUALLY_VERIFIED",
                  ].includes(x.verification_status) && (
                    <button
                      className="verify-link"
                      disabled={busy || !x.source_url}
                      title="Inspect the source link before manually verifying"
                      onClick={() =>
                        action(`/api/contacts/${x.contact_id}/verify-manually`)
                      }
                    >
                      Mark verified
                    </button>
                  )}
                </td>
                <td>
                  <strong>{x.score}/100</strong>
                </td>
                <td>
                  <span className="badge">{x.draft_status}</span>
                  {x.exclusion_reasons.length > 0 && (
                    <small>{x.exclusion_reasons.join("; ")}</small>
                  )}
                </td>
                <td>
                  <button
                    className="icon"
                    disabled={!x.draft_id}
                    onClick={() => setPreview(x)}
                  >
                    <Eye size={17} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!data.length && (
        <Empty
          title="No prospects ready for review"
          copy="Run a discovery campaign in DRAFT mode. Qualified contacts and policy-checked drafts will collect here."
        />
      )}
      {preview && (
        <div className="modal">
          <article>
            <button className="close" onClick={() => setPreview(null)}>
              <X />
            </button>
            <span>
              {preview.company} · {preview.email}
            </span>
            <h2>{preview.subject}</h2>
            <pre>{preview.body}</pre>
            <div className="evidence">
              <strong>Source evidence</strong>
              <p>{preview.source_description}</p>
              <a href={preview.source_url} target="_blank">
                Open source page
              </a>
            </div>
          </article>
        </div>
      )}
      {sendPlan && (
        <div className="modal">
          <article className="confirm">
            <button className="close" onClick={() => setSendPlan(null)}>
              <X />
            </button>
            <h2>Confirm bulk send</h2>
            <div className="send-counts">
              <div>
                <strong>{sendPlan.selected}</strong>
                <span>Selected</span>
              </div>
              <div>
                <strong>{sendPlan.eligible.length}</strong>
                <span>Eligible</span>
              </div>
              <div>
                <strong>{sendPlan.excluded.length}</strong>
                <span>Excluded</span>
              </div>
            </div>
            <p>
              Daily limit: {sendPlan.limits.daily}. Hourly limit:{" "}
              {sendPlan.limits.hourly}. Gmail:{" "}
              {sendPlan.gmail.email || sendPlan.gmail.status}.
            </p>
            {sendPlan.excluded.map((x: Obj) => (
              <small key={x.id}>
                Draft {x.id}: {x.reasons.join(", ")}
              </small>
            ))}
            <button
              disabled={
                !sendPlan.eligible.length ||
                sendPlan.gmail.status !== "CONNECTED"
              }
              onClick={async () => {
                await action("/api/review/bulk/send", {
                  draft_ids: sendPlan.eligible,
                  provider: "gmail",
                  confirm: true,
                });
                setSendPlan(null);
                setSelected([]);
              }}
            >
              Send {sendPlan.eligible.length} with Gmail
            </button>
          </article>
        </div>
      )}
    </>
  );
}
function Table({ headers, rows }: { headers: string[]; rows: any[][] }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {headers.map((h) => (
              <th key={h}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {r.map((v, j) => (
                <td key={j}>{v}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
function PageTools() {
  return (
    <div className="tools">
      <div className="searchbox">
        <Search size={16} />
        <input placeholder="Search records" />
      </div>
    </div>
  );
}
function Empty({
  title,
  copy,
  action,
  href,
}: {
  title: string;
  copy: string;
  action?: string;
  href?: string;
}) {
  return (
    <div className="empty">
      <div className="empty-mark">G</div>
      <h2>{title}</h2>
      <p>{copy}</p>
      {action && href ? <a href={href}>{action}</a> : null}
    </div>
  );
}
