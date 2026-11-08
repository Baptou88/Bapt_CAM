from abc import ABC, abstractmethod


class ToolRepository(ABC):
    """Interface abstraite pour les dépôts d'outils"""

    @abstractmethod
    def get_all_tools(self):
        """Récupère tous les outils"""
        pass

    @abstractmethod
    def get_tool_by_id(self, tool_id):
        """Récupère un outil par son ID"""
        pass

    @abstractmethod
    def add_tool(self, tool):
        """Ajoute un outil"""
        pass

    @abstractmethod
    def update_tool(self, tool):
        """Met à jour un outil"""
        pass

    @abstractmethod
    def delete_tool(self, tool_id):
        """Supprime un outil"""
        pass
