# -*- coding: utf-8 -*-
"""VGG_Adam_v4.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/19W8lUWar1PBf6V4Fk62KZgEjPMY5pRhK
"""

from google.colab import drive
import os
from datetime import datetime

drive.mount('/content/drive')
os.chdir('/content/drive/MyDrive/DL and CV')

"""# Imports"""

import time
import random
from tqdm.notebook import tqdm_notebook
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
from sklearn.model_selection import train_test_split

import torch
from torch import nn

import torchvision.datasets as datasets
import torchvision.transforms as transforms

from torch.utils.data import DataLoader
from torchvision.models import vgg19_batch_norm
from torch.utils.tensorboard import SummaryWriter

def seed():
  """ This function is used when running any cell to make sure all the seed are the same"""
  rand_seed = 0
  random.seed(rand_seed)
  os.environ['PYTHONHASHSEED'] = str(rand_seed)
  np.random.seed(rand_seed)
  torch.manual_seed(rand_seed)
  torch.cuda.manual_seed(rand_seed)
  torch.cuda.manual_seed_all(rand_seed) # if you are using multi-GPU.
  torch.backends.cudnn.benchmark = False
  torch.backends.cudnn.deterministic = True

"""# Train & Validate"""

#-- Freeze the randomness
seed()

def model_train(model, model_name, lr, optimizer, epochs, tb_writer, parameters):
  #-- Build a lamba function to get the current time stamp when it is called
  ts = lambda x: x.now().strftime('%d_%m_%Y__%H:%M:%S')  
  #-- Change the VGG output layer to 10 to match the number of MNIST and CIFAR classes
  model.classifier[6] = nn.Linear(4096, 10)  
  #-- Pass model to to cuda
  model.to(device)  
  #-- Define the loss criterion
  loss_criterion = nn.CrossEntropyLoss()  

  print('###################### Training {} {} model for {} epochs ######################'.format(model_name, parameters, epochs))
  #-- Set the lowest validation loss to positive infinity 
  best_val_loss = np.inf
  #-- Loop over the dataset for a number of epochs 
  for epoch in range(epochs):
      #-- Initiate train loss, correct training, epoch loss, epoch accuracy, and epoch_accuracy
      train_loss = 0.0
      train_correct = 0
      total = 0 
      epoch_loss = 0.0
      epoch_acc = 0.0

      #-- Set model to train mode
      model.train()

      #-- Loop over the train loader dataset
      for i, (images, labels) in tqdm_notebook(enumerate(train_loader)): 
          #-- Pass images and labels to cuda
          images, labels = images.to(device), labels.to(device)
          #-- Empty the gradiant
          optimizer.zero_grad() 
          #-- Feed-forward pass
          outputs = model(images) 
          #-- Get the predictions 
          _, preds = torch.max(outputs, 1)  
          #-- Training loss calculation
          loss = loss_criterion(outputs, labels)  
          #-- Apply backpropagation to calculate gradients
          loss.backward()
          #-- Adjusting learning weights
          optimizer.step() 
          #-- Gather data and report
          train_loss += loss.item() * images.size(0) 
          total += labels.size(0)
          train_correct += (preds == labels).sum().item()  

          #-- Print results every 100 batch
          if (i + 1) % 100 == 0:
            print_ = 'Epoch {} of {}, Step: {} of {}, Training loss: {:.7f}, Training accuracy: {:.7f}, Time: {}'
            print(print_.format(epoch + 1, epochs, i + 1, len(train_loader), (train_loss / total), (train_correct / total), ts(datetime) ))
          epoch_loss = train_loss / total
          epoch_acc = train_correct / total

      #-- Print end of epoch training's results and save them in tensorboard
      print_ = 'Epoch {} of {}, Average training loss: {:.7f}, Average training accuracy: {:.7f}, Time: {}'
      print(print_.format(epoch + 1, epochs, epoch_loss,epoch_acc, ts(datetime)))
      tb_writer.add_scalars(model_name+'_epoch_loss_accuracy_'+parameters, {'train_loss':epoch_loss, 'train_accuracy':epoch_acc}, epoch + 1)
      
      print('###################### Validating {} {} model ######################'.format(model_name, parameters))
      
      #-- Initiate validation loss, correct validation , epoch loss, epoch accuracy, and epoch_accuracy
      val_loss = 0.0
      val_correct = 0
      total = 0
      val_epoch_loss = 0.0
      val_epoch_acc = 0.0

      with torch.no_grad(): 
        #-- Set model to evaluation mode
        model.eval()
        for i, (val_images, val_labels) in tqdm_notebook(enumerate(val_loader)):
            #-- Pass images and labels to cuda
            val_images, val_labels = val_images.to(device), val_labels.to(device)
            outputs = model(val_images)  
            #-- Get the predictions
            _, predicted = torch.max(outputs.data, 1)
            #-- Validation loss calculation
            loss = loss_criterion(outputs, val_labels)
            #-- Print results every 100 batch
            val_loss += loss.item() * val_images.size(0)  
            total += val_labels.size(0)
            val_correct += (predicted == val_labels).sum().item()
            
            #-- Check every 100 step
            if (i + 1) % 100 == 0:
              #-- if there a new loss that is ower than best_val_loss , save model
              if val_epoch_loss < best_val_loss :
                print_ = 'Step: {} of {}, Validation loss: {:.7f}, Validation accuracy: {:.7f}, Time: {}'
                print(print_.format(i + 1, len(val_loader), (val_loss / total), (val_correct / total) ,ts(datetime)), end=' | ')

                print('Loss decreased from {:.7f} to {:.7f} .... Saving the model'.format(best_val_loss, val_epoch_loss))
                best_val_loss = val_epoch_loss

                #-- Saving the model state dict
                model_name_extra = '__lr {}__epochs {}'.format(lr, epochs)
                model_save_path = os.path.join(model_dir, model_name+model_name_extra)
                torch.save(model.state_dict(), model_save_path)

              else:
                print_ = 'Step: {} of {}, Validation loss: {:.7f}, Validation accuracy: {:.7f}, Time: {}'
                print(print_.format(i + 1, len(val_loader), (val_loss / total), (val_correct / total),ts(datetime)))

            val_epoch_loss = val_loss / total
            val_epoch_acc = val_correct / total

        #-- Print end of epoch training's results and save them in tensorboard
        print_ = 'Average validation loss: {:.7f}, Average validation accuracy: {:.7f}, Time: {}'
        print(print_.format(val_epoch_loss, val_epoch_acc,ts(datetime)))
        tb_writer.add_scalars(model_name+'_epoch_loss_accuracy_'+parameters, {'val_loss':val_epoch_loss, 'val_accuracy':val_epoch_acc}, epoch + 1)

  return model, model_save_path

"""# Test"""

#-- Freeze the randomness
seed()

def model_test(model, model_name, tb_writer, parameters):  
  ts = lambda x: x.now().strftime('%d_%m_%Y__%H:%M:%S')

  print('###################### Testing {} {} model ######################'.format(model_name, parameters))
  correct = 0
  total = 0
  test_pred_labels = []
  test_actual_labels = []
  incorrect_pred = 0
  correct_pred = 0

  with torch.no_grad():
    for i, (test_images, test_labels) in tqdm_notebook(enumerate(test_loader)):
      #-- Pass images and labels to Cuda
      test_images, test_labels = test_images.to(device), test_labels.to(device)
      #-- Feed-forward pass
      outputs = model(test_images)  
      #-- Get the predictions
      _, predicted = torch.max(outputs.data, 1)
      #-- Change CPU to numpy
      temp = predicted.detach().cpu().numpy()  
      #-- Add the prediction to the test_pred_labels list
      test_pred_labels.append(temp)  
      #-- Add the acutal labels to the test_actual_labels list
      test_actual_labels.append(test_labels.detach().cpu().numpy())
      total += test_labels.size(0)
      correct += (predicted == test_labels).sum().item()
      #-- Check if the ground truth labels match the predicted labels
      if ~test_labels.all().eq(predicted.all()): #-- If so, save 10 sample images
        if incorrect_pred < 10:
          plot_results(test_images, test_labels, predicted, i, model_name, parameters, 'incorrect')
          incorrect_pred +=1
      else:
        if correct_pred < 10: #-- If not, save 10 sample images
          plot_results(test_images, test_labels, predicted, i, model_name, parameters, 'correct')
          correct_pred +=1
      #-- Print results every 100 batch
      if (i + 1) % 100 == 0:
        print('Step: {} of {}, Test accuracy: {:.7f}, Time: {}'.format(i+1, len(test_loader), (correct / total), ts(datetime) ))
  
  #-- Calculate the final accuracy and then print it
  acc = correct / total
  print('Average testing accuracy: {:.7f}, Time: {}'.format(acc, ts(datetime)))
  tb_writer.add_text(model_name+'_test_accuracy_'+parameters, str(acc))

"""# Plot results"""

#-- Create a graph to compare the the actual labels with the predicted results
def plot_results(test_images, test_labels, predicted, index, model_name, parameters, correct_incorrect):
  fig = plt.figure()
  fig.suptitle('Testing {} model ({}) {} \n {}'.format(model_name, index+1, parameters, time.ctime()), fontsize=13)
  for i, (image, label, pred) in enumerate(zip(test_images, test_labels, predicted)):
    plt.subplot(1,test_images.shape[0], i+1) 
    plt.tight_layout(pad=0)
    plt.imshow(image[0].cpu(), cmap='gray')
    plt.title("Actual: {} \n Prediction: {}".format(label, pred), fontsize=10)
    plt.xticks([])
    plt.yticks([])

  #-- Save images to disk and tensorboard
  tb_writer.add_figure('Testing {} model ({}) {}'.format(model_name, index+1, parameters), fig, 0)
  image_save_path = os.path.join(output_dir, 'Test {} model_{}_{}_{}.png'.format(model_name, index+1, parameters, correct_incorrect))
  fig.savefig(image_save_path, bbox_inches='tight', pad_inches=0, transparent=True)

"""# Loading and Spliting MNIST Data"""

#-- Freeze the randomness
seed()

#-- Prepare GPU
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

#-- Create data, train, and test directories
data_dir  = './datasets/MNIST'
train_dir = os.path.join(data_dir, 'train')
test_dir  = os.path.join(data_dir, 'test')

#-- Create directories for models and outputs
model_dir  = './models/MNIST'
output_dir = '/content/drive/MyDrive/DL and CV/outputs/MNIST'
Path(output_dir).mkdir(parents=True, exist_ok=True)

trans = transforms.Compose([transforms.Resize(224), #-- VGG model requires this image shape
                              transforms.RandomRotation(15), #-- images augmentation to challenge the model
                              transforms.Grayscale(num_output_channels=3), #-- VGG model requires 3 channels
                              transforms.ToTensor(), transforms.Normalize((0.1307,), (0.3081,))]) #-- Values normalization

#-- Download MNIST training data, and splitting it to training and validation
train_data = datasets.MNIST(root=train_dir, train=True, download=True, transform=trans)

#-- Split the training data to training and validation datasets.
train_indices, val_indices = train_test_split(list(range(len(train_data.targets))), test_size=5000, stratify=train_data.targets, random_state=0)
train = torch.utils.data.Subset(train_data, train_indices)
val = torch.utils.data.Subset(train_data, val_indices)

#-- Download MNIST test data
test = datasets.MNIST(root=test_dir, train=False, download=True, transform=trans)

#-- Setting training batch size:
batch_size = 4

#-- Build the training, validation, and test data loaders
train_loader = DataLoader(dataset=train, batch_size=batch_size, shuffle=False)  
val_loader   = DataLoader(dataset=val,   batch_size=batch_size, shuffle=False)  
test_loader  = DataLoader(dataset=test,  batch_size=batch_size, shuffle=False) 

#-- Print out the number of salmples for training, vlidation, and test sets.
print("Number of Samples in Training Dataset: ",   len(train))
print("Number of Samples in Validation Dataset: ", len(val))
print("Number of Samples in Testing Dataset: ",    len(test))

"""# MNIST Main"""

#-- Parameters
epochs = 5

for learning_rate in [0.1, 0.01, 0.001, 0.0001]:
  #-- Freeze the randomness
  seed()
  model = vgg19_bn(pretrained=False)
  model_name = 'vgg19_batch_norm'
  lr = learning_rate
  parameters = 'ADAM, lr_{}'.format(lr)

  #-- Initiating a tensorboard writer that contains all logs for training, validation, and testing
  tb_writer = SummaryWriter('./models/MNIST/runs', filename_suffix='_'+model_name+'_'+parameters)

  #-- Create the model's critrion loss function and a optimization function 
  optimizer = torch.optim.Adam(model.parameters(), lr=lr)
  
  #-- Train and valiate the model
  model, model_save_path = model_train(model, model_name, lr, optimizer, epochs, tb_writer, parameters)

  #-- Load the best saved model for testing
  model.load_state_dict(torch.load(model_save_path))
  model.to(device)

  #-- Set the model mode to evaluation to prepare for testing
  model.eval()
  model_test(model, model_name, tb_writer, parameters) 
  
  #-- Close the Tensoboard writer
  tb_writer.close()

  #-- Delete the model
  del model

"""# Loading and Spliting CIFAR Data"""

#-- Freeze the randomness
seed()

#-- Prepare GPU
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

#-- Create data, train, and test directories
data_dir  = './datasets/CIFAR'
train_dir = os.path.join(data_dir, 'train')
test_dir  = os.path.join(data_dir, 'test')

#-- Create directories for models and outputs
model_dir  = './models/CIFAR'
output_dir = '/content/drive/MyDrive/DL and CV/outputs/CIFAR'
Path(output_dir).mkdir(parents=True, exist_ok=True)

trans = transforms.Compose([transforms.Resize(224), #-- VGG model requires this image shape
                              transforms.RandomRotation(15), #-- images augmentation to challenge the model
                              transforms.ToTensor(), transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))]) #-- Values normalization

#-- Download CIFAR10 training data, and splitting it to training and validation
train_data = datasets.CIFAR10(root=train_dir, train=True, download=True, transform=trans)

#-- Split the training data to training and validation datasets.
train_indices, val_indices = train_test_split(list(range(len(train_data.targets))), test_size=5000, stratify=train_data.targets, random_state=0)
train = torch.utils.data.Subset(train_data, train_indices)
val = torch.utils.data.Subset(train_data, val_indices)

#-- Download CIFAR10 test data
test = datasets.CIFAR10(root=test_dir, train=False, download=True, transform=trans)

#-- Setting training batch size:
batch_size = 4

#-- Build the training, validation, and test data loaders
train_loader = DataLoader(dataset=train, batch_size=batch_size, shuffle=False)  
val_loader   = DataLoader(dataset=val,   batch_size=batch_size, shuffle=False)  
test_loader  = DataLoader(dataset=test,  batch_size=batch_size, shuffle=False) 

print("Number of Samples in Training Dataset: ",   len(train))
print("Number of Samples in Validation Dataset: ", len(val))
print("Number of Samples in Testing Dataset: ",    len(test))

"""# CIFAR Main"""

#-- Parameters
epochs = 5

for learning_rate in [0.1, 0.01, 0.001, 0.0001]:
  #-- Freeze the randomness
  seed()
  model = vgg19_bn(pretrained=False)
  model_name = 'vgg19_batch_norm'
  lr = learning_rate
  parameters = 'ADAM, lr_{}'.format(lr)

  #-- Initiating a tensorboard writer that contains all logs for training, validation, and testing
  tb_writer = SummaryWriter('./models/CIFAR/runs', filename_suffix='_'+model_name+'_'+parameters)

  #-- Create the model's critrion loss function and a optimization function 
  optimizer = torch.optim.Adam(model.parameters(), lr=lr)
  
  #-- Train and valiate the model
  model, model_save_path = model_train(model, model_name, lr, optimizer, epochs, tb_writer, parameters)

  #-- Load the best saved model for testing
  model.load_state_dict(torch.load(model_save_path))
  model.to(device)

  #-- Set the model mode to evaluation to prepare for testing
  model.eval()
  model_test(model, model_name, tb_writer, parameters) 
  
  #-- Close the Tensoboard writer
  tb_writer.close()

  #-- Delete the model
  del model