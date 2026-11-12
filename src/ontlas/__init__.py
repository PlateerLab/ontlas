"""Ontlas: one domain ontology definition, executed on whatever store or reasoner a deployment has."""
from ontlas.model import ModelError, Ontology

__version__ = "0.20.1"
__all__ = ["Ontology", "ModelError", "__version__"]
