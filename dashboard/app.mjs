import {demo, validateReport, parseReport} from './report.mjs';
const $ = id => document.getElementById(id);
const usd = n => new Intl.NumberFormat('pt-BR',{style:'currency',currency:'USD'}).format(n);
const pct = n => new Intl.NumberFormat('pt-BR',{maximumFractionDigits:1,signDisplay:'exceptZero'}).format(n)+'%';
let report = validateReport(demo);
function element(tag,text,className) { const e=document.createElement(tag); if(text!==undefined)e.textContent=text;if(className)e.className=className;return e; }
function services() {
  $('rows').replaceChildren();
  const entries=Object.entries(report.services).sort((a,b)=>b[1]-a[1]);
  const max=Math.max(1,...entries.map(e=>e[1]));
  const filtered=entries.filter(([name])=>name.toLocaleLowerCase('pt-BR').includes($('search').value.toLocaleLowerCase('pt-BR')));
  for(const [name,cost] of filtered){const row=element('tr');row.append(element('td',name),element('td',usd(cost)),element('td',Object.hasOwn(report.percentages,name)?pct(report.percentages[name]):'Não informada'));const cell=element('td');const bar=element('progress');bar.max=max;bar.value=cost;bar.setAttribute('aria-label',`${name}: ${usd(cost)}`);cell.append(bar);row.append(cell);$('rows').append(row);}
  $('empty').hidden=filtered.length>0;
}
function render(source) {
  $('source').textContent=source;$('period').textContent=report.period;$('generated').textContent='Relatório gerado em '+report.generated_at;
  $('total').textContent=usd(report.total_cost);$('largest').textContent=report.largest_service??'Nenhum';
  $('variation').textContent=report.comparison?.variation==null?'Sem comparação':pct(report.comparison.variation);
  $('previous').textContent=report.comparison?'Anterior: '+usd(report.comparison.previous_total)+' · Atual: '+usd(report.comparison.current_total):'Período anterior não disponível';
  $('count').textContent=String(report.alerts.length);$('alert-list').replaceChildren();
  for(const alert of report.alerts){const card=element('article',undefined,'alert '+alert.severity);card.append(element('strong',alert.severity==='warning'?'ATENÇÃO':'INFORMAÇÃO'),element('p',alert.message));$('alert-list').append(card);}
  if(!report.alerts.length)$('alert-list').append(element('p','Nenhum alerta neste relatório.'));
  $('ai-text').textContent=report.ai_interpretation||'Sem interpretação de IA neste relatório.';
  $('ai-status').textContent=report.ai_error||'Interpretação fornecida pelo relatório; revise as recomendações antes de agir.';
  services();
}
let importVersion=0;
$('file').addEventListener('change',async event=>{const file=event.target.files[0];if(!file)return;const version=++importVersion;$('error').hidden=true;try{if(file.size>2*1024*1024)throw Error('O limite é 2 MB por relatório.');const next=parseReport(await file.text());if(version!==importVersion)return;report=next;$('search').value='';render('Relatório importado · '+file.name);}catch(error){if(version!==importVersion)return;$('error').textContent=error.message;$('error').hidden=false;}finally{if(version===importVersion)event.target.value='';}});
$('reset').addEventListener('click',()=>{importVersion++;report=validateReport(demo);$('search').value='';$('file').value='';$('error').hidden=true;render('Demonstração · dados fictícios');});
$('search').addEventListener('input',services);
render('Demonstração · dados fictícios');
