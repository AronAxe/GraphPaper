/* Pure spatial layout and projection. No GPU, network, inference, or evidence mutation. */
(function(root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.GraphScene = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function() {
  'use strict';
  const styles = {
    concept: {color:'#8ea8ff', shape:'diamond', name:'Idea'},
    theme: {color:'#a4a0ff', shape:'diamond', name:'Theme'},
    claim: {color:'#f28fc3', shape:'circle', name:'Claim'},
    source: {color:'#62b8ff', shape:'square', name:'Source'},
    evidence: {color:'#bc9cff', shape:'hexagon', name:'Evidence'},
    person: {color:'#ffbc78', shape:'hexagon', name:'Person'},
    character: {color:'#ffbc78', shape:'hexagon', name:'Character'},
    event: {color:'#f4c56c', shape:'triangle', name:'Event'},
    tension: {color:'#ff8d87', shape:'triangle', name:'Tension'},
    question: {color:'#f4c56c', shape:'triangle', name:'Question'},
    canon: {color:'#c0a2ff', shape:'square', name:'Canon'},
    cluster: {color:'#9aaaff', shape:'hexagon', name:'Cluster'}
  };
  const families = [
    {family:'Support',color:'#55d7bb',dash:'',match:/support|confirm|evidence|reinforce|enabl/},
    {family:'Challenge',color:'#ff8e9a',dash:'8 5',match:/contradict|oppose|challeng|conflict|refut|limit|tension/},
    {family:'Citation',color:'#66b9ff',dash:'',match:/cit|reference|source|document|mention/},
    {family:'Sequence / cause',color:'#f5be6d',dash:'3 4',match:/cause|lead|result|before|after|depend|require|consequence|fund/},
    {family:'Analogy / style',color:'#ba9aff',dash:'10 4 2 4',match:/analog|contrast|style|influenc|similar|express/},
    {family:'Other',color:'#9aa9c5',dash:'2 5',match:/.*/}
  ];
  const nodeStyle = kind => styles[String(kind).toLowerCase()] || styles.concept;
  const edgeStyle = relation => families.find(f=>f.match.test(String(relation).toLowerCase()));
  const clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
  function layout(graph, spacing=1) {
    const result=Object.create(null), buckets=new Map();
    for(const n of graph.nodes) {
      const key=String(n.community ?? 0);
      if(!buckets.has(key))buckets.set(key,[]);
      buckets.get(key).push(n);
    }
    const groups=[...buckets.entries()].sort(([a],[b])=>a.localeCompare(b));
    const size=Math.max(1,graph.nodes.length), groupRadius=groups.length>1?180+Math.sqrt(size)*12:0;
    groups.forEach(([key,nodes],gi)=>{
      nodes.sort((a,b)=>String(a.id).localeCompare(String(b.id)));
      const angle=gi*2.399963, radius=groupRadius*Math.sqrt((gi+1)/groups.length);
      const cx=Math.cos(angle)*radius, cy=Math.sin(angle)*radius*.72;
      nodes.forEach((n,i)=>{
        const a=i*2.399963, r=nodes.length===1?0:58*Math.sqrt(i+.6);
        result[n.id]={x:(cx+Math.cos(a)*r)*spacing,y:(cy+Math.sin(a)*r)*spacing,z:Math.sin(a*.73+gi)*Math.min(160,r*.38)*spacing};
      });
    });
    const positions=Object.values(result);
    if(positions.length){
      const cx=(Math.min(...positions.map(p=>p.x))+Math.max(...positions.map(p=>p.x)))/2;
      const cy=(Math.min(...positions.map(p=>p.y))+Math.max(...positions.map(p=>p.y)))/2;
      for(const p of positions){p.x-=cx;p.y-=cy;}
    }
    return result;
  }
  function project(p, c={}) {
    const yaw=c.flat?0:(c.yaw||0), pitch=c.flat?0:(c.pitch||0), z=c.flat?0:(p.z||0);
    const x1=p.x*Math.cos(yaw)+z*Math.sin(yaw), z1=-p.x*Math.sin(yaw)+z*Math.cos(yaw);
    const y1=p.y*Math.cos(pitch)-z1*Math.sin(pitch), depth=p.y*Math.sin(pitch)+z1*Math.cos(pitch);
    const focal=c.focal||1600, perspective=c.flat?1:focal/Math.max(focal*.2,focal+depth);
    const scale=clamp(c.zoom||1,.08,8)*perspective;
    return {x:550+(c.panX||0)+x1*scale,y:360+(c.panY||0)+y1*scale,scale,depth};
  }
  function dragDelta(dx,dy,p,c) {
    const scale=project(p,c).scale, x=dx/scale, y=dy/scale, yaw=c.flat?0:c.yaw||0,pitch=c.flat?0:c.pitch||0;
    return {x:Math.cos(yaw)*x+Math.sin(yaw)*Math.sin(pitch)*y,y:Math.cos(pitch)*y,z:Math.sin(yaw)*x-Math.cos(yaw)*Math.sin(pitch)*y};
  }
  function view(graph, opt={}) {
    const query=String(opt.query||'').toLocaleLowerCase().trim(), all=new Set(graph.nodes.map(n=>n.id));
    let edges=graph.edges.filter(e=>all.has(e.source)&&all.has(e.target));
    const degree=new Map();
    for(const e of edges){degree.set(e.source,(degree.get(e.source)||0)+1);degree.set(e.target,(degree.get(e.target)||0)+1);}
    let ids=null;
    if(opt.focus&&all.has(opt.focus)) {
      ids=new Set([opt.focus]);
      const adj=new Map();
      for(const e of edges){if(!adj.has(e.source))adj.set(e.source,[]);if(!adj.has(e.target))adj.set(e.target,[]);adj.get(e.source).push(e.target);adj.get(e.target).push(e.source);}
      let frontier=[opt.focus];
      for(let i=0;i<(opt.hops||1);i++){const next=[];for(const a of frontier)for(const b of adj.get(a)||[])if(!ids.has(b)){ids.add(b);next.push(b);}frontier=next;}
    }
    const members=opt.members?new Set(opt.members):null;
    let nodes=graph.nodes.filter(n=>(!ids||ids.has(n.id))&&(!members||members.has(n.id))&&(!opt.kind||n.kind===opt.kind)&&(!query||[n.label,n.description,n.kind,n.id].some(t=>String(t||'').toLocaleLowerCase().includes(query))));
    if(opt.relation){edges=edges.filter(e=>e.relation===opt.relation);const related=new Set(edges.flatMap(e=>[e.source,e.target]));nodes=nodes.filter(n=>related.has(n.id));}
    const matched=nodes.length;
    let visible=new Set(nodes.map(n=>n.id));edges=edges.filter(e=>visible.has(e.source)&&visible.has(e.target));
    if(opt.cluster&&nodes.length>40&&!query&&!ids) {
      const buckets=new Map(), mapping=new Map();
      for(const n of nodes){const key=String(n.community??0)+' / '+(n.kind||'concept');if(!buckets.has(key))buckets.set(key,[]);buckets.get(key).push(n);}
      const maxSize=Math.max(24,Math.ceil(nodes.length/36)), clusters=[];
      for(const [key,bucket] of buckets){bucket.sort((a,b)=>String(a.id).localeCompare(String(b.id)));for(let i=0;i<bucket.length;i+=maxSize){const part=bucket.slice(i,i+maxSize),id='atlas_cluster_'+clusters.length;const n={id,label:nodeStyle(part[0].kind).name+' · '+part.length,kind:'cluster',community:clusters.length,description:part.slice(0,4).map(n=>n.label).join(' · '),members:part.map(n=>n.id)};clusters.push(n);for(const p of part)mapping.set(p.id,id);}}
      const joined=new Map();for(const e of edges){const a=mapping.get(e.source),b=mapping.get(e.target);if(a===b)continue;const key=JSON.stringify([a,b,e.relation]);if(!joined.has(key))joined.set(key,{...e,id:'atlas_edge_'+joined.size,source:a,target:b,count:0});joined.get(key).count++;}
      return {nodes:clusters,edges:[...joined.values()],hidden:0,matched,total:graph.nodes.length,clustered:true};
    }
    const limit=opt.limit||350;
    if(nodes.length>limit)nodes=nodes.slice().sort((a,b)=>(b.id===opt.selected?1e6:degree.get(b.id)||0)-(a.id===opt.selected?1e6:degree.get(a.id)||0)).slice(0,limit);
    visible=new Set(nodes.map(n=>n.id));edges=edges.filter(e=>visible.has(e.source)&&visible.has(e.target));
    return {nodes,edges,hidden:matched-nodes.length,matched,total:graph.nodes.length,clustered:false};
  }
  function path(a,b,bend=0) {
    const dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy);
    if(d<1)return `M ${a.x} ${a.y-10} C ${a.x+65} ${a.y-75}, ${a.x+85} ${a.y+55}, ${a.x+10} ${a.y+10}`;
    const k=bend||18;
    return `M ${a.x} ${a.y} Q ${(a.x+b.x)/2-dy/d*k} ${(a.y+b.y)/2+dx/d*k} ${b.x} ${b.y}`;
  }
  function labelSlots(nodes, points, selected, allLabels=false) {
    const boxes=[],accepted=new Set();
    const ordered=nodes.slice().sort((a,b)=>(b.id===selected?1e6:0)-(a.id===selected?1e6:0)||points[a.id].depth-points[b.id].depth);
    for(const n of ordered){const p=points[n.id], w=Math.min(180,Math.max(74,String(n.label).length*6.2));const box={x:p.x-w/2,y:p.y+21,w,h:34};
      if(p.x<0||p.x>1100||p.y<0||p.y>720)continue;
      if(n.id===selected||allLabels||(!boxes.some(b=>box.x<b.x+b.w+8&&box.x+box.w+8>b.x&&box.y<b.y+b.h+6&&box.y+box.h+6>b.y)&&accepted.size<45)){accepted.add(n.id);boxes.push(box);}
    }
    return accepted;
  }
  return {styles,families,nodeStyle,edgeStyle,layout,project,dragDelta,view,path,labelSlots,clamp};
});
