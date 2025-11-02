from flask_cors import CORS
from flask import Flask, request, jsonify, wrappers
from visualize_fc_neurons import NetworkVisualizer
import os

app = Flask(__name__)
CORS(app)

# initialize globally so we don't have to reload the neural network every time we want to classify
VISUALIZER = NetworkVisualizer()
VISUALIZER.load_model()

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

    return jsonify({
        'label': label,
        'score': score,
        'edge positions': VISUALIZER.edge_display_data,
        'neuron_positions': VISUALIZER.node_display_data,
        'num_layers': VISUALIZER.num_layers,
        'layer_sizes': VISUALIZER.layer_sizes,
        'layer_names': VISUALIZER.layer_names,
    })

@app.route('/main', methods=['POST'])
def main():
    data = request.json
    if data['image_path'] and type(data['image_path']) == str:
        return send_visualization_data(data)

    return jsonify({'error': 'Invalid image path'}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
