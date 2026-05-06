"""
01_download_osm_data.py

Downloads the street network for a given area from OpenStreetMap.
Using Oxford, UK as the initial test region.
"""

import osmnx as ox
import matplotlib.pyplot as plt
import os

# Configure OSMnx
ox.settings.log_console = True
ox.settings.use_cache = True

def download_network(place_name="Oxford, UK", network_type="drive"):
    """Download the road network for a place. Returns a NetworkX graph."""
    print(f"\nDownloading street network for: {place_name}")
    print(f"Network type: {network_type}\n")
    
    try:
        G = ox.graph_from_place(place_name, network_type=network_type)
        print(f"Download successful!")
        print(f"Nodes (intersections): {len(G.nodes())}")
        print(f"Edges (road segments): {len(G.edges())}")
        return G
    except Exception as e:
        print(f"Error downloading data: {e}")
        return None


def save_network(G, place_name="Oxford"):
    """Save network as GraphML + GeoJSON for nodes and edges."""
    os.makedirs("data/raw", exist_ok=True)
    
    graphml_path = f"data/raw/{place_name.lower().replace(' ', '_')}_network.graphml"
    ox.save_graphml(G, graphml_path)
    print(f"Saved GraphML: {graphml_path}")
    
    nodes, edges = ox.graph_to_gdfs(G)
    
    nodes_path = f"data/raw/{place_name.lower().replace(' ', '_')}_nodes.geojson"
    nodes.to_file(nodes_path, driver="GeoJSON")
    print(f"Saved nodes: {nodes_path}")
    
    edges_path = f"data/raw/{place_name.lower().replace(' ', '_')}_edges.geojson"
    edges.to_file(edges_path, driver="GeoJSON")
    print(f"Saved edges: {edges_path}")
    
    return nodes, edges


def visualize_network(G, place_name="Oxford", save=True):
    """Plot the street network and optionally save as PNG."""
    print(f"\nCreating visualization...")
    
    # Create figure
    fig, ax = ox.plot_graph(
        G,
        node_size=0,
        edge_linewidth=0.5,
        edge_color='#999999',
        bgcolor='white',
        show=False,
        close=False
    )
    
    ax.set_title(f"{place_name} Street Network", fontsize=16, fontweight='bold')
    
    if save:
        os.makedirs("data/visualizations", exist_ok=True)
        output_path = f"data/visualizations/{place_name.lower().replace(' ', '_')}_network.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved: {output_path}")
    
    plt.show()


def print_sample_data(nodes, edges, n=5):
    """Print a few rows of nodes/edges so we can see what the data looks like."""
    print(f"\n--- Sample Node Data (first {n}) ---")
    print(nodes.head(n))
    print(f"\nColumns available: {list(nodes.columns)}")
    
    print(f"\n--- Sample Edge Data (first {n}) ---")
    print(edges.head(n))
    print(f"\nColumns available: {list(edges.columns)}")


def main():
    print("\n--- OSM Data Download ---\n")
    
    place_name = "Oxford, UK"
    
    G = download_network(place_name)
    if G is None:
        print("Failed to download network.")
        return
    
    nodes, edges = save_network(G, place_name)
    print_sample_data(nodes, edges)
    visualize_network(G, place_name)
    
    print("\nAll done. Check data/raw/ and data/visualizations/ for output.\n")


if __name__ == "__main__":
    main()
