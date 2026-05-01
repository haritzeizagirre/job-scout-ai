from .base import BaseAdapter
from .justremote import JustRemoteAdapter
from .nodesk import NoDeskAdapter
from .workingnomads import WorkingNomadsAdapter
from .generic_ai import GenericAIAdapter

class AdapterFactory:
    @staticmethod
    def get_adapter(url: str) -> BaseAdapter:
        if "justremote.co" in url.lower():
            print("=> Using JustRemoteAdapter")
            return JustRemoteAdapter()
        elif "nodesk.co" in url.lower():
            print("=> Using NoDeskAdapter")
            return NoDeskAdapter()
        elif "workingnomads.com" in url.lower():
            print("=> Using WorkingNomadsAdapter")
            return WorkingNomadsAdapter()
        else:
            print("=> Using GenericAIAdapter")
            return GenericAIAdapter()
