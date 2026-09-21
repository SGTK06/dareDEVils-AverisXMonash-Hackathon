import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleHelp,
  Clipboard,
  Clock3,
  Download,
  FileText,
  Filter,
  Inbox as InboxIcon,
  Keyboard,
  LogOut,
  Menu,
  Moon,
  MoreHorizontal,
  PanelRight,
  RefreshCw,
  Search,
  Send,
  Settings2,
  ShieldCheck,
  Sun,
  Upload,
  X,
  XCircle
} from "lucide-react";
import {
  api,
  type EmailRecord,
  type EmailStatus,
  type FieldResult,
  type ClassificationTestResult,
  type ComparisonTestResult
  ,type EndToEndScore
} from "./api.ts";

type View = "inbox" | "review" | "runs" | "test" | "export";

type DashboardProps = {
  userEmail: string;
  onSignOut: () => void;
};

const statusMeta: Record<EmailStatus, { label: string; className: string }> = {
  Mismatch: { label: "Mismatch", className: "status-mismatch" },
  Match: { label: "Match", className: "status-match" },
  "Needs review": { label: "Needs review", className: "status-review" },
  Failed: { label: "Failed", className: "status-failed" },
  Classified: { label: "Classified", className: "status-neutral" }
};

function Dashboard({ userEmail, onSignOut }: DashboardProps) {
  const [view, setView] = useState<View>("inbox");
  const [selected, setSelected] = useState<EmailRecord | null>(null);
  const [query, setQuery] = useState("");
  const [dark, setDark] = useState(false);
  const [filter, setFilter] = useState<EmailStatus | "All">("All");
  const [toast, setToast] = useState("");
  const [helpOpen, setHelpOpen] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);
  const [emails, setEmails] = useState<EmailRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    const handler = (event: KeyboardEvent) => {
      if (event.key === "/" && document.activeElement?.tagName !== "INPUT") {
        event.preventDefault();
        document.getElementById("global-search")?.focus();
      }
      if (event.key === "?" && document.activeElement?.tagName !== "INPUT")
        setHelpOpen(true);
      if (event.key === "Escape") {
        setHelpOpen(false);
        setSelected(null);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [dark]);

  useEffect(() => {
    api
      .listEmails()
      .then(setEmails)
      .catch((error) => {
        setLoadError(
          error instanceof Error ? error.message : "Unable to load inbox"
        );
      })
      .finally(() => setLoading(false));
  }, []);

  const filteredEmails = useMemo(
    () =>
      emails.filter((email) => {
        const matchesFilter = filter === "All" || email.status === filter;
        const haystack =
          `${email.subject} ${email.sender} ${email.id}`.toLowerCase();
        return matchesFilter && haystack.includes(query.toLowerCase());
      }),
    [emails, filter, query]
  );

  const notify = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 2600);
  };
  const openEmail = async (email: EmailRecord) => {
    setSelected(email);
    try {
      const detail = await api.getEmail(email.id);
      setSelected(detail);
      setEmails((current) =>
        current.map((item) => (item.id === detail.id ? detail : item))
      );
    } catch (error) {
      notify(error instanceof Error ? error.message : "Unable to open email");
    }
  };

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileNav ? "sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-mark">
            <ShieldCheck size={17} />
          </div>
          <span>harborline</span>
          <button
            className="icon-button mobile-close"
            onClick={() => setMobileNav(false)}
            aria-label="Close navigation"
          >
            <X size={17} />
          </button>
        </div>
        <div className="workspace-label">OPERATIONS WORKSPACE</div>
        <nav className="main-nav" aria-label="Main navigation">
          <NavButton
            icon={<InboxIcon size={16} />}
            label="Inbox"
            count={emails.length.toString()}
            active={view === "inbox"}
            onClick={() => {
              setView("inbox");
              setSelected(null);
              setMobileNav(false);
            }}
          />
          <NavButton
            icon={<AlertTriangle size={16} />}
            label="Review queue"
            count={emails
              .filter((email) => email.status === "Needs review")
              .length.toString()}
            active={view === "review"}
            onClick={() => {
              setView("review");
              setSelected(null);
              setMobileNav(false);
            }}
          />
          <NavButton
            icon={<Activity size={16} />}
            label="Run status"
            active={view === "runs"}
            onClick={() => {
              setView("runs");
              setSelected(null);
              setMobileNav(false);
            }}
          />
          <NavButton
            icon={<Activity size={16} />}
            label="Test"
            active={view === "test"}
            onClick={() => {
              setView("test");
              setSelected(null);
              setMobileNav(false);
            }}
          />
          <NavButton
            icon={<BarChart3 size={16} />}
            label="Export"
            active={view === "export"}
            onClick={() => {
              setView("export");
              setSelected(null);
              setMobileNav(false);
            }}
          />
        </nav>
        <div className="sidebar-spacer" />
        <div className="pipeline-health">
          <span className="health-dot" />
          Pipeline healthy <span className="health-time">2m ago</span>
        </div>
        <button className="nav-button muted">
          <Settings2 size={16} /> Settings
        </button>

        {/* Polished User Profile & Sign-out Row */}
        <div
          className="user-row"
          style={{
            borderTop: "1px solid var(--border-color, #e5e7eb)",
            marginTop: "8px",
            paddingTop: "12px",
            display: "flex",
            alignItems: "center",
            gap: "10px"
          }}
        >
          <div className="avatar" style={{ flexShrink: 0 }}>
            {userEmail.slice(0, 2).toUpperCase()}
          </div>
          <div
            style={{
              minWidth: 0,
              flex: 1,
              display: "flex",
              flexDirection: "column"
            }}
          >
            <strong
              style={{
                fontSize: "12px",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap"
              }}
            >
              {userEmail}
            </strong>
            <span
              style={{ fontSize: "11px", color: "var(--muted-color, #6b7280)" }}
            >
              Operations
            </span>
          </div>
          <button
            className="icon-button"
            onClick={onSignOut}
            aria-label="Sign out"
            title="Sign out"
            style={{ flexShrink: 0 }}
          >
            <LogOut size={16} />
          </button>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <button
            className="icon-button mobile-menu"
            onClick={() => setMobileNav(true)}
            aria-label="Open navigation"
          >
            <Menu size={19} />
          </button>
          <div className="breadcrumbs">
            <span>Workspace</span>
            <ChevronRight size={14} />
            <strong>
              {view === "inbox"
                ? "Inbox"
                : view === "review"
                  ? "Review queue"
                  : view === "runs"
                    ? "Run status"
                    : view === "test"
                      ? "Test"
                      : "Export"}
            </strong>
          </div>
          <div className="top-actions">
            <button
              className="icon-button help-button"
              onClick={() => setHelpOpen(true)}
              aria-label="Keyboard shortcuts"
            >
              <Keyboard size={16} />
              <span>Shortcuts</span>
            </button>
            <button
              className="icon-button"
              onClick={() => setDark(!dark)}
              aria-label="Toggle theme"
            >
              {dark ? <Sun size={17} /> : <Moon size={17} />}
            </button>
            <button
              className="button button-primary"
              onClick={() => setView("export")}
            >
              <Upload size={15} /> Export results
            </button>
          </div>
        </header>

        {loading && (
          <div className="page-wrap">
            <div className="empty-state">
              <RefreshCw size={24} />
              <strong>Loading inbox</strong>
              <span>
                Fetching live email records from the verification service.
              </span>
            </div>
          </div>
        )}
        {!loading && loadError && (
          <div className="page-wrap">
            <div className="empty-state">
              <XCircle size={24} />
              <strong>Inbox unavailable</strong>
              <span>{loadError}</span>
              <button
                className="button button-primary"
                onClick={() => window.location.reload()}
              >
                Retry connection
              </button>
            </div>
          </div>
        )}
        {!loading && !loadError && view === "inbox" && (
          <>
            <InboxView
              emails={filteredEmails}
              allEmails={emails}
              query={query}
              setQuery={setQuery}
              filter={filter}
              setFilter={setFilter}
              onOpen={openEmail}
              onRetry={(id) => notify(`Retry queued for ${id}`)}
            />
            {selected && (
              <div className="detail-overlay">
                <DetailView
                  email={selected}
                  onBack={() => setSelected(null)}
                  onNotify={notify}
                />
              </div>
            )}
          </>
        )}
        {!loading && !loadError && view === "review" && (
          <ReviewView emails={emails} onOpen={openEmail} onNotify={notify} />
        )}
        {!loading && !loadError && view === "runs" && (
          <RunsView emails={emails} onNotify={notify} />
        )}
        {!loading && !loadError && view === "test" && (
          <TestView onNotify={notify} />
        )}
        {!loading && !loadError && view === "export" && (
          <ExportView emails={emails} onNotify={notify} />
        )}
        {selected && view !== "inbox" && (
          <div className="detail-overlay">
            <DetailView
              email={selected}
              onBack={() => setSelected(null)}
              onNotify={notify}
            />
          </div>
        )}
      </main>
      {helpOpen && <ShortcutDialog onClose={() => setHelpOpen(false)} />}
      {toast && (
        <div className="toast">
          <CheckCircle2 size={16} />
          {toast}
        </div>
      )}
    </div>
  );
}

function NavButton({
  icon,
  label,
  count,
  active,
  onClick
}: {
  icon: ReactNode;
  label: string;
  count?: string;
  active?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      className={`nav-button ${active ? "nav-active" : ""}`}
      onClick={onClick}
    >
      {icon}
      <span>{label}</span>
      {count && <span className="nav-count">{count}</span>}
    </button>
  );
}

function InboxView({
  emails: list,
  allEmails,
  query,
  setQuery,
  filter,
  setFilter,
  onOpen,
  onRetry
}: {
  emails: EmailRecord[];
  allEmails: EmailRecord[];
  query: string;
  setQuery: (value: string) => void;
  filter: EmailStatus | "All";
  setFilter: (value: EmailStatus | "All") => void;
  onOpen: (email: EmailRecord) => void;
  onRetry: (id: string) => void;
}) {
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 50; // Set to 50 emails per page

  const totalPages = Math.ceil(list.length / pageSize) || 1;
  const paginatedEmails = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return list.slice(start, start + pageSize);
  }, [list, currentPage, pageSize]);

  const comparisons = allEmails.filter(
    (email) => email.category === "Comparison request"
  ).length;
  const mismatches = allEmails.filter(
    (email) => email.status === "Mismatch"
  ).length;
  const reviews = allEmails.filter(
    (email) => email.status === "Needs review"
  ).length;
  const failed = allEmails.filter((email) => email.status === "Failed").length;
  const stats = [
    {
      label: "Total",
      value: allEmails.length.toString(),
      detail: "Live inbox"
    },
    {
      label: "Comparisons",
      value: comparisons.toString(),
      detail: "Classified requests"
    },
    {
      label: "Mismatches",
      value: mismatches.toString(),
      detail: "Processed results"
    },
    {
      label: "Needs review",
      value: reviews.toString(),
      detail: "Requires operator"
    },
    { label: "Failed", value: failed.toString(), detail: "Action required" }
  ];

  return (
    <section
      className="page-wrap"
      style={{
        display: "flex",
        flexDirection: "column",
        height: "calc(100vh - 65px)",
        overflow: "hidden"
      }}
    >
      <div className="page-heading" style={{ flexShrink: 0 }}>
        <div>
          <h1>Inbox</h1>
          <p>Shipping document verification, at a glance.</p>
        </div>
        <div className="live-status">
          <span className="health-dot" />
          Live
        </div>
      </div>
      <div className="stats-strip" style={{ flexShrink: 0 }}>
        {stats.map((stat) => (
          <div className="stat" key={stat.label}>
            <span>{stat.label}</span>
            <strong>{stat.value}</strong>
            <small>{stat.detail}</small>
          </div>
        ))}
      </div>
      <div className="toolbar" style={{ flexShrink: 0 }}>
        <div className="search-field">
          <Search size={16} />
          <input
            id="global-search"
            value={query}
            onChange={(event) => {
              setCurrentPage(1);
              setQuery(event.target.value);
            }}
            placeholder="Search emails, senders, IDs..."
          />
          <kbd>/</kbd>
        </div>
        <div className="filter-group">
          <Filter size={15} />
          <select
            value={filter}
            onChange={(event) => {
              setCurrentPage(1);
              setFilter(event.target.value as EmailStatus | "All");
            }}
            aria-label="Filter by status"
          >
            <option value="All">All statuses</option>
            <option>Mismatch</option>
            <option>Match</option>
            <option>Needs review</option>
            <option>Failed</option>
            <option>Classified</option>
          </select>
          <button className="button button-quiet">
            <Filter size={14} /> More filters
          </button>
        </div>
      </div>

      {/* Scrollable table container */}
      <div
        className="table-wrap"
        style={{ flex: 1, overflowY: "auto", minHeight: 0 }}
      >
        <table>
          <thead>
            <tr>
              <th className="check-col">
                <input type="checkbox" aria-label="Select all emails" />
              </th>
              <th>Email</th>
              <th>Category</th>
              <th>Status</th>
              <th>Result</th>
              <th>Received</th>
              <th>Attachments</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {paginatedEmails.map((email) => (
              <EmailRow
                key={email.id}
                email={email}
                onOpen={onOpen}
                onRetry={onRetry}
              />
            ))}
          </tbody>
        </table>
        {list.length === 0 && (
          <div className="empty-state">
            <Search size={24} />
            <strong>No emails found</strong>
            <span>Try a different search or clear the status filter.</span>
          </div>
        )}
      </div>

      <div className="table-footer" style={{ flexShrink: 0 }}>
        <span>
          Showing{" "}
          {paginatedEmails.length > 0 ? (currentPage - 1) * pageSize + 1 : 0}–
          {Math.min(currentPage * pageSize, list.length)} of {list.length}{" "}
          emails
        </span>
        <div>
          <button
            className="pager"
            onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
            disabled={currentPage === 1}
          >
            Previous
          </button>

          {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
            <button
              key={page}
              className={`pager ${currentPage === page ? "pager-current" : ""}`}
              onClick={() => setCurrentPage(page)}
            >
              {page}
            </button>
          ))}

          <button
            className="pager"
            onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
            disabled={currentPage === totalPages}
          >
            Next
          </button>
        </div>
      </div>
    </section>
  );
}

function EmailRow({
  email,
  onOpen,
  onRetry
}: {
  email: EmailRecord;
  onOpen: (email: EmailRecord) => void;
  onRetry: (id: string) => void;
}) {
  const meta = statusMeta[email.status];
  return (
    <tr
      onClick={() => onOpen(email)}
      tabIndex={0}
      onKeyDown={(event) => event.key === "Enter" && onOpen(email)}
    >
      <td onClick={(event) => event.stopPropagation()}>
        <input type="checkbox" aria-label={`Select ${email.id}`} />
      </td>
      <td>
        <div className="email-cell">
          <strong>{email.subject}</strong>
          <span>
            {email.sender} <code>{email.id}</code>
          </span>
        </div>
      </td>
      <td>
        <span className="category-badge">{email.category}</span>
      </td>
      <td>
        <span className={`status ${meta.className}`}>
          <span className="status-dot" />
          {meta.label}
        </span>
      </td>
      <td>
        <span
          className={`result-text ${email.status === "Mismatch" ? "result-alert" : ""}`}
        >
          {email.result}
        </span>
      </td>
      <td className="mono muted-text">{email.received}</td>
      <td>
        <span className="attachments">
          <FileText size={14} />
          {email.attachments.length}
          {email.missingAttachment && (
            <AlertTriangle size={14} className="attachment-warning" />
          )}
        </span>
      </td>
      <td>
        <button
          className="row-action"
          onClick={(event) => {
            event.stopPropagation();
            if (email.status === "Failed") {
              onRetry(email.id);
            } else {
              onOpen(email);
            }
          }}
          aria-label={
            email.status === "Failed" ? `Retry ${email.id}` : `Open ${email.id}`
          }
        >
          {email.status === "Failed" ? (
            <RefreshCw size={15} />
          ) : (
            <ChevronRight size={16} />
          )}
        </button>
      </td>
    </tr>
  );
}

function DetailView({
  email,
  onBack,
  onNotify
}: {
  email: EmailRecord;
  onBack: () => void;
  onNotify: (message: string) => void;
}) {
  const [evidence, setEvidence] = useState<FieldResult | null>(null);
  const [reclassify, setReclassify] = useState(false);
  const meta = statusMeta[email.status];
  const fields = email.fields ?? [];
  const [edited, setEdited] = useState<Record<string, string>>({});
  const reviewRequired = email.status === "Needs review" || email.checkRequired;
  const processingLabel =
    email.classificationProvider === "gemini"
      ? "LLM fallback"
      : email.classificationProvider === "spacy"
        ? "NLP comparison"
        : email.classificationProvider === "primary+gemini_failed"
          ? "NLP comparison · LLM fallback"
          : "Classification pipeline";
  return (
    <section className="detail-layout">
      <div className="detail-header">
        <button className="back-link" onClick={onBack}>
          <ArrowLeft size={16} /> Back to inbox
        </button>
        <div className="detail-actions">
          <button className="button button-quiet">
            <Clipboard size={14} /> Copy ID
          </button>
          <button className="button button-quiet">
            <MoreHorizontal size={15} />
          </button>
        </div>
      </div>
      <div className="detail-grid">
        <aside className="context-panel">
          <div className="context-section">
            <span className="eyebrow">EMAIL CONTEXT</span>
            <h2>{email.subject}</h2>
            <p className="sender-line">{email.sender}</p>
            <div className="context-meta">
              <span>{email.received}</span>
              <code>{email.id}</code>
            </div>
          </div>
          <div className="context-section">
            <div className="section-label">
              Classification{" "}
              <button
                className="text-button"
                onClick={() => setReclassify(!reclassify)}
              >
                Reclassify
              </button>
            </div>
            <div className="classification">
              <span className="category-badge">{email.category}</span>
              <span className="confidence">
                {(email.categoryConfidence * 100).toFixed(1)}% ·{" "}
                {processingLabel}
              </span>
            </div>
            {reclassify && (
              <select className="select-full" defaultValue={email.category}>
                <option>{email.category}</option>
                <option>Comparison request</option>
                <option>General</option>
                <option>Invoice query</option>
              </select>
            )}
            <p className="reason-copy">
              {email.category === "Comparison request"
                ? "Subject and attachments indicate a draft document check."
                : "Message classified and routed outside document comparison."}
            </p>
          </div>
          <div className="context-section">
            <div className="section-label">
              Attachments{" "}
              <span className="muted-text">{email.attachments.length}</span>
            </div>
            {email.attachments.length ? (
              email.attachments.map((file) => (
                <div className="attachment-row" key={file}>
                  <FileText size={16} />
                  <div>
                    <strong>{file}</strong>
                    <span>Attachment available from inbox</span>
                  </div>
                  <button className="icon-button" aria-label={`View ${file}`}>
                    <PanelRight size={15} />
                  </button>
                </div>
              ))
            ) : (
              <div className="muted-empty">No attachments</div>
            )}
          </div>
          <div className="context-section timeline-section">
            <div className="section-label">Pipeline timeline</div>
            <TimelineStep label="Ingested" time="Completed" state="done" />
            <TimelineStep
              label="Classified"
              time="Completed from API"
              state="done"
            />
            <TimelineStep
              label="Extracted"
              time="Completed on demand"
              state={email.status === "Failed" ? "failed" : "done"}
            />
            <TimelineStep
              label="Compared"
              time={
                email.status === "Failed" ? "Waiting" : "Completed on demand"
              }
              state={email.status === "Failed" ? "waiting" : "done"}
            />
            <TimelineStep
              label="Reviewed"
              time={
                email.status === "Needs review"
                  ? "Waiting for operator"
                  : "Not required"
              }
              state={email.status === "Needs review" ? "waiting" : "muted"}
            />
            {email.status === "Failed" && (
              <div className="timeline-error">
                <strong>{email.reason ?? "Processing failed"}</strong>
                <span>Try the step again to continue.</span>
                <button
                  className="button button-small"
                  onClick={() => onNotify(`Retry queued for ${email.id}`)}
                >
                  <RefreshCw size={13} /> Retry
                </button>
              </div>
            )}
          </div>
        </aside>
        <div className="comparison-panel">
          <div className="result-header">
            <div>
              <span className={`status ${meta.className}`}>
                <span className="status-dot" />
                {meta.label}
              </span>
              <h1>
                {email.status === "Mismatch"
                  ? "1 mismatch found"
                  : email.status === "Match"
                    ? "No mismatch detected"
                    : email.status === "Needs review"
                      ? `Needs review — ${email.reason}`
                      : email.status === "Failed"
                        ? "Processing failed"
                        : "Not a comparison request"}
              </h1>
              <p>
                {email.status === "Mismatch"
                  ? "The SI is the reference. Review the differing field before sending the final report."
                  : email.status === "Match"
                    ? "All seven fields agree after normalization."
                    : (email.reason ?? email.result)}
              </p>
            </div>
            <button className="button button-quiet">
              <Download size={14} /> Download evidence
            </button>
          </div>
          {fields.length > 0 ? (
            <div className="comparison-table">
              <div className="comparison-head">
                <span>Field</span>
                <span>SI · reference</span>
                <span>BL · draft</span>
                <span>Result</span>
              </div>
              {fields.map((field) => (
                <div
                  className={`comparison-row ${field.result === "mismatch" ? "row-mismatch" : field.result === "review" ? "row-review" : ""}`}
                  key={field.field}
                >
                  <strong>{field.field}</strong>
                  <span className="value-cell">
                    {reviewRequired ? (
                      <input
                        className="review-input"
                        aria-label={`${field.field} SI value`}
                        defaultValue={field.si}
                        onChange={(e) =>
                          setEdited((v) => ({
                            ...v,
                            [`${field.field}_si`]: e.target.value
                          }))
                        }
                      />
                    ) : (
                      <code>{field.si}</code>
                    )}
                    <Confidence value={field.confidence} />
                  </span>
                  <span className="value-cell">
                    {reviewRequired ? (
                      <input
                        className="review-input"
                        aria-label={`${field.field} BL value`}
                        defaultValue={field.bl}
                        onChange={(e) =>
                          setEdited((v) => ({
                            ...v,
                            [`${field.field}_bl`]: e.target.value
                          }))
                        }
                      />
                    ) : (
                      <code>{field.bl}</code>
                    )}
                    <Confidence value={field.confidence} />
                  </span>
                  <span>
                    <ResultBadge result={field.result} />
                    <button
                      className="evidence-button"
                      onClick={() => setEvidence(field)}
                      aria-label={`View evidence for ${field.field}`}
                    >
                      <PanelRight size={14} />
                    </button>
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="no-comparison">
              <div className="empty-icon">
                <CheckCircle2 size={22} />
              </div>
              <strong>No document comparison was run</strong>
              <span>
                This message was classified as <b>{email.category}</b> and
                stopped before extraction.
              </span>
            </div>
          )}
          <div className="detail-note">
            <CircleHelp size={15} />
            <span>
              Comparison results are based on extracted document values. Select
              the evidence icon to inspect the source snippet.
            </span>
          </div>
          {reviewRequired && (
            <div className="review-save-bar">
              <span>
                <AlertTriangle size={15} /> Check required · edit values, then
                resolve this case.
              </span>
              <button
                className="button button-primary"
                onClick={async () => {
                  await api.correct(email.id, edited);
                  onNotify("Correction saved and review resolved");
                }}
              >
                Save correction
              </button>
            </div>
          )}
        </div>
      </div>
      {evidence && (
        <EvidenceDrawer field={evidence} onClose={() => setEvidence(null)} />
      )}
    </section>
  );
}

function Confidence({ value }: { value: number }) {
  return (
    <span
      className={`confidence-dot ${value < 0.7 ? "low" : ""}`}
      title={`${Math.round(value * 100)}% confidence`}
    />
  );
}
function ResultBadge({ result }: { result: FieldResult["result"] }) {
  const labels = {
    match: ["match", "Match"],
    mismatch: ["mismatch", "Mismatch"],
    normalized: ["normalized", "Normalized"],
    review: ["review", "Needs review"]
  };
  const [className, label] = labels[result];
  return (
    <span className={`result-badge ${className}`}>
      {result === "match" ? (
        <Check size={13} />
      ) : result === "mismatch" ? (
        <X size={13} />
      ) : result === "normalized" ? (
        "≈"
      ) : (
        <AlertTriangle size={13} />
      )}
      {label}
    </span>
  );
}
function TimelineStep({
  label,
  time,
  state
}: {
  label: string;
  time: string;
  state: "done" | "failed" | "waiting" | "muted";
}) {
  return (
    <div className={`timeline-step ${state}`}>
      <span className="timeline-icon">
        {state === "done" ? (
          <Check size={12} />
        ) : state === "failed" ? (
          <X size={12} />
        ) : state === "waiting" ? (
          <Clock3 size={12} />
        ) : (
          <span />
        )}
      </span>
      <div>
        <strong>{label}</strong>
        <span>{time}</span>
      </div>
    </div>
  );
}
function EvidenceDrawer({
  field,
  onClose
}: {
  field: FieldResult;
  onClose: () => void;
}) {
  return (
    <aside className="evidence-drawer">
      <div className="drawer-heading">
        <div>
          <span className="eyebrow">SOURCE EVIDENCE</span>
          <h2>{field.field}</h2>
        </div>
        <button
          className="icon-button"
          onClick={onClose}
          aria-label="Close evidence"
        >
          <X size={17} />
        </button>
      </div>
      <div className="evidence-block">
        <span className="evidence-label">SHIPPING INSTRUCTION</span>
        <code>{field.si}</code>
        <p>Matched from the reference document.</p>
      </div>
      <div className="evidence-block source-block">
        <span className="evidence-label">RAW SOURCE SNIPPET</span>
        <pre>{`...\n${field.evidence}\n...`}</pre>
        <span className="highlight-line">{field.evidence}</span>
      </div>
      <div className="evidence-block">
        <span className="evidence-label">NORMALIZED VALUE</span>
        <code>{field.bl}</code>
        <p>
          Confidence <strong>{Math.round(field.confidence * 100)}%</strong>
        </p>
      </div>
    </aside>
  );
}

function ReviewView({
  emails,
  onOpen,
  onNotify
}: {
  emails: EmailRecord[];
  onOpen: (email: EmailRecord) => void;
  onNotify: (message: string) => void;
}) {
  const reviewEmails = emails.filter(
    (email) => email.status === "Needs review"
  );
  return (
    <section className="page-wrap review-page">
      <div className="page-heading">
        <div>
          <h1>Review queue</h1>
          <p>Resolve uncertain cases with the evidence in view.</p>
        </div>
        <button
          className="button button-primary"
          onClick={() => onNotify("Review queue is up to date")}
        >
          <RefreshCw size={15} /> Refresh queue
        </button>
      </div>
      <div className="queue-banner">
        <div className="queue-count">
          <strong>{reviewEmails.length}</strong>
          <span>cases waiting for review</span>
        </div>
        <div>
          <span className="status status-review">
            <span className="status-dot" />
            Review cases are ordered by the inbox source
          </span>
        </div>
      </div>
      <div className="review-scroll">
        <div className="review-list">
          {reviewEmails.map((email) => (
            <button
              className="review-item"
              key={email.id}
              onClick={() => onOpen(email)}
            >
              <div className="review-item-main">
                <div className="review-icon">
                  <AlertTriangle size={16} />
                </div>
                <div>
                  <strong>{email.subject}</strong>
                  <span>
                    {email.sender} · {email.id}
                  </span>
                </div>
              </div>
              <div className="review-reason">
                <span>REASON</span>
                <strong>{email.reason}</strong>
              </div>
              <div className="review-fields">
                <span>Affected</span>
                <b>
                  {email.missingAttachment
                    ? "Attachment missing"
                    : email.fields
                        ?.filter(
                          (field) =>
                            field.result === "review" ||
                            field.result === "mismatch"
                        )
                        .map((field) => field.field)
                        .join(", ") || "Classification confidence"}
                </b>
              </div>
              <ChevronRight size={17} />
            </button>
          ))}
        </div>
      </div>
      <div className="review-empty-note">
        <CheckCircle2 size={17} />
        <span>
          When a case is resolved, its comparison report is recomputed
          automatically.
        </span>
      </div>
    </section>
  );
}

function TestView({ onNotify }: { onNotify: (message: string) => void }) {
  const [mode, setMode] = useState<"classification" | "comparison" | "end-to-end">("classification");
  const [run, setRun] = useState<ClassificationTestResult | null>(null);
  const [running, setRunning] = useState(false);
  const [selected, setSelected] = useState<
    ClassificationTestResult["results"][number] | null
  >(null);
  const execute = async () => {
    setRunning(true);
    try {
      setRun(await api.runClassificationTest());
      onNotify("Classification test completed");
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Test failed");
    } finally {
      setRunning(false);
    }
  };
  const labels = [
    "BL_COMPARISON",
    "SI_REQUEST",
    "INVOICE_QUERY",
    "GENERAL",
    "SPAM"
  ];
  if (mode === "end-to-end") {
    return <EndToEndTestView onNotify={onNotify} onBack={() => setMode("classification")} onComparison={() => setMode("comparison")} />;
  }
  if (mode === "comparison") {
    return <ComparisonTestView onNotify={onNotify} onBack={() => setMode("classification")} onEndToEnd={() => setMode("end-to-end")} />;
  }
  return (
    <section className="page-wrap">
      <div className="page-heading">
        <div>
          <h1>Pipeline test</h1>
          <p>
            Re-run classification across all 520 emails against the private
            ground truth.
          </p>
        </div>
        <button
          className="button button-primary"
          onClick={execute}
          disabled={running}
        >
          <RefreshCw size={15} />{" "}
          {running ? "Running 520 emails..." : "Run classification test"}
        </button>
      </div>
      <div className="view-tabs" role="tablist" aria-label="Pipeline tests">
        <button className="button button-secondary" role="tab" aria-selected="true">Classification</button>
        <button className="button button-secondary" role="tab" onClick={() => setMode("comparison")}>Comparison</button>
        <button className="button button-secondary" role="tab" onClick={() => setMode("end-to-end")}>End to end</button>
      </div>
      {!run ? (
        <div className="empty-state">
          <Activity size={24} />
          <strong>No test run yet</strong>
          <span>
            Run the complete classification pipeline to inspect accuracy and
            errors.
          </span>
        </div>
      ) : (
        <>
          <div className="stats-strip">
            <div className="stat">
              <span>Accuracy</span>
              <strong>{(run.accuracy * 100).toFixed(1)}%</strong>
              <small>
                {run.correct} / {run.total} correct
              </small>
            </div>
            <div className="stat">
              <span>Macro precision</span>
              <strong>{(run.macro.precision * 100).toFixed(1)}%</strong>
            </div>
            <div className="stat">
              <span>Macro sensitivity</span>
              <strong>{(run.macro.recall * 100).toFixed(1)}%</strong>
            </div>
            <div className="stat">
              <span>Macro F1</span>
              <strong>{(run.macro.f1 * 100).toFixed(1)}%</strong>
            </div>
            <div className="stat">
              <span>Review escalations</span>
              <strong>{run.review_count}</strong>
            </div>
          </div>
          <div className="test-grid">
            <div>
              <div className="panel-heading">
                <div>
                  <span className="eyebrow">CONFUSION MATRIX</span>
                  <h2>Actual versus predicted</h2>
                </div>
              </div>
              <div className="matrix-wrap">
                <table className="test-matrix">
                  <thead>
                    <tr>
                      <th>Actual \ Predicted</th>
                      {labels.map((label) => (
                        <th key={label}>{label.replace("_", " ")}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {labels.map((actual) => (
                      <tr key={actual}>
                        <th>{actual.replace("_", " ")}</th>
                        {labels.map((predicted) => (
                          <td
                            className={
                              actual === predicted ? "matrix-correct" : ""
                            }
                            key={predicted}
                          >
                            {run.confusion_matrix[actual]?.[predicted] ?? 0}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            <div className="score-panel">
              <span className="eyebrow">PER-CATEGORY QUALITY</span>
              {labels.map((label) => (
                <div className="test-metric" key={label}>
                  <strong>{label.replace("_", " ")}</strong>
                  <span>
                    P {(run.per_category[label].precision * 100).toFixed(1)}% ·
                    R {(run.per_category[label].recall * 100).toFixed(1)}% · F1{" "}
                    {(run.per_category[label].f1 * 100).toFixed(1)}%
                  </span>
                  <small>
                    {run.per_category[label].support} actual records
                  </small>
                </div>
              ))}
            </div>
          </div>
          <div className="test-results">
            <div className="panel-heading">
              <div>
                <span className="eyebrow">RECORD-LEVEL RESULTS</span>
                <h2>Ground truth versus classifier</h2>
              </div>
            </div>
            <div className="test-result-head">
              <span>Email</span>
              <span>Ground truth</span>
              <span>Predicted</span>
              <span>Confidence</span>
              <span />
            </div>
            {run.results
              .filter((item) => !item.correct)
              .map((item) => (
                <button
                  className="test-result-row"
                  key={item.email_id}
                  onClick={() => setSelected(item)}
                >
                  <span>
                    <strong>{item.email_id}</strong>
                    <small>{item.subject}</small>
                  </span>
                  <span>{item.actual}</span>
                  <span className="result-alert">{item.predicted}</span>
                  <span>{(item.confidence * 100).toFixed(1)}%</span>
                  <ChevronRight size={15} />
                </button>
              ))}
            {run.results.every((item) => item.correct) && (
              <div className="empty-state">
                <CheckCircle2 size={22} />
                <strong>No misclassifications</strong>
              </div>
            )}
          </div>
          {selected && (
            <div className="test-detail">
              <button className="icon-button" onClick={() => setSelected(null)}>
                <X size={16} />
              </button>
              <span className="eyebrow">TEST DETAIL</span>
              <h2>{selected.email_id}</h2>
              <p>{selected.subject}</p>
              <div className="test-detail-values">
                <span>
                  Ground truth<strong>{selected.actual}</strong>
                </span>
                <span>
                  Predicted<strong>{selected.predicted}</strong>
                </span>
                <span>
                  Score
                  <strong>{(selected.confidence * 100).toFixed(1)}%</strong>
                </span>
                <span>
                  Path
                  <strong>
                    {selected.provider === "spacy"
                      ? "NLP comparison"
                      : "LLM fallback"}
                  </strong>
                </span>
              </div>
              {selected.review_reason && (
                <p className="reason-copy">{selected.review_reason}</p>
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}

function ComparisonTestView({ onNotify, onBack, onEndToEnd }: { onNotify: (message: string) => void; onBack: () => void; onEndToEnd: () => void }) {
  const [run, setRun] = useState<ComparisonTestResult | null>(null);
  const [running, setRunning] = useState(false);
  const [selected, setSelected] = useState<ComparisonTestResult["results"][number] | null>(null);
  const execute = async () => {
    setRunning(true);
    try { setRun(await api.runComparisonTest()); onNotify("Comparison test completed"); }
    catch (error) { onNotify(error instanceof Error ? error.message : "Test failed"); }
    finally { setRunning(false); }
  };
  const statuses = ["OK", "MISMATCH", "NEEDS_REVIEW"];
  const label = (value: string) => value.replaceAll("_", " ");
  return <section className="page-wrap">
    <div className="page-heading">
      <div><h1>Pipeline test</h1><p>Re-run document comparison across the 200 comparison requests in the v2 dataset.</p></div>
      <button className="button button-primary" onClick={execute} disabled={running}><RefreshCw size={15} /> {running ? "Running comparisons..." : "Run comparison test"}</button>
    </div>
    <div className="view-tabs" role="tablist" aria-label="Pipeline tests">
      <button className="button button-secondary" onClick={onBack}>Classification</button>
      <button className="button button-secondary" role="tab" aria-selected="true">Comparison</button>
      <button className="button button-secondary" onClick={onEndToEnd}>End to end</button>
    </div>
    <p className="reason-copy"><strong>Reading comparison outcomes:</strong> <b>No defect</b> means an SI/BL pair was compared and no field differed. <b>Not comparable</b> means the request has no usable SI/BL pair and is correctly routed to review while documents are awaited.</p>
    {!run ? <div className="empty-state"><Activity size={24} /><strong>No comparison test run yet</strong><span>Run the comparison pipeline to inspect defect detection and review escalation.</span></div> : <>
      <div className="stats-strip">
        <div className="stat"><span>SI / BL pairs</span><strong>{run.pair_total}</strong><small>{run.not_comparable_total} requests awaiting documents</small></div>
        <div className="stat"><span>Exact defect fields</span><strong>{(run.pair_exact_defect_field_accuracy * 100).toFixed(1)}%</strong><small>pair records only</small></div>
        <div className="stat"><span>Field F1</span><strong>{(run.macro_field.f1 * 100).toFixed(1)}%</strong><small>macro across seven fields</small></div>
        <div className="stat"><span>Review recall</span><strong>{(run.review_recall * 100).toFixed(1)}%</strong><small>uncertain cases escalated</small></div>
        <div className="stat"><span>Review precision</span><strong>{(run.review_precision * 100).toFixed(1)}%</strong><small>escalations that needed review</small></div>
      </div>
      <div className="test-grid">
        <div><div className="panel-heading"><div><span className="eyebrow">COMPARABLE PAIRS ONLY</span><h2>Expected outcome versus pipeline outcome</h2></div></div><div className="matrix-wrap"><table className="test-matrix"><thead><tr><th>Expected \ Predicted</th>{statuses.map(s => <th key={s}>{label(s)}</th>)}</tr></thead><tbody>{statuses.map(actual => <tr key={actual}><th>{label(actual)}</th>{statuses.map(predicted => <td className={actual === predicted ? "matrix-correct" : ""} key={predicted}>{run.status_confusion_matrix[actual]?.[predicted] ?? 0}</td>)}</tr>)}</tbody></table></div></div>
        <div className="score-panel"><span className="eyebrow">FIELD QUALITY</span>{Object.entries(run.field_metrics).map(([field, metric]) => <div className="test-metric" key={field}><strong>{label(field)}</strong><span>P {(metric.precision * 100).toFixed(1)}% · R {(metric.recall * 100).toFixed(1)}% · F1 {(metric.f1 * 100).toFixed(1)}%</span><small>{metric.support} defective examples</small></div>)}</div>
      </div>
      <div className="test-results"><div className="panel-heading"><div><span className="eyebrow">RECORD-LEVEL RESULTS</span><h2>Comparable pair issues</h2><p>Requests without an SI and BL pair are tracked separately as awaiting documents.</p></div></div><div className="test-result-head"><span>Email</span><span>Ground truth</span><span>Predicted</span><span>Fields</span><span /></div>{run.results.filter(item => !item.correct && item.has_attachment_pair).map(item => <button className="test-result-row" key={item.email_id} onClick={() => setSelected(item)}><span><strong>{item.email_id}</strong><small>{item.subject}</small></span><span>{item.actual}</span><span className="result-alert">{item.predicted}</span><span>{item.predicted_fields.length ? item.predicted_fields.map(label).join(", ") : item.review_reason ?? "—"}</span><ChevronRight size={15} /></button>)}{run.results.filter(item => item.has_attachment_pair && !item.correct).length === 0 && <div className="empty-state"><CheckCircle2 size={22} /><strong>No comparable-pair errors</strong></div>}</div>
      {selected && <div className="test-detail"><button className="icon-button" onClick={() => setSelected(null)}><X size={16} /></button><span className="eyebrow">COMPARISON DETAIL</span><h2>{selected.email_id}</h2><p>{selected.subject}</p><div className="test-detail-values"><span>Ground truth<strong>{selected.actual}</strong></span><span>Predicted<strong>{selected.predicted}</strong></span><span>Expected fields<strong>{selected.actual_fields.map(label).join(", ") || "None"}</strong></span><span>Predicted fields<strong>{selected.predicted_fields.map(label).join(", ") || "None"}</strong></span></div>{selected.review_reason && <p className="reason-copy">Review reason: {selected.review_reason}</p>}</div>}
    </>}
  </section>;
}

function EndToEndTestView({ onNotify, onBack, onComparison }: { onNotify: (message: string) => void; onBack: () => void; onComparison: () => void }) {
  const [score, setScore] = useState<EndToEndScore | null>(null);
  const [running, setRunning] = useState(false);
  const execute = async () => {
    setRunning(true);
    try {
      const submission = await api.buildSubmission();
      setScore(await api.submit(submission));
      onNotify("End-to-end score completed");
    } catch (error) { onNotify(error instanceof Error ? error.message : "Scoring failed"); }
    finally { setRunning(false); }
  };
  return <section className="page-wrap">
    <div className="page-heading"><div><h1>Pipeline test</h1><p>Score the current classification and comparison output against the private v2 ground truth.</p></div><button className="button button-primary" onClick={execute} disabled={running}><RefreshCw size={15} /> {running ? "Building and scoring..." : "Run end-to-end score"}</button></div>
    <div className="view-tabs" role="tablist" aria-label="Pipeline tests"><button className="button button-secondary" onClick={onBack}>Classification</button><button className="button button-secondary" onClick={onComparison}>Comparison</button><span className="button button-secondary" aria-selected="true">End to end</span></div>
    {!score ? <div className="empty-state"><Activity size={24} /><strong>No end-to-end score yet</strong><span>Run the complete submission through the existing scoring endpoint.</span></div> : <>
      <div className="stats-strip"><div className="stat"><span>Total score</span><strong>{(score.final_score * 100).toFixed(1)}%</strong><small>weighted leaderboard score</small></div><div className="stat"><span>Stage 1 macro F1</span><strong>{(score.stage1.macro_f1 * 100).toFixed(1)}%</strong><small>classification quality</small></div><div className="stat"><span>Comparison F1</span><strong>{(score.stage3.defect_f1 * 100).toFixed(1)}%</strong><small>defect detection</small></div><div className="stat"><span>End-to-end catch</span><strong>{(score.end_to_end.rate * 100).toFixed(1)}%</strong><small>{score.end_to_end.success} / {score.end_to_end.total} exact defects</small></div><div className="stat"><span>Review recall</span><strong>{(score.reliability.escalation_recall * 100).toFixed(1)}%</strong><small>reliability axis</small></div></div>
      <div className="test-grid"><div className="score-panel"><span className="eyebrow">SCORE COMPONENTS</span><div className="test-metric"><strong>Classification</strong><span>Macro F1 {(score.stage1.macro_f1 * 100).toFixed(1)}% · accuracy {(score.stage1.accuracy * 100).toFixed(1)}%</span><small>Weight {(score.weights.stage1 * 100).toFixed(0)}%</small></div><div className="test-metric"><strong>Comparison</strong><span>Defect F1 {(score.stage3.defect_f1 * 100).toFixed(1)}% · field F1 {(score.stage3.field_f1 * 100).toFixed(1)}%</span><small>Weight {(score.weights.stage3 * 100).toFixed(0)}%</small></div><div className="test-metric"><strong>Exact defect capture</strong><span>{score.end_to_end.success} of {score.end_to_end.total} successful</span><small>Weight {(score.weights.end_to_end * 100).toFixed(0)}%</small></div></div><div className="score-panel"><span className="eyebrow">RELIABILITY</span><div className="test-metric"><strong>Escalation precision</strong><span>{(score.reliability.escalation_precision * 100).toFixed(1)}%</span><small>{score.reliability.pred_review} cases escalated</small></div><div className="test-metric"><strong>Escalation recall</strong><span>{(score.reliability.escalation_recall * 100).toFixed(1)}%</span><small>{score.reliability.gold_review} cases required review</small></div><div className="test-metric"><strong>Escalation F1</strong><span>{(score.reliability.escalation_f1 * 100).toFixed(1)}%</span><small>precision and recall combined</small></div></div></div>
      <div className="test-results"><div className="panel-heading"><div><span className="eyebrow">SCORING CONTRACT</span><h2>How this score is calculated</h2></div></div><p className="reason-copy">The score comes directly from <code>POST /submit</code>. It combines classification macro F1, comparable-document defect F1, and exact end-to-end defect capture using the server’s configured weights.</p></div>
    </>}
  </section>;
}

function RunsView({
  emails,
  onNotify
}: {
  emails: EmailRecord[];
  onNotify: (message: string) => void;
}) {
  const failed = emails.filter((email) => email.status === "Failed").length;
  const comparisons = emails.filter(
    (email) => email.category === "Comparison request"
  ).length;
  return (
    <section className="page-wrap">
      <div className="page-heading">
        <div>
          <h1>Run status</h1>
          <p>Processing history across the current inbox.</p>
        </div>
        <button
          className="button button-primary"
          onClick={() => onNotify("Retrying all failed items")}
        >
          <RefreshCw size={15} /> Retry all failed
        </button>
      </div>
      <div className="run-overview">
        <div>
          <span className="eyebrow">CURRENT RUN</span>
          <strong>Inbox sync · live source</strong>
          <span>{emails.length} emails · Loaded from verification service</span>
        </div>
        <span className="run-pill">
          <span className="health-dot" />
          {emails.length - failed} complete · {failed} failed
        </span>
      </div>
      <div className="run-table">
        <div className="run-head">
          <span>Step</span>
          <span>Completed</span>
          <span>Failed</span>
          <span>Avg. duration</span>
          <span>Status</span>
        </div>
        {[
          ["Ingest", emails.length.toString(), "0", "—", "Complete"],
          ["Classify", emails.length.toString(), "0", "—", "Complete"],
          [
            "Extract",
            (emails.length - failed).toString(),
            failed.toString(),
            "On demand",
            failed ? `${failed} failed` : "Complete"
          ],
          ["Compare", comparisons.toString(), "0", "On demand", "Complete"],
          ["Export", "—", "—", "—", "Waiting"]
        ].map((row) => (
          <div className="run-row" key={row[0]}>
            <strong>{row[0]}</strong>
            <span>{row[1]}</span>
            <span className={row[2] === "1" ? "result-alert" : ""}>
              {row[2]}
            </span>
            <span className="mono">{row[3]}</span>
            <span
              className={
                row[4] === "1 failed"
                  ? "status status-failed"
                  : "status status-neutral"
              }
            >
              <span className="status-dot" />
              {row[4]}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

function ExportView({
  emails,
  onNotify
}: {
  emails: EmailRecord[];
  onNotify: (message: string) => void;
}) {
  const [submitted, setSubmitted] = useState(false);
  const [submission, setSubmission] = useState<Record<string, unknown> | null>(
    null
  );
  const [score, setScore] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  return (
    <section className="page-wrap export-page">
      <div className="page-heading">
        <div>
          <h1>Export results</h1>
          <p>Prepare the self-evaluation payload for this inbox run.</p>
        </div>
        <button
          className="button button-primary"
          onClick={async () => {
            setSubmitting(true);
            try {
              const payload = await api.buildSubmission();
              const result = await api.submit(payload);
              setSubmission(payload);
              const returnedScore =
                typeof result.final_score === "number"
                  ? result.final_score
                  : typeof result.score === "number"
                    ? result.score
                    : null;
              setScore(returnedScore);
              setSubmitted(true);
              onNotify("Submission scored successfully");
            } catch (error) {
              onNotify(
                error instanceof Error ? error.message : "Submission failed"
              );
            } finally {
              setSubmitting(false);
            }
          }}
        >
          <Send size={15} />{" "}
          {submitting ? "Submitting..." : "Submit to self-evaluation"}
        </button>
      </div>
      <div className="export-grid">
        <div className="export-preview">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">JSON PREVIEW</span>
              <h2>sample_submission.json</h2>
            </div>
            <button className="button button-quiet">
              <Clipboard size={14} /> Copy
            </button>
          </div>
          <pre>
            {JSON.stringify(
              submission ?? {
                info: "Build a live submission to preview all inbox records",
                records: emails.length
              },
              null,
              2
            )}
          </pre>
          <div className="export-footer">
            <span>
              <Check size={14} /> Schema valid
            </span>
            <button className="button button-quiet">
              <Download size={14} /> Download JSON
            </button>
          </div>
        </div>
        <div className="score-panel">
          <span className="eyebrow">SELF-EVALUATION</span>
          {submitted ? (
            <>
              <div className="score-result">
                <strong>
                  {score === null ? "—" : `${(score * 100).toFixed(1)}%`}
                </strong>
                <span>/ 100</span>
              </div>
              <div className="score-breakdown">
                <span>
                  Records submitted{" "}
                  <b>{submission ? Object.keys(submission).length : 0}</b>
                </span>
                <span>
                  Service response <b>received</b>
                </span>
                <span>
                  Source <b>live API</b>
                </span>
              </div>
              <div className="score-note">
                <CheckCircle2 size={15} /> Score received just now
              </div>
            </>
          ) : (
            <div className="score-empty">
              <BarChart3 size={22} />
              <strong>No score yet</strong>
              <span>Submit this payload to see the returned scoreboard.</span>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function ShortcutDialog({ onClose }: { onClose: () => void }) {
  return (
    <div className="dialog-backdrop" onClick={onClose}>
      <div
        className="shortcut-dialog"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="drawer-heading">
          <div>
            <span className="eyebrow">KEYBOARD</span>
            <h2>Shortcuts</h2>
          </div>
          <button
            className="icon-button"
            onClick={onClose}
            aria-label="Close shortcuts"
          >
            <X size={17} />
          </button>
        </div>
        {[
          ["/", "Focus search"],
          ["Enter", "Open selected email"],
          ["Esc", "Close panel"],
          ["?", "Show shortcuts"]
        ].map(([key, label]) => (
          <div className="shortcut-row" key={key}>
            <kbd>{key}</kbd>
            <span>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Dashboard;
