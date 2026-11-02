#!/usr/bin/env python3
"""Compare actual production object transitions with the frozen Windows driver."""
from behavior_suite import rows
from mesa_runtime import require

def verify_lifetime(reference,directory,case):
    original=rows(reference/'behavior-events.csv');native=rows(directory/'lifetime-events.csv')
    # Compare original vessel callback entry/exit and host notification order.
    # UI-only callbacks and render-driven animation are outside external-view scope.
    callbacks={f'vessel.{action}.{edge}' for action in ('setcaps','load','postcreation','pre','post') for edge in ('before','after')}
    phases=callbacks|{'module.pre','module.post','module.create','module.delete','module.focus',
        'input.create','input.delete','input.focus','input.attach','input.detach',
        'world.update.before','world.update.after','world.finalise.before','world.finalise.after',
        'time.end.before','time.end.after','app.frame.end'}
    def selected(events):
        first=next(i for i,r in enumerate(events) if r['phase']=='world.update.before')
        return [r for r in events[first:] if r['phase'] in phases]
    original_events,native_events=selected(original),selected(native)
    def order(events):
        return [(r['frame'],r['tick'],r['phase'],r['object'],r['detail']) for r in events]
    left,right=order(original_events),order(native_events)
    if left!=right:
        first=next((i for i,(a,b) in enumerate(zip(left,right)) if a!=b),min(len(left),len(right)))
        raise ValueError(f'Original object/callback ordering differs at {first}: {left[first:first+3]} versus {right[first:first+3]} (counts {len(left)}/{len(right)})')
    for a,b in zip(original_events,native_events):
        require(float(a['seconds'])==float(b['seconds']),'Callback elapsed time differs from the Windows reference')
        require(abs(float(a['mjd'])-float(b['mjd']))<=1e-10,'Callback epoch exceeds the frozen MJD budget')
    state=rows(directory/'flight-state.csv');children=[r for r in state if r['object']=='Child']
    require(children and all(r['class']=='ShuttlePB' for r in children),'Actual source-built child vessel missing')
    visuals=rows(directory/'visual-events.csv');child=[r['event'] for r in visuals if r['object']=='Child']
    require(child==['register','unregister'],'Child visual not registered/released exactly once')
    draws=rows(directory/'object-draws-all.csv')
    require(any(r['object']=='Child' and int(r['mesh_draw_calls'])>0 for r in draws),'Child actual stock geometry was never drawn')
    releases=[r['phase'] for r in native if r['object']=='Child' and r['phase'].startswith(('module.interface.release','module.library.close'))]
    require(releases==['module.interface.release.before','module.interface.release.after','module.library.close.before','module.library.close.after'],'Child native interface/library release order incomplete')
    manifest=[r for r in rows(directory/'visual-meshes.csv') if r['object']=='Child']
    require(len(manifest)==1 and manifest[0]['class']=='ShuttlePB' and manifest[0]['module_version']=='2' and manifest[0]['thrusters']=='16' and all(int(manifest[0][k])>0 for k in ('groups','materials','textures')),'Actual child module/mesh/material/texture identity missing')
    return dict(original_order=True,compared_events=len(left),child_samples=len(children),actual_child_mesh_drawn=True,visual_lifetime=True,module_lifetime=True)
