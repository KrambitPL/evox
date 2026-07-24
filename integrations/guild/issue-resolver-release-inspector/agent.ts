"use agent"

import { agent, guildTools, type Task } from "@guildai/agents-sdk"
import { z } from "zod"

const tools = { ...guildTools }
type Tools = typeof tools

const inputSchema = z.object({
  type: z.literal("text"),
  text: z.string().min(1).describe("Issue-resolution or release-inspection request."),
})

const outputSchema = z.object({
  type: z.literal("text"),
  text: z.string(),
})

const RELEASE_POLICY_VERSION = "evox-release-governance-v1"

async function run(
  input: z.infer<typeof inputSchema>,
  _task: Task<Tools>,
): Promise<z.infer<typeof outputSchema>> {
  return {
    type: "text",
    text: [
      `Evox Issue Resolver / Release Inspector (${RELEASE_POLICY_VERSION})`,
      "Inspect the supplied issue evidence and release receipt.",
      "A release is valid only when its immutable release ID, policy digest, approved system, evidence, active version, and rollback linkage agree.",
      "This Guild agent does not publish or mutate releases; Evox's approved-release CLI boundary performs that action.",
      `Request: ${input.text}`,
    ].join("\n"),
  }
}

export default agent({
  description: "Inspects Evox issue-resolution evidence and immutable release governance receipts.",
  inputSchema,
  outputSchema,
  tools,
  run,
})
