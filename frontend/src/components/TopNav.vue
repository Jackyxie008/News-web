<script setup lang="ts">
import { List } from 'lucide-vue-next'
import ResetButton from '@/components/ResetButton.vue'
import SelectPill from '@/components/SelectPill.vue'
import SearchPill from '@/components/SearchPill.vue'

const props = defineProps<{
  query: string
  type: string | null
  media: string | null
  continent: string | null
  country: string | null
  heat: 'hot' | 'time' | null
  typeOptions: { label: string; value: string }[]
  mediaOptions: { label: string; value: string }[]
  continentOptions: { label: string; value: string }[]
  countryOptions: { label: string; value: string }[]
}>()

const emit = defineEmits<{
  'update:query': [value: string]
  'update:type': [value: string | null]
  'update:media': [value: string | null]
  'update:continent': [value: string | null]
  'update:country': [value: string | null]
  'update:heat': [value: 'hot' | 'time' | null]
  reset: []
}>()

function onMenu() {}

const heatOptions: { label: string; value: string }[] = [
  { label: '热度优先', value: 'hot' },
  { label: '时间优先', value: 'time' },
]
</script>

<template>
  <header class="h-[61px] bg-[#d9d9d9]">
    <div class="mx-auto flex h-full max-w-[1440px] items-center gap-2 px-2">
      <button
        class="inline-flex h-[27px] w-[27px] items-center justify-center text-black hover:opacity-80"
        type="button"
        aria-label="菜单"
        @click="onMenu"
      >
        <List class="h-[27px] w-[27px]" />
      </button>

      <ResetButton @click="emit('reset')" />

      <SelectPill
        :model-value="props.type"
        placeholder="新闻类型"
        :options="props.typeOptions"
        @update:model-value="(value) => emit('update:type', value)"
      />
      <SelectPill
        :model-value="props.media"
        placeholder="新闻媒体"
        :options="props.mediaOptions"
        @update:model-value="(value) => emit('update:media', value)"
      />
      <SelectPill
        :model-value="props.continent"
        placeholder="大洲"
        :options="props.continentOptions"
        @update:model-value="(value) => emit('update:continent', value)"
      />
      <SelectPill
        :model-value="props.country"
        placeholder="国家/地区"
        :options="props.countryOptions"
        @update:model-value="(value) => emit('update:country', value)"
      />
      <SelectPill
        :model-value="props.heat"
        placeholder="热度"
        :options="heatOptions"
        @update:model-value="(value) => emit('update:heat', value as 'hot' | 'time' | null)"
      />

      <div class="ml-auto w-[281px]">
        <SearchPill
          :model-value="props.query"
          placeholder="搜索"
          @update:model-value="(value) => emit('update:query', value)"
        />
      </div>
    </div>
  </header>
</template>
