from argparse import ArgumentParser
from pathlib import Path

from PIL import Image
import torch
import torch.nn.functional as F
from torchvision.models import vgg19, VGG19_Weights


def load_vgg19(pretrained_weights: VGG19_Weights = VGG19_Weights.DEFAULT):
    """Load VGG19 with the requested pretrained weights and return
    (model, preprocess_transform, labels).
    """
    weights = pretrained_weights
    model = vgg19(weights=weights)
    model.eval()
    preprocess = weights.transforms()

    # get the textual labels for the classification results
    meta = weights.meta
    labels = meta["categories"]

    return model, preprocess, labels


def predict_image(image_path: str):
    """Predict the content of an image using a pretrained VGG19 model.
    returns (label, score) tuple for the top prediction.
    """
    model, preprocess, labels = load_vgg19()

    img = Image.open(image_path).convert("RGB")
    # resize and normalize the image
    input_tensor = preprocess(img).unsqueeze(0)

    # move the model and input tensor to GPU if available
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    input_tensor = input_tensor.to(device)

    with torch.no_grad():
        out = model(input_tensor)
        # normalize the classification probabilities to sum up to 1
        probs = F.softmax(out[0], dim=0)
        predicted = torch.max(probs, dim=0)

    # get the index of the top prediction label and its score - confidence 
    # of the model in the prediction
    idx = predicted.indices.cpu()
    score = predicted.values.cpu()

    return labels[idx], float(score)


def main():
    p = ArgumentParser()
    p.add_argument("image", nargs="?", default="panda.jpg", help="Path to input image")
    args = p.parse_args()

    image_path = Path(args.image)

    results = predict_image(str(image_path))
    print(results)

if __name__ == "__main__":
    main()