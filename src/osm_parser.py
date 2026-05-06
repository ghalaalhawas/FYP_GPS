"""
osm_parser.py - OSM data loading and parsing

Provides OSMParser class for loading street networks from OpenStreetMap.
Used by the other scripts for junction analysis.
"""

import osmnx as ox
import geopandas as gpd
import os
from pathlib import Path

class OSMParser:
    """Loads and parses OpenStreetMap road network data."""
    
    def __init__(self, place_name="Oxford, UK", network_type="drive"):
        self.place_name = place_name
        self.network_type = network_type
        self.G = None
        self.nodes = None
        self.edges = None
        
        # Configure OSMnx
        ox.settings.log_console = True
        ox.settings.use_cache = True
        
        self.data_dir = Path("data")
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_filename(self):
        return self.place_name.lower().replace(' ', '_').replace(',', '').replace('.', '')
    
    def load_network(self, force_download=False):
        """Load the street network graph. Downloads from OSM if not cached locally."""
        filename = self._get_filename()
        graphml_path = self.raw_dir / f"{filename}_network.graphml"
        
        if graphml_path.exists() and not force_download:
            print(f"Loading cached network: {graphml_path}")
            self.G = ox.load_graphml(graphml_path)
        else:
            print(f"Downloading network for: {self.place_name}")
            self.G = ox.graph_from_place(
                self.place_name,
                network_type=self.network_type
            )
            ox.save_graphml(self.G, graphml_path)
            print(f"Saved to: {graphml_path}")
        
        self.nodes, self.edges = ox.graph_to_gdfs(self.G)
        print(f"Loaded {len(self.nodes)} nodes, {len(self.edges)} edges")
        
        return self.G
    
    def get_nodes(self):
        if self.nodes is None:
            raise ValueError("Network not loaded yet - call load_network() first")
        return self.nodes
    
    def get_edges(self):
        if self.edges is None:
            raise ValueError("Network not loaded yet - call load_network() first")
        return self.edges
    
    def get_junctions(self, min_streets=3):
        """Return nodes where at least min_streets roads meet."""
        if self.nodes is None:
            raise ValueError("Network not loaded yet - call load_network() first")
        
        junctions = self.nodes[self.nodes['street_count'] >= min_streets].copy()
        print(f"Found {len(junctions)} junctions (>= {min_streets} streets)")
        return junctions
    
    def get_junction_edges(self, junction_id):
        """Get all edges connected to a junction node. Returns list of dicts."""
        if self.G is None:
            raise ValueError("Network not loaded yet - call load_network() first")
        
        in_edges = list(self.G.in_edges(junction_id, data=True))
        out_edges = list(self.G.out_edges(junction_id, data=True))
        
        all_edges = []
        seen = set()
        
        for u, v, data in in_edges + out_edges:
            edge_key = tuple(sorted([u, v]))
            if edge_key not in seen:
                seen.add(edge_key)
                # try to grab the actual road geometry (LineString) from the edges gdf
                geom = None
                try:
                    if (u, v, 0) in self.edges.index:
                        geom = self.edges.loc[(u, v, 0), 'geometry']
                    elif (v, u, 0) in self.edges.index:
                        geom = self.edges.loc[(v, u, 0), 'geometry']
                except (KeyError, TypeError):
                    pass
                all_edges.append({
                    'from': u,
                    'to': v,
                    'highway': data.get('highway', 'unknown'),
                    'maxspeed': data.get('maxspeed', None),
                    'name': data.get('name', 'Unnamed'),
                    'length': data.get('length', 0),
                    'geometry': geom,
                })
        
        return all_edges
    
    def get_road_classification(self, highway_tag):
        """Map an OSM highway tag to a numeric class (0-10, higher = bigger road)."""
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
        """Pull out a numeric speed (mph) from the OSM maxspeed tag. Returns None if unavailable."""
        if maxspeed_tag is None or maxspeed_tag == '':
            return None
        
        if isinstance(maxspeed_tag, list):
            maxspeed_tag = maxspeed_tag[0] if maxspeed_tag else None
            if maxspeed_tag is None:
                return None
        
        maxspeed_str = str(maxspeed_tag).lower()
        
        import re
        match = re.search(r'(\d+)', maxspeed_str)
        if not match:
            return None
        
        speed = int(match.group(1))
        
        # convert km/h to mph if needed
        if 'km' in maxspeed_str or 'kph' in maxspeed_str:
            speed = int(speed * 0.621371)
        
        return speed
    
    def infer_speed_limit(self, highway_tag):
        """Guess a typical UK speed limit from the road type (for when maxspeed is missing)."""
        if isinstance(highway_tag, list):
            highway_tag = highway_tag[0] if highway_tag else 'unknown'
        
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
        """Build a dict of useful info about a single junction."""
        if self.nodes is None or self.G is None:
            raise ValueError("Network not loaded yet - call load_network() first")
        
        node = self.nodes.loc[junction_id]
        edges = self.get_junction_edges(junction_id)
        
        # figure out speed limits for each connected road
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
        """Export nodes and edges as GeoJSON files."""
        filename = self._get_filename()
        
        nodes_path = self.raw_dir / f"{filename}_nodes.geojson"
        self.nodes.to_file(nodes_path, driver="GeoJSON")
        print(f"Saved nodes: {nodes_path}")
        
        edges_path = self.raw_dir / f"{filename}_edges.geojson"
        self.edges.to_file(edges_path, driver="GeoJSON")
        print(f"Saved edges: {edges_path}")
    
    def print_statistics(self):
        """Print a quick overview of the loaded network."""
        if self.G is None:
            raise ValueError("Network not loaded yet - call load_network() first")
        
        print(f"\n--- Network Stats: {self.place_name} ---")
        print(f"Nodes: {len(self.nodes)}")
        print(f"Edges: {len(self.edges)}")
        print(f"Type:  {self.network_type}")
        
        # junction breakdown
        junctions_3 = len(self.nodes[self.nodes['street_count'] == 3])
        junctions_4 = len(self.nodes[self.nodes['street_count'] == 4])
        junctions_5plus = len(self.nodes[self.nodes['street_count'] >= 5])
        
        print(f"\nJunctions:")
        print(f"  T-junctions (3-way): {junctions_3}")
        print(f"  Crossroads  (4-way): {junctions_4}")
        print(f"  Complex     (5+):    {junctions_5plus}")
        
        if 'highway' in self.edges.columns:
            print(f"\nCommon road types:")
            print(self.edges['highway'].value_counts().head())
        print()


def main():
    """Quick test of the parser."""
    print("\n--- OSM Parser Test ---\n")
    
    parser = OSMParser("Oxford, UK")
    parser.load_network()
    parser.print_statistics()
    
    junctions = parser.get_junctions(min_streets=3)
    
    # look at one junction as a sanity check
    if len(junctions) > 0:
        sample_id = junctions.index[0]
        print(f"\n--- Sample Junction ---")
        
        info = parser.get_junction_info(sample_id)
        print(f"ID: {info['id']}")
        print(f"Location: {info['location']}")
        print(f"Roads meeting: {info['street_count']}")
        print(f"Road types: {info['road_types']}")
        print(f"Speed limits: {info['speed_limits']} mph")
        print(f"Speed diff: {info['speed_differential']} mph")
        print(f"Connected roads:")
        for edge in info['edges']:
            print(f"  - {edge['name']} ({edge['highway']})")
    
    parser.save_network_data()
    print("\nDone.\n")


if __name__ == "__main__":
    main()
