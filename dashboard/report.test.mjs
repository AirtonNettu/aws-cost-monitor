import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {demo, parseReport, validateReport} from './report.mjs';
test('imports compatible JSON and keeps zero variation',()=>{const r=structuredClone(demo);r.comparison.variation=0;assert.equal(parseReport(JSON.stringify(r)).comparison.variation,0);});
test('preserves credits, percentages above 100 and null comparison',()=>{const r={...demo,total_cost:-4,percentages:{'Amazon EC2':120},comparison:null};assert.equal(validateReport(r).total_cost,-4);});
test('accepts empty-cost reports without AI',()=>{assert.equal(validateReport({...demo,total_cost:0,services:{},percentages:{},largest_service:null,has_positive_cost:false,comparison:null,alerts:[],ai_error:null}).largest_service,null);});
test('rejects malformed, incomplete and oversized JSON',()=>{for(const text of ['{','{}','null',' '.repeat(2*1024*1024+1)])assert.throws(()=>parseReport(text));});
test('rejects invalid numeric values and alerts',()=>{for(const change of [{total_cost:Infinity},{services:{EC2:-1}},{comparison:{previous_total:0,current_total:0,variation:'0'}},{alerts:[{type:'growth',severity:'html',message:'bad'}]}])assert.throws(()=>validateReport({...demo,...change}));});
test('treats untrusted strings as data',()=>{const r=parseReport(JSON.stringify({...demo,ai_interpretation:'<img src=x onerror=alert(1)>'}));assert.equal(r.ai_interpretation,'<img src=x onerror=alert(1)>');assert.doesNotMatch(readFileSync(new URL('./app.mjs',import.meta.url),'utf8'),/innerHTML|insertAdjacentHTML|eval\(/);});
test('imports actual Python-generated report without network',()=>{
  const code=`from src.analysis.cost_analyzer import analyze_costs, compare_periods
from src.reports.report_generator import build_report_json
from src.analysis.finops_rules import generate_alerts
costs=[{'start':'2026-09-01','end':'2026-10-01','groups':[{'Keys':['EC2'],'Metrics':{'UnblendedCost':{'Amount':'100'}}},{'Keys':['Credit'],'Metrics':{'UnblendedCost':{'Amount':'-25'}}}]}]
a=analyze_costs(costs)
print(build_report_json(costs,a,compare_periods(costs),alerts=generate_alerts(a,None)))`;
  const result=spawnSync('uv',['run','--frozen','python','-c',code],{cwd:new URL('../',import.meta.url),encoding:'utf8'});
  assert.equal(result.status,0,result.stderr);
  const r=parseReport(result.stdout);assert.equal(r.total_cost,75);assert.equal(r.services.EC2,100);assert.equal(r.percentages.EC2,133.3);assert.equal(r.comparison,null);
});
