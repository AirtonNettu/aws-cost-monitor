import {
  Bot,
  CircleAlert,
  Clock3,
  Lightbulb,
  ScanEye,
  ShieldCheck,
  Sparkles,
} from 'lucide-react'
import type { Snapshot } from '../../api/contracts'

export function AiPanel({
  ai,
  simulated,
}: {
  ai: Snapshot['ai']
  simulated: boolean
}) {
  return (
    <section className="ai-panel panel">
      <div className="panel-heading">
        <div className="inline-heading">
          <div className="ai-icon">
            <Sparkles size={23} aria-hidden="true" />
          </div>
          <div>
            <h2>Seu analista FinOps</h2>
            <p>Interpretação contextual, números preservados</p>
          </div>
        </div>
        <span className="badge">{ai.model ?? 'Modelo não informado'}</span>
      </div>
      {simulated && (
        <p className="ai-demo-label">
          Conteúdo ilustrativo · nenhuma chamada ao Ollama foi realizada
        </p>
      )}
      {ai.status === 'processing' ? (
        <div className="ai-state" role="status">
          <Clock3 size={30} aria-hidden="true" />
          <h3>Análise em processamento</h3>
          <p>
            A interpretação será exibida quando estiver disponível. Os dados
            financeiros continuam acessíveis.
          </p>
        </div>
      ) : ai.status === 'unavailable' ? (
        <div className="ai-state">
          <Bot size={30} aria-hidden="true" />
          <h3>IA indisponível</h3>
          <p>
            {ai.reason ??
              'O backend não disponibilizou uma interpretação para este snapshot.'}
          </p>
          <p>Custos e alertas determinísticos permanecem disponíveis.</p>
        </div>
      ) : (
        <>
          <div className="ai-summary">
            <p className="eyebrow">
              <Bot size={15} aria-hidden="true" /> RESUMO DA ANÁLISE
            </p>
            <h3>Resumo executivo</h3>
            <p className="preserve-lines">
              {ai.text || 'Resumo não fornecido pelo backend.'}
            </p>
          </div>
          <div className="ai-section-grid">
            {[
              {
                title: 'Observações relevantes',
                items: ai.observations,
                Icon: ScanEye,
              },
              {
                title: 'Recomendações de otimização',
                items: ai.recommendations,
                Icon: Lightbulb,
              },
              {
                title: 'Possíveis desperdícios',
                items: ai.potential_waste,
                Icon: CircleAlert,
              },
            ].map(({ title, items, Icon }) => (
              <section key={title}>
                <Icon size={19} aria-hidden="true" />
                <h3>{title}</h3>
                {items.length ? (
                  <ul>
                    {items.map((item, i) => (
                      <li key={i}>{item}</li>
                    ))}
                  </ul>
                ) : (
                  <p>
                    O backend não forneceu uma seção estruturada. Consulte o
                    resumo disponível.
                  </p>
                )}
              </section>
            ))}
          </div>
        </>
      )}
      <p className="ai-disclaimer">
        <ShieldCheck size={17} aria-hidden="true" />
        Recomendações de IA exigem validação humana. Python calcula; a IA apenas
        interpreta. Nenhuma ação em recursos AWS é executada por esta interface.
      </p>
    </section>
  )
}
