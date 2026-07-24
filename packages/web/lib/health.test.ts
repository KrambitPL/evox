import { describe, expect, it } from 'vitest'

import { normaliseHealth } from './health'

describe('normaliseHealth', () => {
  it('preserves an unavailable integration instead of presenting it as healthy', () => {
    expect(normaliseHealth({
      services: [{ name: 'Pioneer', status: 'unavailable', detail: 'Credential not configured' }],
    })).toEqual([{ name: 'Pioneer', status: 'unavailable', detail: 'Credential not configured' }])
  })

  it('marks an absent health response as unconfigured', () => {
    expect(normaliseHealth(undefined)).toEqual([])
  })
})
