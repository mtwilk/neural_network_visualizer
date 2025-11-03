from flask_cors import CORS
from flask import Flask, request, jsonify, wrappers
from visualize_fc_neurons import NetworkVisualizer
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# initialize globally so we don't have to reload the neural network every time we want to classify
VISUALIZER = NetworkVisualizer()
VISUALIZER.load_model()

def convert_to_json_serializable(obj):
    """Convert numpy types to native Python types for JSON serialization."""
    import numpy as np
    
    if isinstance(obj, (np.integer, np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (list, tuple)):
        return [convert_to_json_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_to_json_serializable(value) for key, value in obj.items()}
    else:
        return obj

def send_visualization_data(data: dict) -> wrappers.Response:
    """
    compute and return all necessary visualization data as a JSON response.
    positions are tuples of (x, y) coordinates. color is a list of 4 elements, RGB and Alpha.

    :type: color List[float]
    :type: position: Tuple[float, float]

    :type: label: str
    :type: score: float
    :type: edge positions: List[Tuple[position_start, position_end, color]]
    :type: neuron_positions: List[Tuple[position, color]]
    :type: num_layers: int
    :type: layer_sizes: List[int]
    :type: layer_names: List[str]
    :rytype: Response
    """
    label, score = VISUALIZER.classify_image(data['image_path'])

    VISUALIZER.compute_visualization_data()

    # Convert all data to JSON-serializable format
    response_data = {
        'label': label,
        'score': float(score),
        'edge positions': convert_to_json_serializable(VISUALIZER.edge_display_data),
        'neuron_positions': convert_to_json_serializable(VISUALIZER.node_display_data),
        'num_layers': int(VISUALIZER.num_layers),
        'layer_sizes': convert_to_json_serializable(VISUALIZER.layer_sizes),
        'layer_names': VISUALIZER.layer_names,
    }

    return jsonify(response_data)

# @app.route('/')
# def index():
#     return jsonify({'status': 'Flask server is running', 'routes': ['/main']})

@app.route('/main', methods=['POST'])
def main():
    data = request.json
    if type(data['image_path']) == str:
        return send_visualization_data(data)

    return jsonify({'error': 'Invalid image path'}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
