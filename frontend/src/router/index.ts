import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { usePluginStore } from '@/stores/plugin'
import { loadPluginRoutes } from '@/router/plugin-loader'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/dashboard' },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/auth/callback',
      name: 'auth-callback',
      component: () => import('@/views/AuthCallbackView.vue'),
      meta: { public: true },
    },
    {
      // Persistent shell — all authenticated views live inside here
      path: '/',
      name: 'main',
      component: () => import('@/components/AppLayout.vue'),
      children: [
        {
          path: 'dashboard',
          name: 'dashboard',
          component: () => import('@/views/DashboardView.vue'),
        },
        // Character
        {
          path: 'character/:id/overview',
          name: 'character-overview',
          component: () => import('@/views/character/OverviewView.vue'),
        },
        {
          path: 'character/:id/wallet',
          name: 'character-wallet',
          component: () => import('@/views/character/WalletView.vue'),
        },
        {
          path: 'character/:id/skills',
          name: 'character-skills',
          component: () => import('@/views/character/SkillsView.vue'),
        },
        {
          path: 'character/:id/assets',
          name: 'character-assets',
          component: () => import('@/views/character/AssetsView.vue'),
        },
        {
          path: 'character/:id/mail',
          name: 'character-mail',
          component: () => import('@/views/character/MailView.vue'),
        },
        {
          path: 'character/:id/notifications',
          name: 'character-notifications',
          component: () => import('@/views/character/NotificationsView.vue'),
        },
        // Corporation
        {
          path: 'corporation/:id/overview',
          name: 'corporation-overview',
          component: () => import('@/views/corporation/OverviewView.vue'),
        },
        {
          path: 'corporation/:id/members',
          name: 'corporation-members',
          component: () => import('@/views/corporation/MembersView.vue'),
        },
        {
          path: 'corporation/:id/wallet',
          name: 'corporation-wallet',
          component: () => import('@/views/corporation/WalletView.vue'),
        },
        {
          path: 'corporation/:id/assets',
          name: 'corporation-assets',
          component: () => import('@/views/corporation/AssetsView.vue'),
        },
        // Alliance
        {
          path: 'alliance/:id/overview',
          name: 'alliance-overview',
          component: () => import('@/views/alliance/OverviewView.vue'),
        },
        // Admin (superuser only)
        {
          path: 'admin',
          component: () => import('@/views/admin/AdminLayout.vue'),
          meta: { requiresSuperuser: true },
          children: [
            { path: '', redirect: '/admin/system' },
            { path: 'system', name: 'admin-system', component: () => import('@/views/admin/SystemView.vue') },
            { path: 'users', name: 'admin-users', component: () => import('@/views/admin/UsersView.vue') },
            { path: 'roles', name: 'admin-roles', component: () => import('@/views/admin/RolesView.vue') },
            { path: 'permissions', name: 'admin-permissions', component: () => import('@/views/admin/PermissionsView.vue') },
            { path: 'sde', name: 'admin-sde', component: () => import('@/views/admin/SdeView.vue') },
            { path: 'buckets', name: 'admin-buckets', component: () => import('@/views/admin/BucketsView.vue') },
            { path: 'tokens', name: 'admin-tokens', component: () => import('@/views/admin/ApiTokensView.vue') },
            { path: 'plugins', name: 'admin-plugins', component: () => import('@/views/admin/PluginsView.vue') },
          ],
        },
      ],
    },
  ],
})

// Track whether plugin routes have been registered for the current session.
// Must be reset to false on logout so re-login picks up fresh routes.
let pluginRoutesLoaded = false

export function resetPluginRoutesFlag() {
  pluginRoutesLoaded = false
}

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  if (!to.meta.public && !auth.isLoggedIn) {
    return { name: 'login' }
  }
  if (to.meta.requiresSuperuser && !auth.isSuperuser) {
    return { name: 'dashboard' }
  }

  // Register plugin routes once after the user is authenticated.
  // This runs inside beforeEach so routes exist before the initial navigation
  // resolves — fixing hard-refresh on /plugins/* paths.
  if (auth.isLoggedIn && !pluginRoutesLoaded) {
    pluginRoutesLoaded = true
    await loadPluginRoutes(router)
    usePluginStore().fetchEnabledPlugins()

    // If the target is a plugin path, re-trigger navigation now that the
    // routes are registered (otherwise the initial guard run would 404).
    if (to.path.startsWith('/plugins/')) {
      return to.fullPath
    }
  }
})

export default router
