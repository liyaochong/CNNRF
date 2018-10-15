# utf-8
# Author: ilikewind
'''
fine-tuning for binary classifier
'''

import os
import datetime as dt
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
#import seaborn as sns

from keras.applications import xception
from keras.applications import inception_resnet_v2
from keras.applications import inception_v3
from keras.applications import resnet50
from keras.callbacks import ModelCheckpoint
from keras.callbacks import EarlyStopping
from keras.callbacks import ReduceLROnPlateau
from keras.callbacks import CSVLogger
from keras.preprocessing import image
from keras.layers import Dense, GlobalAveragePooling2D
from keras.models import Model
from keras.models import model_from_json
from keras import backend as k
from keras.preprocessing.image import ImageDataGenerator
from keras.utils.np_utils import to_categorical
from keras.optimizers import Adam
from keras.optimizers import RMSprop
from mpl_toolkits.axes_grid1 import ImageGrid
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix
from tqdm import tqdm

from util_defined import config, hp

# sort file
def get_file_list(file_path):
    dir_list = os.listdir(file_path)
    if not dir_list:
        return
    else:
        dir_list = sorted(dir_list, key=lambda x:
                          os.path.getmtime(os.path.join(file_path, x)))
    return dir_list

'''
create data generator 
'''
def get_data_generator(train_path, val_path):

    train_datagen = ImageDataGenerator(featurewise_center=False,
                                       featurewise_std_normalization=False,
                                       rescale=1./255,
                                       rotation_range=20,
                                       zoom_range=0.2,
                                       horizontal_flip=True)
    train_generator = train_datagen.flow_from_directory(train_path,
                                                        target_size=(256,256),
                                                        batch_size=32,
                                                        class_mode='categorical',
                                                        classes={'normal': 0, 'tumor': 1})

    val_datagen = ImageDataGenerator(rescale=1./255,
                                     horizontal_flip=False)

    val_generator = val_datagen.flow_from_directory(val_path,
                                                    target_size=(256,256),
                                                    batch_size=32,
                                                    class_mode='categorical',
                                                    classes={'normal': 0, 'tumor': 1})

    return train_generator, val_generator

def create_model():
    base_model = inception_resnet_v2.InceptionResNetV2(weights='imagenet',
                                                       include_top=False,
                                                       pooling='avg')
    x = base_model.output
    x = Dense(500, activation='relu')(x)
    predictons = Dense(2, activation='softmax')(x)
    model = Model(inputs=base_model.input, outputs=predictons)
    # no frozen
    for layer in base_model.layers:
        layer.trainable = True

    model.compile(optimizer='Adam', loss='categorical_crossentropy',
                  metrics=['accuracy'])

    return model

def reload_model(json_path, weights_dir):
    model = model_from_json(open(json_path).read())
    weights_path = os.path.join(weights_dir, 'InRe2weights.best.h5')
    model.load_weights(weights_path)
    model.compile(optimizer='Adam', loss='categorical_crossentropy',
                  metrics=['accuracy'])
    return model



def callback_function(saved_model_dir):
    filepath = 'InRe2weights.best.h5'
    saved_path = os.path.join(saved_model_dir, filepath)
    csv_path = os.path.join(saved_model_dir, 'result.csv')

    model_chekpoint = ModelCheckpoint(filepath=saved_path, monitor='acc', verbose=1,
                                      save_best_only=True, save_weights_only=True, period=1)

    early_stoping = EarlyStopping(monitor='acc', verbose=1, min_delta=0,
                                  patience=8, mode='auto')

    reduce_lr = ReduceLROnPlateau(monitor='acc', factor=0.4,
                                  patience=5, min_lr=0.00001)

    csv_logger = CSVLogger(filename=csv_path, separator=',', append=True)
    return [model_chekpoint, early_stoping, reduce_lr, csv_logger]

if __name__ == '__main__':

    train_path = config.TRAIN_PATCHES
    val_path = config.VAL_PATCHES
    train_save_weight_path = config.TRAIN_SAVED_MODEL_INCEPTIONRESNET_V2

    # get train_generator and validate_generator
    train_generator, validate_generator = get_data_generator(train_path, val_path)

    # json file name
    json_name = 'InceptionResnet_v2_finetuning.json'
    json_path = os.path.join(train_save_weight_path, json_name)


    if not os.path.exists(json_path):
        # create train model
        model = create_model()
        # save net to json
        json_string = model.to_json()
        open(json_path, 'w').write(json_string)
    else:
        model = reload_model(json_path, train_save_weight_path)
        print("reload model")

    # get callback function
    callbacks = callback_function(train_save_weight_path)


    history = model.fit_generator(generator=train_generator, epochs=hp.EPOCH,
                                  verbose=1, callbacks=callbacks, validation_data=validate_generator,
                                  workers=6, use_multiprocessing=False, shuffle=True, initial_epoch=0)

# do not forget make roc curve