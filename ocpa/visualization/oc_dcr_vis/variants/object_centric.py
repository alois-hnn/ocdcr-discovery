"""
OCDCR graph visualizer.
Extends basic visualization with support for objects, spawn and sync relations.
"""

from graphviz import Digraph
from typing import Set, Dict
from ocpa.objects.oc_dcr_graph.obj import OCDCRGraph, OCDCRRelation, Event
from ocpa.visualization.oc_dcr_vis.variants.utils_viz import cluster_to_same_cluster, is_ancestor_or_self, get_edge_attrs, initialize_graph, add_events

def add_edge(relation: OCDCRRelation, graph: Digraph, 
             head_group_relations: Dict[Event, Set[Event]], 
             tail_group_relations: Dict[Event, Set[Event]] = None) -> None:
    """
    Add an edge to the graph, handling object-centric specific features.
    
    Args:
        relation: The relation to add
        graph: The Digraph to modify
        head_group_relations: Nested groups relation for the source event/ both events if tail_group_relations is None
        tail_group_relations: Nested groups relation for the target event (optional)
    """
    source = relation.start_event
    target = relation.target_event
    
    edge_attrs = get_edge_attrs(relation.type)

    # Handle quantifiers if present
    if hasattr(relation, "quantifier_head"):
        edge_attrs["taillabel"] = "∀" if relation.quantifier_head else ""
    if hasattr(relation, "quantifier_tail"):
        edge_attrs["headlabel"] += (" ∀" if relation.quantifier_tail else "")

    # Handle edges to groups for target (either using tail_group_relations or head_group_relations if tail_group_relations is None)
    if tail_group_relations:
        if target.isGroup and target in tail_group_relations and tail_group_relations[target]:
            edge_attrs["lhead"] = f"cluster_{target.activity}"
    elif target.isGroup and target in head_group_relations and head_group_relations[target]:
        edge_attrs["lhead"] = f"cluster_{target.activity}"
    
    # Handle edges from groups for source
    if source.isGroup and source in head_group_relations and head_group_relations[source]:
        edge_attrs["ltail"] = f"cluster_{source.activity}"

    graph.edge(source.activity, target.activity, **edge_attrs)

def apply(ocdcr: OCDCRGraph, parameters: Dict = None) -> Digraph:
    """
    Main function to visualize an object-centric DCR graph.
    
    Args:
        ocdcr: The OCDCR graph to visualize
        parameters: Visualization parameters
        
    Returns:
        The generated Digraph visualization
    """
    graph, image_format = initialize_graph(parameters)
    cluster_entry_points = {}  # Tracks first activity in each object cluster for cluster edges

    add_events(ocdcr.events, graph, ocdcr.nestedgroups, ocdcr.nestedgroups, ocdcr.marking, parameters)

    # Visualize object clusters
    for obj_id, obj in ocdcr.objects.items():
        cluster_name = f"cluster_{obj_id}"
        with graph.subgraph(name=cluster_name) as subgraph:
            if obj.spawn is None:
                color = "#E1F8E6"
            else:
                color = "#E5EFF7"
            subgraph.attr(label=f"Object: {obj_id}", style="rounded,filled", fillcolor=color)
            add_events(list(obj.events), subgraph, obj.nestedgroups, obj.nestedgroups,obj.marking, parameters)
    
            if list(obj.events):  # Check if there are any events
                cluster_entry_points[obj_id] = list(obj.events)[0].activity
            
            # Add relations within this object
            for relation in obj.relations:
                source = relation.start_event
                target = relation.target_event
                if (source.isGroup or target.isGroup) and (
                    source == target or 
                    is_ancestor_or_self(source, target) or 
                    is_ancestor_or_self(target, source)
                ):
                    cluster_to_same_cluster(subgraph, relation, obj.nestedgroups)
                else:
                    add_edge(relation, subgraph, obj.nestedgroups)

    # Add spawn relations between activities and objects
    if hasattr(ocdcr, 'spawn_relations'):
        for spawn_act, obj_id in ocdcr.spawn_relations.items():
            if obj_id in cluster_entry_points:
                graph.edge(
                    spawn_act.activity,
                    cluster_entry_points[obj_id],  
                    lhead=f"cluster_{obj_id}",      # Point to object cluster
                    color="#000080",                # dark blue for spawns
                    arrowhead="normal",
                    headlabel="*", 
                    labelfontcolor="#000080",
                )

    # Add top level relations and synchronization relations
    for rel in getattr(ocdcr, 'relations', set()) | getattr(ocdcr, 'sync_relations', set()):
        # Determine which object contains the start and end events
        # Get group relations for start and end events
        head_groups = (ocdcr.objects[ocdcr.activityToObject[rel.start_event]].nestedgroups 
                    if rel.start_event not in ocdcr.events else {})
        tail_groups = (ocdcr.objects[ocdcr.activityToObject[rel.target_event]].nestedgroups 
                    if rel.target_event not in ocdcr.events else {})
        
        add_edge(rel, graph, head_groups, tail_groups)

    # Final formatting
    graph.attr(overlap='false')
    graph.format = image_format.replace("html", "plain-text")
    return graph