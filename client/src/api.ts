export type Category =
  | "Comparison request"
  | "New SI request"
  | "Invoice query"
  | "General"
  | "Spam";
export type EmailStatus =
  | "Mismatch"
  | "Match"
  | "Needs review"
  | "Failed"
  | "Classified";

export type FieldResult = {
  field: string;
  si: string;
  bl: string;
  result: "match" | "mismatch" | "normalized" | "review";
  confidence: number;
  evidence: string;
};

type RawEmail = {
  email_id: string;
  from: string;
  subject: string;
  body: string;
  attachments: string[];
};

export type EmailRecord = {
  id: string;
  subject: string;
  sender: string;
  received: string;
  category: Category;
  categoryConfidence: number;
  status: EmailStatus;
  result: string;
  attachments: string[];
  missingAttachment?: boolean;
  reason?: string;
  fields?: FieldResult[];
  raw?: RawEmail;
  checkRequired?: boolean;
  classificationProvider?: string;
};

type Submission = Record<
  string,
  {
    category: string;
    status: string;
    review_reason: string | null;
    has_defect: boolean;
    defect_fields: string[];
  }
>;

const fieldDefinitions = [
  { name: "Shipper", labels: ["shipper/exporter", "shipper"] },
  { name: "Consignee", labels: ["consignee", "to the order of"] },
  { name: "Notify party", labels: ["notify party", "notify"] },
  { name: "Port of loading", labels: ["port of loading", "load port", "pol"] },
  {
    name: "Port of discharge",
    labels: ["discharge port", "port of discharge", "pod"]
  },
  {
    name: "Container count",
    labels: ["no. of containers or packages", "container count", "containers"]
  },
  { name: "Gross weight (kg)", labels: ["gross weight", "gross wt"] }
];

const apiBase = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");
const endpoint = (path: string) => `${apiBase}${path}`;
const cache = new Map<string, EmailRecord>();

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(endpoint(path), options);
  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

function classify(): { category: Category; confidence: number } {
  return { category: "General", confidence: 0 };
}

function summary(email: RawEmail): EmailRecord {
  const { category, confidence } = classify();
  const comparison = category === "Comparison request";
  const missing = comparison && email.attachments.length < 2;
  return {
    id: email.email_id,
    subject: email.subject,
    sender: email.from,
    received: "Available from source",
    category,
    categoryConfidence: confidence,
    status: comparison && missing ? "Needs review" : "Classified",
    result: comparison
      ? missing
        ? "Awaiting review"
        : "Ready to compare"
      : "Classified — no check needed",
    attachments: email.attachments,
    missingAttachment: missing,
    reason: missing ? "Required SI or BL attachment is missing" : undefined,
    raw: email
  };
}

function attachmentPath(path: string) {
  return path
    .replace(/^attachments\//, "")
    .split("/")
    .map(encodeURIComponent)
    .join("/");
}

async function readAttachment(path: string) {
  const response = await fetch(
    endpoint(`/attachments/${attachmentPath(path)}`)
  );
  if (!response.ok) throw new Error(`Unable to read ${path}`);
  if (!path.toLowerCase().endsWith(".txt"))
    throw new Error(
      `${path} is not a text attachment; document OCR is required`
    );
  return response.text();
}

function valueFromLine(text: string, labels: string[]) {
  const line = text.split(/\r?\n/).find((candidate) => {
    const lower = candidate.trim().toLowerCase();
    return labels.some(
      (label) =>
        lower.startsWith(`${label}:`) ||
        lower.startsWith(`${label} (`) ||
        lower.startsWith(`${label} `)
    );
  });
  if (!line) return "";
  const colon = line.indexOf(":");
  return (colon >= 0 ? line.slice(colon + 1) : line)
    .trim()
    .replace(/\s+/g, " ");
}

function normalized(field: string, value: string) {
  const clean = value
    .toLowerCase()
    .replace(/,/g, "")
    .replace(/[().:'"/\\-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  if (field === "Container count") return clean.match(/\d+/)?.[0] ?? clean;
  if (field === "Gross weight (kg)") return clean.match(/[\d.]+/)?.[0] ?? clean;
  return clean
    .replace(/\b(limited|ltd|pte|sdn|bhd|co|company)\b/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function extractFields(siText: string, blText: string): FieldResult[] {
  return fieldDefinitions.map(({ name, labels }) => {
    const si = valueFromLine(siText, labels);
    const bl = valueFromLine(blText, labels);
    const missing = !si || !bl;
    const same = !missing && normalized(name, si) === normalized(name, bl);
    return {
      field: name,
      si,
      bl,
      result: missing
        ? "review"
        : same
          ? si.trim() === bl.trim()
            ? "match"
            : "normalized"
          : "mismatch",
      confidence: missing ? 0 : same ? 1 : 0.72,
      evidence: bl || si || "No source value found"
    };
  });
}

async function processEmail(
  raw: RawEmail,
  existing?: EmailRecord
): Promise<EmailRecord> {
  const record = existing ?? summary(raw);
  if (record.category !== "Comparison request") return record;
  if (raw.attachments.length < 2)
    return {
      ...record,
      status: "Needs review",
      result: "Awaiting review",
      reason: "Required SI or BL attachment is missing",
      missingAttachment: true
    };
  try {
    const [siText, blText] = await Promise.all([
      readAttachment(raw.attachments[0]),
      readAttachment(raw.attachments[1])
    ]);
    const fields = extractFields(siText, blText);
    const needsReview = fields.some((field) => field.result === "review");
    const mismatches = fields.filter((field) => field.result === "mismatch");
    return {
      ...record,
      fields,
      status: needsReview
        ? "Needs review"
        : mismatches.length
          ? "Mismatch"
          : "Match",
      result: needsReview
        ? `${fields.filter((field) => field.result === "review").length} fields need review`
        : mismatches.length
          ? `${mismatches.length} field${mismatches.length > 1 ? "s" : ""} differ`
          : "No mismatch detected",
      reason: needsReview
        ? "Required value is missing or unreadable"
        : undefined
    };
  } catch (error) {
    return {
      ...record,
      status: "Needs review",
      result: "Awaiting review",
      reason:
        error instanceof Error ? error.message : "Document could not be read"
    };
  }
}

function toSubmission(records: EmailRecord[]): Submission {
  return Object.fromEntries(
    records.map((email) => [
      email.id,
      {
        category:
          email.category === "Comparison request"
            ? "BL_COMPARISON"
            : email.category === "New SI request"
              ? "SI_REQUEST"
              : email.category.toUpperCase().replace(/ /g, "_"),
        status:
          email.status === "Mismatch"
            ? "MISMATCH"
            : email.status === "Needs review"
              ? "NEEDS_REVIEW"
              : "OK",
        review_reason:
          email.status === "Needs review"
            ? (email.reason ?? "Needs operator review")
            : null,
        has_defect: email.status === "Mismatch",
        defect_fields:
          email.fields
            ?.filter((field) => field.result === "mismatch")
            .map((field) =>
              field.field
                .toLowerCase()
                .replace(/ \(kg\)/, "_kg")
                .replace(/ /g, "_")
            ) ?? []
      }
    ])
  );
}

export const api = {
  async runClassificationTest() {
    return request<ClassificationTestResult>("/tests/classification", { method: "POST" });
  },
  async listEmails() {
    const raw = await request<RawEmail[]>("/emails");
    const records = raw.map(summary);
    const classifications = await request<{ results: Array<{ email_id: string; category: string; confidence: number; check_required: boolean; review_reason?: string }> }>("/classifications/run", { method: "POST" });
    const byId = new Map(classifications.results.map((item) => [item.email_id, item]));
    records.forEach((record) => {
      const classification = byId.get(record.id);
      if (!classification) return;
      const categoryMap: Record<string, Category> = { BL_COMPARISON: "Comparison request", SI_REQUEST: "New SI request", INVOICE_QUERY: "Invoice query", GENERAL: "General", SPAM: "Spam" };
      record.category = categoryMap[classification.category] ?? "General";
      record.categoryConfidence = classification.confidence;
      record.checkRequired = classification.check_required;
      if (classification.check_required) { record.status = "Needs review"; record.reason = classification.review_reason ?? "Low classification confidence"; }
    });
    records.forEach((record) => cache.set(record.id, record));
    return records;
  },
  async getEmail(id: string) {
    const raw = await request<RawEmail>(`/emails/${encodeURIComponent(id)}`);
    const record = await processEmail(raw, cache.get(id));
    try {
      const classification = await request<{ check_required: boolean; category: string; confidence: number; provider?: string }>(`/classifications/${encodeURIComponent(id)}`);
      record.category = classification.category === "BL_COMPARISON" ? "Comparison request" : classification.category === "SI_REQUEST" ? "New SI request" : classification.category === "INVOICE_QUERY" ? "Invoice query" : classification.category === "SPAM" ? "Spam" : "General";
      record.categoryConfidence = classification.confidence;
      record.checkRequired = classification.check_required;
      record.classificationProvider = classification.provider;
      if (classification.check_required && record.status === "Classified") record.status = "Needs review";
    } catch { /* classification service is optional during local development */ }
    cache.set(id, record);
    return record;
  },
  async correct(id: string, correctedValues: Record<string, string>, category?: string) {
    await request(`/classifications/${encodeURIComponent(id)}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ corrected_values: correctedValues, category }) });
    const current = cache.get(id);
    if (current) { const updated = { ...current, status: "Classified" as EmailStatus, result: "Review resolved", checkRequired: false }; cache.set(id, updated); return updated; }
    return this.getEmail(id);
  },
  async retry(id: string) {
    return this.getEmail(id);
  },
  async approve(id: string) {
    const existing = cache.get(id);
    if (existing)
      cache.set(id, {
        ...existing,
        status: "Match",
        result: "Review resolved"
      });
    return cache.get(id) ?? this.getEmail(id);
  },
  async buildSubmission() {
    const records = cache.size ? [...cache.values()] : await this.listEmails();
    const pending = records.filter(
      (record) =>
        record.category === "Comparison request" &&
        !record.missingAttachment &&
        !record.fields
    );
    const processed = await Promise.all(
      pending.map((record) => this.getEmail(record.id))
    );
    const merged = records.map(
      (record) => processed.find((item) => item.id === record.id) ?? record
    );
    return toSubmission(merged);
  },
  async submit(submission: Submission) {
    return request<{
      score?: number;
      final_score?: number;
      [key: string]: unknown;
    }>("/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(submission)
    });
  }
};

export type ClassificationTestResult = {
  total: number; correct: number; accuracy: number; review_count: number;
  confusion_matrix: Record<string, Record<string, number>>;
  per_category: Record<string, { support: number; precision: number; recall: number; f1: number }>;
  macro: { precision: number; recall: number; f1: number };
  results: Array<{ email_id: string; subject: string; actual: string; predicted: string; confidence: number; provider: string; check_required: boolean; review_reason?: string; correct: boolean }>;
};
