export function validateReport(r) {
  const object = v => v !== null && typeof v === 'object' && !Array.isArray(v);
  const number = v => typeof v === 'number' && Number.isFinite(v);
  const string = v => typeof v === 'string';
  const optionalText = v => v === null || string(v);
  if (!object(r) || !string(r.period) || !string(r.generated_at) || !number(r.total_cost)
      || typeof r.has_positive_cost !== 'boolean' || !optionalText(r.largest_service)
      || !object(r.services) || !object(r.percentages) || !Array.isArray(r.alerts)
      || !optionalText(r.ai_interpretation) || !optionalText(r.ai_error)) throw Error('Formato de relatório inválido. Use o JSON gerado pelo AWS Cost Monitor.');
  if (Object.keys(r.services).length > 1000 || r.alerts.length > 1000
      || Object.values(r.services).some(v => !number(v) || v < 0)
      || Object.values(r.percentages).some(v => !number(v))) throw Error('Valores de serviços inválidos.');
  if (r.comparison !== null && (!object(r.comparison) || !number(r.comparison.previous_total)
      || !number(r.comparison.current_total) || !(r.comparison.variation === null || number(r.comparison.variation)))) throw Error('Comparação inválida.');
  if (r.alerts.some(a => !object(a) || !string(a.type) || !['info','warning'].includes(a.severity) || !string(a.message))) throw Error('Alertas inválidos.');
  return r;
}
export function parseReport(text) {
  if (new TextEncoder().encode(text).length > 2 * 1024 * 1024) throw Error('O limite é 2 MB por relatório.');
  let r; try { r = JSON.parse(text); } catch { throw Error('Não foi possível ler o JSON.'); }
  return validateReport(r);
}
export const demo = {
  generated_at:'2026-10-01 09:00:00', period:'2026-09-01 a 2026-10-01', total_cost:184.5,
  has_positive_cost:true, largest_service:'Amazon EC2',
  services:{'Amazon EC2':96,'Amazon RDS':52,'Amazon S3':24.5,'AWS Lambda':12},
  percentages:{'Amazon EC2':52,'Amazon RDS':28.2,'Amazon S3':13.3,'AWS Lambda':6.5},
  comparison:{previous_total:150,current_total:184.5,variation:23},
  alerts:[{type:'growth',severity:'warning',message:'Exemplo: custo cresceu 23% em relação ao período anterior.'},{type:'concentration',severity:'warning',message:'Exemplo: Amazon EC2 concentra 52% do total.'}],
  ai_interpretation:null, ai_error:'Demonstração sem IA. Nenhum modelo foi executado.'
};
