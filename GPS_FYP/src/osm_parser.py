"""
Basic OSM Data Parser
Week 5 - January 27 - February 2, 2026

This module provides a clean interface for loading and parsing OSM data.
Used by other scripts as a foundation for junction analysis.

Usage:
    from osm_parser import OSMParser
    
    parser = OSMParser("Oxford, UK")
    network = parser.load_network()
    junctions = parser.get_junctions()
"""

import osmnx as ox
import geopandas as gpd
import os
from pathlib import Path

class OSMParser:
    """Parse and load OpenStreetMap network data."""
    
    def __init__(self, place_name="Oxford, UK", network_type="drive"):
        """
        Initialize OSM parser.
        
        Args:
            place_name (str): Name of place to load
            network_type (str): Type of network ('drive', 'walk', 'bike', 'all')
        """
        self.place_name = place_name
        self.network_type = network_type
        self.G = None
        self.nodes = None
        self.edges = None
        
        # Configure OSMnx
        ox.settings.log_console = True
        ox.settings.use_cache = True
        
        # Set up data paths
        self.data_dir = Path("data")
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        
        # Create directories if they don't exist
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_filename(self):
        """Generate filename from place name."""
        return self.place_name.lower().replace(' ', '_').replace(',', '').replace('.', '')
    
    def load_network(self, force_download=False):
        """
        Load street network. Downloads if not cached.
        
        Args:
            force_download (bool): Force fresh download even if cached
        
        Returns:
            NetworkX graph
        """
        filename = self._get_filename()
        graphml_path = self.raw_dir / f"{filename}_network.graphml"
        
        if graphml_path.exists() and not force_download:
            print(f"📂 Loading cached network: {graphml_path}")
            self.G = ox.load_graphml(graphml_path)
        else:
            print(f"⬇️  Downloading network: {self.place_name}")
            self.G = ox.graph_from_place(
                self.place_name,
                network_type=self.network_type
            )
            # Save for future use
            ox.save_graphml(self.G, graphml_path)
            print(f"💾 Saved network: {graphml_path}")
        
        # Convert to GeoDataFrames
        self.nodes, self.edges = ox.graph_to_gdfs(self.G)
        
        print(f"✅ Loaded {len(self.nodes)} nodes, {len(self.edges)} edges")
        
        return self.G
    
    def get_nodes(self):
        """Get nodes GeoDataFrame."""
        if self.nodes is None:
            raise ValueError("Network not loaded. Call load_network() first.")
        return self.nodes
    
    def get_edges(self):
        """Get edges GeoDataFrame."""
        if self.edges is None:
            raise ValueError("Network not loaded. Call load_network() first.")
        return self.edges
    
    def get_junctions(self, min_streets=3):
        """
        Get junctions (nodes where multiple roads meet).
        
        Args:
            min_streets (int): Minimum number of streets to classify as junction
        
        Returns:
            GeoDataFrame of junctions
        """
        if self.nodes is None:
            raise ValueError("Network not loaded. Call load_network() first.")
        
        junctions = self.nodes[self.nodes['street_count'] >= min_streets].copy()
        print(f"🔍 Found {len(junctions)} junctions (>= {min_streets} streets)")
        
        return junctions
    
    def get_junction_edges(self, junction_id):
        """
        Get all edges connected to a specific junction.
        
        Args:
            junction_id: OSM node ID
        
        Returns:
            List of edge dictionaries
        """
        if self.G is None:
            raise ValueError("Network not loaded. Call load_network() first.")
        
        # Get incoming and outgoing edges
        in_edges = list(self.G.in_edges(junction_id, data=True))
        out_edges = list(self.G.out_edges(junction_id, data=True))
        
        # Combine and deduplicate
        all_edges = []
        seen = set()
        
        for u, v, data in in_edges + out_edges:
            edge_key = tuple(sorted([u, v]))
            if edge_key not in seen:
                seen.add(edge_key)
                all_edges.append({
                    'from': u,
                    'to': v,
                    'highway': data.get('highway', 'unknown'),
                    'maxspeed': data.get('maxspeed', None),
                    'name': data.get('name', 'Unnamed'),
                    'length': data.get('length', 0)
                })
        
        return all_edges
    
    def get_road_classification(self, highway_tag):
        """
        Convert OSM highway tag to numeric classification.
        Higher number = more major road.
        
        Args:
            highway_tag (str or list): OSM highway tag value
        
        Returns:
            int: Road classification score (0-10)
        """
        # Handle list of tags (take first)
        if isinstance(highway_tag, list):
            highway_tag = highway_tag[0] if highway_tag else 'unknown'
        
        classification = {
            'motorway': 10,
            'trunk': 9,
            'primary': 8,
            'secondary': 6,
            'tertiary': 4,
            'unclassified': 3,
            'residential': 2,
            'service': 1,
            'unknown': 0
        }
        
        return classification.get(highway_tag, 0)
    
    def extract_speed_limit(self, maxspeed_tag):
        """
        Extract numeric speed limit from OSM maxspeed tag.
        
        Args:
            maxspeed_tag: OSM maxspeed value (e.g., "30 mph", "50", None)
        
        Returns:
            int: Speed in mph, or None if not available
        """
        if maxspeed_tag is None or maxspeed_tag == '':
            return None
        
        # Handle list
        if isinstance(maxspeed_tag, list):
            maxspeed_tag = maxspeed_tag[0] if maxspeed_tag else None
            if maxspeed_tag is None:
                return None
        
        # Convert to string
        maxspeed_str = str(maxspeed_tag).lower()
        
        # Extract number
        import re
        match = re.search(r'(\d+)', maxspeed_str)
        if not match:
            return None
        
        speed = int(match.group(1))
        
        # Convert km/h to mph if needed
        if 'km' in maxspeed_str or 'kph' in maxspeed_str:
            speed = int(speed * 0.621371)
        
        return speed
    
    def infer_speed_limit(self, highway_tag):
        """
        Infer typical speed limit based on road classification.
        Used when maxspeed tag is missing.
        
        Args:
            highway_tag (str): OSM highway tag
        
        Returns:
            int: Estimated speed in mph
        """
        # Handle list
        if isinstance(highway_tag, list):
            highway_tag = highway_tag[0] if highway_tag else 'unknown'
        
        # UK typical speeds
        typical_speeds = {
            'motorway': 70,
            'trunk': 70,
            'primary': 60,
            'secondary': 50,
            'tertiary': 40,
            'unclassified': 40,
            'residential': 30,
            'service': 20,
        }
        
        return typical_speeds.get(highway_tag, 30)
    
    def get_junction_info(self, junction_id):
        """
        Get comprehensive information about a junction.
        
        Args:
            junction_id: OSM node ID
        
        Returns:
            dict: Junction information
        """
        if self.nodes is None or self.G is None:
            raise ValueError("Network not loaded. Call load_network() first.")
        
        # Get node info
        node = self.nodes.loc[junction_id]
        
        # Get connected edges
        edges = self.get_junction_edges(junction_id)
        
        # Analyze roads
        road_types = []
        speed_limits = []
        
        for edge in edges:
            road_types.append(edge['highway'])
            speed = self.extract_speed_limit(edge['maxspeed'])
            if speed is None:
                speed = self.infer_speed_limit(edge['highway'])
            speed_limits.append(speed)
        
        info = {
            'id': junction_id,
            'location': (node.geometry.y, node.geometry.x),  # lat, lon
            'street_count': node['street_count'],
            'edges': edges,
            'road_types': road_types,
            'speed_limits': speed_limits,
            'max_speed': max(speed_limits) if speed_limits else None,
            'min_speed': min(speed_limits) if speed_limits else None,
            'speed_differential': max(speed_limits) - min(speed_limits) if speed_limits else 0
        }
        
        return info
    
    def save_network_data(self):
        """Save network data to GeoJSON files."""
        filename = self._get_filename()
        
        # Save nodes
        nodes_path = self.raw_dir / f"{filename}_nodes.geojson"
        self.nodes.to_file(nodes_path, driver="GeoJSON")
        print(f"💾 Saved nodes: {nodes_path}")
        
        # Save edges
        edges_path = self.raw_dir / f"{filename}_edges.geojson"
        self.edges.to_file(edges_path, driver="GeoJSON")
        print(f"💾 Saved edges: {edges_path}")
    
    def print_statistics(self):
        """Print network statistics."""
        if self.G is None:
            raise ValueError("Network not loaded. Call load_network() first.")
        
        print("\n" + "="*60)
        print(f"NETWORK STATISTICS: {self.place_name}")
        print("="*60)
        print(f"Total nodes: {len(self.nodes)}")
        print(f"Total edges: {len(self.edges)}")
        print(f"Network type: {self.network_type}")
        
        # Junction breakdown
        junctions_3 = len(self.nodes[self.nodes['street_count'] == 3])
        junctions_4 = len(self.nodes[self.nodes['street_count'] == 4])
        junctions_5plus = len(self.nodes[self.nodes['street_count'] >= 5])
        
        print(f"\nJunction breakdown:")
        print(f"  T-junctions (3-way): {junctions_3}")
        print(f"  Crossroads (4-way): {junctions_4}")
        print(f"  Complex (5+ way): {junctions_5plus}")
        
        # Road types
        if 'highway' in self.edges.columns:
            print(f"\nMost common road types:")
            print(self.edges['highway'].value_counts().head())
        
        print("="*60 + "\n")


def main():
    """Test the OSM parser."""
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║  OSM Data Parser - Week 5                                ║
    ║  Basic OSM data loading and analysis                     ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    # Create parser
    parser = OSMParser("Oxford, UK")
    
    # Load network
    parser.load_network()
    
    # Print statistics
    parser.print_statistics()
    
    # Get junctions
    junctions = parser.get_junctions(min_streets=3)
    
    # Analyze a sample junction
    if len(junctions) > 0:
        sample_id = junctions.index[0]
        print(f"\n{'='*60}")
        print(f"SAMPLE JUNCTION ANALYSIS")
        print(f"{'='*60}\n")
        
        info = parser.get_junction_info(sample_id)
        print(f"Junction ID: {info['id']}")
        print(f"Location: {info['location']}")
        print(f"Number of roads: {info['street_count']}")
        print(f"Road types: {info['road_types']}")
        print(f"Speed limits: {info['speed_limits']} mph")
        print(f"Speed differential: {info['speed_differential']} mph")
        print(f"\nConnected roads:")
        for edge in info['edges']:
            print(f"  - {edge['name']} ({edge['highway']})")
    
    # Save data
    parser.save_network_data()
    
    print("\n✅ OSM Parser test complete!")
    print("Parser ready to use in other scripts.\n")


if __name__ == "__main__":
    main()
