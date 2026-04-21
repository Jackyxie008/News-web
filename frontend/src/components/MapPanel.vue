<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet.markercluster'
import type { NewsItem } from '@/lib/news'

const props = defineProps<{
  items: NewsItem[]
  selectedId: string | null
  lang: 'zh' | 'en'
  focusRequestId?: number
}>()

const emit = defineEmits<{ select: [news: NewsItem | null] }>()

const mapRef = ref<HTMLDivElement | null>(null)
const map = ref<L.Map | null>(null)
const layer = ref<L.MarkerClusterGroup | null>(null)
const tileLayer = ref<L.TileLayer | null>(null)
const markersByNewsId = new Map<string, L.Marker[]>()
const markerToNews = new WeakMap<L.Marker, NewsItem>()

const selected = computed(() => props.items.find((n) => n.id === props.selectedId) ?? null)

function googleTileUrl() {
  const hl = props.lang === 'en' ? 'en' : 'zh-CN'
  return `https://mt1.google.com/vt/lyrs=m&hl=${hl}&gl=CN&x={x}&y={y}&z={z}`
}

function markerIcon(active: boolean) {
  const dot = active ? 12 : 10
  const halo = active ? 26 : 22
  const bg = active ? '#dc2626' : '#ef4444'
  const haloBg = active ? 'rgba(220, 38, 38, 0.28)' : 'rgba(239, 68, 68, 0.22)'
  return L.divIcon({
    className: 'news-marker-icon',
    html: `
      <span style="position:relative;display:block;width:${halo}px;height:${halo}px;">
        <span style="position:absolute;inset:0;border-radius:9999px;background:${haloBg};"></span>
        <span style="position:absolute;left:50%;top:50%;width:${dot}px;height:${dot}px;transform:translate(-50%,-50%);border-radius:9999px;background:${bg};box-shadow:0 0 0 1px rgba(255,255,255,0.85);"></span>
      </span>
    `,
    iconSize: [halo, halo],
    iconAnchor: [Math.round(halo / 2), Math.round(halo / 2)],
  })
}

function popupNode(n: NewsItem) {
  const wrap = document.createElement('div')
  wrap.style.width = '280px'
  wrap.style.fontFamily = 'ui-sans-serif, system-ui'

  const title = document.createElement('div')
  title.textContent = n.title
  title.style.fontWeight = '700'
  title.style.fontSize = '14px'
  title.style.lineHeight = '18px'
  title.style.marginBottom = '6px'

  const meta = document.createElement('div')
  meta.textContent = `${n.date} · ${n.media} · ${n.country}`
  meta.style.color = '#71717a'
  meta.style.fontSize = '12px'
  meta.style.lineHeight = '16px'
  meta.style.marginBottom = '10px'

  const summary = document.createElement('div')
  summary.textContent = n.summary
  summary.style.color = '#3f3f46'
  summary.style.fontSize = '12px'
  summary.style.lineHeight = '16px'

  wrap.appendChild(title)
  wrap.appendChild(meta)
  wrap.appendChild(summary)
  return wrap
}

function clusterPopupNode(cluster: L.MarkerCluster) {
  const wrap = document.createElement('div')
  wrap.style.width = '300px'
  wrap.style.fontFamily = 'ui-sans-serif, system-ui'

  const title = document.createElement('div')
  title.textContent = props.lang === 'en' ? `News (${cluster.getChildCount()})` : `新闻 (${cluster.getChildCount()})`
  title.style.fontWeight = '700'
  title.style.fontSize = '13px'
  title.style.marginBottom = '8px'
  wrap.appendChild(title)

  const list = document.createElement('div')
  list.style.maxHeight = '220px'
  list.style.overflowY = 'auto'
  list.style.display = 'flex'
  list.style.flexDirection = 'column'
  list.style.gap = '4px'

  const childMarkers = cluster.getAllChildMarkers() as L.Marker[]
  const seenNews = new Set<string>()
  for (const marker of childMarkers) {
    const news = markerToNews.get(marker)
    if (!news) continue
    if (seenNews.has(news.id)) continue
    seenNews.add(news.id)

    const btn = document.createElement('button')
    btn.type = 'button'
    btn.style.width = '100%'
    btn.style.textAlign = 'left'
    btn.style.padding = '6px 8px'
    btn.style.borderRadius = '8px'
    btn.style.border = '0'
    btn.style.cursor = 'pointer'
    btn.style.background = 'rgba(244, 244, 245, 0.9)'
    btn.onmouseenter = () => {
      btn.style.background = 'rgba(228, 228, 231, 0.95)'
    }
    btn.onmouseleave = () => {
      btn.style.background = 'rgba(244, 244, 245, 0.9)'
    }

    const titleText = document.createElement('div')
    titleText.textContent = news.title
    titleText.style.fontSize = '12px'
    titleText.style.lineHeight = '16px'
    titleText.style.fontWeight = '700'
    titleText.style.color = '#18181b'

    const dateText = document.createElement('div')
    const dateLabel = props.lang === 'en' ? 'Published' : '发布时间'
    dateText.textContent = `${dateLabel}: ${news.date || '-'}`
    dateText.style.marginTop = '2px'
    dateText.style.fontSize = '11px'
    dateText.style.lineHeight = '14px'
    dateText.style.color = '#71717a'

    btn.appendChild(titleText)
    btn.appendChild(dateText)

    btn.onclick = () => {
      emit('select', news)
    }
    list.appendChild(btn)
  }

  if (!list.childElementCount) {
    const empty = document.createElement('div')
    empty.textContent = props.lang === 'en' ? 'No news' : '暂无新闻'
    empty.style.fontSize = '12px'
    empty.style.color = '#71717a'
    list.appendChild(empty)
  }

  wrap.appendChild(list)
  return wrap
}

function openClusterPopup(cluster: L.MarkerCluster) {
  const content = clusterPopupNode(cluster)
  if (cluster.getPopup()) {
    cluster.setPopupContent(content)
  } else {
    cluster.bindPopup(content, {
      autoPan: true,
      closeButton: true,
      maxWidth: 340,
      closeOnClick: false,
      autoClose: true,
      className: 'cluster-news-popup',
    })
  }
  cluster.openPopup()
}

function normalizeCoords(lat: number, lng: number): [number, number] | null {
  const latOk = lat >= -90 && lat <= 90
  const lngOk = lng >= -180 && lng <= 180
  if (latOk && lngOk) return [lat, lng]

  // 部分数据可能经纬度写反：尝试自动纠偏
  const swappedLatOk = lng >= -90 && lng <= 90
  const swappedLngOk = lat >= -180 && lat <= 180
  if (swappedLatOk && swappedLngOk) return [lng, lat]

  return null
}

function newsCoords(news: NewsItem): [number, number][] {
  const points = Array.isArray(news.locations) ? news.locations : []
  const normalizedPoints: [number, number][] = []
  for (const point of points) {
    if (!Number.isFinite(point.lat) || !Number.isFinite(point.lng)) continue
    const normalized = normalizeCoords(point.lat, point.lng)
    if (normalized) normalizedPoints.push(normalized)
  }
  if (normalizedPoints.length > 0) return normalizedPoints
  const single = normalizeCoords(news.lat, news.lng)
  return single ? [single] : []
}

function renderMarkers() {
  if (!map.value) return
  if (layer.value) layer.value.remove()
  markersByNewsId.clear()

  const g = L.markerClusterGroup({
    showCoverageOnHover: false,
    maxClusterRadius: 50,
    zoomToBoundsOnClick: false,
    spiderfyOnMaxZoom: false,
    chunkedLoading: true,
    chunkInterval: 120,
    chunkDelay: 30,
    removeOutsideVisibleBounds: true,
    animate: false,
    animateAddingMarkers: false,
    iconCreateFunction(cluster) {
      const count = cluster.getChildCount()
      const dot = 20
      const halo = 36
      const fontSize = 13
      return L.divIcon({
        className: 'news-cluster-icon',
        html: `
          <div class="news-cluster-wrap" style="width:${halo}px;height:${halo}px;">
            <span class="news-cluster-halo"></span>
            <span class="news-cluster-dot" style="width:${dot}px;height:${dot}px;font-size:${fontSize}px;">${count}</span>
          </div>
        `,
        iconSize: [halo, halo],
      })
    },
  })

  for (const n of props.items) {
    const points = newsCoords(n)
    if (points.length === 0) continue
    const active = n.id === props.selectedId
    const markers: L.Marker[] = []
    for (const point of points) {
      const m = L.marker(point, { icon: markerIcon(active), keyboard: false })
      m.on('click', (event: L.LeafletMouseEvent) => {
        event.originalEvent?.preventDefault()
        event.originalEvent?.stopPropagation()
        emit('select', n)
        if (m.getPopup()) {
          m.setPopupContent(popupNode(n))
        } else {
          m.bindPopup(popupNode(n), {
            autoPan: true,
            closeButton: true,
            closeOnClick: false,
            autoClose: true,
            className: 'single-news-popup',
          })
        }
        m.openPopup()
      })
      m.bindPopup(popupNode(n), {
        autoPan: true,
        closeButton: true,
        closeOnClick: false,
        autoClose: true,
        className: 'single-news-popup',
      })
      g.addLayer(m)
      markerToNews.set(m, n)
      markers.push(m)
    }
    markersByNewsId.set(n.id, markers)
  }

  g.on('clusterclick', (event: L.LeafletEvent & { layer: L.MarkerCluster; originalEvent?: MouseEvent }) => {
    event.originalEvent?.preventDefault()
    event.originalEvent?.stopPropagation()
    const cluster = event.layer
    openClusterPopup(cluster)
  })

  map.value.addLayer(g)
  layer.value = g
}

function applySelectedStyle() {
  for (const [id, markers] of markersByNewsId) {
    const active = id === props.selectedId
    for (const marker of markers) marker.setIcon(markerIcon(active))
  }
}

function firstMarkerOfSelected() {
  if (!selected.value) return null
  const markers = markersByNewsId.get(selected.value.id)
  if (!markers || markers.length === 0) return null
  return markers[0]
}

function focusSelected() {
  if (!map.value) return
  if (!selected.value) return
  const m = firstMarkerOfSelected()
  if (!m) return
  map.value.panTo(m.getLatLng(), { animate: true, duration: 0.25 })
  m.openPopup()
}

function centerSelected() {
  if (!map.value) return
  if (!selected.value) return
  const m = firstMarkerOfSelected()
  if (!m) return
  const currentZoom = map.value.getZoom()
  map.value.setView(m.getLatLng(), currentZoom, { animate: true })
}

function fitSelectedCountry() {
  if (!map.value) return
  if (!selected.value) return
  const m = firstMarkerOfSelected()
  if (!m) return

  const latlng = m.getLatLng()
  const currentZoom = map.value.getZoom()
  const targetZoom = Math.min(18, currentZoom + 5)
  map.value.setView(latlng, targetZoom, { animate: true })
}

onMounted(() => {
  if (!mapRef.value) return
  const m = L.map(mapRef.value, {
    center: [20, 0],
    zoom: 2,
    worldCopyJump: true,
    preferCanvas: true,
    zoomControl: false,
    closePopupOnClick: false,
  })
  const t = L.tileLayer(googleTileUrl(), {
    maxZoom: 18,
    minZoom: 2,
    attribution: '',
  })
  t.addTo(m)
  tileLayer.value = t
  L.control.zoom({ position: 'bottomleft' }).addTo(m)

  map.value = m
  renderMarkers()
})

onUnmounted(() => {
  map.value?.remove()
  map.value = null
})

watch(
  () => props.items,
  () => {
    renderMarkers()
  },
)

watch(
  () => props.selectedId,
  () => {
    applySelectedStyle()
    focusSelected()
  },
)

watch(
  () => props.focusRequestId,
  () => {
    fitSelectedCountry()
  },
)

watch(
  () => props.lang,
  () => {
    tileLayer.value?.setUrl(googleTileUrl(), false)
  },
)
</script>

<template>
  <div class="h-full w-full">
    <div ref="mapRef" class="h-full w-full bg-black" />
  </div>
</template>

<style>
.news-cluster-icon {
  background: transparent;
  border: 0;
}

.news-cluster-wrap {
  position: relative;
  display: block;
}

.news-cluster-halo {
  position: absolute;
  inset: 0;
  border-radius: 9999px;
  background: rgba(239, 68, 68, 0.24);
}

.news-cluster-dot {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 9999px;
  background: #dc2626;
  color: #ffffff;
  line-height: 1;
  font-weight: 700;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.88), 0 6px 16px rgba(0, 0, 0, 0.28);
}

.leaflet-popup-content-wrapper {
  position: relative;
}
</style>
