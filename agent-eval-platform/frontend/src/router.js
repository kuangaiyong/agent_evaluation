import { createRouter, createWebHistory } from 'vue-router'
import { store } from './store'

const routes = [
  { path: '/login', component: () => import('./pages/Login.vue') },
  {
    path: '/', component: () => import('./layout/MainLayout.vue'),
    children: [
      { path: '', component: () => import('./pages/Home.vue') },
      { path: 'dashboard', component: () => import('./pages/Dashboard.vue') },
      { path: 'access', component: () => import('./pages/Access.vue') },
      { path: 'traces', component: () => import('./pages/Traces.vue') },
      { path: 'traces/:id', component: () => import('./pages/TraceDetail.vue') },
      { path: 'metrics', component: () => import('./pages/Metrics.vue') },
      { path: 'evaluators', component: () => import('./pages/Evaluators.vue') },
      { path: 'tasks', component: () => import('./pages/Tasks.vue') },
      { path: 'tasks/:id', component: () => import('./pages/TaskDetail.vue') },
      { path: 'badcases', component: () => import('./pages/BadCases.vue') },
      { path: 'datacenter', component: () => import('./pages/Datacenter.vue') },
      { path: 'regression', component: () => import('./pages/Regression.vue') },
      { path: 'notifications', component: () => import('./pages/Notifications.vue') },
      { path: 'system', component: () => import('./pages/System.vue') },
    ],
  },
]
const router = createRouter({ history: createWebHistory(), routes })
router.beforeEach(to => {
  if (!store.token && to.path !== '/login') return '/login'
})
export default router
