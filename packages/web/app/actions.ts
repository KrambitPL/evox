'use server'

import { createMission } from '@/lib/api'
import { validateMissionDraft, type MissionDraft } from '@/lib/mission'

export type MissionActionResult = { missionId?: string; error?: string; fieldErrors?: Record<string, string> }

export async function submitMissionAction(draft: MissionDraft): Promise<MissionActionResult> {
  const fieldErrors = validateMissionDraft(draft)
  if (Object.keys(fieldErrors).length) return { fieldErrors }

  try {
    const mission = await createMission(draft)
    return { missionId: mission.id }
  } catch (error) {
    return { error: error instanceof Error ? error.message : 'The control plane could not create this mission.' }
  }
}
