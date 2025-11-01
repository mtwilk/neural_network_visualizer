from argparse import ArgumentParser
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import torch
import torch.nn as nn
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


def compute_neuron_positions(layer_sizes: List[int], xspacing: float) -> List[List[Tuple[float, float]]]:
    neuron_positions = []
    
    for layer_idx, size in enumerate(layer_sizes):
        x = layer_idx * xspacing
        y_spacing = 1.0 / (size + 1)
        
        positions = []
        for neuron_idx in range(size):
            y = (neuron_idx + 1) * y_spacing
            positions.append((x, y))
        
        neuron_positions.append(positions)

    return neuron_positions

def visualize_fc_network_with_input(fc_layers: List[Dict],
                                    activations: Dict[str, torch.Tensor],
                                    input_activations: Dict[str, torch.Tensor],
                                    image_name: str,
                                    subsample: int = 10000,
                                    edge_width: float = 0.02):
    neuron_size = edge_width
    
    fig, ax = plt.subplots(figsize=(24, 14))
    
    layer_sizes = []
    layer_names = []
    
    # Add input layer (from first FC layer input size)
    layer_sizes.append(fc_layers[0]['module'].in_features)
    layer_names.append('input')
    
    for fc_info in fc_layers:
        module = fc_info['module']
        layer_sizes.append(module.out_features)
        layer_names.append(fc_info['name'].split('.')[-1])  # Short name
    
    print(f"Layer architecture: {layer_sizes}")
    
    # Compute positions
    num_layers = len(layer_sizes)
    xspacing = 1.0 / (num_layers + 1)
    
    neuron_positions = compute_neuron_positions(layer_sizes, xspacing)
    
    layer_activations = []
    # Input layer activations (flattened conv features)
    first_fc_name = fc_layers[0]['name']
    input_act = input_activations.get(first_fc_name)
    layer_activations.append(input_act[0].detach().cpu().numpy())
    
    # FC layer outputs
    for fc_info in fc_layers:
        name = fc_info['name']
        act = activations.get(name)
        layer_activations.append(act[0].detach().cpu().numpy())
    
    # Compute edge values using collected activations
    print("Computing edge values...")
    all_values = []
    edge_data = []
    
    for layer_idx, fc_info in enumerate(fc_layers):
        module = fc_info['module']
        name = fc_info['name']
        
        # Get input and output activations from our collected data
        input_np = layer_activations[layer_idx]  # Previous layer
        output_np = layer_activations[layer_idx + 1]  # Current layer
        
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
    print(f"Edge value range (1-99 percentile): [{vmin:.4f}, {vmax:.4f}]")
    
    
    # Draw edges with subsampling
    print(f"Drawing connections (subsampling to ~{subsample} edges)...")
    edges_drawn = 0
    
    for edge_info in edge_data:
        layer_idx = edge_info['layer_idx']
        contributions = edge_info['contributions']
        # get the output layer size and input layer size
        out_size, in_size = contributions.shape
        
        total_edges = out_size * in_size
        if subsample and total_edges > subsample:
            # edge_indices = np.random.choice(total_edges, subsample, replace=False)
            # sample the most extreme edge values, half positive, half negative
            # with the sum equal to subsample
            lowest_indices = np.argpartition(contributions.flatten(), subsample // 2)[:subsample // 2]
            highest_indices = np.argpartition(contributions.flatten(), -subsample // 2)[-subsample // 2:]
            edge_indices = np.concatenate((lowest_indices, highest_indices))
        else:
            edge_indices = np.arange(total_edges)
        
        for edge_flat_idx in edge_indices:
            # Convert flat edge index to (out_idx, in_idx)
            out_idx = edge_flat_idx // in_size
            in_idx = edge_flat_idx % in_size
            
            pos_in = neuron_positions[layer_idx][in_idx]
            pos_out = neuron_positions[layer_idx + 1][out_idx]
            
            if pos_in is None or pos_out is None:
                continue
            
            value = contributions[out_idx, in_idx]
            color = value_to_color(value, vmin, vmax)
            
            x1, y1 = pos_in
            x2, y2 = pos_out
            
            ax.plot([x1, x2], [y1, y2],
                   color=color[:3],
                   alpha=color[3],
                   linewidth=edge_width,
                   zorder=1)
            
            edges_drawn += 1
    
    print(f"Drew {edges_drawn} edges")
    
    # Draw neurons (colored by activation)
    print("Drawing neurons...")
    for layer_idx in range(num_layers):
        act_values = layer_activations[layer_idx]
        
        for neuron_idx, pos in enumerate(neuron_positions[layer_idx]):
            x, y = pos
            
            # Color by activation
            # if act_values is not None and neuron_idx < len(act_values):
            #     val = act_values[neuron_idx]
            #     if val >= 0:
            #         intensity = min(1.0, val / vmax) if vmax > 0 else 0
            #         node_color = (0.0, intensity, 0.0)
            #     else:
            #         intensity = min(1.0, abs(val) / abs(vmin)) if vmin < 0 else 0
            #         node_color = (intensity, 0.0, 0.0)
            # else:
            #     node_color = (0.5, 0.5, 0.5)
            node_color = value_to_color(act_values[neuron_idx], vmin, vmax)
            
            circle = plt.Circle((x, y), neuron_size / 1000, color=node_color, zorder=2, 
                              ec='lightgray', linewidth=0.2)
            ax.add_patch(circle)
    
    # Labels
    for layer_idx in range(num_layers):
        x = layer_idx * xspacing
        ax.text(x, -0.05, layer_names[layer_idx], 
               ha='center', va='top', fontsize=11, fontweight='bold')
        ax.text(x, 1.05, f"{layer_sizes[layer_idx]} neurons",
               ha='center', va='bottom', fontsize=9)
    
    # ax.set_xlim(-0.1, 1.1)
    # ax.set_ylim(-0.1, 1.15)
    ax.set_facecolor('black')
    ax.set_aspect('equal')
    ax.axis('off')
    
    ax.set_title(f"NN visualization: {image_name}, ({edges_drawn:,} connections shown)",
                fontsize=12, fontweight='bold', pad=20)
    
    # Legend
    legend_elements = [
        mpatches.Patch(color='green', label='Positive (brighter = stronger)'),
        mpatches.Patch(color='red', label='Negative (brighter = stronger)'),
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=11)
    
    plt.tight_layout()
    return fig


def main():
    parser = ArgumentParser(description="Visualize FC layer neurons and connections")
    parser.add_argument("image", help="Path to input image")
    parser.add_argument("--output", default=None,
                       help="Save visualization to file")
    parser.add_argument("--subsample", type=int, default=10000,
                       help="Maximum number of connections to draw (for readability)")
    parser.add_argument("--edge-width", type=float, default=0.02,
                       help="Width of connection lines (default: 0.02)")
    parser.add_argument("--neuron-size", type=float, default=None,
                       help="Size of neuron circles (default: 2x edge-width)")
    args = parser.parse_args()
    
    # Check image
    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Error: Image not found: {image_path}")
        return
    
    print(f"Loading VGG19 model...")
    weights = VGG19_Weights.DEFAULT
    model = vgg19(weights=weights)
    model.eval()


    # print(f"Loading ResNet18 model...")
    # weights = ResNet18_Weights.DEFAULT
    # model = resnet18(weights=weights)
    # model.eval()

    # print("Loading EfficientNet_B0 model...")
    # weights = EfficientNet_B0_Weights.DEFAULT
    # model = efficientnet_b0(weights=weights)
    # model.eval()

    preprocess = weights.transforms()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    
    print(f"Registering hooks on FC layers...")
    extractor = FCActivationExtractor()
    fc_layers = extractor.register_hooks(model)
    print(f"Found {len(fc_layers)} fully connected layers:")
    for fc_info in fc_layers:
        module = fc_info['module']
        print(f"  {fc_info['name']}: {module.in_features} -> {module.out_features}")
    
    # Load and process image
    print(f"Processing image: {image_path}")
    img = Image.open(image_path).convert("RGB")
    input_tensor = preprocess(img).unsqueeze(0).to(device)
    
    # Run inference
    print("Running inference...")
    with torch.no_grad():
        output = model(input_tensor)
    
    print(f"Captured {len(extractor.activations)} layer activations")
    print(f"Captured {len(extractor.input_activations)} layer inputs")
    
    # Visualize
    print("Creating visualization...")
    fig = visualize_fc_network_with_input(fc_layers, 
                                          extractor.activations,
                                          extractor.input_activations,
                                          image_path.name,
                                          subsample=args.subsample,
                                          edge_width=args.edge_width)
    
    if args.output:
        print(f"Saving to {args.output}...")
        fig.savefig(args.output, dpi=300, bbox_inches='tight')
        print("Saved!")
    else:
        print("Displaying plot...")
        plt.show()
    
    # Cleanup
    extractor.remove_hooks()
    print("Done!")


if __name__ == "__main__":
    main()
