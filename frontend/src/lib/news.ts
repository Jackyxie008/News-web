import { isIn } from '@rapideditor/country-coder'

export type Lang = 'zh' | 'en'

export type NewsItem = {
  id: string
  title: string
  summary: string
  date: string
  ts: number
  media: string
  continent: string
  country: string
  type: string
  heat: number
  lat: number
  lng: number
}

export type NewsDetail = NewsItem & {
  location: string
  published: string
  newsType: string
  keywords: string[]
  fullText: string
  links: string[]
  linkItems?: { url: string; source: string }[]
  imageUrl?: string
  imageSource?: string
}

export type FilterState = {
  query: string
  country: string | null
  media: string | null
  continent: string | null
  type: string | null
  heat: 'hot' | 'time' | null
  timeRange: { start: string; end: string } | null
}

export type PieDatum = { name: string; value: number }
export type LineDatum = { date: string; value: number }

export type ChartData = {
  pie: PieDatum[]
  line: LineDatum[]
}

const API_BASE = (import.meta.env.VITE_API_BASE ?? '').replace(/\/$/, '')
const newsListCache = new Map<Lang, NewsItem[]>()
const newsDetailCache = new Map<string, NewsDetail | null>()
const countryByCoordCache = new Map<string, boolean>()

function apiUrl(path: string) {
  return `${API_BASE}${path}`
}

export async function fetchNewsList(lang: Lang = 'zh'): Promise<NewsItem[]> {
  const cached = newsListCache.get(lang)
  if (cached) return cached
  const res = await fetch(apiUrl(`/api/news?lang=${lang}`))
  if (!res.ok) throw new Error(`获取新闻列表失败: ${res.status}`)
  const data = (await res.json()) as { items?: NewsItem[] }
  const items = Array.isArray(data.items) ? data.items : []
  newsListCache.set(lang, items)
  return items
}

export async function fetchNewsById(id: string, lang: Lang = 'zh'): Promise<NewsDetail | null> {
  const cacheKey = `${lang}:${id}`
  if (newsDetailCache.has(cacheKey)) return newsDetailCache.get(cacheKey) ?? null
  const res = await fetch(apiUrl(`/api/news/${id}?lang=${lang}`))
  if (res.status === 404) return null
  if (!res.ok) throw new Error(`获取新闻详情失败: ${res.status}`)
  const item = (await res.json()) as NewsDetail
  newsDetailCache.set(cacheKey, item)
  return item
}

function dayKey(ts: number) {
  const d = new Date(ts)
  const y = d.getUTCFullYear()
  const m = String(d.getUTCMonth() + 1).padStart(2, '0')
  const dd = String(d.getUTCDate()).padStart(2, '0')
  return `${y}-${m}-${dd}`
}

function contains(haystack: string, needle: string) {
  const q = needle.trim().toLowerCase()
  if (!q) return true
  return haystack.toLowerCase().includes(q)
}

function isPointInCountry(code: string, lat: number, lng: number, id: string) {
  const cacheKey = `${code}|${id}`
  const cached = countryByCoordCache.get(cacheKey)
  if (cached !== undefined) return cached

  let result = false
  if (Number.isFinite(lat) && Number.isFinite(lng)) {
    try {
      // country-coder uses [longitude, latitude]
      result = Boolean(isIn([lng, lat], code))
    } catch {
      result = false
    }
  }
  countryByCoordCache.set(cacheKey, result)
  return result
}

export function filterNews(items: NewsItem[], filter: FilterState) {
  const list = items.filter((n) => {
    if (filter.country) {
      const selected = filter.country.trim().toUpperCase()
      // 兼容旧值（名称）和新值（ISO alpha-2 code）
      if (/^[A-Z]{2}$/.test(selected)) {
        if (!isPointInCountry(selected, n.lat, n.lng, n.id)) return false
      } else if (n.country !== filter.country) {
        return false
      }
    }
    if (filter.media && n.media !== filter.media) return false
    if (filter.continent && n.continent !== filter.continent) return false
    if (filter.type && n.type !== filter.type) return false
    if (filter.timeRange) {
      if (n.date < filter.timeRange.start) return false
      if (n.date > filter.timeRange.end) return false
    }
    if (filter.query) {
      const s = `${n.title} ${n.summary} ${n.media} ${n.country} ${n.continent} ${n.type}`
      if (!contains(s, filter.query)) return false
    }
    return true
  })

  if (filter.heat === 'hot') return list.slice().sort((a, b) => b.heat - a.heat)
  if (filter.heat === 'time') return list.slice().sort((a, b) => b.ts - a.ts)
  return list
}

export function buildChartData(items: NewsItem[]): ChartData {
  const pieMap = new Map<string, number>()
  for (const n of items) pieMap.set(n.type, (pieMap.get(n.type) ?? 0) + 1)

  const pie = [...pieMap.entries()]
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)

  const byDay = new Map<string, number>()
  for (const n of items) {
    const k = n.date
    byDay.set(k, (byDay.get(k) ?? 0) + 1)
  }

  const line = [...byDay.entries()]
    .sort((a, b) => (a[0] < b[0] ? -1 : 1))
    .map(([date, value]) => ({ date, value }))

  return { pie, line }
}

function make(
  id: string,
  title: string,
  media: string,
  continent: string,
  country: string,
  type: string,
  heat: number,
  lat: number,
  lng: number,
  ts: number,
): NewsItem {
  return {
    id,
    title,
    summary: '这是用于演示联动与图表统计的摘要内容。',
    date: dayKey(ts),
    ts,
    media,
    continent,
    country,
    type,
    heat,
    lat,
    lng,
  }
}

const now = Date.now()
const day = 24 * 60 * 60 * 1000

const citySeeds = [
  { continent: '亚洲', country: '日本', lat: 35.6762, lng: 139.6503 },
  { continent: '亚洲', country: '中国', lat: 39.9042, lng: 116.4074 },
  { continent: '亚洲', country: '新加坡', lat: 1.3521, lng: 103.8198 },
  { continent: '亚洲', country: '阿联酋', lat: 25.2048, lng: 55.2708 },
  { continent: '欧洲', country: '德国', lat: 52.52, lng: 13.405 },
  { continent: '欧洲', country: '法国', lat: 48.8566, lng: 2.3522 },
  { continent: '欧洲', country: '英国', lat: 51.5074, lng: -0.1278 },
  { continent: '欧洲', country: '瑞典', lat: 59.3293, lng: 18.0686 },
  { continent: '北美洲', country: '美国', lat: 38.9072, lng: -77.0369 },
  { continent: '北美洲', country: '加拿大', lat: 45.4215, lng: -75.6972 },
  { continent: '南美洲', country: '巴西', lat: -23.5505, lng: -46.6333 },
  { continent: '南美洲', country: '阿根廷', lat: -34.6037, lng: -58.3816 },
  { continent: '非洲', country: '肯尼亚', lat: -1.2921, lng: 36.8219 },
  { continent: '非洲', country: '埃及', lat: 30.0444, lng: 31.2357 },
  { continent: '大洋洲', country: '澳大利亚', lat: -33.8688, lng: 151.2093 },
  { continent: '大洋洲', country: '新西兰', lat: -41.2865, lng: 174.7762 },
]

const titles: Record<string, string[]> = {
  政治: ['峰会举行', '议会讨论', '外交会谈', '政策发布'],
  经济: ['数据公布', '市场波动', '投资增长', '贸易谈判'],
  科技: ['新品发布', '研发突破', '投资回暖', '产业合作'],
  体育: ['赛事开幕', '焦点战', '纪录刷新', '转会动态'],
  文化: ['艺术展览', '文化节', '交流活动', '遗产保护'],
}

const medias = ['新闻媒体', '环球观察', '今日快讯', '深度报道']
const types = ['政治', '经济', '科技', '体育', '文化']

export const mockNews: NewsItem[] = Array.from({ length: 60 }).map((_, i) => {
  const seed = citySeeds[i % citySeeds.length]
  const t = types[i % types.length]
  const title = `${seed.country}${titles[t][i % titles[t].length]}`
  const media = medias[i % medias.length]
  const heat = 40 + ((i * 7) % 60)
  const ts = now - day * (i % 28) - (i % 12) * 60 * 60 * 1000
  return make(
    `n${i + 1}`,
    title,
    media,
    seed.continent,
    seed.country,
    t,
    heat,
    seed.lat,
    seed.lng,
    ts,
  )
})
