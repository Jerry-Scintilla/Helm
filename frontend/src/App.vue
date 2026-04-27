<script setup lang="ts">
import { darkTheme, type GlobalThemeOverrides } from 'naive-ui'
import { RouterView } from 'vue-router'

const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#c96442',
    primaryColorHover: '#d97757',
    primaryColorPressed: '#b5593b',
    primaryColorSuppl: '#d97757',
    bodyColor: '#141413',
    cardColor: '#1e1e1c',
    modalColor: '#1e1e1c',
    popoverColor: '#252523',
    tableColorStriped: '#1a1a18',
    borderColor: '#30302e',
    textColorBase: '#faf9f5',
    textColor1: '#faf9f5',
    textColor2: '#b0aea5',
    textColor3: '#87867f',
    placeholderColor: '#5e5d59',
    dividerColor: '#30302e',
    borderRadius: '8px',
    borderRadiusSmall: '6px',
    fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif',
    fontFamilyMono: '"JetBrains Mono", "Fira Code", monospace',
  },
  Menu: {
    color: 'transparent',
    itemColorHover: 'rgba(201,100,66,0.08)',
    itemColorActive: 'rgba(201,100,66,0.14)',
    itemColorActiveHover: 'rgba(201,100,66,0.18)',
    itemColorActiveCollapsed: 'rgba(201,100,66,0.14)',
    itemTextColor: '#b0aea5',
    itemTextColorHover: '#faf9f5',
    itemTextColorActive: '#c96442',
    itemTextColorActiveHover: '#d97757',
    itemTextColorChildActive: '#c96442',
    itemIconColor: '#87867f',
    itemIconColorHover: '#faf9f5',
    itemIconColorActive: '#c96442',
    arrowColor: '#87867f',
    arrowColorHover: '#b0aea5',
    groupTextColor: '#5e5d59',
  },
  Layout: {
    color: '#141413',
    headerColor: '#141413',
    siderColor: '#141413',
    footerColor: '#141413',
  },
  DataTable: {
    thColor: '#1a1a18',
    tdColor: 'transparent',
    tdColorHover: 'rgba(201,100,66,0.06)',
    borderColor: '#30302e',
    thTextColor: '#87867f',
    tdTextColor: '#b0aea5',
  },
  Tag: {
    colorBordered: 'transparent',
  },
  Tabs: {
    tabTextColorLine: '#87867f',
    tabTextColorActiveLine: '#faf9f5',
    tabTextColorHoverLine: '#b0aea5',
    barColor: '#c96442',
  },
  Input: {
    color: '#1e1e1c',
    colorFocus: '#252523',
    border: '1px solid #30302e',
    borderFocus: '1px solid #c96442',
    borderHover: '1px solid #5e5d59',
    textColor: '#faf9f5',
    placeholderColor: '#5e5d59',
    caretColor: '#c96442',
  },
  Select: {
    peers: {
      InternalSelection: {
        color: '#1e1e1c',
        colorActive: '#252523',
        border: '1px solid #30302e',
        borderActive: '1px solid #c96442',
        borderHover: '1px solid #5e5d59',
        textColor: '#faf9f5',
      },
    },
  },
  Button: {
    textColor: '#b0aea5',
    textColorHover: '#faf9f5',
    border: '1px solid #30302e',
    borderHover: '1px solid #5e5d59',
    borderPressed: '1px solid #c96442',
    color: '#1e1e1c',
    colorHover: '#252523',
    colorPressed: '#141413',
    rippleColor: '#c96442',
  },
}
</script>

<template>
  <n-config-provider :theme="darkTheme" :theme-overrides="themeOverrides">
    <n-global-style />
    <n-message-provider>
      <n-dialog-provider>
        <RouterView />
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<style>
/* Serif heading utility — used across all views */
.h-serif { font-family: Georgia, 'Times New Roman', serif; font-weight: 500; }

/* Warm scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #141413; }
::-webkit-scrollbar-thumb { background: #30302e; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #5e5d59; }
</style>
