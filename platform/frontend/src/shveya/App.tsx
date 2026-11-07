import { useCallback, useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react"
import {
  api,
  type Collection,
  type DeliveryLeg,
  type DeliveryOffer,
  type Finance,
  type Garment,
  type Master,
  type Order,
  type Overview,
  type Role,
  type Session,
  useResource,
} from "./api"
import { statusText, translate, type LabelKey, type Locale } from "./i18n"
import "./styles.css"

type AdminTab =
  | "overview" | "orders" | "garments" | "finance" | "masters" | "logistics"
  | "customers" | "disputes" | "settings" | "pulse" | "tasks" | "system" | "api-keys"

type TabDef = { id: AdminTab; label: LabelKey; icon: string }
const GROUPS: { label: LabelKey; tabs: TabDef[] }[] = [
  { label: "business", tabs: [
    { id: "overview", label: "overview", icon: "◉" },
    { id: "orders", label: "orders", icon: "▣" },
    { id: "garments", label: "garments", icon: "◇" },
    { id: "finance", label: "finance", icon: "₽" },
  ] },
  { label: "operations", tabs: [
    { id: "masters", label: "masters", icon: "✦" },
    { id: "logistics", label: "logistics", icon: "↗" },
    { id: "customers", label: "customers", icon: "♧" },
    { id: "disputes", label: "disputes", icon: "✓" },
  ] },
  { label: "service", tabs: [
    { id: "settings", label: "settings", icon: "⚙" },
    { id: "pulse", label: "pulse", icon: "≋" },
    { id: "tasks", label: "tasks", icon: "☷" },
    { id: "system", label: "system", icon: "▤" },
    { id: "api-keys", label: "apiKeys", icon: "⌘" },
  ] },
]
const repairCategories = ["подшив", "молния", "шов", "ушив", "пальто"]

// Future modules can be enabled after their API endpoint is installed.
export const extensionRegistry: { id: string; title: [string, string]; endpoint: string; enabled: boolean }[] = [
  { id: "marketing", title: ["Маркетинг", "Marketing"], endpoint: "/admin/marketing", enabled: false },
  { id: "accounting", title: ["Бухгалтерия", "Contabilidad"], endpoint: "/admin/accounting", enabled: false },
]

const money = (value: string | number | null | undefined) => {
  if (value === null || value === undefined || value === "") return "—"
  const n = Number(value)
  return Number.isFinite(n) ? new Intl.NumberFormat("ru-RU", { style: "currency", currency: "RUB", maximumFractionDigits: 2 }).format(n) : String(value)
}
const dateTime = (value?: string) => value ? new Date(value).toLocaleString("ru-RU") : "—"
const shortId = (value: string) => value.slice(0, 8).toUpperCase()
const arr = <T,>(value: Collection<T> | T[] | null): T[] =>
  Array.isArray(value) ? value : value && "data" in value && Array.isArray(value.data) ? value.data : []

function IconButton({ children, onClick, title }: { children: ReactNode; onClick: () => void; title: string }) {
  return <button className="icon-button" onClick={onClick} type="button" aria-label={title} title={title}>{children}</button>
}

function ProtectedPhoto({ url, alt, className }: { url?: string; alt: string; className: string }) {
  const [src, setSrc] = useState<string | null>(null)
  useEffect(() => {
    if (!url) { setSrc(null); return }
    if (!url.startsWith("/api/")) { setSrc(url); return }
    let cancelled = false
    let objectUrl: string | null = null
    const token = localStorage.getItem("access_token")
    fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((response) => { if (!response.ok) throw new Error(String(response.status)); return response.blob() })
      .then((blob) => { objectUrl = URL.createObjectURL(blob); if (!cancelled) setSrc(objectUrl) })
      .catch(() => { if (!cancelled) setSrc(null) })
    return () => { cancelled = true; if (objectUrl) URL.revokeObjectURL(objectUrl) }
  }, [url])
  return src ? <img className={className} src={src} alt={alt} /> : <div className={`${className} placeholder`} aria-label={alt}>◇</div>
}

function StatePanel({ loading, error, empty, retry, children, locale }: {
  loading: boolean; error: string | null; empty?: string; retry: () => void; children: ReactNode; locale: Locale
}) {
  if (loading) return <div className="skeleton-stack" role="status" aria-live="polite"><div className="skeleton" /><div className="skeleton" /><div className="skeleton short" /></div>
  if (error) return <div className="error-banner" role="alert"><strong>{translate(locale, "tryAgain")}</strong><span>{error}</span><button type="button" onClick={retry}>{translate(locale, "retry")}</button></div>
  if (empty) return <div className="empty-state"><div className="empty-icon">◇</div><p>{empty}</p></div>
  return <>{children}</>
}

function Toast({ text, onClose }: { text: string | null; onClose: () => void }) {
  if (!text) return null
  return <div className="toast" role="status">{text}<button type="button" onClick={onClose} aria-label="Закрыть">×</button></div>
}

function useMutation(locale: Locale, onDone?: () => void) {
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const run = useCallback(async <T,>(path: string, body?: unknown, method = "POST"): Promise<T | null> => {
    setBusy(true)
    setNotice(null)
    try {
      const result = await api<T>(path, method, body)
      setNotice(translate(locale, "actionDone"))
      onDone?.()
      return result
    } catch (err) {
      setNotice(`${translate(locale, "requestError")}: ${err instanceof Error ? err.message : ""}`)
      return null
    } finally {
      setBusy(false)
    }
  }, [locale, onDone])
  return { busy, notice, clearNotice: () => setNotice(null), run }
}

function StatCard({ label, value, tone = "mint" }: { label: string; value: ReactNode; tone?: "mint" | "violet" | "peach" | "blue" }) {
  return <div className={`stat-frame ${tone}`}><div className="stat-card"><span>{label}</span><strong>{value}</strong></div></div>
}

function OrderCard({ order, locale, onClick }: { order: Order; locale: Locale; onClick?: () => void }) {
  const photo = order.garments?.[0]?.photo_url ?? order.garments?.[0]?.photos?.[0]?.url
  const body = <>
    <ProtectedPhoto className="order-thumb" url={photo} alt={order.garments?.[0]?.name ?? translate(locale, "garments")} />
    <div className="order-main"><div className="order-line"><strong>№ {shortId(order.id)}</strong><span className={`status status-${order.status?.toLowerCase()}`}>{statusText(locale, order.status)}</span></div>
      <p>{order.garments?.map((g) => g.name).filter(Boolean).join(", ") || order.description || order.customer_name || translate(locale, "noData")}</p>
      <small>{order.customer_name ? `${order.customer_name} · ` : ""}{dateTime(order.created_at)}</small>
    </div>
    <strong className="order-money">{money(order.customer_total ?? order.client_price)}</strong>
  </>
  return onClick ? <button className="order-card" type="button" onClick={onClick}>{body}</button> : <div className="order-card">{body}</div>
}

function OverviewTab({ locale }: { locale: Locale }) {
  const { data, loading, error, reload } = useResource<Overview>("/admin/overview")
  return <StatePanel locale={locale} loading={loading} error={error} retry={reload}>
    <div className="stat-grid">
      <StatCard label={translate(locale, "totalOrders")} value={data?.orders_total ?? "—"} />
      <StatCard label={translate(locale, "activeOrders")} value={data?.orders_active ?? "—"} tone="violet" />
      <StatCard label={translate(locale, "ready")} value={data?.orders_ready ?? "—"} tone="blue" />
      <StatCard label={translate(locale, "activeMasters")} value={data?.masters_active ?? "—"} tone="peach" />
      <StatCard label={translate(locale, "revenue")} value={money(data?.revenue_total)} />
    </div>
    <section className="panel"><div className="panel-heading"><div><span className="eyebrow">ОПЕРАЦИИ</span><h2>{translate(locale, "queue")}</h2></div><span className="live-dot">●</span></div>
      {data?.queue?.length ? <div className="card-list">{data.queue.map((order) => <OrderCard key={order.id} order={order} locale={locale} />)}</div> : <div className="empty-state"><p>{translate(locale, "firstOrder")}</p></div>}
    </section>
  </StatePanel>
}

function OrdersTab({ locale }: { locale: Locale }) {
  const list = useResource<Collection<Order>>("/admin/orders")
  const [selected, setSelected] = useState<string | null>(null)
  const [filter, setFilter] = useState("ALL")
  const [masterId, setMasterId] = useState("")
  const [orderLatitude, setOrderLatitude] = useState("")
  const [orderLongitude, setOrderLongitude] = useState("")
  const [customerPhone, setCustomerPhone] = useState("")
  const [customerEmail, setCustomerEmail] = useState("")
  const [categories, setCategories] = useState<Record<string, string>>({})
  const [markup, setMarkup] = useState("30")
  const [mode, setMode] = useState<"partner" | "yandex">("partner")
  const [offer, setOffer] = useState<{ value: DeliveryOffer; createdAt: string; orderId: string } | null>(null)
  const [offerBusy, setOfferBusy] = useState(false)
  const [offerError, setOfferError] = useState<string | null>(null)
  const detail = useResource<Order>(selected ? `/admin/orders/${encodeURIComponent(selected)}` : null)
  const suggestions = useResource<{ status: string; data: Master[] }>(selected ? `/admin/orders/${encodeURIComponent(selected)}/suggest-masters` : null)
  const reloadAll = useCallback(() => { list.reload(); detail.reload(); suggestions.reload() }, [list.reload, detail.reload, suggestions.reload])
  const mutation = useMutation(locale, reloadAll)
  const fetchOffer = async () => {
    if (!selected) return
    setOfferBusy(true); setOffer(null); setOfferError(null)
    try {
      const value = await api<DeliveryOffer>("/delivery/offers", "POST", { order_id: selected, mode, pickup_requested_at: detail.data?.pickup_requested_at, door_to_door: detail.data?.pickup_mode === "door" })
      setOffer({ value, createdAt: new Date().toISOString(), orderId: selected })
    } catch (err) { setOfferError(err instanceof Error ? err.message : translate(locale, "requestError")) }
    finally { setOfferBusy(false) }
  }
  const freshOffer = offer?.orderId === selected && offer.value.mode === mode && (mode === "partner" || (offer.value.pickup.expires_at && offer.value.return.expires_at && Date.parse(offer.value.pickup.expires_at) > Date.now() && Date.parse(offer.value.return.expires_at) > Date.now())) ? offer : null
  const orders = arr(list.data)
  const shown = filter === "ALL" ? orders : orders.filter((o) => o.status === filter)
  const filters = ["ALL", "NEW", "IN_WORK", "QC", "READY"]
  return <>
    <div className="filter-row">{filters.map((item) => <button type="button" className={filter === item ? "chip active" : "chip"} key={item} onClick={() => setFilter(item)}>{item === "ALL" ? translate(locale, "orders") : statusText(locale, item)} <b>{item === "ALL" ? list.data?.count ?? orders.length : orders.filter((o) => o.status === item).length}</b></button>)}</div>
    <div className={selected ? "order-layout open" : "order-layout"}>
      <section className="panel"><StatePanel locale={locale} loading={list.loading} error={list.error} retry={list.reload} empty={!shown.length ? translate(locale, "firstOrder") : undefined}><div className="card-list">{shown.map((order) => <OrderCard key={order.id} order={order} locale={locale} onClick={() => { setSelected(order.id); setOffer(null) }} />)}</div></StatePanel></section>
      {selected && <aside className="panel order-detail"><div className="panel-heading"><h2>№ {shortId(selected)}</h2><IconButton title={translate(locale, "close")} onClick={() => setSelected(null)}>×</IconButton></div>
        <StatePanel locale={locale} loading={detail.loading} error={detail.error} retry={detail.reload}>
          {detail.data && <>
            <p className="status-line">{statusText(locale, detail.data.status)}</p>
            <p><b>{translate(locale, "address")}:</b> {detail.data.address || translate(locale, "noData")}</p>
            {detail.data.assignment_status === "needs_address" && <div className="action-box"><small>{translate(locale, "needsAddress")}</small><div className="two-cols"><label>{translate(locale, "latitude")}<input type="number" step="any" min="-90" max="90" value={orderLatitude} onChange={(e) => setOrderLatitude(e.target.value)} /></label><label>{translate(locale, "longitude")}<input type="number" step="any" min="-180" max="180" value={orderLongitude} onChange={(e) => setOrderLongitude(e.target.value)} /></label></div><button className="button secondary" type="button" disabled={mutation.busy || !orderLatitude || !orderLongitude} onClick={() => void mutation.run(`/admin/orders/${selected}/location`, { latitude: Number(orderLatitude), longitude: Number(orderLongitude) }, "PATCH")}>{translate(locale, "save")}</button></div>}
            <div className="action-box"><div className="two-cols"><label>{translate(locale, "phone")}<input type="tel" pattern="\+7[0-9]{10}" placeholder="+7XXXXXXXXXX" value={customerPhone} onChange={(e) => setCustomerPhone(e.target.value)} /></label><label>{translate(locale, "receiptEmail")}<input type="email" value={customerEmail} onChange={(e) => setCustomerEmail(e.target.value)} /></label></div><button className="button secondary" type="button" disabled={mutation.busy || !/^\+7\d{10}$/.test(customerPhone)} onClick={() => void mutation.run(`/admin/orders/${selected}/contact`, { phone: customerPhone, receipt_email: customerEmail || undefined }, "PATCH")}>{translate(locale, "save")}</button></div>
            <div className="finance-lines"><div><span>{translate(locale, "price")}</span><b>{money(detail.data.quoted_repair_price)}</b></div><div><span>{translate(locale, "pickupPrice")}</span><b>{money(detail.data.quoted_pickup_price)}</b></div><div><span>{translate(locale, "returnPrice")}</span><b>{money(detail.data.quoted_return_price)}</b></div><div><span>{translate(locale, "total")}</span><b>{money(detail.data.customer_total)}</b></div></div>
            <p><b>{translate(locale, "paymentStatus")}:</b> {statusText(locale, detail.data.payment_status)}</p>
            <div className="detail-garments">{detail.data.garments?.map((g) => <div className="garment-row" key={g.id}><ProtectedPhoto className="order-thumb" url={g.photos?.[0]?.url} alt={g.name || translate(locale, "garments")} /><div><strong>{g.name || translate(locale, "garments")}</strong><p>{g.problem || translate(locale, "noData")}</p><small>{statusText(locale, g.status)}</small>{g.photos?.map((photo) => <div className="photo-review" key={photo.id}><ProtectedPhoto className="review-thumb" url={photo.url} alt={`${g.name || ""} ${photo.kind || ""}`} /><span>{photo.kind} · {statusText(locale, photo.moderation_status)}</span>{photo.moderation_status === "PENDING" && <button type="button" className="button secondary" disabled={mutation.busy} onClick={() => void mutation.run(`/admin/photos/${photo.id}/approve`)}>{translate(locale, "approvePhoto")}</button>}</div>)}{!g.category && <div className="action-box"><label>{translate(locale, "category")}<select value={categories[g.id] ?? ""} onChange={(e) => setCategories((old) => ({ ...old, [g.id]: e.target.value }))}><option value="">—</option>{repairCategories.map((item) => <option key={item} value={item}>{item}</option>)}</select></label><button className="button secondary" type="button" disabled={mutation.busy || !categories[g.id]} onClick={() => void mutation.run(`/admin/garments/${g.id}/category`, { category: categories[g.id] }, "PATCH")}>{translate(locale, "save")}</button></div>}</div></div>)}</div>
            <div className="action-box"><label>{translate(locale, "chooseMaster")}<select value={masterId} onChange={(e) => setMasterId(e.target.value)}><option value="">—</option>{suggestions.data?.data.map((m) => <option key={m.id} value={m.id}>{m.name} · {m.distance_km} {translate(locale, "distance")}</option>)}</select></label>{suggestions.data?.status === "needs_address" && <small>{translate(locale, "needsAddress")}</small>}{suggestions.data?.status === "needs_classification" && <small>{translate(locale, "needsClassification")}</small>}{suggestions.data?.status === "no_eligible_master" && <small>{translate(locale, "noEligibleMaster")}</small>}<button className="button secondary" type="button" disabled={!masterId || mutation.busy} onClick={() => void mutation.run(`/admin/orders/${selected}/assign`, { master_id: masterId })}>{translate(locale, "assign")}</button></div>
            <div className="action-box"><label>{translate(locale, "deliveryMode")}<select value={mode} onChange={(e) => { setMode(e.target.value as "partner" | "yandex"); setOffer(null) }}><option value="partner">{translate(locale, "partner")}</option><option value="yandex">{translate(locale, "yandex")}</option></select></label><button className="button secondary" type="button" disabled={offerBusy} onClick={() => void fetchOffer()}>{offerBusy ? translate(locale, "waiting") : translate(locale, "offer")}</button>
              {offerError && <p className="error-banner" role="alert">{offerError}</p>}
              {freshOffer ? <div className="finance-lines"><div><span>{translate(locale, "pickupPrice")}</span><b>{money(freshOffer.value.pickup.amount)}</b></div><div><span>{translate(locale, "returnPrice")}</span><b>{money(freshOffer.value.return.amount)}</b></div></div> : <small>{translate(locale, "offerExpired")}</small>}
            </div>
            <div className="action-box"><label>{translate(locale, "markup")}<input type="number" min="30" max="200" value={markup} onChange={(e) => setMarkup(e.target.value)} /></label><button className="button secondary" type="button" disabled={!freshOffer || Number(markup) < 30 || mutation.busy} onClick={() => freshOffer && void mutation.run(`/admin/orders/${selected}/quote`, { markup_percent: Number(markup), pickup_delivery_price: freshOffer.value.pickup.amount, return_delivery_price: freshOffer.value.return.amount, delivery_quote_mode: mode, delivery_quote_reference: freshOffer.value.pickup.reference, delivery_quote_created_at: freshOffer.createdAt })}>{translate(locale, "confirmPrice")}</button></div>
            <p className="notice-line">{translate(locale, "quoteLocked")}</p>
            <div className="action-box"><button className="button" type="button" disabled={mutation.busy || detail.data.payment_status !== "PAID"} onClick={() => void mutation.run(`/admin/orders/${selected}/dispatch-pickup`, { mode: detail.data?.delivery_quote_mode })}>{translate(locale, "callCourier")}</button></div>
          </>}
        </StatePanel>
        <Toast text={mutation.notice} onClose={mutation.clearNotice} />
      </aside>}
    </div>
  </>
}

function GarmentsTab({ locale }: { locale: Locale }) {
  const resource = useResource<Collection<Garment>>("/admin/garments")
  const garments = arr(resource.data)
  return <section className="panel"><StatePanel locale={locale} loading={resource.loading} error={resource.error} retry={resource.reload} empty={!garments.length ? translate(locale, "firstGarment") : undefined}>
    <div className="tile-grid">{garments.map((g) => <div className="garment-tile" key={g.id}><ProtectedPhoto className="photo-placeholder" url={g.photos?.[0]?.url ?? g.photo_url} alt={g.name || translate(locale, "garments")} /><div><strong>{g.name || translate(locale, "garments")}</strong><p>{g.problem || translate(locale, "noData")}</p><span className="status">{statusText(locale, g.status)}</span><small>{g.master_name ? `${translate(locale, "assigned")}: ${g.master_name}` : ""}</small></div></div>)}</div>
  </StatePanel></section>
}

function FinanceTab({ locale }: { locale: Locale }) {
  const resource = useResource<Finance>("/admin/finance")
  const f = resource.data
  return <StatePanel locale={locale} loading={resource.loading} error={resource.error} retry={resource.reload}>
    <div className="stat-grid">
      <StatCard label="CM / заказ" value={money(f?.cm_per_completed_order)} />
      <StatCard label={translate(locale, "revenue")} value={money(f?.revenue_total)} tone="violet" />
      <StatCard label={translate(locale, "repairRevenue")} value={money(f?.repair_revenue)} tone="peach" />
      <StatCard label={translate(locale, "paidOrders")} value={f?.orders_paid ?? "—"} tone="blue" />
    </div>
    <section className="panel"><h2>{translate(locale, "breakdown")}</h2><div className="finance-lines">
      <div><span>{translate(locale, "masterPayouts")}</span><b>{money(f?.master_payouts)}</b></div>
      <div><span>{translate(locale, "deliveryCosts")}</span><b>{money(f?.delivery_costs)}</b></div>
      <div><span>{translate(locale, "reserve")}</span><b>{money(f?.reserve_total)}</b></div>
      <div><span>{translate(locale, "deliveryRevenue")}</span><b>{money(f?.delivery_revenue)}</b></div>
    </div></section>
  </StatePanel>
}

function MastersTab({ locale }: { locale: Locale }) {
  const list = useResource<Collection<Master>>("/admin/masters")
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState("")
  const [phone, setPhone] = useState("")
  const [contactEmail, setContactEmail] = useState("")
  const [skills, setSkills] = useState<string[]>([])
  const [zone, setZone] = useState("")
  const [masterAddress, setMasterAddress] = useState("")
  const [latitude, setLatitude] = useState("")
  const [longitude, setLongitude] = useState("")
  const [capacity, setCapacity] = useState("5")
  const [markup, setMarkup] = useState("30")
  const [invite, setInvite] = useState<{ username: string; temporary_password: string } | null>(null)
  const mutation = useMutation(locale, list.reload)
  const skillOptions = repairCategories
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const result = await mutation.run<Master & { username?: string; temporary_password?: string }>("/admin/masters", { name, phone, contact_email: contactEmail, skills, zone, address: masterAddress, latitude: Number(latitude), longitude: Number(longitude), capacity: Number(capacity), markup_percent: Number(markup) })
    if (result) {
      setShowForm(false); setName(""); setPhone(""); setContactEmail(""); setSkills([]); setMasterAddress(""); setLatitude(""); setLongitude("")
      if (result.username && result.temporary_password) setInvite({ username: result.username, temporary_password: result.temporary_password })
    }
  }
  return <>
    <div className="toolbar"><button className="button" type="button" onClick={() => setShowForm(true)}>{translate(locale, "addMaster")}</button></div>
    <section className="panel"><StatePanel locale={locale} loading={list.loading} error={list.error} retry={list.reload} empty={!arr(list.data).length ? translate(locale, "firstMaster") : undefined}>
      <div className="tile-grid">{arr(list.data).map((m) => <div className="master-card" key={m.id}><div className="avatar">{m.name?.slice(0, 1).toUpperCase()}</div><div className="master-info"><strong>{m.name}</strong><small>{m.zone || "—"}</small><p>{m.skills?.join(" · ") || translate(locale, "noData")}</p><div className="master-stats"><span>★ {m.rating ?? "—"}</span><span>{translate(locale, "inWork")}: {m.in_work ?? "—"}</span><span>{translate(locale, "payout")}: {money(m.payout_due)}</span></div></div></div>)}</div>
    </StatePanel></section>
    {showForm && <div className="modal-backdrop" role="presentation" onClick={() => setShowForm(false)}><form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={(e) => void submit(e)}><div className="panel-heading"><h2>{translate(locale, "addMaster")}</h2><IconButton title={translate(locale, "close")} onClick={() => setShowForm(false)}>×</IconButton></div>
      <label>{translate(locale, "name")}<input value={name} onChange={(e) => setName(e.target.value)} required autoFocus /></label>
      <label>{translate(locale, "phone")}<input value={phone} onChange={(e) => setPhone(e.target.value)} required type="tel" /></label>
      <label>{translate(locale, "receiptEmail")}<input value={contactEmail} onChange={(e) => setContactEmail(e.target.value)} required type="email" /></label>
      <fieldset><legend>{translate(locale, "skills")}</legend><div className="checks">{skillOptions.map((skill) => <label key={skill}><input type="checkbox" checked={skills.includes(skill)} onChange={() => setSkills((old) => old.includes(skill) ? old.filter((s) => s !== skill) : [...old, skill])} />{skill}</label>)}</div></fieldset>
      <label>{translate(locale, "zone")}<input value={zone} onChange={(e) => setZone(e.target.value)} required /></label>
      <label>{translate(locale, "masterAddress")}<input value={masterAddress} onChange={(e) => setMasterAddress(e.target.value)} required /></label>
      <div className="two-cols"><label>{translate(locale, "latitude")}<input value={latitude} onChange={(e) => setLatitude(e.target.value)} type="number" step="any" min="-90" max="90" required /></label><label>{translate(locale, "longitude")}<input value={longitude} onChange={(e) => setLongitude(e.target.value)} type="number" step="any" min="-180" max="180" required /></label></div>
      <label>{translate(locale, "capacity")}<input value={capacity} onChange={(e) => setCapacity(e.target.value)} type="number" min="1" max="100" required /></label>
      <label>{translate(locale, "markup")}<input value={markup} onChange={(e) => setMarkup(e.target.value)} type="number" min="30" max="200" required /></label>
      <div className="modal-actions"><button className="button secondary" type="button" onClick={() => setShowForm(false)}>{translate(locale, "cancel")}</button><button className="button" type="submit" disabled={mutation.busy || !skills.length || Number(markup) < 30}>{translate(locale, "save")}</button></div>
    </form></div>}
    {invite && <div className="modal-backdrop"><div className="modal" role="dialog" aria-modal="true"><h2>{translate(locale, "addMaster")}</h2><p>{translate(locale, "oneTimeLogin")}</p><p><b>{translate(locale, "username")}:</b> {invite.username}</p><p><b>{translate(locale, "tempPassword")}:</b> {invite.temporary_password}</p><button className="button" type="button" onClick={() => setInvite(null)}>{translate(locale, "close")}</button></div></div>}
    <Toast text={mutation.notice} onClose={mutation.clearNotice} />
  </>
}

function LogisticsTab({ locale }: { locale: Locale }) {
  const resource = useResource<Collection<DeliveryLeg>>("/admin/logistics")
  const legs = arr(resource.data)
  return <section className="panel"><StatePanel locale={locale} loading={resource.loading} error={resource.error} retry={resource.reload} empty={!legs.length ? translate(locale, "noData") : undefined}>
    <div className="card-list">{legs.map((leg) => <div className="leg-card" key={leg.id}><div className="leg-number">{(leg.sequence ?? leg.leg_number) === 1 ? "→" : "←"}</div><div><strong>№ {leg.order_id ? shortId(leg.order_id) : shortId(leg.id)}</strong><p>{leg.origin_address ?? leg.address_from ?? "—"} → {leg.destination_address ?? leg.address_to ?? "—"}</p><small>{leg.due ? dateTime(leg.due) : translate(locale, "noTime")} · {leg.mode === "partner" ? translate(locale, "partner") : leg.mode === "yandex" ? translate(locale, "yandex") : "—"}</small></div><div><span className="status">{statusText(locale, leg.status)}</span><b>{money(leg.quoted_price ?? leg.actual_cost ?? leg.actual_price)}</b></div></div>)}</div>
  </StatePanel></section>
}

type Tariff = { id: string; zone: string; pickup_price: string; return_price: string; active: boolean }
function SettingsTab({ locale, role }: { locale: Locale; role: Role }) {
  const tariffs = useResource<Collection<Tariff>>("/admin/tariffs")
  const [zone, setZone] = useState("")
  const [pickup, setPickup] = useState("")
  const [back, setBack] = useState("")
  const mutation = useMutation(locale, tariffs.reload)
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const result = await mutation.run<Tariff>("/admin/tariffs", { zone, pickup_price: pickup, return_price: back, active: true, allow_free: false })
    if (result) { setZone(""); setPickup(""); setBack("") }
  }
  return <section className="panel"><div className="panel-heading"><h2>{translate(locale, "tariffs")}</h2></div>
    <StatePanel locale={locale} loading={tariffs.loading} error={tariffs.error} retry={tariffs.reload} empty={!arr(tariffs.data).length ? translate(locale, "noData") : undefined}>
      <div className="finance-lines">{arr(tariffs.data).map((t) => <div key={t.id}><span>{t.zone} · {t.active ? statusText(locale, "ACTIVE") : statusText(locale, "INACTIVE")}</span><b>{translate(locale, "pickupPrice")}: {money(t.pickup_price)} · {translate(locale, "returnPrice")}: {money(t.return_price)}</b></div>)}</div>
    </StatePanel>
    {role === "owner" ? <form className="action-box" onSubmit={(e) => void submit(e)}><label>{translate(locale, "tariffZone")}<input value={zone} onChange={(e) => setZone(e.target.value)} required /></label><div className="two-cols"><label>{translate(locale, "pickupPrice")}<input type="number" min="0.01" step="0.01" value={pickup} onChange={(e) => setPickup(e.target.value)} required /></label><label>{translate(locale, "returnPrice")}<input type="number" min="0.01" step="0.01" value={back} onChange={(e) => setBack(e.target.value)} required /></label></div><button className="button" type="submit" disabled={mutation.busy}>{translate(locale, "save")}</button></form> : <p className="notice-line">{translate(locale, "ownerOnly")}</p>}
    <Toast text={mutation.notice} onClose={mutation.clearNotice} />
  </section>
}

const genericFields: Record<string, string> = {
  name: "Имя", title: "Название", status: "Статус", description: "Описание",
  phone_masked: "Телефон", address_masked: "Адрес", type: "Тип", created_at: "Создано",
  count: "Количество", value: "Значение", enabled: "Включено", state: "Состояние",
}
function GenericTab({ tab, locale }: { tab: AdminTab; locale: Locale }) {
  const endpoint = tab === "api-keys" ? "api-keys" : tab
  const resource = useResource<Collection<Record<string, unknown>> | Record<string, unknown>>(`/admin/${endpoint}`)
  const rows = resource.data && "data" in resource.data ? arr(resource.data as Collection<Record<string, unknown>>) : []
  const scalars = resource.data && !("data" in resource.data) ? Object.entries(resource.data).filter(([key, value]) => key in genericFields && ["string", "number", "boolean"].includes(typeof value)) : []
  const title = translate(locale, GROUPS.flatMap((g) => g.tabs).find((t) => t.id === tab)?.label ?? "overview")
  return <section className="panel"><div className="panel-heading"><h2>{title}</h2></div><StatePanel locale={locale} loading={resource.loading} error={resource.error} retry={resource.reload} empty={!rows.length && !scalars.length ? translate(locale, "noData") : undefined}>
    {rows.length ? <div className="card-list">{rows.map((row, index) => <div className="generic-card" key={String(row.id ?? index)}>{Object.entries(row).filter(([key, value]) => key in genericFields && value !== null && value !== undefined).slice(0, 5).map(([key, value]) => <p key={key}><span>{genericFields[key]}</span><strong>{key === "status" ? statusText(locale, String(value)) : key === "created_at" ? dateTime(String(value)) : String(value)}</strong></p>)}</div>)}</div> : <div className="finance-lines">{scalars.map(([key, value]) => <div key={key}><span>{genericFields[key]}</span><b>{String(value)}</b></div>)}</div>}
  </StatePanel></section>
}

function Admin({ locale, role }: { locale: Locale; role: Role }) {
  const allTabs = GROUPS.flatMap((g) => g.tabs).map((t) => t.id)
  const getTab = () => {
    const candidate = location.hash.replace(/^#\/?/, "") as AdminTab
    return allTabs.includes(candidate) ? candidate : "overview"
  }
  const [tab, setTab] = useState<AdminTab>(getTab)
  useEffect(() => {
    const handler = () => setTab(getTab())
    window.addEventListener("hashchange", handler)
    return () => window.removeEventListener("hashchange", handler)
  }, [])
  return <div className="admin-layout">
    <aside className="sidebar"><div className="brand-mark"><span className="brand-symbol">✳</span><div><b>{translate(locale, "brand")}</b><small>{translate(locale, "subtitle")}</small></div></div>
      <nav aria-label="Разделы панели">{GROUPS.map((group) => <div className="nav-group" key={group.label}><span className="nav-heading">{translate(locale, group.label)}</span>{group.tabs.map((item) => <a key={item.id} className={tab === item.id ? "nav-link active" : "nav-link"} href={`#/${item.id}`} aria-current={tab === item.id ? "page" : undefined}><span>{item.icon}</span>{translate(locale, item.label)}</a>)}</div>)}</nav>
      <div className="sidebar-footer">{translate(locale, "extensionHint")}<div className="future-modules">{extensionRegistry.map((item) => <span key={item.id}>{item.title[locale === "ru" ? 0 : 1]}</span>)}</div></div>
    </aside>
    <main className="main-content"><div className="page-intro"><div><span className="eyebrow">ШВЕЯМОЗГ / ПЕРМЬ</span><h1>{translate(locale, GROUPS.flatMap((g) => g.tabs).find((x) => x.id === tab)?.label ?? "overview")}</h1></div><span className="place-pill">Пермь</span></div>
      {tab === "overview" ? <OverviewTab locale={locale} /> : tab === "orders" ? <OrdersTab locale={locale} /> : tab === "garments" ? <GarmentsTab locale={locale} /> : tab === "finance" ? <FinanceTab locale={locale} /> : tab === "masters" ? <MastersTab locale={locale} /> : tab === "logistics" ? <LogisticsTab locale={locale} /> : tab === "settings" ? <SettingsTab locale={locale} role={role} /> : <GenericTab tab={tab} locale={locale} />}
    </main>
  </div>
}

function MasterPortal({ locale }: { locale: Locale }) {
  const jobs = useResource<Collection<Garment>>("/master/jobs")
  const [prices, setPrices] = useState<Record<string, string>>({})
  const [reasons, setReasons] = useState<Record<string, string>>({})
  const [uploaded, setUploaded] = useState<Record<string, boolean>>({})
  const mutation = useMutation(locale, jobs.reload)
  const upload = async (id: string, file: File) => {
    const form = new FormData(); form.append("file", file); form.append("stage", "AFTER_MASTER")
    const result = await mutation.run(`/garments/${id}/photos`, form)
    if (result) setUploaded((old) => ({ ...old, [id]: true }))
  }
  return <main className="mobile-main"><div className="page-intro"><div><span className="eyebrow">ШВЕЯМОЗГ</span><h1>{translate(locale, "myJobs")}</h1></div></div>
    <StatePanel locale={locale} loading={jobs.loading} error={jobs.error} retry={jobs.reload} empty={!arr(jobs.data).length ? translate(locale, "firstGarment") : undefined}>
      <div className="mobile-list">{arr(jobs.data).map((g) => <article className="mobile-card" key={g.id}><ProtectedPhoto className="mobile-photo" url={g.photos?.find((p) => p.moderation_status === "APPROVED")?.url ?? g.photo_url} alt={g.name || translate(locale, "garments")} /><h2>{g.name || translate(locale, "garments")}</h2><p>{g.problem || translate(locale, "noData")}</p><span className="status">{statusText(locale, g.status)}</span>
        <div className="price-form"><label>{translate(locale, "estimate")}<input type="number" min="1" step="0.01" value={prices[g.id] ?? ""} onChange={(e) => setPrices((old) => ({ ...old, [g.id]: e.target.value }))} /></label><button className="button secondary" type="button" disabled={mutation.busy || !Number(prices[g.id])} onClick={() => void mutation.run(`/master/jobs/${g.id}/estimate`, { amount: prices[g.id] })}>{translate(locale, "sendEstimate")}</button></div>
        <div className="mobile-actions"><button className="button" type="button" disabled={mutation.busy} onClick={() => void mutation.run(`/master/jobs/${g.id}/accept`)}>{translate(locale, "accept")}</button><label className="file-button">{translate(locale, "uploadPhoto")}<input type="file" accept="image/*" capture="environment" onChange={(e) => { const file = e.target.files?.[0]; if (file) void upload(g.id, file) }} /></label><button className="button" type="button" disabled={mutation.busy || !uploaded[g.id]} onClick={() => void mutation.run(`/master/jobs/${g.id}/ready`)}>{translate(locale, "finished")}</button></div>
        <div className="problem-row"><input aria-label={translate(locale, "problem")} placeholder={translate(locale, "problem")} value={reasons[g.id] ?? ""} onChange={(e) => setReasons((old) => ({ ...old, [g.id]: e.target.value }))} /><button className="button danger" type="button" disabled={mutation.busy || !reasons[g.id]?.trim()} onClick={() => void mutation.run(`/master/jobs/${g.id}/problem`, { reason: reasons[g.id] })}>{translate(locale, "reportProblem")}</button></div>
      </article>)}</div>
    </StatePanel><Toast text={mutation.notice} onClose={mutation.clearNotice} /></main>
}

function CourierPortal({ locale }: { locale: Locale }) {
  const legs = useResource<Collection<DeliveryLeg>>("/courier/legs")
  const [proof, setProof] = useState<Record<string, boolean>>({})
  const mutation = useMutation(locale, legs.reload)
  const upload = async (id: string, stage: "pickup" | "deliver", file: File) => {
    const form = new FormData(); form.append("file", file); form.append("stage", stage)
    const result = await mutation.run(`/courier/legs/${id}/photo`, form)
    if (result) setProof((old) => ({ ...old, [`${id}:${stage}`]: true }))
  }
  return <main className="mobile-main"><div className="page-intro"><div><span className="eyebrow">ШВЕЯМОЗГ</span><h1>{translate(locale, "myLegs")}</h1></div></div>
    <StatePanel locale={locale} loading={legs.loading} error={legs.error} retry={legs.reload} empty={!arr(legs.data).length ? translate(locale, "noData") : undefined}>
      <div className="mobile-list">{arr(legs.data).map((leg) => <article className="mobile-card" key={leg.id}><span className="eyebrow">№ {leg.order_id ? shortId(leg.order_id) : shortId(leg.id)}</span><h2>{(leg.sequence ?? leg.leg_number) === 1 ? translate(locale, "pickupPrice") : translate(locale, "returnPrice")}</h2><p>{leg.origin_address ?? leg.address_from ?? "—"} → {leg.destination_address ?? leg.address_to ?? "—"}</p><small>{dateTime(leg.due)}</small><span className="status">{statusText(locale, leg.status)}</span>
        {(leg.status === "PLANNED" || leg.status === "PICKED_UP") && <label className="file-button">{translate(locale, "proofPhoto")} · {leg.status === "PLANNED" ? translate(locale, "take") : translate(locale, "delivered")}<input type="file" accept="image/*" capture="environment" onChange={(e) => { const file = e.target.files?.[0]; if (file) void upload(leg.id, leg.status === "PLANNED" ? "pickup" : "deliver", file) }} /></label>}
        <div className="mobile-actions"><button className="button" type="button" disabled={mutation.busy || leg.status !== "PLANNED" || !proof[`${leg.id}:pickup`]} onClick={() => void mutation.run(`/courier/legs/${leg.id}/pickup`)}>{translate(locale, "take")}</button><button className="button" type="button" disabled={mutation.busy || leg.status !== "PICKED_UP" || !proof[`${leg.id}:deliver`]} onClick={() => void mutation.run(`/courier/legs/${leg.id}/deliver`)}>{translate(locale, "delivered")}</button></div>
      </article>)}</div>
    </StatePanel><Toast text={mutation.notice} onClose={mutation.clearNotice} /></main>
}

function CustomerPortal({ locale, session }: { locale: Locale; session: Session }) {
  const orders = useResource<Collection<Order>>("/app/orders")
  const [creating, setCreating] = useState(false)
  const [address, setAddress] = useState("")
  const [description, setDescription] = useState("")
  const [garmentName, setGarmentName] = useState("")
  const [contactPhone, setContactPhone] = useState(session.phone ?? "")
  const [receiptEmail, setReceiptEmail] = useState(session.receipt_email ?? session.email ?? "")
  const [category, setCategory] = useState("")
  const [garmentPhoto, setGarmentPhoto] = useState<File | null>(null)
  const [coordinates, setCoordinates] = useState<{ latitude: number; longitude: number } | null>(null)
  const [locationError, setLocationError] = useState("")
  const [pickupMode, setPickupMode] = useState<"entrance" | "door">("entrance")
  const [pickupTime, setPickupTime] = useState("")
  const [requested, setRequested] = useState<Record<string, string>>({})
  const [returnModes, setReturnModes] = useState<Record<string, "entrance" | "door">>({})
  const mutation = useMutation(locale, orders.reload)
  const pay = async (orderId: string) => {
    const result = await mutation.run<{ confirmation_url?: string }>(`/app/orders/${orderId}/pay`, { receipt_email: receiptEmail })
    if (result?.confirmation_url) window.location.assign(result.confirmation_url)
  }
  const detectLocation = () => {
    if (!navigator.geolocation) { setLocationError(translate(locale, "locationUnavailable")); return }
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => { setCoordinates({ latitude: coords.latitude, longitude: coords.longitude }); setLocationError("") },
      () => setLocationError(translate(locale, "locationUnavailable")),
      { enableHighAccuracy: true, timeout: 10000 },
    )
  }
  const create = async (event: FormEvent) => {
    event.preventDefault()
    const contact = await mutation.run("/app/contact", { phone: contactPhone, receipt_email: receiptEmail }, "PUT")
    if (!contact) return
    const result = await mutation.run<Order>("/app/orders", { address, description, latitude: coordinates?.latitude, longitude: coordinates?.longitude, pickup_mode: pickupMode, pickup_requested_at: pickupTime ? new Date(pickupTime).toISOString() : undefined, garments: [{ name: garmentName, category, problem: description }] })
    if (!result) return
    const garmentId = result.garments?.[0]?.id
    if (garmentPhoto && garmentId) {
      const form = new FormData(); form.append("file", garmentPhoto); form.append("stage", "BEFORE_CUSTOMER")
      await mutation.run(`/garments/${garmentId}/photos`, form)
    }
    setCreating(false); setAddress(""); setDescription(""); setGarmentName(""); setCategory(""); setGarmentPhoto(null); setPickupTime(""); setCoordinates(null)
  }
  return <main className="mobile-main client"><div className="page-intro"><div><span className="eyebrow">ШВЕЯМОЗГ</span><h1>{translate(locale, "myOrders")}</h1></div><div className="two-cols"><button className="button secondary" type="button" onClick={orders.reload}>{translate(locale, "refreshStatus")}</button><button className="button" type="button" onClick={() => setCreating(true)}>{translate(locale, "createOrder")}</button></div></div>
    <StatePanel locale={locale} loading={orders.loading} error={orders.error} retry={orders.reload} empty={!arr(orders.data).length ? translate(locale, "firstOrder") : undefined}>
      <div className="mobile-list">{arr(orders.data).map((order) => <article className="mobile-card" key={order.id}><OrderCard order={order} locale={locale} /><div className="finance-lines"><div><span>{translate(locale, "price")}</span><b>{money(order.quoted_repair_price)}</b></div><div><span>{translate(locale, "pickupPrice")}</span><b>{money(order.quoted_pickup_price)}</b></div><div><span>{translate(locale, "returnPrice")}</span><b>{money(order.quoted_return_price)}</b></div><div><span>{translate(locale, "total")}</span><b>{money(order.customer_total)}</b></div></div><small>{translate(locale, "quoteLocked")}</small><p>{translate(locale, "paymentStatus")}: {statusText(locale, order.payment_status)}</p>
        {order.status === "QUOTED" && <button className="button full" type="button" disabled={mutation.busy} onClick={() => void mutation.run(`/app/orders/${order.id}/confirm-quote`)}>{translate(locale, "confirmQuote")}</button>}
        {order.status === "CONFIRMED" && order.payment_status === "PENDING" && <button className="button full" type="button" disabled={mutation.busy} onClick={() => void pay(order.id)}>{translate(locale, "payTotal")}</button>}
        {order.status === "READY" && <div className="return-form"><label>{translate(locale, "desiredTime")}<input type="datetime-local" value={requested[order.id] ?? ""} onChange={(e) => setRequested((old) => ({ ...old, [order.id]: e.target.value }))} /></label><label>{translate(locale, "handoffMode")}<select value={returnModes[order.id] ?? "entrance"} onChange={(e) => setReturnModes((old) => ({ ...old, [order.id]: e.target.value as "entrance" | "door" }))}><option value="entrance">{translate(locale, "entrance")}</option><option value="door">{translate(locale, "door")}</option></select></label><button className="button full" type="button" disabled={mutation.busy || !requested[order.id]} onClick={() => void mutation.run(`/app/orders/${order.id}/confirm-return`, { requested_at: new Date(requested[order.id]).toISOString(), mode: order.delivery_quote_mode, handoff_mode: returnModes[order.id] ?? "entrance" })}>{translate(locale, "confirmReturn")}</button></div>}
      </article>)}</div>
    </StatePanel>
    {creating && <div className="modal-backdrop" role="presentation" onClick={() => setCreating(false)}><form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={(e) => void create(e)}><div className="panel-heading"><h2>{translate(locale, "createOrder")}</h2><IconButton title={translate(locale, "close")} onClick={() => setCreating(false)}>×</IconButton></div><label>{translate(locale, "garmentName")}<input value={garmentName} onChange={(e) => setGarmentName(e.target.value)} required /></label><label>{translate(locale, "category")}<select value={category} onChange={(e) => setCategory(e.target.value)} required><option value="">—</option>{repairCategories.map((item) => <option value={item} key={item}>{item}</option>)}</select></label><label>{translate(locale, "photo")}<input type="file" accept="image/*" capture="environment" onChange={(e) => setGarmentPhoto(e.target.files?.[0] ?? null)} required /></label><label>{translate(locale, "description")}<textarea value={description} onChange={(e) => setDescription(e.target.value)} required /></label><label>{translate(locale, "address")}<input value={address} onChange={(e) => setAddress(e.target.value)} required /></label><label>{translate(locale, "phone")}<input type="tel" pattern="\+7[0-9]{10}" value={contactPhone} onChange={(e) => setContactPhone(e.target.value)} required placeholder="+7XXXXXXXXXX" /></label><label>{translate(locale, "receiptEmail")}<input type="email" value={receiptEmail} onChange={(e) => setReceiptEmail(e.target.value)} required /></label><button className="button secondary full" type="button" onClick={detectLocation}>{coordinates ? translate(locale, "locationReady") : translate(locale, "detectLocation")}</button>{locationError && <p className="error-banner" role="alert">{locationError}</p>}<label>{translate(locale, "handoffMode")}<select value={pickupMode} onChange={(e) => setPickupMode(e.target.value as "entrance" | "door")}><option value="entrance">{translate(locale, "entrance")}</option><option value="door">{translate(locale, "door")}</option></select></label><label>{translate(locale, "pickupTime")}<input type="datetime-local" value={pickupTime} onChange={(e) => setPickupTime(e.target.value)} /></label><button className="button full" type="submit" disabled={mutation.busy}>{translate(locale, "save")}</button></form></div>}
    <Toast text={mutation.notice} onClose={mutation.clearNotice} />
  </main>
}

function Login({ locale, onLogin }: { locale: Locale; onLogin: (value: Session) => void }) {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const submit = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError(null)
    try {
      const result = await api<{ access_token: string }>("/auth/login", "POST", { username, password })
      localStorage.setItem("access_token", result.access_token)
      const session = await api<Session>("/me")
      onLogin(session)
    } catch (err) {
      localStorage.removeItem("access_token")
      setError(err instanceof Error ? err.message : "Не удалось войти")
    } finally { setBusy(false) }
  }
  return <main className="login-page"><div className="login-art"><div className="brand-mark"><span className="brand-symbol">✳</span><div><b>{translate(locale, "brand")}</b><small>{translate(locale, "subtitle")}</small></div></div><h1>{translate(locale, "loginStory")}</h1><p>{translate(locale, "loginStoryBody")}</p></div><form className="login-form" onSubmit={(e) => void submit(e)}><span className="eyebrow">ШВЕЯМОЗГ</span><h2>{translate(locale, "signIn")}</h2><label>{translate(locale, "username")}<input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required /></label><label>{translate(locale, "password")}<input value={password} onChange={(e) => setPassword(e.target.value)} type="password" autoComplete="current-password" required /></label>{error && <div className="error-banner" role="alert">{error}</div>}<button className="button full" type="submit" disabled={busy}>{busy ? translate(locale, "waiting") : translate(locale, "signIn")}</button></form></main>
}

export default function App() {
  const [locale, setLocale] = useState<Locale>(() => localStorage.getItem("shveya_locale") === "es" ? "es" : "ru")
  const [dark, setDark] = useState(() => localStorage.getItem("shveya_theme") === "dark")
  const [session, setSession] = useState<Session | null>(null)
  const [authLoading, setAuthLoading] = useState(Boolean(localStorage.getItem("access_token")))
  useEffect(() => {
    if (!localStorage.getItem("access_token")) return
    api<Session>("/me").then(setSession).catch(() => setSession(null)).finally(() => setAuthLoading(false))
  }, [])
  useEffect(() => { localStorage.setItem("shveya_locale", locale) }, [locale])
  useEffect(() => { localStorage.setItem("shveya_theme", dark ? "dark" : "light") }, [dark])
  const portal = useMemo(() => location.pathname.startsWith("/master") ? "master" : location.pathname.startsWith("/courier") ? "courier" : location.pathname.startsWith("/app") ? "customer" : "admin", [])
  const allowed: Record<string, Role[]> = { admin: ["owner", "operator"], master: ["master"], courier: ["courier"], customer: ["customer"] }
  const logout = () => { localStorage.removeItem("access_token"); setSession(null) }
  return <div className={dark ? "shveya theme-dark" : "shveya"}>
    {authLoading ? <div className="auth-loading"><div className="skeleton" /></div> : !session ? <Login locale={locale} onLogin={setSession} /> : !allowed[portal].includes(session.role) ? <div className="forbidden"><h1>{translate(locale, "forbidden")}</h1><button className="button" type="button" onClick={logout}>{translate(locale, "signOut")}</button></div> : <>
      <header className="topbar"><span className="topbar-brand">✳ <b>{translate(locale, "brand")}</b></span><div className="topbar-actions"><span className="operator-name">{session.name || session.email || session.role}</span><button type="button" onClick={() => setLocale(locale === "ru" ? "es" : "ru")} aria-label="Язык / Idioma">{locale.toUpperCase()} ⇄</button><button type="button" onClick={() => setDark(!dark)} aria-label={dark ? "Светлая тема" : "Тёмная тема"}>{dark ? "☀" : "☾"}</button><button type="button" onClick={logout}>{translate(locale, "signOut")}</button></div></header>
      {portal === "admin" ? <Admin locale={locale} role={session.role} /> : portal === "master" ? <MasterPortal locale={locale} /> : portal === "courier" ? <CourierPortal locale={locale} /> : <CustomerPortal locale={locale} session={session} />}
    </>}
  </div>
}

