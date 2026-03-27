"""
02_detect_junctions.py

Finds and classifies road junctions from OSM data.
Identifies T-junctions, crossroads, and complex junctions,
and assigns preliminary danger scores.
"""

import osmnx as ox
import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from shapely.geometry import Point
import os

def load_network(place_name="Oxford, UK"):
    """Load the network from a cached graphml file, or download it."""
    filename = place_name.lower().replace(' ', '_').replace(',', '')
    graphml_path = f"data/raw/{filename}_network.graphml"
    
    if os.path.exists(graphml_path):
        print(f"Loading network from: {graphml_path}")
        G = ox.load_graphml(graphml_path)
    else:
        print(f"Downloading network for: {place_name}")
        G = ox.graph_from_place(place_name, network_type="drive")
    
    # Convert to GeoDataFrames
    nodes, edges = ox.graph_to_gdfs(G)
    
    return G, nodes, edges


def identify_junctions(nodes, min_streets=3):
    """Filter out nodes that are actual junctions (3+ streets meeting)."""
    print(f"\n--- Identifying Junctions ---")
    
    # Filter nodes with street_count >= min_streets
    junctions = nodes[nodes['street_count'] >= min_streets].copy()
    
    print(f"Total nodes: {len(nodes)}")
    print(f"Junctions (>= {min_streets} streets): {len(junctions)}")
    
    return junctions


def classify_junctions(junctions):
    """Add a junction_type label based on how many roads meet."""
    print(f"\n--- Classifying Junctions ---")
    
    def get_junction_type(street_count):
        if street_count == 3:
            return "T-junction"
        elif street_count == 4:
            return "Crossroads"
        elif street_count == 5:
            return "5-way"
        else:
            return f"{street_count}-way"
    
    junctions['junction_type'] = junctions['street_count'].apply(get_junction_type)
    
    print("\nDistribution:")
    print(junctions['junction_type'].value_counts().sort_index())
    
    return junctions


def calculate_danger_score(junctions, edges):
    """Assign a preliminary danger score (0-1) based on junction type."""
    print(f"\n--- Calculating Danger Scores ---")
    
    def score_junction(row):
        # Base score on street count
        street_count = row['street_count']
        
        # T-junctions are often more dangerous
        if street_count == 3:
            base_score = 0.7
        elif street_count == 4:
            base_score = 0.5
        elif street_count >= 5:
            base_score = 0.8  # Complex junctions
        else:
            base_score = 0.3
        
        return base_score
    
    junctions['danger_score'] = junctions.apply(score_junction, axis=1)
    
    print(f"Danger score statistics:")
    print(junctions['danger_score'].describe())
    
    return junctions


def visualize_junctions(G, junctions, place_name="Oxford"):
    """Generate a few map visualizations of the junctions we found."""
    print(f"\n--- Creating Visualizations ---")
    os.makedirs("data/visualizations", exist_ok=True)
    
    # Visualization 1: All junctions
    fig, ax = ox.plot_graph(
        G,
        node_size=0,
        edge_linewidth=0.3,
        edge_color='#CCCCCC',
        bgcolor='white',
        show=False,
        close=False,
        figsize=(12, 12)
    )
    
    # Plot junctions
    junctions.plot(
        ax=ax,
        color='red',
        markersize=20,
        alpha=0.6,
        zorder=3
    )
    
    ax.set_title(f"{place_name} - Road Junctions (3+ roads)", 
                 fontsize=16, fontweight='bold')
    
    output_path = f"data/visualizations/{place_name.lower().replace(' ', '_')}_junctions_all.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_path}")
    plt.close()
    
    # Visualization 2: Junctions by type
    fig, ax = ox.plot_graph(
        G,
        node_size=0,
        edge_linewidth=0.3,
        edge_color='#CCCCCC',
        bgcolor='white',
        show=False,
        close=False,
        figsize=(12, 12)
    )
    
    # Color code by junction type
    colors = {
        'T-junction': 'red',
        'Crossroads': 'orange',
        '5-way': 'purple',
    }
    
    for junction_type, color in colors.items():
        subset = junctions[junctions['junction_type'] == junction_type]
        if len(subset) > 0:
            subset.plot(
                ax=ax,
                color=color,
                markersize=25,
                alpha=0.7,
                label=junction_type,
                zorder=3
            )
    
    # Handle other junction types
    other = junctions[~junctions['junction_type'].isin(colors.keys())]
    if len(other) > 0:
        other.plot(
            ax=ax,
            color='blue',
            markersize=25,
            alpha=0.7,
            label='Other',
            zorder=3
        )
    
    ax.legend(loc='upper right', fontsize=12)
    ax.set_title(f"{place_name} - Junctions by Type", 
                 fontsize=16, fontweight='bold')
    
    output_path = f"data/visualizations/{place_name.lower().replace(' ', '_')}_junctions_by_type.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_path}")
    plt.close()
    
    # Visualization 3: Danger scores
    fig, ax = ox.plot_graph(
        G,
        node_size=0,
        edge_linewidth=0.3,
        edge_color='#CCCCCC',
        bgcolor='white',
        show=False,
        close=False,
        figsize=(12, 12)
    )
    
    # Plot with danger score color gradient
    junctions.plot(
        ax=ax,
        column='danger_score',
        cmap='YlOrRd',
        markersize=30,
        alpha=0.8,
        legend=True,
        legend_kwds={'label': 'Danger Score', 'shrink': 0.5},
        zorder=3
    )
    
    ax.set_title(f"{place_name} - Junction Danger Scores (Preliminary)", 
                 fontsize=16, fontweight='bold')
    
    output_path = f"data/visualizations/{place_name.lower().replace(' ', '_')}_danger_scores.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_path}")
    plt.close()


def save_junctions_data(junctions, place_name="Oxford"):
    """Save junction data as GeoJSON for use in later scripts."""
    os.makedirs("data/processed", exist_ok=True)
    
    filename = place_name.lower().replace(' ', '_').replace(',', '')
    output_path = f"data/processed/{filename}_junctions.geojson"
    
    # Select relevant columns
    output_cols = ['osmid', 'street_count', 'junction_type', 'danger_score', 'geometry']
    available_cols = [col for col in output_cols if col in junctions.columns]
    
    junctions[available_cols].to_file(output_path, driver="GeoJSON")
    print(f"\nSaved junction data: {output_path}")


def print_interesting_junctions(junctions, n=10):
    """Show the top N junctions by danger score."""
    print(f"\n--- Top {n} Highest Danger Score Junctions ---")
    
    top_junctions = junctions.nlargest(n, 'danger_score')
    
    for idx, row in top_junctions.iterrows():
        print(f"Junction ID: {row.get('osmid', idx)}")
        print(f"  Type: {row['junction_type']}")
        print(f"  Streets: {row['street_count']}")
        print(f"  Danger Score: {row['danger_score']:.2f}")
        print(f"  Location: ({row.geometry.y:.5f}, {row.geometry.x:.5f})")
        print()


def main():
    print("\n--- Junction Detection ---\n")
    
    place_name = "Oxford, UK"
    
    # Step 1: Load network
    G, nodes, edges = load_network(place_name)
    
    # Step 2: Identify junctions
    junctions = identify_junctions(nodes, min_streets=3)
    
    # Step 3: Classify junction types
    junctions = classify_junctions(junctions)
    
    # Step 4: Calculate preliminary danger scores
    junctions = calculate_danger_score(junctions, edges)
    
    visualize_junctions(G, junctions, place_name)
    save_junctions_data(junctions, place_name)
    print_interesting_junctions(junctions)
    
    print(f"\nDone - {len(junctions)} junctions found and saved.\n")


if __name__ == "__main__":
    main()
