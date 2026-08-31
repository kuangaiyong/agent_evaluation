import axios from 'axios'
import { store, logout } from './store'
import router from './router'

const http = axios.create({ baseURL: '/api', timeout: 30000 })
http.interceptors.request.use(cfg => {
  if (store.token) cfg.headers['Authorization'] = 'Bearer ' + store.token
  if (store.wsId) cfg.headers['X-Workspace'] = store.wsId
  return cfg
})
http.interceptors.response.use(
  r => r.data,
  err => {
    if (err.response?.status === 401) { logout(); router.push('/login') }
    const msg = err.response?.data?.detail || err.message || '请求失败'
    return Promise.reject(new Error(typeof msg === 'string' ? msg : JSON.stringify(msg)))
  }
)
export default http

export const api = {
  login: d => http.post('/auth/login', d),
  workspaces: () => http.get('/system/workspaces'),
  dashboard: p => http.get('/dashboard', { params: p }),
  apps: () => http.get('/apps'),
  createApp: d => http.post('/apps', d),
  rotateKey: id => http.post('/apps/' + id + '/key'),
  updateApp: (id, d) => http.post('/apps/' + id + '/update', d),
  verifyApp: id => http.post('/apps/' + id + '/verify'),
  traces: p => http.get('/traces', { params: p }),
  trace: id => http.get('/traces/' + id),
  replay: sid => http.get('/sessions/' + sid + '/replay'),
  evaluators: () => http.get('/evaluators'),
  createEvaluator: d => http.post('/evaluators', d),
  trial: (id, d) => http.post('/evaluators/' + id + '/trial', d),
  publishEvaluator: id => http.post('/evaluators/' + id + '/publish'),
  tasks: p => http.get('/tasks', { params: p }),
  createTask: d => http.post('/tasks', d),
  task: id => http.get('/tasks/' + id),
  taskAction: (id, action) => http.post('/tasks/' + id + '/action', { action }),
  taskResults: id => http.get('/tasks/' + id + '/results'),
  badcases: p => http.get('/badcases', { params: p }),
  badcase: id => http.get('/badcases/' + id),
  review: (id, d) => http.post('/badcases/' + id + '/review', d),
  batchReview: d => http.post('/badcases/batch', d),
  trajectories: p => http.get('/trajectories', { params: p }),
  datasets: () => http.get('/datasets'),
  dataset: id => http.get('/datasets/' + id),
  createDataset: d => http.post('/datasets', d),
  deleteDataset: id => http.post('/datasets/' + id + '/delete'),
  uploadDataset: (id, file) => { const fd = new FormData(); fd.append('file', file); return http.post('/datasets/' + id + '/upload', fd) },
  fromTraces: (id, d) => http.post('/datasets/' + id + '/from-traces', d),
  regRuns: () => http.get('/regression/runs'),
  regRun: id => http.get('/regression/runs/' + id),
  regGateInfo: () => http.get('/regression/gate-info'),
  updateTask: (id, d) => http.post('/tasks/' + id + '/update', d),
  createRegRun: d => http.post('/regression/runs', d),
  notifications: p => http.get('/notifications', { params: p }),
  readNotif: id => http.post('/notifications/' + id + '/read'),
  readAllNotifs: () => http.post('/notifications/read-all'),
  members: () => http.get('/system/members'),
  audits: () => http.get('/system/audits'),
  invite: d => http.post('/system/members/invite', d),
  metrics: p => http.get('/metrics', { params: p }),
  metric: code => http.get('/metrics/' + code),
  metricFacets: () => http.get('/metrics/facets'),
  metricCoverage: () => http.get('/metrics/coverage'),
}
