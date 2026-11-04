"""Orthogonal flow connections with separate tracks for overlapping spans."""
from collections import defaultdict
import math

YES = '#19764c'
NO = '#c15b15'
FLOW = '#2868b2'
DETOURS = ('#7551a8', '#00828b', '#a44372')

def route_edges(model):
    positions = {n.id: (n.lane * 500, n.id * 210) for n in model.nodes}
    incoming = defaultdict(list)
    for index, (_, target, _) in enumerate(model.edges):
        incoming[target].append(index)
    tracks = []
    routes = []
    outer = max((x for x, _ in positions.values()), default=0) + 440
    for index, (origin, target, label) in enumerate(model.edges):
        x1,y1 = positions[origin]
        x2,y2 = positions[target]
        siblings = incoming[target]
        rank = siblings.index(index)
        offset = (rank - (len(siblings)-1)/2) * 22
        target_kind = model.nodes[target].kind
        border = abs(offset)/3.6 if target_kind == 'decision' else 50*(1-math.sqrt(max(0,1-(offset/180)**2))) if target_kind == 'terminal' else 0
        end = (x2+180+offset,y2+border)
        right_exit = label == 'No' and model.nodes[origin].kind == 'decision'
        start = (x1+360,y1+50) if right_exit else (x1+180,y1+100)
        departure = y1+128
        approach = y2-32-rank*18
        detour = not (target == origin+1 and x1 == x2 and not right_exit)
        if detour:
            low,high = sorted((start[1],end[1]))
            track = next((n for n, spans in enumerate(tracks)
                          if all(high+25 < a or low > b+25 for a,b in spans)),len(tracks))
            if track == len(tracks): tracks.append([])
            tracks[track].append((low,high))
            side = outer + track*34
            if right_exit:
                points = [start,(side,start[1]),(side,approach),(end[0],approach),end]
                label_pos = (start[0]+15,start[1]-27)
            else:
                points = [start,(start[0],departure),(side,departure),
                          (side,approach),(end[0],approach),end]
                label_pos = (start[0]+12,start[1]+2)
            color = YES if label=='Yes' else NO if label=='No' else DETOURS[track%len(DETOURS)]
        else:
            track = None
            points = [start,(start[0],departure),(end[0],departure),end]
            label_pos = (start[0]+12,start[1]+6)
            color = YES if label=='Yes' else FLOW
        routes.append({'points':points,'color':color,'label':label,'label_pos':label_pos,
                       'track':track,'origin':origin,'target':target})
    return positions, routes
