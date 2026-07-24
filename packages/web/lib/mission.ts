export type MissionDraft = {
  objective: string
  successCriteria: string[]
  capabilities: string[]
  hardConstraints: string[]
  datasetIds: string[]
  budgetUsd: number
  hitlRequired: boolean
}

export type MissionDraftErrors = Partial<Record<keyof MissionDraft, string>>

const requiredArrayMessage = 'Add at least one item.'

export function validateMissionDraft(draft: MissionDraft): MissionDraftErrors {
  const errors: MissionDraftErrors = {}

  if (!draft.objective.trim()) {
    errors.objective = 'State the outcome the system must achieve.'
  }
  if (!draft.successCriteria.some((item) => item.trim())) {
    errors.successCriteria = requiredArrayMessage
  }
  if (!draft.capabilities.some((item) => item.trim())) {
    errors.capabilities = requiredArrayMessage
  }
  if (!draft.hardConstraints.some((item) => item.trim())) {
    errors.hardConstraints = requiredArrayMessage
  }
  if (draft.datasetIds.filter((item) => item.trim()).length !== 3) {
    errors.datasetIds = 'Provide train, development, and held-out dataset references.'
  }
  if (!Number.isFinite(draft.budgetUsd) || draft.budgetUsd <= 0) {
    errors.budgetUsd = 'Set a budget greater than zero.'
  }

  return errors
}
