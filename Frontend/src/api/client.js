import axios from 'axios'

const BASE = 'http://localhost:8000/api'
const api  = axios.create({ baseURL: BASE })

export const createSession    = ()                    => api.post('/session/new')
export const search           = (domain, session_id)  => api.post('/search', { domain, session_id })
export const getQuestions     = (session_id)          => api.post('/interview/questions', { session_id })
export const submitAnswers    = (session_id, answers) => api.post('/interview/submit', { session_id, answers })
export const runTargeting     = (session_id)          => api.post('/target', { session_id })
export const generateMessages = (session_id, profile) => api.post('/messages/generate', { session_id, ...profile })
export const getSessionData   = (session_id)          => api.get(`/session/${session_id}`)

export default api
