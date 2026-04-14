<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import L from 'leaflet'
import type { NewsItem } from '@/lib/news'

const props = defineProps<{
  items: NewsItem[]
  selectedId: string | null
}>()

const emit = defineEmits<{ select: [news: NewsItem | null] }>()

const router = useRouter()

const mapRef = ref<HTMLDivElement | null>(null)
const map = ref<L.Map | null>(null)
const layer = ref<L.LayerGroup | null>(null)
const markerById = new Map<string, L.CircleMarker>()

const selected = computed(() => props.items.find((n) => n.id === props.selectedId) ?? null)

function googleTileUrl() {
  return 'https://mt1.google.com/vt/lyrs=m&hl=zh-CN&gl=CN&x={x}&y={y}&z={z}'
}

function markerStyle(active: boolean) {
  return {
    radius: active ? 7 : 5,
    weight: active ? 3 : 2,
    color: active ? '#ffffff' : '#e5e7eb',
    fillColor: active ? '#ef4444' : '#22c55e',
    fillOpacity: 0.95,
  }
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

  const actions = document.createElement('div')
  actions.style.display = 'flex'
  actions.style.gap = '8px'
  actions.style.marginTop = '12px'

  const btn = document.createElement('button')
  btn.type = 'button'
  btn.textContent = '查看详情'
  btn.style.borderRadius = '10px'
  btn.style.padding = '8px 10px'
  btn.style.fontSize = '12px'
  btn.style.fontWeight = '600'
  btn.style.border = '1px solid #e4e4e7'
  btn.style.background = '#111827'
  btn.style.color = '#ffffff'
  btn.style.cursor = 'pointer'
  btn.addEventListener('click', () => router.push(`/news/${n.id}`))

  actions.appendChild(btn)
  wrap.appendChild(title)
  wrap.appendChild(meta)
  wrap.appendChild(summary)
  wrap.appendChild(actions)
  return wrap
}

function renderMarkers() {
  if (!map.value) return
  if (layer.value) layer.value.remove()
  markerById.clear()

  const g = L.layerGroup()
  for (const n of props.items) {
    const active = n.id === props.selectedId
    const m = L.circleMarker([n.lat, n.lng], markerStyle(active))
    m.on('click', () => emit('select', n))
    m.bindPopup(popupNode(n), { autoPan: true, closeButton: true })
    m.addTo(g)
    markerById.set(n.id, m)
  }
  g.addTo(map.value)
  layer.value = g
}

function applySelectedStyle() {
  for (const [id, m] of markerById) {
    const active = id === props.selectedId
    m.setStyle(markerStyle(active))
  }
}

function focusSelected() {
  if (!map.value) return
  if (!selected.value) return
  const m = markerById.get(selected.value.id)
  if (!m) return
  map.value.panTo([selected.value.lat, selected.value.lng], { animate: true, duration: 0.25 })
  m.openPopup()
}

onMounted(() => {
  if (!mapRef.value) return
  const m = L.map(mapRef.value, {
    center: [20, 0],
    zoom: 2,
    worldCopyJump: true,
    zoomControl: true,
  })
  L.tileLayer(googleTileUrl(), {
    maxZoom: 18,
    minZoom: 2,
    attribution: '',
  }).addTo(m)

  m.on('click', () => emit('select', null))
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
  { deep: true },
)

watch(
  () => props.selectedId,
  () => {
    applySelectedStyle()
    focusSelected()
  },
)
</script>

<template>
  <div class="h-full w-full">
    <div ref="mapRef" class="h-full w-full bg-black" />
  </div>
</template>
