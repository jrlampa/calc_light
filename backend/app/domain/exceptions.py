class ElectricalEngineError(Exception):
    """Base category for electrical engine exceptions."""
    pass

class CableNotFoundError(ElectricalEngineError):
    """Raised when a conductor is not found in the catalog."""
    pass

class TransformerNotFoundError(ElectricalEngineError):
    """Raised when a transformer power rating is not found."""
    pass
