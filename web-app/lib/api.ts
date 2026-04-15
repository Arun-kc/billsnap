const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const AUTH_TOKEN = process.env.NEXT_PUBLIC_AUTH_TOKEN ?? "";

async function request<T>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${AUTH_TOKEN}`,
      ...(init.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
      ...init.headers,
    },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error");
    throw new Error(`API ${res.status}: ${text}`);
  }

  return res.json() as Promise<T>;
}

// ── Types ────────────────────────────────────────────────────────────────────

export interface UploadResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface JobStatus {
  job_id: string;
  status: "pending" | "processing" | "completed" | "failed" | "needs_review";
  bill_id?: string;
  extraction_confidence?: number;
}

export interface LineItem {
  id: string;
  bill_id: string;
  item_name?: string;
  hsn_code?: string;
  quantity?: number;
  unit?: string;
  unit_price?: number;
  total_price?: number;
  gst_rate?: number;
  sort_order: number;
}

export interface BillSummary {
  id: string;
  vendor_name?: string;
  bill_date?: string;
  total_amount?: number;
  category?: string;
  document_type: string;
  is_verified: boolean;
  extraction_confidence?: number;
  thumbnail_url?: string;
}

export interface BillDetail extends BillSummary {
  vendor_gstin?: string;
  bill_number?: string;
  taxable_amount?: number;
  cgst_amount: number;
  sgst_amount: number;
  igst_amount: number;
  user_notes?: string;
  image_url?: string;
  line_items: LineItem[];
  created_at: string;
  updated_at: string;
}

export interface MonthlySummary {
  total_amount: number;
  total_cgst: number;
  total_sgst: number;
  total_igst: number;
  bill_count: number;
  unverified_count: number;
}

export interface Pagination {
  page: number;
  per_page: number;
  total: number;
}

export interface BillListResponse {
  bills: BillSummary[];
  pagination: Pagination;
  summary: MonthlySummary;
}

export interface BillUpdatePayload {
  vendor_name?: string;
  vendor_gstin?: string;
  bill_number?: string;
  bill_date?: string;
  document_type?: string;
  category?: string;
  total_amount?: number;
  taxable_amount?: number;
  cgst_amount?: number;
  sgst_amount?: number;
  igst_amount?: number;
  is_verified?: boolean;
  user_notes?: string;
  line_items?: Omit<LineItem, "id" | "bill_id">[];
}

// ── API calls ────────────────────────────────────────────────────────────────

export async function uploadBill(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  return request<UploadResponse>("/api/v1/bills/upload", {
    method: "POST",
    body: form,
  });
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  return request<JobStatus>(`/api/v1/jobs/${jobId}`);
}

export async function getBill(billId: string): Promise<BillDetail> {
  return request<BillDetail>(`/api/v1/bills/${billId}`);
}

export async function listBills(params: {
  month?: string;
  verified?: boolean;
  category?: string;
  page?: number;
  per_page?: number;
}): Promise<BillListResponse> {
  const qs = new URLSearchParams();
  if (params.month) qs.set("month", params.month);
  if (params.verified !== undefined) qs.set("verified", String(params.verified));
  if (params.category) qs.set("category", params.category);
  if (params.page) qs.set("page", String(params.page));
  if (params.per_page) qs.set("per_page", String(params.per_page));
  return request<BillListResponse>(`/api/v1/bills?${qs}`);
}

export async function updateBill(
  billId: string,
  payload: BillUpdatePayload
): Promise<BillDetail> {
  return request<BillDetail>(`/api/v1/bills/${billId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteBill(billId: string): Promise<void> {
  await request(`/api/v1/bills/${billId}`, { method: "DELETE" });
}

export function exportUrl(month: string, format: "csv" | "xlsx"): string {
  return `${API_BASE}/api/v1/bills/export?month=${month}&format=${format}&token=${AUTH_TOKEN}`;
}
