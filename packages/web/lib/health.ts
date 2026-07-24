export type HealthStatus = 'healthy' | 'degraded' | 'unavailable' | 'unknown'

export type IntegrationHealth = {
  name: string
  status: HealthStatus
  detail?: string
}

type HealthPayload = {
  services?: Array<{ name?: unknown; status?: unknown; detail?: unknown }>
}

export function normaliseHealth(payload: HealthPayload | undefined): IntegrationHealth[] {
  if (!payload?.services) return []

  return payload.services.flatMap((service) => {
    if (typeof service.name !== 'string') return []
    const status: HealthStatus = service.status === 'healthy' || service.status === 'degraded' || service.status === 'unavailable'
      ? service.status
      : 'unknown'
    return [{ name: service.name, status, detail: typeof service.detail === 'string' ? service.detail : undefined }]
  })
}
