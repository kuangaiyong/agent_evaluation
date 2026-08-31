import { reactive } from 'vue'

export const store = reactive({
  token: localStorage.getItem('ae_token') || '',
  user: JSON.parse(localStorage.getItem('ae_user') || 'null'),
  wsId: localStorage.getItem('ae_ws') || '',
  wsRole: localStorage.getItem('ae_ws_role') || '',
  workspaces: [],
})

export function setSession({ token, user, workspace }) {
  store.token = token; store.user = user
  store.wsId = workspace.id; store.wsRole = workspace.role_in_ws
  localStorage.setItem('ae_token', token)
  localStorage.setItem('ae_user', JSON.stringify(user))
  localStorage.setItem('ae_ws', workspace.id)
  localStorage.setItem('ae_ws_role', workspace.role_in_ws)
}
export function setWorkspace(wsId, role) {
  store.wsId = wsId; store.wsRole = role || store.wsRole
  localStorage.setItem('ae_ws', wsId)
  localStorage.setItem('ae_ws_role', store.wsRole)
}
export function logout() {
  store.token = ''; store.user = null; store.wsId = ''; store.wsRole = ''
  Object.keys(localStorage).filter(k => k.startsWith('ae_')).forEach(k => localStorage.removeItem(k))
}
