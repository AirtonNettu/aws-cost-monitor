// Verifica o contrato do consumidor contra uma resposta HTTP real do FastAPI.
import console from 'node:console'
import { execFileSync } from 'node:child_process'
import { snapshotSchema } from '../src/api/contracts.ts'
const data = execFileSync(
  'uv',
  ['run', '--frozen', 'python', 'scripts/export_contract_fixture.py'],
  { cwd: '..', encoding: 'utf8' },
)
const snapshot = snapshotSchema.parse(JSON.parse(data))
if (
  snapshot.source !== 'mock' ||
  snapshot.summary.total_cost !== 112.5 ||
  snapshot.comparison?.variation !== 0
)
  throw new Error('Contrato financeiro divergente.')
console.log(
  'Contrato FastAPI → Zod validado com HTTP real, SQLite temporário e dados sintéticos.',
)
