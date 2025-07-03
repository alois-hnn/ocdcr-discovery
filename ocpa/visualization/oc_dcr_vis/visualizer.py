from copy import deepcopy
from pm4py.visualization.common import gview
from pm4py.visualization.common import save as gsave

from ocpa.visualization.oc_dcr_vis import basic as basic
from ocpa.visualization.oc_dcr_vis import object_centric as oc
from ocpa.objects.oc_dcr_graph import OCDCRGraph

def apply(dcr, parameters=None):
    dcr = deepcopy(dcr)
    if isinstance(dcr, OCDCRGraph):
        return oc.apply(dcr, parameters)
    else:
        return basic.apply(dcr, parameters)

def save(gviz, output_file_path):
    """
    Save the diagram

    Parameters
    -----------
    gviz
        GraphViz diagram
    output_file_path
        Path where the GraphViz output should be saved
    """
    gsave.save(gviz, output_file_path)


def view(gviz):
    """
    View the diagram

    Parameters
    -----------
    gviz
        GraphViz diagram
    """
    return gview.view(gviz)