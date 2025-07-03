"""
Shared utilities for DCR graph visualization.
Contains common functions used by both basic and object-centric visualizers.
"""
from graphviz import Digraph
from typing import Set, Dict, Tuple
from pm4py.util import exec_utils
from ocpa.objects.oc_dcr_graph import DCRRelation, Event, RelationTyps, DCRMarking
import tempfile

# Temporary file for graphviz output
filename = tempfile.NamedTemporaryFile(suffix=".gv")
filename.close()

def initialize_graph(parameters: Dict = None) -> Tuple[Digraph, str]:
    """
    Initialize a Graphviz Digraph with default or provided parameters.
    
    Args:
        parameters: Dictionary of visualization parameters including:
            - format: Output format (default: 'png')
            - set_rankdir: Graph direction (default: 'LR' for left-to-right)
            - font_size: Font size for nodes (default: 12)
            - bgcolor: Background color (default: 'white')
    
    Returns:
        Tuple containing:
            - Initialized Digraph object
            - Image format string
    """
    # Get parameters or use defaults
    image_format = exec_utils.get_param_value("format", parameters, "png")
    set_rankdir = exec_utils.get_param_value("set_rankdir", parameters, 'LR')
    font_size = exec_utils.get_param_value("font_size", parameters, "12")
    bgcolor = exec_utils.get_param_value("bgcolor", parameters, "white")

    # Create and configure the graph
    graph = Digraph("", filename=filename.name, engine='dot', 
                  graph_attr={
                      'bgcolor': bgcolor,
                      'rankdir': set_rankdir,
                      'compound': "true",  # Allows edges between clusters
                      'size': '60!'       # Fixed size
                  },
                  node_attr={
                      'shape': 'egg'       # Default node shape
                  }, 
                  edge_attr={
                      'arrowsize': '0.7',  # Arrow size
                      'labelfontsize':'10' # Edge label font size
                  })
    
    return graph, image_format

def getNodeLabel(event:Event, marking:DCRMarking) -> str:
    headlabel = event.activity + "   "

    if event in marking.executed:
        headlabel += " [E]"

    if event in marking.included:
        headlabel += " [I]"

    if event in marking.pending:
        headlabel += " [P]"

    return headlabel

def add_node(graph: Digraph, event: Event, group_relations: Dict[Event, Set[Event]], marking:DCRMarking,
             parameters: Dict = None) -> None:
    """
    Add a node or group of nodes to the graph.
    
    Args:
        graph: The Digraph to add nodes to
        event: The event to add (could be a single event or a group)
        group_relations: Dictionary mapping group events to their members
        marking: Marking of the node
        parameters: Visualization parameters (for font size)
    """
    nodelabel= getNodeLabel(event,marking)
    if not event.isGroup:
        # Add regular event node
        graph.node(
            name=event.activity, 
            label=nodelabel,
            style='solid',
            font_size=exec_utils.get_param_value("font_size", parameters, "12")
        )
    else:
        # Create a cluster for group events
        cluster_name = f"cluster_{event.activity}"
        with graph.subgraph(name=cluster_name) as subgraph:
            # Configure group appearance
            subgraph.attr(
                label=f"Group: {nodelabel}",
                style="rounded,filled",
                fillcolor="#F5F5DC",  # Beige color for groups
            )
            # Add invisible center point for the group
            subgraph.node(event.activity, event.activity, 
                        shape='point', width='0.8', 
                        color='', fillcolor='transparent',
                        style='invis')
            # Recursively add all group members
            if event in group_relations:
                for act in group_relations[event]:
                    add_node(subgraph, act, group_relations, marking,parameters)

def get_edge_attrs(relation_type: RelationTyps) -> Dict:
    """
    Get visualization attributes for different relation types.
    
    Args:
        relation_type: The type of DCR relation
        
    Returns:
        Dictionary of Graphviz attributes for the edge
    """
    return {
        RelationTyps.I: {  # Include relation
            "color": "#30A627",  # Green
            "fontcolor": "#30A627",
            "arrowhead": "normal", 
            "headlabel": "+"  # + symbol for include
        },
        RelationTyps.E: {  # Exclude relation
            "color": "#FC0C1B",  # Red
            "fontcolor": "#FC0C1B",
            "arrowhead": "normal", 
            "headlabel": "%"  # % symbol for exclude
        },
        RelationTyps.R: {  # Response relation
            "color": "#2993FC",  # Blue
            "fontcolor": "#2993FC",
            "arrowhead": "normal",
            "arrowtail": "dot",
            "dir": "both",  # Bidirectional
            "headlabel": ""
        },
        RelationTyps.C: {  # Condition relation
            "color": "#FFA500",  # Orange
            "fontcolor": "#FFA500",
            "arrowhead": "dotnormal", 
            "headlabel": ""
        }
    }[relation_type]

def is_ancestor_or_self(node: Event, other: Event) -> bool:
    """
    Check if one event is an ancestor of another in the group hierarchy.
    
    Args:
        node: The potential ancestor node
        other: The potential descendant node
        
    Returns:
        True if node is ancestor of other or same node, False otherwise
    """
    current = node
    while current is not None:
        if current == other:
            return True
        current = current.parent
    return False

def cluster_to_same_cluster(graph: Digraph, relation: DCRRelation, 
                           groupRelation: Dict[Event, Set[Event]]) -> None:
    """
    Handle edges between nodes in the same cluster or hierarchy.
    Uses an invisible bridge node to properly render the edge.
    
    Args:
        graph: The Digraph to modify
        relation: The relation to visualize
        groupRelation: Dictionary of group memberships
    """
    source = relation.start_event
    target = relation.target_event

    # Create invisible bridge node
    bridge_id = f"bridge_{relation.start_event.activity}_{relation.target_event.activity}"
    graph.node(bridge_id, shape="point", width="0", style="invis")
    
    # First segment: from source to bridge
    edge_attrs = get_edge_attrs(relation.type)
    if hasattr(relation, "quantifier_head"):
        edge_attrs["taillabel"] = "∀" if relation.quantifier_head else ""
    
    if source.isGroup and source in groupRelation and groupRelation[source]:
        edge_attrs["ltail"] = f"cluster_{source.activity}"

    # Make first segment invisible
    edge_attrs["arrowhead"] = "none"
    edge_attrs["headlabel"] = ""
    graph.edge(source.activity, bridge_id, **edge_attrs)

    # Second segment: from bridge to target
    edge_attrs = get_edge_attrs(relation.type)
    if hasattr(relation, "quantifier_tail"):
        edge_attrs["headlabel"] += (" ∀" if relation.quantifier_tail else "")
    if target.isGroup and target in groupRelation and groupRelation[target]:
        edge_attrs["lhead"] = f"cluster_{target.activity}"
    graph.edge(bridge_id, target.activity, **edge_attrs)

def add_events(events: list, graph: Digraph, group_relations: Dict[Event, Set[Event]], nestedgroups: Dict[Event, Set[Event]], marking:DCRMarking, parameters: Dict = None) -> None:
    """
    Process and add a list of events to the graph, handling group hierarchies.
    
    Args:
        events: List of events to process
        graph: The Digraph to add nodes to
        group_relations: Current dictionary of group relationships
        nestedgroups: Dictionary of nested group memberships
        parameters: Visualization parameters
    """
    eventnodes = set()
    for event in events:
        if event not in eventnodes:
            # Walk up the hierarchy to find the top-level parent
            while event.parent is not None:
                event = event.parent
                if event in nestedgroups:
                    eventnodes.update(nestedgroups.get(event, set()))
            
            eventnodes.add(event)
            
            # If this is a group, add all its members
            if event.isGroup and event in nestedgroups:
                eventnodes.update(nestedgroups.get(event, set()))
            
            # Add the node (or group) to the graph
            add_node(graph, event, group_relations,marking, parameters)


        