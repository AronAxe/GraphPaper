/* Pure, dependency-free spatial graph geometry. Shared by the UI and Node tests. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.GraphMath=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const MAX_NODES=180,MAX_EDGES=360;
 const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
 const family={support:['supports','support','reinforces','corroborates','backs','supported_by','can_support','seeks_to_support'],contradiction:['contradicts','contradiction','opposes','conflicts_with','challenges','refutes'],citation:['cites','citation','references','quotes','sourced_from','draws_from'],causal:['causes','leads_to','enables','produces','results_in','depends_on','can_produce'],style:['influences_style','style_influence','expresses','uses_style','style'],question:['questions','raises_question','open_question','asks','uncertain','can_question']};
 function relation(value){const r=String(value||'').trim().toLowerCase().replace(/[\s-]+/g,'_');for(const [k,list] of Object.entries(family))if(list.includes(r))return k;return 'association';}
 function kind(value){const k=String(value||'concept').toLowerCase();if(['source','document','paper','article','reference'].includes(k))return 'source';if(['claim','argument','hypothesis','finding'].includes(k))return 'claim';if(['evidence','quote','quotation','data','fact'].includes(k))return 'evidence';if(['theme','topic','concept','idea'].includes(k))return k==='theme'||k==='topic'?'theme':'concept';if(['angle','question','risk','tension','conflict'].includes(k))return 'angle';if(['person','character','organization'].includes(k))return 'character';if(['section','draft','draft_section','scene','event'].includes(k))return 'section';if(['voice','style','habit','rhythm','diction','rule','canon'].includes(k))return 'style';return 'concept';}
 function visible(g,o={}){
  const limit=clamp(Number(o.limit)||60,10,MAX_NODES),search=String(o.search||'').trim().toLowerCase();
  const all=new Map(g.nodes.map(n=>[n.id,n])),degree=new Map(),adj=new Map();
  for(const e of g.edges){degree.set(e.source,(degree.get(e.source)||0)+1);degree.set(e.target,(degree.get(e.target)||0)+1);if(!adj.has(e.source))adj.set(e.source,new Set());if(!adj.has(e.target))adj.set(e.target,new Set());adj.get(e.source).add(e.target);adj.get(e.target).add(e.source);}
  const neighborhood=new Set();if(o.focus&&all.has(o.focus)){neighborhood.add(o.focus);let front=[o.focus];for(let i=0;i<(Number(o.hops)||1);i++){const next=[];for(const id of front)for(const n of adj.get(id)||[])if(!neighborhood.has(n)){neighborhood.add(n);next.push(n);}front=next;}}
  const matched=new Set();if(search){for(const n of g.nodes)if([n.label,n.kind,n.description].join(' ').toLowerCase().includes(search))matched.add(n.id);for(const e of g.edges)if([e.relation,e.description].join(' ').toLowerCase().includes(search)){matched.add(e.source);matched.add(e.target);}}
  const path=new Set(o.path||[]),pins=new Set(o.pins||[]);
  let candidates=g.nodes.filter(n=>(!o.kind||kind(n.kind)===o.kind)&&(!o.focus||neighborhood.has(n.id))&&(!search||matched.has(n.id)));
  const rank=n=>(n.id===o.selected?1e7:0)+(path.has(n.id)?1e6:0)+(pins.has(n.id)?1e5:0)+(degree.get(n.id)||0);
  candidates.sort((a,b)=>rank(b)-rank(a)||String(a.id).localeCompare(String(b.id)));
  const nodes=candidates.slice(0,limit),ids=new Set(nodes.map(n=>n.id));
  const links=g.edges.filter(e=>ids.has(e.source)&&ids.has(e.target)&&(!o.relation||relation(e.relation)===o.relation));
  links.sort((a,b)=>((b.source===o.selected||b.target===o.selected)?1:0)-((a.source===o.selected||a.target===o.selected)?1:0));
  return {nodes,edges:links.slice(0,MAX_EDGES),degree,matching:candidates.length,availableEdges:links.length,total:g.nodes.length};
 }
 function layout(nodes,edges){
  const sorted=nodes.slice().sort((a,b)=>String(a.id).localeCompare(String(b.id))),positions=Object.create(null);
  const communities=new Set(sorted.map(n=>n.community||0)),useCommunity=communities.size>1;
  const groups=new Map();for(const n of sorted){const key=useCommunity?'c'+(n.community||0):kind(n.kind);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(n);}
  const keys=[...groups.keys()].sort(),centers={},ring=keys.length>1?Math.max(180,Math.sqrt(nodes.length)*36):0;
  keys.forEach((key,j)=>{const theta=j*2*Math.PI/keys.length-.5;centers[key]={x:Math.cos(theta)*ring*1.2,y:Math.sin(theta)*ring*.85,z:(j-(keys.length-1)/2)*65};groups.get(key).forEach((n,i)=>{const t=i*2.399963,r=55*Math.sqrt(i+1),c=centers[key];positions[n.id]={x:c.x+Math.cos(t)*r,y:c.y+Math.sin(t)*r,z:c.z+Math.sin(t*1.31)*70};});});
  for(let step=0;step<64;step++){
   const forces=Object.create(null);for(const n of sorted)forces[n.id]={x:-positions[n.id].x*.002,y:-positions[n.id].y*.002};
   for(let i=0;i<sorted.length;i++)for(let j=i+1;j<sorted.length;j++){const a=positions[sorted[i].id],b=positions[sorted[j].id];let dx=a.x-b.x,dy=a.y-b.y,d=Math.max(20,Math.hypot(dx,dy));if(!dx&&!dy)dx=1;const f=Math.min(16,12500/(d*d));forces[sorted[i].id].x+=dx/d*f;forces[sorted[i].id].y+=dy/d*f;forces[sorted[j].id].x-=dx/d*f;forces[sorted[j].id].y-=dy/d*f;}
   for(const e of edges){const a=positions[e.source],b=positions[e.target];if(!a||!b||e.source===e.target)continue;const dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy)||1,f=clamp((d-190)*.006,-1,2);forces[e.source].x+=dx/d*f;forces[e.source].y+=dy/d*f;forces[e.target].x-=dx/d*f;forces[e.target].y-=dy/d*f;}
   for(const n of sorted){positions[n.id].x+=clamp(forces[n.id].x,-6,6);positions[n.id].y+=clamp(forces[n.id].y,-6,6);}
  }
  return positions;
 }
 function project(p,c){
  const zoom=clamp(Number(c.zoom)||1,.12,5);if(c.mode==='2d')return {x:p.x*zoom+(c.panX||0),y:p.y*zoom+(c.panY||0),z:0,scale:1};
  const cy=Math.cos(c.yaw||0),sy=Math.sin(c.yaw||0),cp=Math.cos(c.pitch||0),sp=Math.sin(c.pitch||0);
  const x=p.x*cy+(p.z||0)*sy,z=-p.x*sy+(p.z||0)*cy,y=p.y*cp-z*sp,depth=p.y*sp+z*cp;
  const scale=clamp(1200/(Math.max(400,1200+depth)),.35,2.5);
  return {x:x*scale*zoom+(c.panX||0),y:y*scale*zoom+(c.panY||0),z:depth,scale};
 }
 function move(p,dx,dy,c){const s=project(p,c).scale*(c.zoom||1);dx/=s;dy/=s;if(c.mode==='2d')return {...p,x:p.x+dx,y:p.y+dy};const cy=Math.cos(c.yaw),sy=Math.sin(c.yaw),cp=Math.cos(c.pitch),sp=Math.sin(c.pitch);return {x:p.x+dx*cy+dy*sp*sy,y:p.y+dy*cp,z:(p.z||0)+dx*sy-dy*sp*cy};}
 function curve(a,b,index=0){if(Math.hypot(b.x-a.x,b.y-a.y)<1)return {d:`M ${a.x+9} ${a.y-8} C ${a.x+72} ${a.y-74},${a.x-65} ${a.y-74},${a.x-9} ${a.y-8}`,x:a.x,y:a.y-57};const dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy),nx=-dy/d,ny=dx/d,offset=20+index*24,sx=a.x+dx/d*17,sy=a.y+dy/d*17,tx=b.x-dx/d*21,ty=b.y-dy/d*21,cx=(a.x+b.x)/2+nx*offset,cy=(a.y+b.y)/2+ny*offset;return {d:`M ${sx} ${sy} Q ${cx} ${cy} ${tx} ${ty}`,x:(a.x+b.x)/2+nx*offset/2,y:(a.y+b.y)/2+ny*offset/2};}
 return {MAX_NODES,MAX_EDGES,clamp,relation,kind,visible,layout,project,move,curve};
});
