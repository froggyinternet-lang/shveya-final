import { useCallback, useEffect, useState } from "react"

export type Role = "owner" | "operator" | "master" | "courier" | "customer"
export type Session = {
  id: string
  email?: string
  name?: string
  phone?: string
  receipt_email?: string
  role: Role
  is_active?: boolean
}
export type Collection<T> = { data: T[]; count: number }
export type Garment = {
  id: string
  name?: string
  category?: string
  problem?: string
  status?: string
  master_name?: string
  photo_url?: string
  photos?: { id: string; url?: string; file_path?: string; stage?: string; kind?: string; moderation_status?: string }[]
  estimate_amount?: string | number
  estimate?: string | number
}
export type Order = {
  id: string
  status: string
  customer_name?: string
  address?: string
  description?: string
  created_at?: string
  quoted_at?: string
  repair_price?: string | number
  client_price?: string | number
  customer_total?: string | number
  quoted_repair_price?: string | number
  quoted_pickup_price?: string | number
  quoted_return_price?: string | number
  pickup_delivery_price?: string | number
  return_delivery_price?: string | number
  payment_status?: string
  pickup_mode?: "entrance" | "door"
  pickup_requested_at?: string
  delivery_quote_mode?: "partner" | "yandex"
  assignment_status?: "needs_address" | "needs_classification" | "needs_master" | "assigned"
  pickup_price?: string | number
  return_price?: string | number
  master_id?: string
  master_name?: string
  garments?: Garment[]
}
export type Master = {
  id: string
  name: string
  phone?: string
  skills?: string[]
  zone?: string
  rating?: string | number
  in_work?: number
  ready_count?: number
  payout_due?: string | number
  is_active?: boolean
  is_available?: boolean
  markup_percent?: string | number
  distance_km?: number
}
export type Overview = {
  orders_total?: number
  orders_active?: number
  orders_ready?: number
  masters_active?: number
  revenue_total?: string | number
  cm_today?: string | number
  cm_week?: string | number
  claims_open?: number
  hold_total?: string | number
  queue?: Order[]
}
export type Finance = {
  revenue_total?: string | number
  repair_revenue?: string | number
  delivery_revenue?: string | number
  orders_paid?: number
  cm_per_completed_order?: string | number
  master_payouts?: string | number
  delivery_costs?: string | number
  reserve_total?: string | number
}
export type DeliveryLeg = {
  id: string
  order_id?: string
  leg_number?: number
  sequence?: number
  status?: string
  mode?: string
  quoted_price?: string | number
  actual_price?: string | number
  due?: string
  address_from?: string
  address_to?: string
  origin_address?: string
  destination_address?: string
  actual_cost?: string | number
  handoff_mode?: "entrance" | "door"
}

export type DeliveryOffer = {
  pickup: { amount: string | number; reference: string; expires_at: string | null }
  return: { amount: string | number; reference: string; expires_at: string | null; indicative: boolean }
  mode: "partner" | "yandex"
}

const root = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "")

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message)
  }
}

export async function api<T>(path: string, method = "GET", body?: unknown): Promise<T> {
  const token = localStorage.getItem("access_token")
  const headers: Record<string, string> = { Accept: "application/json" }
  if (token) headers.Authorization = `Bearer ${token}`
  if (body !== undefined && !(body instanceof FormData)) headers["Content-Type"] = "application/json"
  const response = await fetch(`${root}/api${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body),
    credentials: "same-origin",
  })
  const raw = await response.text()
  let payload: unknown
  try {
    payload = raw ? JSON.parse(raw) : null
  } catch {
    payload = null
  }
  if (!response.ok) {
    if (response.status === 401) localStorage.removeItem("access_token")
    const detail =
      payload && typeof payload === "object" && "detail" in payload
        ? String((payload as { detail: unknown }).detail)
        : `HTTP ${response.status}`
    throw new ApiError(response.status, detail)
  }
  return payload as T
}

export function useResource<T>(path: string | null, stamp = 0) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(Boolean(path))
  const [revision, setRevision] = useState(0)
  const reload = useCallback(() => setRevision((n) => n + 1), [])
  useEffect(() => {
    if (!path) {
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    api<T>(path)
      .then((value) => {
        if (!cancelled) setData(value)
      })
      .catch((reason: unknown) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : "Ошибка запроса")
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [path, stamp, revision])
  return { data, error, loading, reload }
}
