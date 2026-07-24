import { describe, expect, it } from 'vitest'

import { validateMissionDraft } from './mission'

describe('validateMissionDraft', () => {
  it('rejects a mission without an objective', () => {
    expect(validateMissionDraft({
      objective: '   ',
      successCriteria: ['A cited answer'],
      capabilities: ['knowledge-search'],
      hardConstraints: ['Preserve permissions'],
      datasetIds: ['evoagentx-train-v1', 'evoagentx-dev-v1', 'evoagentx-held-out-v1'],
      budgetUsd: 20,
      hitlRequired: true,
    })).toEqual({ objective: 'State the outcome the system must achieve.' })
  })

  it('accepts a complete governed mission draft', () => {
    expect(validateMissionDraft({
      objective: 'Resolve documented issue reports',
      successCriteria: ['A cited answer'],
      capabilities: ['knowledge-search'],
      hardConstraints: ['Preserve permissions'],
      datasetIds: ['evoagentx-train-v1', 'evoagentx-dev-v1', 'evoagentx-held-out-v1'],
      budgetUsd: 20,
      hitlRequired: true,
    })).toEqual({})
  })
})
