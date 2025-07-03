from typing import Optional
from dataclasses import dataclass

@dataclass(unsafe_hash=True)
class Event:
	"""
	Represents an event in a DCR graph.

	Attributes:
		activity: The activity name of the event
		isGroup: Whether this event is a group and contains other events
		parent: The parent event if this event is part of a group, None otherwise
	"""
	activity: str
	isGroup: bool = False
	parent: Optional['Event'] = None


