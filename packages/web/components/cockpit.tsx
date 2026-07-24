'use client'

import { useState, useTransition } from 'react'
import Link from 'next/link'

import { submitMissionAction } from '@/app/actions'
import type { IntegrationHealth } from '@/lib/health'
import type { MissionDraft } from '@/lib/mission'

type Stage = 'define' | 'system' | 'trial' | 'gate' | 'operate'

const stages: Array<{ id: Stage; label: string; note: string }> = [
  { id: 'define', label: 'Define', note: 'governed brief' },
  { id: 'system', label: 'System', note: 'generated rails' },
  { id: 'trial', label: 'Trial', note: 'measured evidence' },
  { id: 'gate', label: 'Gate', note: 'release decision' },
  { id: 'operate', label: 'Operate', note: 'live stewardship' },
]

const sponsorNames = ['Pioneer', 'Senso', 'Actian', 'Band', 'Guild.ai', 'Replay.io']

const initialDraft: MissionDraft = {
  objective: '', successCriteria: [''], capabilities: ['model_inference', 'knowledge_retrieval'], hardConstraints: [''], datasetIds: ['corpus/train.json', 'corpus/dev.json', 'corpus/release-gate/heldout.json'], budgetUsd: 5, hitlRequired: true,
}

function LinesField({ id, label, hint, value, onChange, error }: { id: string; label: string; hint: string; value: string[]; onChange: (value: string[]) => void; error?: string }) {
  return <label className="field" htmlFor={id}>
    <span className="field-label">{label}</span><span className="field-hint">{hint}</span>
    <textarea id={id} value={value.join('\n')} onChange={(event) => onChange(event.target.value.split('\n'))} aria-invalid={Boolean(error)} aria-describedby={error ? `${id}-error` : undefined} />
    {error && <span className="field-error" id={`${id}-error`}>{error}</span>}
  </label>
}

function EmptyState({ title, copy, action }: { title: string; copy: string; action: string }) {
  return <section className="empty-state" aria-live="polite"><span className="empty-mark">∅</span><h2>{title}</h2><p>{copy}</p><span>{action}</span></section>
}

function HealthStrip({ health }: { health: IntegrationHealth[] }) {
  const indexed = new Map(health.map((item) => [item.name.toLowerCase(), item]))
  return <section className="health-strip" aria-label="Sponsor integration health">
    <span className="health-title">Integration truth</span>
    {sponsorNames.map((name) => {
      const item = indexed.get(name.toLowerCase())
      const status = item?.status ?? 'unknown'
      return <span className="health-item" key={name} role="status" aria-label={`${name} integration`} title={item?.detail ?? 'No live health record received.'}><i className={`status status-${status}`} aria-hidden="true" />{name}<b>{status}</b></span>
    })}
  </section>
}

export function Cockpit({ initialHealth }: { initialHealth: IntegrationHealth[] }) {
  const [stage, setStage] = useState<Stage>('define')
  const [draft, setDraft] = useState(initialDraft)
  const [missionId, setMissionId] = useState<string>()
  const [notice, setNotice] = useState<string>()
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [pending, startTransition] = useTransition()

  function patchDraft(patch: Partial<MissionDraft>) { setDraft((current) => ({ ...current, ...patch })) }
  function createMissionFromDraft() {
    setNotice(undefined); setFieldErrors({})
    startTransition(async () => {
      const result = await submitMissionAction(draft)
      if (result.fieldErrors) return setFieldErrors(result.fieldErrors)
      if (result.error) return setNotice(result.error)
      setMissionId(result.missionId); setStage('system')
    })
  }

  return <main className="cockpit-shell">
    <header className="masthead"><Link className="wordmark" href="/" aria-label="Evox home">EVOX<span>◒</span></Link><p>Governed learning loop <i>·</i> owner console</p><span className="environment">CONTROL PLANE</span></header>
    <HealthStrip health={initialHealth} />
    <div className="cockpit-grid">
      <nav className="stage-nav" aria-label="Learning loop stages">{stages.map((item, index) => <button className={stage === item.id ? 'stage-link active' : 'stage-link'} onClick={() => setStage(item.id)} key={item.id} aria-current={stage === item.id ? 'step' : undefined}><span>{String(index + 1).padStart(2, '0')}</span><strong>{item.label}</strong><small>{item.note}</small></button>)}</nav>
      <section className="workspace" aria-labelledby="workspace-title">
        <div className="workspace-kicker"><span>LOOP / {stage.toUpperCase()}</span>{missionId && <span className="mission-chip">Mission {missionId}</span>}</div>
        {stage === 'define' && <div className="define-layout"><div className="stage-intro"><p className="eyebrow">A bounded beginning</p><h1 id="workspace-title">Define the work.<br /><em>Freeze the rules.</em></h1><p>Every field becomes a signed input to the system’s release evidence. Ambiguity belongs here, before the system begins to learn.</p></div><form className="mission-form" onSubmit={(event) => { event.preventDefault(); createMissionFromDraft() }}>
          <label className="field" htmlFor="objective"><span className="field-label">Objective</span><span className="field-hint">The outcome the system must achieve.</span><textarea id="objective" value={draft.objective} onChange={(event) => patchDraft({ objective: event.target.value })} aria-invalid={Boolean(fieldErrors.objective)} />{fieldErrors.objective && <span className="field-error">{fieldErrors.objective}</span>}</label>
          <LinesField id="criteria" label="Success criteria" hint="One measurable criterion per line." value={draft.successCriteria} onChange={(successCriteria) => patchDraft({ successCriteria })} error={fieldErrors.successCriteria} />
          <LinesField id="capabilities" label="Allowed capabilities" hint="Only these capabilities may be bound." value={draft.capabilities} onChange={(capabilities) => patchDraft({ capabilities })} error={fieldErrors.capabilities} />
          <LinesField id="constraints" label="Hard constraints" hint="Immutable after the system is forged." value={draft.hardConstraints} onChange={(hardConstraints) => patchDraft({ hardConstraints })} error={fieldErrors.hardConstraints} />
          <LinesField id="datasets" label="Evaluation datasets" hint="Registered dataset identifiers, one per line." value={draft.datasetIds} onChange={(datasetIds) => patchDraft({ datasetIds })} error={fieldErrors.datasetIds} />
          <div className="field-row"><label className="field" htmlFor="budget"><span className="field-label">Budget ceiling (USD)</span><input id="budget" type="number" min="0" step="0.01" value={draft.budgetUsd || ''} onChange={(event) => patchDraft({ budgetUsd: Number(event.target.value) })} aria-invalid={Boolean(fieldErrors.budgetUsd)} />{fieldErrors.budgetUsd && <span className="field-error">{fieldErrors.budgetUsd}</span>}</label><label className="switch-field"><input type="checkbox" checked={draft.hitlRequired} onChange={(event) => patchDraft({ hitlRequired: event.target.checked })} /><span><b>Human approval required</b><small>Promotion pauses for owner review.</small></span></label></div>
          {notice && <p className="notice" role="alert">{notice}</p>}<button className="primary-action" type="submit" disabled={pending}>{pending ? 'Creating mission…' : 'Create governed mission'} <span>→</span></button>
        </form></div>}
        {stage === 'system' && <><div className="stage-intro compact"><p className="eyebrow">System specification</p><h1 id="workspace-title">The graph is a contract,<br /><em>not a black box.</em></h1></div><EmptyState title="No generated system yet" copy={missionId ? 'The mission exists, but the control plane has not returned a forged system specification.' : 'Create a mission first. Forge runs through the durable job boundary.'} action="Generated nodes, capability bindings, and immutable-policy digest will appear here." /></>}
        {stage === 'trial' && <><div className="stage-intro compact"><p className="eyebrow">Evidence comparison</p><h1 id="workspace-title">Trial only what<br /><em>you can measure.</em></h1></div><EmptyState title="No candidate evidence" copy="Baseline and candidate results only appear after the evaluation job records repeated, frozen-case outcomes." action="This view never estimates results or fills missing evidence." /></>}
        {stage === 'gate' && <><div className="stage-intro compact"><p className="eyebrow">Release authority</p><h1 id="workspace-title">A decision needs<br /><em>a receipt.</em></h1></div><EmptyState title="No release decision" copy="Promotion is unavailable until a signed decision receipt records held-out evidence, invariants, and rollback target." action="A returned decision will make the promote action explicit here." /></>}
        {stage === 'operate' && <><div className="stage-intro compact"><p className="eyebrow">Live stewardship</p><h1 id="workspace-title">Learning continues.<br /><em>Live stays fixed.</em></h1></div><EmptyState title="No active release" copy="There is no published system to monitor. Feedback, failures, and rollback remain unavailable until promotion succeeds." action="Operational records are read from the control plane; they are never invented in the cockpit." /></>}
      </section>
    </div>
  </main>
}
