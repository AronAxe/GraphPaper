"""Real UI interactions and persistence; synthetic projects only, no model calls."""
from playwright.sync_api import expect


def exercise(page, check, out):
    original=page.evaluate('() => state.p?.id || null')
    page.evaluate("async () => {const p=await api('/demo',{mode:'nonfiction'});await setProject(p,'graph');}")
    expect(page.locator('#graph-svg .atlas-node')).to_have_count(18)
    response=page.request.get(page.url.split('/#')[0].rstrip('/')+'/static/graph-paper.jpg')
    assert response.ok and response.body()[:2]==b'\xff\xd8'
    assert len(response.body())>10000
    assert 'graph-paper.jpg' in page.locator('.sidebar').evaluate('(el)=>getComputedStyle(el).backgroundImage')
    assert page.locator('.sidebar').evaluate('(el)=>getComputedStyle(el).backgroundColor')=='rgb(243, 240, 231)'
    check('Paper sidebar uses a bundled real scan; workspace uses the new ink palette')
    assert len(set(page.locator('[data-node]').evaluate_all('(els)=>els.map(e=>e.dataset.depth)')))>10
    assert len(set(page.locator('.atlas-edge-wrap>path:first-child').evaluate_all('(els)=>els.map(e=>e.getAttribute("stroke"))')))>=2
    check('Nodes occupy 3D coordinates and relationship families have distinct line colors')
    node=page.locator('#graph-svg [data-node]').first
    nid=node.get_attribute('data-node')
    before=page.evaluate('() => JSON.parse(JSON.stringify(state.p))')
    node.click()
    expect(page.locator('#atlas-edit-form')).to_be_visible()
    page.screenshot(path=str(out/'atlas-dark.png'),full_page=True)
    page.locator('#atlas-item-label').fill('An argument with teeth')
    page.locator('#atlas-item-description').fill('Keep the fucking bite. Do not turn the judgment into a question.')
    page.get_by_role('button',name='Save changes',exact=True).click()
    page.wait_for_function('(id)=>state.p.graph.nodes.find(n=>n.id===id)?.label==="An argument with teeth"',arg=nid)
    saved=page.evaluate('async()=>await api("/projects/"+state.p.id)')
    for key in ['draft','sources','angles','outline','usage','voice_profile']:
        assert saved[key]==before[key]
    edited=next(n for n in saved['graph']['nodes'] if n['id']==nid)
    assert 'fucking bite' in edited['description']
    check('Click-to-edit persists titles and notes without changing writing, voice, sources or token usage')
    page.get_by_role('button',name='Undo last graph edit',exact=True).click()
    page.wait_for_function('(g)=>JSON.stringify(state.p.graph)===JSON.stringify(g)',arg=before['graph'])
    check('Undo restores the saved graph independently of the manuscript')
    page.get_by_role('button',name='Add node',exact=True).click()
    page.locator('#atlas-new-label').fill('A new objection')
    page.locator('#atlas-new-kind').select_option('question')
    page.locator('.modal').get_by_role('button',name='Add node',exact=True).click()
    expect(page.locator('.modal')).to_have_count(0)
    page.wait_for_function('() => state.p.graph.nodes.length===19')
    added=page.evaluate('()=>state.node')
    page.get_by_role('button',name='Connect nodes',exact=True).click()
    page.locator('#atlas-from').select_option(added)
    page.locator('#atlas-to').select_option(nid)
    page.locator('#atlas-link-relation').fill('contradicts')
    page.get_by_role('button',name='Save connection',exact=True).click()
    expect(page.locator('.modal')).to_have_count(0)
    eid=page.evaluate('()=>state.edge')
    page.get_by_role('button',name='Clear selection',exact=True).click()
    edge=page.locator(f'[data-edge="{eid}"]')
    edge.focus();edge.press('Enter')
    expect(page.locator('#atlas-item-label')).to_have_value('contradicts')
    page.locator('#atlas-item-label').fill('supports')
    page.get_by_role('button',name='Save changes',exact=True).click()
    page.wait_for_function('(id)=>state.p.graph.edges.find(e=>e.id===id).relation==="supports"',arg=eid)
    check('Create nodes, connect them, select a relationship and persist its new type')
    page.get_by_role('button',name='Clear selection',exact=True).click()
    before_transform=page.locator(f'[data-node="{nid}"]').get_attribute('transform')
    page.locator('#graph-svg').focus();page.keyboard.press('ArrowRight')
    page.wait_for_function('([id,old])=>document.querySelector(`[data-node="${id}"]`).getAttribute("transform")!==old',arg=[nid,before_transform])
    z=page.evaluate('()=>atlasState().camera.zoom')
    page.get_by_role('button',name='Zoom in',exact=True).click()
    assert page.evaluate('()=>atlasState().camera.zoom')>z
    page.get_by_role('button',name='2D',exact=True).click()
    assert page.evaluate('()=>atlasState().camera.flat') is True
    page.get_by_role('button',name='3D',exact=True).click()
    assert page.evaluate('()=>atlasState().camera.flat') is False
    check('Orbit changes perspective; zoom and the 2D/3D switch operate on the live graph')
    page.locator(f'[data-node="{nid}"]').click()
    page.get_by_role('button',name='Focus neighborhood',exact=True).click()
    assert page.locator('#graph-svg [data-node]').count()<19
    check('Neighborhood focus removes unrelated visual clutter')
    page.get_by_role('button',name='Reset view',exact=True).click()
    page.evaluate("async () => {const p=await api('/projects',{title:'Dense graph regression'});const nodes=Array.from({length:800},(_,i)=>({id:'dense_'+i,label:'Dense idea '+String(i).padStart(4,'0'),kind:i%3?'concept':'claim',community:i%12}));const edges=Array.from({length:799},(_,i)=>({id:'de_'+i,source:'dense_'+i,target:'dense_'+(i+1),relation:i%2?'supports':'contradicts'}));const q=await api('/projects/'+p.id+'/graph/import',{nodes,edges});await setProject(q,'graph');}")
    page.wait_for_function('()=>atlasState().view?.clustered===true')
    view=page.evaluate('()=>atlasState().view')
    assert sum(len(n.get('members',[])) for n in view['nodes'])==800
    assert len(view['nodes'])<80
    page.screenshot(path=str(out/'atlas-dense.png'),full_page=True)
    page.locator('#graph-svg [data-node]').first.click()
    assert page.locator('#graph-svg [data-node]').count()<100
    page.get_by_role('button',name='Reset view',exact=True).click()
    page.locator('#graph-search').fill('Dense idea 0799')
    expect(page.locator('#graph-svg [data-node]')).to_have_count(1)
    check('800-node overview accounts for every node; expand clusters and find nodes beyond old display caps')
    if original:
        page.evaluate("async id=>{const p=await api('/projects/'+id);await setProject(p,'graph');}",original)
    return {'model_calls':0,'dense_nodes':800,'persistent_edits':True,'spatial_projection':True}
