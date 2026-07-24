import { Cockpit } from '@/components/cockpit'
import { getIntegrationHealth } from '@/lib/api'

export const dynamic = 'force-dynamic'

export default async function Home() {
  const health = await getIntegrationHealth().catch(() => [])
  return <Cockpit initialHealth={health} />
}
