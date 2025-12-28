"""Knowledge Graph extraction and visualization service."""

import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import json


@dataclass
class Entity:
    """A node in the knowledge graph."""
    id: str
    label: str
    type: str  # person, organization, concept, location, event, technology
    description: Optional[str] = None
    importance: float = 0.5  # 0-1, affects node size
    properties: Dict[str, Any] = None

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'label': self.label,
            'type': self.type,
            'description': self.description,
            'importance': self.importance,
            'properties': self.properties or {}
        }


@dataclass
class Relationship:
    """An edge in the knowledge graph."""
    source: str
    target: str
    type: str  # relates_to, is_part_of, created_by, uses, etc.
    label: str
    strength: float = 0.5  # 0-1, affects edge thickness
    properties: Dict[str, Any] = None

    def to_dict(self) -> Dict:
        return {
            'source': self.source,
            'target': self.target,
            'type': self.type,
            'label': self.label,
            'strength': self.strength,
            'properties': self.properties or {}
        }


@dataclass
class KnowledgeGraph:
    """Complete knowledge graph structure."""
    nodes: List[Entity]
    edges: List[Relationship]
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict:
        return {
            'nodes': [n.to_dict() for n in self.nodes],
            'edges': [e.to_dict() for e in self.edges],
            'metadata': self.metadata or {}
        }


class KnowledgeGraphExtractor:
    """
    Extract knowledge graphs from text using NLP patterns.

    Creates beautiful, animated graph data for visualization.
    """

    # Entity type patterns
    ENTITY_PATTERNS = {
        'person': [
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b(?:\s+(?:said|wrote|created|invented|discovered|founded))',
            r'(?:Dr\.|Mr\.|Mrs\.|Ms\.|Prof\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'(?:CEO|CTO|founder|author|researcher|scientist|engineer)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ],
        'organization': [
            r'\b((?:Google|Microsoft|Apple|Amazon|Meta|OpenAI|Anthropic|Tesla|NVIDIA|IBM|Intel|Oracle|Salesforce|Adobe|Netflix|Uber|Airbnb|SpaceX|NASA|MIT|Stanford|Harvard|Berkeley|Oxford|Cambridge))\b',
            r'\b([A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*)*)\s+(?:Inc\.|Corp\.|LLC|Ltd\.|Company|University|Institute)',
        ],
        'technology': [
            r'\b((?:Python|JavaScript|TypeScript|React|Vue|Angular|Node\.js|FastAPI|Django|Flask|TensorFlow|PyTorch|Kubernetes|Docker|AWS|Azure|GCP|PostgreSQL|MongoDB|Redis|GraphQL|REST|API|LLM|GPT|BERT|Transformer|Neural Network|Machine Learning|Deep Learning|AI|Artificial Intelligence|NLP|Computer Vision|Blockchain|IoT|5G|Quantum Computing))\b',
        ],
        'concept': [
            r'\b((?:algorithm|architecture|framework|model|system|method|approach|technique|strategy|pattern|principle|theory|hypothesis|paradigm|protocol|standard))\b',
        ],
        'location': [
            r'\b((?:United States|USA|UK|China|Japan|Germany|France|India|Canada|Australia|Silicon Valley|New York|San Francisco|London|Tokyo|Berlin|Paris|Beijing|Seattle|Boston))\b',
        ],
    }

    # Relationship patterns
    RELATIONSHIP_PATTERNS = [
        (r'(\w+)\s+(?:is|are)\s+(?:a|an|the)\s+(\w+)', 'is_a'),
        (r'(\w+)\s+(?:uses?|utilizes?)\s+(\w+)', 'uses'),
        (r'(\w+)\s+(?:creates?|generates?|produces?)\s+(\w+)', 'creates'),
        (r'(\w+)\s+(?:is\s+)?(?:part\s+of|belongs?\s+to)\s+(\w+)', 'part_of'),
        (r'(\w+)\s+(?:depends?\s+on|requires?)\s+(\w+)', 'depends_on'),
        (r'(\w+)\s+(?:connects?\s+to|links?\s+to|integrates?\s+with)\s+(\w+)', 'connects_to'),
        (r'(\w+)\s+(?:is\s+)?(?:based\s+on|built\s+on)\s+(\w+)', 'based_on'),
        (r'(\w+)\s+(?:enables?|allows?|supports?)\s+(\w+)', 'enables'),
        (r'(\w+)\s+(?:improves?|enhances?|optimizes?)\s+(\w+)', 'improves'),
        (r'(\w+)\s+(?:and|with|alongside)\s+(\w+)', 'relates_to'),
    ]

    # Entity type colors (for frontend)
    ENTITY_COLORS = {
        'person': '#FF6B6B',      # Coral red
        'organization': '#4ECDC4', # Teal
        'technology': '#45B7D1',   # Sky blue
        'concept': '#96CEB4',      # Sage green
        'location': '#FFEAA7',     # Soft yellow
        'event': '#DDA0DD',        # Plum
        'default': '#A0A0A0',      # Gray
    }

    def __init__(self):
        self.entity_cache = {}

    def extract_entities(self, text: str) -> List[Entity]:
        """Extract entities from text."""
        entities = {}
        entity_counts = defaultdict(int)

        for entity_type, patterns in self.ENTITY_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    entity_name = match.group(1).strip()
                    entity_id = self._make_id(entity_name)

                    entity_counts[entity_id] += 1

                    if entity_id not in entities:
                        entities[entity_id] = Entity(
                            id=entity_id,
                            label=entity_name,
                            type=entity_type,
                            importance=0.5,
                            properties={'color': self.ENTITY_COLORS.get(entity_type, self.ENTITY_COLORS['default'])}
                        )

        # Adjust importance based on mention frequency
        max_count = max(entity_counts.values()) if entity_counts else 1
        for entity_id, count in entity_counts.items():
            if entity_id in entities:
                entities[entity_id].importance = 0.3 + (0.7 * count / max_count)

        return list(entities.values())

    def extract_relationships(self, text: str, entities: List[Entity]) -> List[Relationship]:
        """Extract relationships between entities."""
        relationships = []
        entity_ids = {e.id for e in entities}
        entity_labels = {e.label.lower(): e.id for e in entities}

        # Check for co-occurrence (entities mentioned close together)
        sentences = re.split(r'[.!?]', text)

        for sentence in sentences:
            sentence_lower = sentence.lower()
            found_entities = []

            for label, entity_id in entity_labels.items():
                if label in sentence_lower:
                    found_entities.append(entity_id)

            # Create relationships between co-occurring entities
            for i, source in enumerate(found_entities):
                for target in found_entities[i+1:]:
                    if source != target:
                        relationships.append(Relationship(
                            source=source,
                            target=target,
                            type='relates_to',
                            label='related',
                            strength=0.5
                        ))

        # Use pattern matching for specific relationships
        for pattern, rel_type in self.RELATIONSHIP_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                source_text = match.group(1).lower()
                target_text = match.group(2).lower()

                source_id = entity_labels.get(source_text)
                target_id = entity_labels.get(target_text)

                if source_id and target_id and source_id != target_id:
                    relationships.append(Relationship(
                        source=source_id,
                        target=target_id,
                        type=rel_type,
                        label=rel_type.replace('_', ' '),
                        strength=0.7
                    ))

        # Deduplicate and merge relationships
        return self._dedupe_relationships(relationships)

    def _dedupe_relationships(self, relationships: List[Relationship]) -> List[Relationship]:
        """Remove duplicate relationships and merge strengths."""
        seen = {}

        for rel in relationships:
            key = (rel.source, rel.target, rel.type)
            reverse_key = (rel.target, rel.source, rel.type)

            if key in seen:
                seen[key].strength = min(1.0, seen[key].strength + 0.1)
            elif reverse_key in seen:
                seen[reverse_key].strength = min(1.0, seen[reverse_key].strength + 0.1)
            else:
                seen[key] = rel

        return list(seen.values())

    def _make_id(self, text: str) -> str:
        """Create a valid ID from text."""
        return re.sub(r'[^a-zA-Z0-9]', '_', text.lower())[:50]

    async def extract_from_text(self, text: str, title: str = "") -> KnowledgeGraph:
        """
        Extract a complete knowledge graph from text.

        Args:
            text: Source text to analyze
            title: Optional title for the graph

        Returns:
            KnowledgeGraph with nodes and edges
        """
        # Extract entities and relationships
        entities = self.extract_entities(text)
        relationships = self.extract_relationships(text, entities)

        # Filter orphan entities (no relationships)
        connected_ids = set()
        for rel in relationships:
            connected_ids.add(rel.source)
            connected_ids.add(rel.target)

        # Keep top entities even if orphaned
        top_entities = sorted(entities, key=lambda e: e.importance, reverse=True)[:5]
        top_ids = {e.id for e in top_entities}

        connected_entities = [e for e in entities if e.id in connected_ids or e.id in top_ids]

        return KnowledgeGraph(
            nodes=connected_entities,
            edges=relationships,
            metadata={
                'title': title,
                'node_count': len(connected_entities),
                'edge_count': len(relationships),
                'entity_types': list(set(e.type for e in connected_entities))
            }
        )

    async def extract_from_documents(
        self,
        documents: List[Dict],
        query: str = ""
    ) -> KnowledgeGraph:
        """
        Extract knowledge graph from multiple documents.

        Combines entities and relationships across documents.
        """
        all_text = query + "\n\n"

        for doc in documents:
            content = doc.get('content', '')
            title = doc.get('title', '')
            all_text += f"{title}\n{content}\n\n"

        return await self.extract_from_text(all_text, title=query or "Knowledge Graph")


# Graph layout algorithms for frontend
class GraphLayoutCalculator:
    """Calculate optimal graph layouts for visualization."""

    @staticmethod
    def force_directed_initial(nodes: List[Dict], width: int = 800, height: int = 600) -> List[Dict]:
        """
        Calculate initial positions for force-directed layout.

        The frontend will animate from these positions.
        """
        import math
        import random

        n = len(nodes)
        if n == 0:
            return nodes

        # Arrange in a circle initially
        center_x, center_y = width / 2, height / 2
        radius = min(width, height) * 0.35

        for i, node in enumerate(nodes):
            angle = (2 * math.pi * i) / n
            node['x'] = center_x + radius * math.cos(angle)
            node['y'] = center_y + radius * math.sin(angle)
            # Add some randomness
            node['x'] += random.uniform(-20, 20)
            node['y'] += random.uniform(-20, 20)

        return nodes

    @staticmethod
    def hierarchical_layout(
        nodes: List[Dict],
        edges: List[Dict],
        width: int = 800,
        height: int = 600
    ) -> List[Dict]:
        """Calculate hierarchical layout based on connections."""
        # Calculate node levels based on incoming edges
        incoming = defaultdict(int)
        for edge in edges:
            incoming[edge['target']] += 1

        # Assign levels
        levels = defaultdict(list)
        for node in nodes:
            level = incoming.get(node['id'], 0)
            levels[level].append(node)

        # Position nodes
        num_levels = max(levels.keys()) + 1 if levels else 1
        level_height = height / (num_levels + 1)

        for level, level_nodes in levels.items():
            y = level_height * (level + 1)
            level_width = width / (len(level_nodes) + 1)

            for i, node in enumerate(level_nodes):
                node['x'] = level_width * (i + 1)
                node['y'] = y

        return nodes


# Singleton instance
knowledge_graph_extractor = KnowledgeGraphExtractor()
graph_layout = GraphLayoutCalculator()
