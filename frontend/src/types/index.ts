export interface DailyCostItem {
  date: string
  department: string
  account_name: string
  tag_value: string | null
  business_module: string | null
  amount_usd: number
}

export interface DailyCostsResponse {
  data: DailyCostItem[]
  total: number
  page: number
  page_size: number
}

export interface MonthlyCostItem {
  year_month: string
  department: string
  amount_usd: number
}

export interface MonthlyCostsResponse {
  data: MonthlyCostItem[]
  total: number
}

export interface SummaryItem {
  department?: string
  account_name?: string
  tag_value?: string | null
  total_amount: number
}

export interface SummaryResponse {
  by_department: SummaryItem[]
  by_account: SummaryItem[]
  by_tag: SummaryItem[]
}

export interface AllocationRule {
  id: number
  account_name: string
  tag_value: string | null
  rule_type: string
  business_module: string | null
  department: string | null
  ratios: Record<string, number> | null
  special_config: Record<string, unknown> | null
  is_active: boolean
  created_at: string | null
  updated_at: string | null
}

export interface AlertThreshold {
  id: number
  department: string
  monthly_threshold_usd: number
  is_active: boolean
  updated_at: string | null
}

export interface SyncLog {
  id: number
  started_at: string
  finished_at: string | null
  status: string
  accounts_synced: string | null
  records_count: number | null
  error_message: string | null
}
