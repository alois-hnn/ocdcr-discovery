from enum import Enum
from typing import Tuple
from dataclasses import dataclass, field

from .event import Event

class RelationTyps(Enum):
	"""
	Enumeration of possible relation types in DCR graphs between two events.

	Attributes:
		I: IncludesTo - event includes another event -> target will be included when source executes
		E: ExcludesTo - event excludes another event -> target will be excluded when source executes
		R: ResponseTo  - event is a response to another event -> target must eventually execute after source
		C: ConditionsFor - event is a condition for another event -> source must have executed for target to be enabled
	"""
	I = 'includesTo'
	E = 'excludesTo'
	R = 'responseTo'
	C = 'conditionsFor'

@dataclass(unsafe_hash=True)
class DCRRelation:
	"""
	Represents a relation between two events in a DCR graph.

	Attributes:
		start_event: The source event of the relation
		target_event: The target event of the relation
		type: The type of relation from RelationTyps
	"""
	start_event: Event
	target_event: Event
	type: RelationTyps

	def get_quantifiers(self) -> Tuple[bool, bool]:
		"""
		Getter for quantifier values
		Returns False for both quantifiers by default for DCR relations, overridden in OCDCRRelation

		Returns:
			tuple with quantifier values
		"""
		if isinstance(self, OCDCRRelation):
			return self.quantifier_head, self.quantifier_tail
		return False, False

@dataclass(unsafe_hash=True)
class OCDCRRelation(DCRRelation):
    """
    Extended DCR relation for OCDCR graphs with quantifiers.

    Attributes:
        quantifier_head: Whether there is a universal quantifier to target event
        quantifier_tail: Whether there is a universal quantifier from start event
    """

    quantifier_head: bool = field(default=False)
    quantifier_tail: bool = field(default=False)

    # guarantess that every DCRRelation has a default value for quantifier
    def __post_init__(self):
        if not hasattr(self, 'quantifier_head') or self.quantifier_head is None:
            self.quantifier_head = False
        if not hasattr(self, 'quantifier_tail') or self.quantifier_tail is None:
            self.quantifier_tail = False

    def get_quantifiers(self) -> Tuple[bool, bool]:
        """
        Getter for quantifier values

        Returns:
            tuple with quantifier values (head_quantifier, tail_quantifier)
        """
        return self.quantifier_head, self.quantifier_tail