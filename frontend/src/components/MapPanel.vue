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
  flyToLocation?: string | null
  hasMore?: boolean
  isLoading?: boolean
}>()

const emit = defineEmits<{ select: [news: NewsItem | null]; 'load-more': [] }>()

const mapRef = ref<HTMLDivElement | null>(null)
const map = ref<L.Map | null>(null)
const layer = ref<L.MarkerClusterGroup | null>(null)
const tileLayer = ref<L.TileLayer | null>(null)
const markersByNewsId = new Map<string, L.Marker[]>()
const markerToNews = new Map<L.Marker, NewsItem>()

// 跟踪当前打开的聚类弹窗
const openCluster = ref<L.MarkerCluster | null>(null)
// 延迟关闭的定时器 ID
let closeClusterTimer: number | null = null

const selected = computed(() => props.items.find((n) => n.id === props.selectedId) ?? null)

function googleTileUrl() {
  const hl = props.lang === 'en' ? 'en' : 'zh-CN'
  return `https://mt1.google.com/vt/lyrs=m&hl=${hl}&gl=CN&x={x}&y={y}&z={z}`
}

function markerIcon(active: boolean) {
  const dot = active ? 12 : 10
  const halo = active ? 26 : 22
  const bg = active ? '#ef4444' : '#f97316'
  const haloBg = active ? 'rgba(239, 68, 68, 0.28)' : 'rgba(249, 115, 22, 0.22)'
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

function formatFullDate(dateStr: string, lang: 'zh' | 'en') {
  if (!dateStr) return '-'
  const dateLabel = lang === 'en' ? 'Time' : '时间'
  return `${dateLabel}: ${dateStr}`
}

function getLocationDisplay(news: NewsItem): string {
  return news.location || news.country || '-'
}

function singlePopupNode(n: NewsItem) {
  const wrap = document.createElement('div')
  wrap.className = 'single-news-popup-content'
  wrap.style.width = '280px'
  wrap.style.fontFamily = 'ui-sans-serif, system-ui'
  wrap.style.padding = '12px'
  wrap.style.boxSizing = 'border-box'

  const title = document.createElement('div')
  title.textContent = n.title
  title.style.fontWeight = '700'
  title.style.fontSize = '12px'
  title.style.lineHeight = '16px'
  title.style.marginBottom = '2px'
  title.style.color = '#18181b'

  const dateText = document.createElement('div')
  dateText.textContent = formatFullDate(n.date, props.lang)
  dateText.style.color = '#71717a'
  dateText.style.fontSize = '11px'
  dateText.style.lineHeight = '14px'

  const locationText = document.createElement('div')
  locationText.textContent = getLocationDisplay(n)
  locationText.style.color = '#71717a'
  locationText.style.fontSize = '11px'
  locationText.style.lineHeight = '14px'

  wrap.appendChild(title)
  wrap.appendChild(dateText)
  wrap.appendChild(locationText)
  return wrap
}

function clusterPopupNode(cluster: L.MarkerCluster) {
  const wrap = document.createElement('div')
  wrap.className = 'cluster-popup-content'
  wrap.style.width = '320px'
  wrap.style.fontFamily = 'ui-sans-serif, system-ui'
  wrap.style.maxHeight = '320px'
  wrap.style.display = 'flex'
  wrap.style.flexDirection = 'column'

  const header = document.createElement('div')
  header.textContent = props.lang === 'en' ? `News Points (${cluster.getChildCount()})` : `新闻点 (${cluster.getChildCount()})`
  header.style.fontWeight = '700'
  header.style.fontSize = '13px'
  header.style.padding = '8px 8px 4px'
  header.style.color = '#18181b'
  wrap.appendChild(header)

  const list = document.createElement('div')
  list.style.maxHeight = '260px'
  list.style.overflowY = 'auto'
  list.style.padding = '4px 8px 8px'

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
    btn.style.padding = '8px'
    btn.style.marginTop = '4px'
    btn.style.borderRadius = '6px'
    btn.style.border = '0'
    btn.style.cursor = 'pointer'
    btn.style.background = 'rgba(244, 244, 245, 0.9)'
    btn.style.display = 'flex'
    btn.style.flexDirection = 'column'
    btn.style.gap = '2px'
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
    dateText.textContent = formatFullDate(news.date, props.lang)
    dateText.style.fontSize = '11px'
    dateText.style.lineHeight = '14px'
    dateText.style.color = '#71717a'

    const locationText = document.createElement('div')
    locationText.textContent = getLocationDisplay(news)
    locationText.style.fontSize = '11px'
    locationText.style.lineHeight = '14px'
    locationText.style.color = '#71717a'

    btn.appendChild(titleText)
    btn.appendChild(dateText)
    btn.appendChild(locationText)

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
    empty.style.padding = '8px'
    list.appendChild(empty)
  }

  wrap.appendChild(list)
  return wrap
}

function openClusterPopup(cluster: L.MarkerCluster) {
  // 清除延迟关闭的定时器
  if (closeClusterTimer !== null) {
    clearTimeout(closeClusterTimer)
    closeClusterTimer = null
  }
  const content = clusterPopupNode(cluster)
  if (cluster.getPopup()) {
    cluster.setPopupContent(content)
  } else {
    cluster.bindPopup(content, {
      autoPan: true,
      closeButton: true,
      maxWidth: 360,
      closeOnClick: false,
      autoClose: true,
      className: 'cluster-news-popup',
    })
  }
  openCluster.value = cluster
  cluster.openPopup()
  
  // 监听弹窗的 mouseover，防止关闭
  const popup = cluster.getPopup()
  if (popup) {
    const popupElement = popup.getElement()
    if (popupElement) {
      popupElement.addEventListener('mouseenter', () => {
        if (closeClusterTimer !== null) {
          clearTimeout(closeClusterTimer)
          closeClusterTimer = null
        }
      })
    }
  }
}

function closeClusterPopup() {
  if (openCluster.value && openCluster.value.isPopupOpen()) {
    openCluster.value.closePopup()
  }
  openCluster.value = null
}

function normalizeCoords(lat: number, lng: number): [number, number] | null {
  const latOk = lat >= -90 && lat <= 90
  const lngOk = lng >= -180 && lng <= 180
  if (latOk && lngOk) return [lat, lng]

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
  markerToNews.clear()
  openCluster.value = null

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
      // 检查聚类中是否包含选中的新闻
      const hasSelected = cluster.getAllChildMarkers().some((m) => {
        const news = markerToNews.get(m)
        return news && news.id === props.selectedId
      })
      const bg = hasSelected ? '#ef4444' : '#f97316'
      const haloBg = hasSelected ? 'rgba(239, 68, 68, 0.24)' : 'rgba(249, 115, 22, 0.24)'
      return L.divIcon({
        className: 'news-cluster-icon',
        html: `
          <div class="news-cluster-wrap" style="width:${halo}px;height:${halo}px;">
            <span class="news-cluster-halo" style="background:${haloBg}"></span>
            <span class="news-cluster-dot" style="width:${dot}px;height:${dot}px;font-size:${fontSize}px;background:${bg}">${count}</span>
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
      
      // 先设置 markerToNews，再添加到聚类
      markerToNews.set(m, n)
      
      m.bindPopup(singlePopupNode(n), {
        autoPan: true,
        closeButton: false,
        closeOnClick: false,
        autoClose: true,
        className: 'single-news-popup',
      })
      
      m.on('mouseover', (event: L.LeafletMouseEvent) => {
        event.originalEvent?.preventDefault()
        closeClusterPopup()
        if (!m.isPopupOpen()) {
          m.openPopup()
        }
      })
      
      m.on('mouseout', (event: L.LeafletMouseEvent) => {
        event.originalEvent?.preventDefault()
        setTimeout(() => {
          if (m.isPopupOpen()) {
            m.closePopup()
          }
        }, 500)
      })
      
      m.on('click', (event: L.LeafletMouseEvent) => {
        event.originalEvent?.preventDefault()
        event.originalEvent?.stopPropagation()
        emit('select', n)
        if (m.getPopup()) {
          m.setPopupContent(singlePopupNode(n))
        } else {
          m.bindPopup(singlePopupNode(n), {
            autoPan: true,
            closeButton: false,
            closeOnClick: false,
            autoClose: true,
            className: 'single-news-popup',
          })
        }
        m.openPopup()
      })
      
      g.addLayer(m)
      markers.push(m)
    }
    markersByNewsId.set(n.id, markers)
  }

  g.on('clusterclick', (event: L.LeafletEvent & { layer: L.MarkerCluster; originalEvent?: MouseEvent }) => {
    event.originalEvent?.preventDefault()
    event.originalEvent?.stopPropagation()
    const cluster = event.layer
    g.eachLayer((layer) => {
      if (layer instanceof L.Marker && layer.isPopupOpen()) {
        layer.closePopup()
      }
    })
    openClusterPopup(cluster)
  })

  g.on('clustermouseover', (event: L.LeafletEvent & { layer: L.MarkerCluster; originalEvent?: MouseEvent }) => {
    event.originalEvent?.preventDefault()
    // 清除延迟关闭的定时器
    if (closeClusterTimer !== null) {
      clearTimeout(closeClusterTimer)
      closeClusterTimer = null
    }
    const cluster = event.layer
    g.eachLayer((layer) => {
      if (layer instanceof L.Marker && layer.isPopupOpen()) {
        layer.closePopup()
      }
    })
    if (!cluster.isPopupOpen()) {
      openClusterPopup(cluster)
    }
  })

  g.on('clustermouseout', (event: L.LeafletEvent & { layer: L.MarkerCluster; originalEvent?: MouseEvent }) => {
    event.originalEvent?.preventDefault()
    // 不再自动关闭，让用户移到弹窗上
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
  closeClusterPopup()
  m.openPopup()
  // 刷新聚类图标以更新颜色
  if (layer.value) {
    layer.value.refreshClusters()
  }
}

function centerSelected() {
  if (!map.value) return
  if (!selected.value) return
  const m = firstMarkerOfSelected()
  if (!m) return
  const currentZoom = map.value.getZoom()
  map.value.setView(m.getLatLng(), currentZoom, { animate: false })
  // 刷新聚类图标以更新颜色
  if (layer.value) {
    layer.value.refreshClusters()
  }
}

function fitSelectedCountry() {
  if (!map.value) return
  if (!selected.value) return
  const m = firstMarkerOfSelected()
  if (!m) return

  const latlng = m.getLatLng()
  const currentZoom = map.value.getZoom()
  const targetZoom = Math.min(18, currentZoom + 5)
  map.value.setView(latlng, targetZoom, { animate: false })
  // 刷新聚类图标以更新颜色
  if (layer.value) {
    layer.value.refreshClusters()
  }
}

// 定位到指定地点（从数据库的坐标数据中找到匹配的位置）
function flyToLocationName(locationName: string) {
  if (!map.value) return
  
  // 固定缩放级别为 6
  const targetZoom = 6
  
  // 在新闻数据中找到匹配的位置
  for (const news of props.items) {
    const locations = news.location?.split(/[;；]/) || []
    const idx = locations.findIndex((loc) => loc.trim() === locationName)
    if (idx >= 0) {
      const points = newsCoords(news)
      if (points.length > 0 && idx < points.length) {
        map.value.setView(points[idx], targetZoom, { animate: false })
        // 延迟重新渲染聚类以更新颜色
        setTimeout(() => {
          if (layer.value) {
            renderMarkers()
          }
        }, 100)
        return
      }
      if (points.length > 0) {
        map.value.setView(points[0], targetZoom, { animate: false })
        setTimeout(() => {
          if (layer.value) {
            renderMarkers()
          }
        }, 100)
        return
      }
    }
  }
  
  // 如果找不到，尝试从第一个新闻点定位
  if (props.items.length > 0) {
    const firstNews = props.items[0]
    const points = newsCoords(firstNews)
    if (points.length > 0) {
      map.value.setView(points[0], targetZoom, { animate: false })
      setTimeout(() => {
        if (layer.value) {
          renderMarkers()
        }
      }, 100)
    }
  }
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

  // 监听缩放变化，刷新聚类图标
  m.on('zoomend', () => {
    if (layer.value) {
      // 延迟重新渲染以确保状态正确
      setTimeout(() => {
        renderMarkers()
      }, 50)
    }
  })

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
    // 延迟重新渲染聚类以确保 markerToNews 已更新
    setTimeout(() => {
      if (map.value && layer.value) {
        renderMarkers()
      }
    }, 0)
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
  () => props.flyToLocation,
  (newLocation) => {
    if (newLocation) {
      flyToLocationName(newLocation)
      // 延迟重新渲染聚类以更新颜色
      setTimeout(() => {
        if (layer.value) {
          renderMarkers()
        }
      }, 200)
    }
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
  background: rgba(249, 115, 22, 0.24);
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
  background: #f97316;
  color: #ffffff;
  line-height: 1;
  font-weight: 700;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.88), 0 6px 16px rgba(0, 0, 0, 0.28);
}

.leaflet-popup-content-wrapper {
  position: relative;
}

.cluster-news-popup .leaflet-popup-content {
  margin: 0;
}

.cluster-popup-content button:hover {
  background: rgba(228, 228, 231, 0.95) !important;
}

.single-news-popup .leaflet-popup-content-wrapper {
  border-radius: 6px;
  padding: 0 !important;
}

.single-news-popup .leaflet-popup-content {
  margin: 0 !important;
}
</style>