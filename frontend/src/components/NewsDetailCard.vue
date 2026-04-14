<script setup lang="ts">
import type { NewsDetail } from '@/lib/news'

const props = defineProps<{
  visible: boolean
  detail: NewsDetail | null
}>()

const emit = defineEmits<{
  close: []
}>()
</script>

<template>
  <aside
    v-if="props.visible"
    class="absolute bottom-6 right-6 top-[88px] z-[1200] w-[min(547px,calc(100vw-24px))] overflow-hidden rounded-[20px] border border-zinc-200 bg-white shadow-[0_20px_60px_rgba(0,0,0,0.28)]"
  >
    <div class="flex h-full flex-col p-6">
      <div class="mb-4 flex items-start justify-between gap-4">
        <h2 class="break-words text-[34px] font-semibold leading-[1.2] text-black">
          {{ props.detail?.title || '新闻标题' }}
        </h2>
        <button
          class="inline-flex h-10 w-10 flex-none items-center justify-center rounded-md bg-black text-2xl leading-none text-white hover:opacity-90"
          type="button"
          aria-label="关闭"
          @click="emit('close')"
        >
          ×
        </button>
      </div>

      <div class="flex-1 space-y-4 overflow-y-auto pr-1 text-black">
        <section>
          <p class="mb-1 text-base font-medium">地点</p>
          <p class="text-sm text-zinc-700">{{ props.detail?.location || props.detail?.country || '-' }}</p>
        </section>

        <section>
          <p class="mb-1 text-base font-medium">发布时间</p>
          <p class="text-sm text-zinc-700">
            {{ props.detail?.published || props.detail?.date || '-' }}
          </p>
        </section>

        <section>
          <p class="mb-2 text-base font-medium">关键字</p>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="keyword in props.detail?.keywords || []"
              :key="keyword"
              class="rounded-full bg-zinc-100 px-3 py-1 text-xs text-zinc-700"
            >
              {{ keyword }}
            </span>
            <span
              v-if="!(props.detail?.keywords && props.detail.keywords.length > 0)"
              class="text-sm text-zinc-700"
            >
              -
            </span>
          </div>
        </section>

        <section>
          <p class="mb-1 text-base font-medium">新闻类型</p>
          <p class="text-sm text-zinc-700">{{ props.detail?.newsType || props.detail?.type || '-' }}</p>
        </section>

        <section>
          <p class="mb-1 text-base font-medium">正文</p>
          <p class="whitespace-pre-wrap text-sm leading-6 text-zinc-700">
            {{ props.detail?.fullText?.trim() || props.detail?.summary || '-' }}
          </p>
        </section>

        <section>
          <p class="mb-1 text-base font-medium">链接</p>
          <div class="space-y-1">
            <a
              v-for="link in props.detail?.links || []"
              :key="link"
              :href="link"
              target="_blank"
              rel="noopener noreferrer"
              class="block truncate text-sm text-blue-700 underline"
            >
              {{ link }}
            </a>
            <p v-if="!(props.detail?.links && props.detail.links.length > 0)" class="text-sm text-zinc-700">
              -
            </p>
          </div>
        </section>
      </div>
    </div>
  </aside>
</template>
