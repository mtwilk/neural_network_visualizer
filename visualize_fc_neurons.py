from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from torchvision.models import vgg19, VGG19_Weights, resnet18, ResNet18_Weights, efficientnet_b0, EfficientNet_B0_Weights
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


class FCActivationExtractor:
    """Extract activations from fully connected layers during classification."""
    
    def __init__(self):
        self.activations: Dict[str, torch.Tensor] = {}
        self.input_activations: Dict[str, torch.Tensor] = {}  # Store inputs too
        self.hooks = []
        self.fc_layers = []
    
    def register_hooks(self, model: nn.Module):
        """Register hooks on fully connected layers."""
        # Find all Linear layers in the classifier
        for name, module in model.named_modules():
            if isinstance(module, nn.Linear):
                self.fc_layers.append({'name': name, 'module': module})
                hook = module.register_forward_hook(self._make_hook(name))
                self.hooks.append(hook)
        
        return self.fc_layers
    
    def _make_hook(self, name: str):
        def hook(module, input, output):
            self.activations[name] = output.detach()
            # Also store the input (flattened tensor from previous layer)
            if isinstance(input, tuple):
                self.input_activations[name] = input[0].detach()
            else:
                self.input_activations[name] = input.detach()
        return hook
    
    def remove_hooks(self):
        """Remove all registered hooks."""
        for hook in self.hooks:
            hook.remove()
        self.hooks.clear()

class NetworkVisualizer:
    def __init__(self):
        self.model = None
        self.weights = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.preprocess = None

        self.extractor = FCActivationExtractor()
        self.fc_layers = []

        self.edge_width = 0.02
        self.subsample = 10000

        self.layer_sizes = []
        self.layer_names = []
        self.num_layers = 0
        self.xspacing = 0.0
        self.image_name = ""

        self.neuron_positions = []
        self.edge_display_data = []
        self.node_display_data = []

    def load_model(self, model_name: str = 'vgg19'):
        if model_name == 'vgg19':
            self.weights = VGG19_Weights.DEFAULT
            self.model = vgg19(weights=self.weights)
        elif model_name == 'resnet18':
            self.weights = ResNet18_Weights.DEFAULT
            self.model = resnet18(weights=self.weights)
        elif model_name == 'efficientnet_b0':
            self.weights = EfficientNet_B0_Weights.DEFAULT
            self.model = efficientnet_b0(weights=self.weights)
        else:
            raise ValueError(f"Unsupported model: {model_name}")
        self.model.eval()
        self.preprocess = self.weights.transforms()
        self.model.to(self.device)

    def classify_image(self, image_path: str):
        """
        Classify an image and return the label and score.
        :rtype: (str, float)
        """
        # Register hooks before running inference
        self.fc_layers = self.extractor.register_hooks(self.model)
        
        img = Image.open(image_path).convert("RGB")
        input_tensor = self.preprocess(img).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            output = self.model(input_tensor)
            probs = F.softmax(output[0], dim=0)
            predicted = torch.max(probs, dim=0)
        
        labels = self.weights.meta["categories"]
        idx = predicted.indices.cpu()
        label = labels[idx]
        score = predicted.values.cpu()
        return label, float(score)


    def compute_neuron_positions(self, layer_sizes: List[int], xspacing: float) -> List[List[Tuple[float, float]]]:
        neuron_positions = []
        
        for layer_idx, size in enumerate(layer_sizes):
            x = layer_idx * xspacing
            y_spacing = 1.0 / (size + 1)
            
            positions = []
            act_values = self.layer_activations[layer_idx]
            for neuron_idx in range(size):
                y = (neuron_idx + 1) * y_spacing
                positions.append((x, y))
                color = self.value_to_color(act_values[neuron_idx],
                                           np.min(act_values),
                                           np.max(act_values))
                
                self.node_display_data.append(((x, y), color))

            neuron_positions.append(positions)

        self.neuron_positions = neuron_positions

    def compute_visualization_data(self):
        self.layer_sizes.append(self.fc_layers[0]['module'].in_features)
        self.layer_names.append('input')

        for fc_info in self.fc_layers:
            module = fc_info['module']
            self.layer_sizes.append(module.out_features)
            self.layer_names.append(fc_info['name'].split('.')[-1])  # Short name

        self.num_layers = len(self.layer_sizes)
        self.xspacing = 1.0 / (self.num_layers + 1)

        self.layer_activations = []
        # Input layer activations (flattened conv features)
        first_fc_name = self.fc_layers[0]['name']
        input_act = self.extractor.input_activations.get(first_fc_name)
        self.layer_activations.append(input_act[0].detach().cpu().numpy())
        
        for fc_info in self.fc_layers:
            name = fc_info['name']
            act = self.extractor.activations.get(name)
            self.layer_activations.append(act[0].detach().cpu().numpy())
        
        self.compute_neuron_positions(self.layer_sizes, self.xspacing)
        # Compute edge values using collected activations
        all_values = []
        edge_data = []

        for layer_idx, fc_info in enumerate(self.fc_layers):
            module = fc_info['module']
            name = fc_info['name']
            
            # Get input and output activations from our collected data
            input_np = self.layer_activations[layer_idx]  # Previous layer
            weight = module.weight.detach().cpu().numpy()  # (out, in)
            
            # Compute contributions
            contributions = weight * input_np[np.newaxis, :]
            
            edge_data.append({
                'layer_idx': layer_idx,
                'contributions': contributions,
            })
        
            all_values = contributions.flatten()
        
        vmin = np.percentile(all_values, 1)
        vmax = np.percentile(all_values, 99)
        
        for edge_info in edge_data:
            layer_idx = edge_info['layer_idx']
            contributions = edge_info['contributions']
            # get the output layer size and input layer size
            out_size, in_size = contributions.shape
            
            total_edges = out_size * in_size
            if self.subsample and total_edges > self.subsample:
                # sample the most extreme edge values, half positive, half negative
                # with the sum equal to subsample
                lowest_indices = np.argpartition(contributions.flatten(), self.subsample // 2)[:self.subsample // 2]
                highest_indices = np.argpartition(contributions.flatten(), -self.subsample // 2)[-self.subsample // 2:]
                edge_indices = np.concatenate((lowest_indices, highest_indices))
            else:
                edge_indices = np.arange(total_edges)
            
            for edge_flat_idx in edge_indices:
                # Convert flat edge index to (out_idx, in_idx)
                out_idx = edge_flat_idx // in_size
                in_idx = edge_flat_idx % in_size

                pos_in = self.neuron_positions[layer_idx][in_idx]
                pos_out = self.neuron_positions[layer_idx + 1][out_idx]

                if pos_in is None or pos_out is None:
                    continue
                
                value = contributions[out_idx, in_idx]
                color = self.value_to_color(value, vmin, vmax)
                self.edge_display_data.append((pos_in, pos_out, color))

    
    def visualize_network(self):
        fig, ax = plt.subplots(figsize=(24, 14))

        print(f"Drawing connections (subsampling to ~{self.subsample} edges)...")
        edges_drawn = 0
        for pos_in, pos_out, color in self.edge_display_data:
            x1, y1 = pos_in
            x2, y2 = pos_out
            ax.plot([x1, x2], [y1, y2],
                    color=color[:3],
                    alpha=color[3],
                    linewidth=self.edge_width,
                    zorder=1)
                
            edges_drawn += 1

        print(f"Drew {edges_drawn} edges")
        print("Drawing neurons...")
        for pos, node_color in self.node_display_data:
            x, y = pos
            polygon = mpatches.RegularPolygon((x, y), 6, radius=self.edge_width / 1000, 
                                             color=node_color, zorder=2,
                                             ec='lightgray', linewidth=0.2)
            ax.add_patch(polygon)
        print("Drawing layer labels...")
        for layer_idx in range(self.num_layers):
            x = layer_idx * self.xspacing
            ax.text(x, -0.05, self.layer_names[layer_idx], 
                ha='center', va='top', fontsize=11, fontweight='bold')
            ax.text(x, 1.05, f"{self.layer_sizes[layer_idx]} neurons",
                ha='center', va='bottom', fontsize=9)
        
        ax.set_xlim(-0.1, 1.1)
        ax.set_ylim(-0.1, 1.15)
        ax.set_facecolor('black')
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title(f"NN visualization: {self.image_name}, ({edges_drawn:,} connections shown)",
                    fontsize=12, fontweight='bold', pad=20)
        
        legend_elements = [
            mpatches.Patch(color='green', label='Positive (brighter = stronger)'),
            mpatches.Patch(color='red', label='Negative (brighter = stronger)'),
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=11)
        
        plt.tight_layout()
        return fig
        
    @staticmethod
    def value_to_color(value: float, vmin: float, vmax: float) -> Tuple[float, float, float, float]:
        """
        Map value to RGBA color:
        - Positive: green with alpha based on magnitude
        - Negative: red with alpha based on magnitude
        """
        if value >= 0:
            if vmax > 0:
                intensity = min(1.0, value / vmax)
            else:
                intensity = 0.0
            return (0.0, intensity, 0.0, min(0.8, intensity * 0.5 + 0.1))
        else:
            if vmin < 0:
                intensity = min(1.0, abs(value) / abs(vmin))
            else:
                intensity = 0.0
            return (intensity, 0.0, 0.0, min(0.8, intensity * 0.5 + 0.1))
        

def main():
    visualizer = NetworkVisualizer()
    visualizer.load_model('vgg19')
    
    image_path = "panda.jpg"  # Example image path
    visualizer.image_name = Path(image_path).name
    
    print(f"Classifying image: {image_path}")
    label, score = visualizer.classify_image(image_path)
    print(f"Classification result: {label} ({score:.2f})")

    print("Computing visualization data...")
    visualizer.compute_visualization_data()
    
    print("Generating visualization...")
    fig = visualizer.visualize_network()
    
    plt.show()

if __name__ == "__main__":
    main()
