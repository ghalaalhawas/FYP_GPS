import json
import os
import matplotlib.pyplot as plt

def analyze_telemetry(telemetry_file, output_dir):
    with open(telemetry_file, 'r') as f:
        data = json.load(f)

    events = data.get('events', [])
    warnings = [e for e in events if e['type'] == 'warning']
    locations = [e for e in events if e['type'] == 'location']

    true_positives = sum(1 for w in warnings if w.get('truePositive', True))
    false_positives = len(warnings) - true_positives

    precision = true_positives / len(warnings) if warnings else 0
    
    print("=== Evaluation Analysis ===")
    print(f"Total Routes Driven (Simulated Locations): {len(locations)}")
    print(f"Total Warnings Triggered: {len(warnings)}")
    print(f"True Positives (Correct approach): {true_positives}")
    print(f"False Positives (Incorrect triggers): {false_positives}")
    print(f"Warning Precision: {precision * 100:.2f}%\n")

    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Precision Pie Chart
    plt.figure(figsize=(6, 6))
    plt.pie([true_positives, false_positives], labels=['True Positives', 'False Positives'], autopct='%1.1f%%', colors=['#4CAF50', '#F44336'])
    plt.title('Warning Accuracy (Precision)')
    plt.savefig(os.path.join(output_dir, 'warning_accuracy.png'))
    plt.close()

    # 2. Warning Distances Bar Chart
    distances = [w['distance'] for w in warnings]
    if distances:
        plt.figure(figsize=(8, 5))
        plt.hist(distances, bins=10, color='#2196F3', edgecolor='black')
        plt.title('Distribution of Warning Trigger Distances')
        plt.xlabel('Distance to Junction (meters)')
        plt.ylabel('Frequency')
        plt.savefig(os.path.join(output_dir, 'warning_distances.png'))
        plt.close()

    print(f"Visualizations saved to {output_dir}")

if __name__ == "__main__":
    analyze_telemetry(
        "data/processed/mock_evaluation_telemetry.json", 
        "data/visualizations/evaluation"
    )
