"""
Junction Detection and Visualization
Week 2 - Data Research & Environment Setup

This script identifies and classifies road junctions from OSM data.
Analyzes junction types and identifies potentially dangerous configurations.

Usage:
    python src/02_detect_junctions.py
"""

import osmnx as ox
import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from shapely.geometry import Point
import os

def load_network(place_name="Oxford, UK"):
    """
    Load network from file if available, otherwise download.
    
    Args:
        place_name: Name of place
    
    Returns:
        NetworkX graph, nodes GeoDataFrame, edges GeoDataFrame
    """
    filename = place_name.lower().replace(' ', '_').replace(',', '')
    graphml_path = f"data/raw/{filename}_network.graphml"
    
    if os.path.exists(graphml_path):
        print(f"📂 Loading existing network from: {graphml_path}")
        G = ox.load_graphml(graphml_path)
    else:
        print(f"⬇️  Downloading network for: {place_name}")
        G = ox.graph_from_place(place_name, network_type="drive")
    
    # Convert to GeoDataFrames
    nodes, edges = ox.graph_to_gdfs(G)
    
    return G, nodes, edges


def identify_junctions(nodes, min_streets=3):
    """
    Identify junctions where multiple roads meet.
    
    Args:
        nodes: GeoDataFrame of nodes
        min_streets: Minimum number of streets to classify as junction (default: 3)
    
    Returns:
        GeoDataFrame of junctions only
    """
    print(f"\n{'='*60}")
    print(f"IDENTIFYING JUNCTIONS")
    print(f"{'='*60}\n")
    
    # Filter nodes with street_count >= min_streets
    junctions = nodes[nodes['street_count'] >= min_streets].copy()
    
    print(f"Total nodes: {len(nodes)}")
    print(f"Junctions (>= {min_streets} streets): {len(junctions)}")
    
    return junctions


def classify_junctions(junctions):
    """
    Classify junctions by type based on number of connecting roads.
    
    Args:
        junctions: GeoDataFrame of junctions
    
    Returns:
        GeoDataFrame with added 'junction_type' column
    """
    print(f"\n{'='*60}")
    print(f"CLASSIFYING JUNCTIONS")
    print(f"{'='*60}\n")
    
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
    
    # Print statistics
    print("Junction type distribution:")
    print(junctions['junction_type'].value_counts().sort_index())
    
    return junctions


def calculate_danger_score(junctions, edges):
    """
    Calculate preliminary danger score for junctions.
    Based on simple heuristics (to be refined in Week 7).
    
    Factors considered:
    - T-junctions (more dangerous than crossroads)
    - Number of roads (more complex = higher risk)
    
    Args:
        junctions: GeoDataFrame of junctions
        edges: GeoDataFrame of edges
    
    Returns:
        GeoDataFrame with 'danger_score' column (0-1)
    """
    print(f"\n{'='*60}")
    print(f"CALCULATING PRELIMINARY DANGER SCORES")
    print(f"{'='*60}\n")
    
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
    """
    Create visualization showing junction locations and types.
    
    Args:
        G: NetworkX graph
        junctions: GeoDataFrame of junctions
        place_name: Name for title
    """
    print(f"\n{'='*60}")
    print(f"CREATING VISUALIZATIONS")
    print(f"{'='*60}\n")
    
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
    print(f"✅ Saved: {output_path}")
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
    print(f"✅ Saved: {output_path}")
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
    print(f"✅ Saved: {output_path}")
    plt.close()


def save_junctions_data(junctions, place_name="Oxford"):
    """
    Save junction data for later use.
    
    Args:
        junctions: GeoDataFrame of junctions
        place_name: Name for file naming
    """
    os.makedirs("data/processed", exist_ok=True)
    
    filename = place_name.lower().replace(' ', '_').replace(',', '')
    output_path = f"data/processed/{filename}_junctions.geojson"
    
    # Select relevant columns
    output_cols = ['osmid', 'street_count', 'junction_type', 'danger_score', 'geometry']
    available_cols = [col for col in output_cols if col in junctions.columns]
    
    junctions[available_cols].to_file(output_path, driver="GeoJSON")
    print(f"\n✅ Saved junction data: {output_path}")


def print_interesting_junctions(junctions, n=10):
    """
    Print details of most interesting (complex/dangerous) junctions.
    
    Args:
        junctions: GeoDataFrame of junctions
        n: Number to print
    """
    print(f"\n{'='*60}")
    print(f"TOP {n} HIGHEST DANGER SCORE JUNCTIONS")
    print(f"{'='*60}\n")
    
    top_junctions = junctions.nlargest(n, 'danger_score')
    
    for idx, row in top_junctions.iterrows():
        print(f"Junction ID: {row.get('osmid', idx)}")
        print(f"  Type: {row['junction_type']}")
        print(f"  Streets: {row['street_count']}")
        print(f"  Danger Score: {row['danger_score']:.2f}")
        print(f"  Location: ({row.geometry.y:.5f}, {row.geometry.x:.5f})")
        print()


def main():
    """Main execution function."""
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║  Junction Detection Script - Week 2                      ║
    ║  GPS Safety App - Dangerous Junction Detection          ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    # Configuration
    place_name = "Oxford, UK"
    
    # Step 1: Load network
    G, nodes, edges = load_network(place_name)
    
    # Step 2: Identify junctions
    junctions = identify_junctions(nodes, min_streets=3)
    
    # Step 3: Classify junction types
    junctions = classify_junctions(junctions)
    
    # Step 4: Calculate preliminary danger scores
    junctions = calculate_danger_score(junctions, edges)
    
    # Step 5: Visualize results
    visualize_junctions(G, junctions, place_name)
    
    # Step 6: Save data
    save_junctions_data(junctions, place_name)
    
    # Step 7: Print interesting findings
    print_interesting_junctions(junctions)
    
    print(f"\n{'='*60}")
    print(f"✅ JUNCTION DETECTION COMPLETE!")
    print(f"{'='*60}")
    print(f"\nWeek 2 Deliverable achieved:")
    print(f"  ✅ Sample OSM data loaded and visualized")
    print(f"  ✅ {len(junctions)} junctions identified and classified")
    print(f"  ✅ Visualizations saved in data/visualizations/")
    print(f"  ✅ Junction data saved for further processing")
    print()


if __name__ == "__main__":
    main()
