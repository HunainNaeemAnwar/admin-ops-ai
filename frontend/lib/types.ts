export interface Worker {
  id: number
  name: string
}

export interface Product {
  id: number
  code: string
  rate: number
}

export interface DailyEntry {
  date: string
  status: "present" | "absent" | "no_data"
  reason?: string
  products: Record<string, number>
}

export interface WorkerMonthData {
  worker: string
  year: number
  month: number
  days: DailyEntry[]
  source: "live" | "archived" | "none"
}

export interface DailyTotals {
  [productCode: string]: number
}

export interface DailyReport {
  date: string
  entries: Array<{
    worker_name: string
    product_code: string
    quantity: number
    status: string
  }>
  totals: DailyTotals
  total_pieces: number
}

export interface MonthlyWorkerSummary {
  worker: string
  totals: Record<string, number>
}

export interface MonthlyReport {
  year: number
  month: number
  workers: MonthlyWorkerSummary[]
}

export interface AuthUser {
  email: string
  is_admin: boolean
  authenticated: boolean
  token?: string
}

export interface ArchiveCheck {
  is_first_day: boolean
  prev_month_archived: boolean
  prev_month: { year: number; month: number }
}

export interface ChatMessage {
  id: string
  role: "user" | "assistant"
  text: string
  timestamp: Date
}

export interface PayslipFile {
  name: string
  worker: string
  year: number
  month: number
}

export interface PayslipListResponse {
  year: number
  month: number
  pdfs: string[]
  excels: string[]
}
