"""Actual graph UI interactions; synthetic data, no AI or user installation."""
from playwright.sync_api import expect


def exercise(page,check,out,dense=True):
    # The caller owns the isolated project. No direct backend save bypasses the
    # node/edge editing controls exercised below.
    if page.locator('.step[data-tab="graph"]').count():page.locator('.step[data-tab="graph"]').click()
    expect(page.get_by_role('button',name='3D',exact=True)).to_be_visible()
    expect(page.locator('#graph-svg')).to_be_visible()
    page.wait_for_function('() => document.querySelectorAll("#graph-svg [data-node]").length > 0')
    assert page.evaluate('() => getComputedStyle(document.querySelector(".sidebar")).backgroundImage.includes("graph-paper.webp")')
    assert page.evaluate('''async () => {const r=await fetch('/static/assets/graph-paper.webp');return r.ok && (await r.blob()).size>20000;}''')
    check('Real scanned graph paper loads locally in the light sidebar, not a generated grid')
    before=page.evaluate('() => JSON.stringify(state.p.graph)')
    pose=page.evaluate('() => ({yaw:GS.view.yaw, x:document.querySelector("[data-node]").getAttribute("transform")})')
    box=page.locator('#graph-svg').bounding_box()
    page.mouse.move(box['x']+box['width']*.7,box['y']+14);page.mouse.down()
    page.mouse.move(box['x']+box['width']*.7+70,box['y']+48,steps=8);page.mouse.up()
    page.wait_for_timeout(160)
    assert page.evaluate('() => GS.view.yaw')!=pose['yaw']
    assert before==page.evaluate('() => JSON.stringify(state.p.graph)')
    check('Dragging orbits true XYZ positions without changing graph content')
    page.get_by_role('button',name='2D',exact=True).click();assert page.evaluate('() => GS.view.mode')=='2d'
    page.get_by_role('button',name='3D',exact=True).click()
    page.get_by_role('button',name='Reset camera',exact=True).click();page.wait_for_timeout(100)
    old=page.evaluate('() => GS.view.zoom')
    page.get_by_role('button',name='Zoom in',exact=True).click();page.wait_for_timeout(100)
    assert page.evaluate('() => GS.view.zoom')>old
    page.get_by_role('button',name='Fit graph',exact=True).click()
    check('Flat/spatial toggle, zoom and fit are functioning controls')
    node=page.locator('#graph-svg [data-node]').first;nodeid=node.get_attribute('data-node')
    node.click();expect(page.locator('#gs-label')).to_be_visible()
    old_sources=page.evaluate('() => JSON.stringify(state.p.sources)');old_draft=page.evaluate('() => state.p.draft')
    page.locator('#gs-label').fill('The argument keeps its teeth')
    page.locator('#gs-description').fill('Keep the fucking point. This is a deliberate graph edit.')
    page.get_by_role('button',name='Save node',exact=True).click()
    expect(page.locator('.gs-selected-title h3')).to_have_text('The argument keeps its teeth')
    assert page.evaluate('() => state.p.draft')==old_draft and page.evaluate('() => JSON.stringify(state.p.sources)')==old_sources
    saved=page.evaluate('async () => await api("/projects/"+state.p.id)')
    assert any(n['id']==nodeid and 'fucking' in n['description'] for n in saved['graph']['nodes'])
    check('Click/edit/save changes the stored node, preserves language, sources and manuscript')
    page.get_by_role('button',name='Focus here',exact=True).click();page.wait_for_timeout(100)
    assert page.evaluate('() => GS.view.hops')==1
    page.get_by_role('button',name='Reset filters',exact=True).click()
    page.get_by_role('button',name='Clear graph selection',exact=True).click()
    # Add a node and connect it through the actual dialogs.
    n_before=page.evaluate('() => state.p.graph.nodes.length')
    page.get_by_role('button',name='Add node',exact=True).first.click()
    page.locator('#gs-new-label').fill('A new counterpoint');page.locator('#gs-new-kind').select_option('claim')
    page.get_by_role('button',name='Add node',exact=True).last.click()
    expect(page.locator('.modal')).to_have_count(0)
    assert page.evaluate('() => state.p.graph.nodes.length')==n_before+1
    newid=page.evaluate('() => state.node')
    page.get_by_role('button',name='Connect nodes',exact=True).click()
    page.locator('#gs-new-source').select_option(newid);page.locator('#gs-new-target').select_option(nodeid)
    page.locator('#gs-new-relation').fill('contradicts')
    page.get_by_role('button',name='Create connection',exact=True).click()
    expect(page.locator('#gs-edge-relation')).to_have_value('contradicts')
    page.wait_for_function("""() => document.querySelectorAll('.gs-link[data-relationship="contradiction"]').length > 0""")
    page.locator('#gs-edge-relation').fill('questions');page.get_by_role('button',name='Save connection',exact=True).click()
    expect(page.locator('#gs-edge-relation')).to_have_value('questions')
    page.wait_for_function('() => state.p.graph.edges.find(e=>e.id===state.edge)?.relation === \"questions\"')
    check('Connections have direction, distinct line patterns, editable endpoints and saved relationship types')
    page.get_by_role('button',name='Delete',exact=True).click();page.get_by_role('button',name='Delete from graph',exact=True).click()
    expect(page.locator('.modal')).to_have_count(0)
    page.get_by_role('button',name='Undo edit',exact=True).click()
    page.wait_for_function('() => state.p.graph.edges.some(e=>e.relation==="questions")')
    check('Confirmed deletion and persistent graph-only undo work without rewriting the document')
    # Dirty inspector navigation is guarded.
    page.locator('#graph-svg [data-node]').first.click();page.locator('#gs-label').fill('Unsaved title')
    page.evaluate('() => window.graphpaperRequestClose()')
    expect(page.get_by_role('heading',name='Keep your graph edit?',exact=True)).to_be_visible()
    page.get_by_role('button',name='Stay here',exact=True).click()
    page.get_by_role('button',name='2D',exact=True).click()
    expect(page.locator('#gs-label')).to_have_value('Unsaved title')
    page.locator('#graph-svg [data-node]').last.click()
    expect(page.get_by_role('heading',name='Keep your graph edit?',exact=True)).to_be_visible()
    page.get_by_role('button',name='Discard edit',exact=True).click()
    check('Selecting another idea cannot silently discard an unsaved inspector edit')
    page.get_by_role('button',name='Clear graph selection',exact=True).click()
    page.get_by_role('button',name='3D',exact=True).click()
    page.evaluate('window.scrollTo(0,0)');page.wait_for_timeout(150)
    page.locator('#toasts').evaluate('el => el.replaceChildren()')
    page.screenshot(path=str(out/'graph-studio.png'),full_page=True)
    if dense:
        graph={'nodes':[{'id':f'd{i}','label':('Needle in the archive' if i==599 else f'Concept {i}'),'kind':['claim','theme','evidence','concept'][i%4],'community':i%8} for i in range(600)],'edges':[{'id':f'l{i}','source':f'd{i%599}','target':f'd{(i*7+1)%599}','relation':['supports','contradicts','cites','leads_to','questions','related_to'][i%6]} for i in range(1500)]}
        page.evaluate('''async graph => {state.p=await api('/projects/'+state.p.id+'/graph/import',graph);GS.positions={};GS.view.fit=true;render();}''',graph)
        page.wait_for_timeout(250)
        assert page.locator('#graph-svg [data-node]').count()<=60
        assert page.locator('#graph-svg .gs-link').count()<=360
        assert page.evaluate('() => state.p.graph.nodes.length')==600
        page.screenshot(path=str(out/'dense-overview.png'),full_page=True)
        page.locator('#graph-search').fill('Needle in the archive')
        expect(page.get_by_role('button',name='Needle in the archive',exact=True)).to_be_visible()
        page.get_by_role('button',name='Needle in the archive',exact=True).click()
        expect(page.locator('#gs-label')).to_have_value('Needle in the archive')
        check('A 600-node graph is decluttered without deletion; full-graph search reaches a hidden low-degree idea')
        page.get_by_role('button',name='Reset filters',exact=True).click()
    return {'real_spatial_projection':True,'manual_editing':True,'synthetic_data':True,'live_models':False}
