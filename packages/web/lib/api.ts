import { normaliseHealth, type IntegrationHealth } from './health'
import type { MissionDraft } from './mission'

type ApiErrorPayload = { detail?: unknown; message?: unknown }

export class ApiError extends Error {
  constructor(message: string, public readonly status?: number) {
    super(message)
  }
}

function apiBaseUrl(): string {
  const baseUrl = process.env.EVOX_API_BASE_URL
  if (!baseUrl) throw new ApiError('EVOX_API_BASE_URL is not configured. Connect the cockpit to the Evox control plane.')
  return baseUrl.replace(/\/$/, '')
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    ...init,
    headers: { 'content-type': 'application/json', ...init?.headers },
    cache: 'no-store',
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({})) as ApiErrorPayload
    const detail = typeof body.detail === 'string' ? body.detail : typeof body.message === 'string' ? body.message : `Control plane returned ${response.status}.`
    throw new ApiError(detail, response.status)
  }
  return response.json() as Promise<T>
}

export async function getIntegrationHealth(): Promise<IntegrationHealth[]> {
  try {
    return normaliseHealth(await request('/v1/integrations/health'))
  } catch (error) {
    if (error instanceof ApiError && !error.status) return []
    throw error
  }
}

export async function createMission(draft: MissionDraft): Promise<{ id: string }> {
  return request('/v1/missions', { method: 'POST', body: JSON.stringify(draft) })
}
