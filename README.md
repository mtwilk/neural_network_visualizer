# Neural network visualization app:
## basic idea 
Visualize an image classification model's neuron activations through a heatmap, use Explainable AI as motivation for research. The model makes a classification on a single instance from the test set (or whatever we will look for a dataset that is suitable, could modify this for whatever suits the research question) and then the application displays it in a 3D space where the user can move around or focus specific parts. 

## implementation plan idea:
For the backend we can either train a CNN (convolutional neural network), which can take a bit of time, or use a readily downloadable pre-trained model like VGG, torch module in python already should have something like this
We use an image dataset of our choice e.g. food, animals, everyday objects, whatever

for the first iteration of the project we can just use matplotlib

The end product can be implemented as a web app with the 3D part being done in JS, for example using the ThreeJS library,
the python server would load the model and then send it to the frontend everytime the user chooses to use a different image instance (so like make a reload button or sth)

## user group
Expert users, so we can invite a few DSAI students as participants in the usability/robustness studies.

## optional idea
We can make use of an additional input device apart from keyboard and mouse to support gestures, I think lecture 5 mentions a device that is connected to the computer and allows the use of gestures. 
Professor said that they have a couple of those at the university. I would first like to focus on getting the basics working and evaluating the feasibility of this. Could also ask a TA if the gestures can
be easily incorporated into the project so e.g. the gesture device would automatically translate the inputs or would we have to do that ourselves.
