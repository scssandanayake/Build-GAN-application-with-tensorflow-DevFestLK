# -*- coding: utf-8 -*-
"""Devfest_Sri_Lanka.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1moWqU9Ua51xjPw6jAwa0pgwGtXW6IPNU

## Import required modules
"""

from matplotlib import pyplot as plt
import numpy as np

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.datasets import fashion_mnist
from tensorflow.keras.models import Sequential
from tensorflow.keras import layers
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers import Adam

"""## Data Loading and Visualization"""

(X_train, y_train), (X_test, y_test) = fashion_mnist.load_data()

X_train.shape

y_train.shape

for img in range(1,12+1):
  plt.subplot(3,4,img)
  plt.imshow(X_train[img])
  plt.title(y_train[img])
  plt.axis("off")

class_names = ['T-shirt/top', 'Trouser', 'Pullover', 'Dress', 'Coat', 'Sandal', 'Shirt', 'Sneaker', 'Bag', 'Ankle boot']

for img in range(1,12+1):
  plt.subplot(3,4,img)
  plt.imshow(X_train[img])
  plt.title(class_names[y_train[img]])
  plt.axis("off")

"""## Data Preprocessing- Normalization"""

train_images = X_train.reshape(X_train.shape[0], 28, 28, 1).astype('float32')

train_images = (train_images - 127.5) / 127.5

"""## Build Generator model

### Fake data points using Latent dimensions vector
"""

LATENT_DIM = 100
WEIGHT_INIT = tf.keras.initializers.RandomNormal(mean=0.0, stddev=0.02)
CHANNELS = 1

def build_generator():
  model = Sequential()
  model.add(layers.Dense(7 * 7 * 256, input_dim=LATENT_DIM))
  model.add(layers.BatchNormalization())
  model.add(layers.ReLU())
  model.add(layers.Reshape((7, 7, 256)))

  model.add(layers.Conv2DTranspose(128, (5, 5), strides=(2, 2),padding="same", kernel_initializer=WEIGHT_INIT))
  model.add(layers.BatchNormalization())
  model.add((layers.ReLU()))

  model.add(layers.Conv2DTranspose(64, (5, 5), strides=(2, 2),padding="same", kernel_initializer=WEIGHT_INIT))
  model.add(layers.BatchNormalization())
  model.add((layers.ReLU()))

  model.add(layers.Conv2D(CHANNELS, (5, 5), padding="same", activation="tanh"))
  return model

generator = build_generator()
generator.summary()

"""## Build Discriminator model

### This is used to classify whether it is fake or real
"""

def build_discriminator(width, height, depth, alpha=0.2):
    model = Sequential()
    input_shape = (height, width, depth)

    model.add(layers.Conv2D(64, (5, 5), strides=(2, 2), padding="same",
        input_shape=input_shape))
    model.add(layers.BatchNormalization())
    model.add(layers.LeakyReLU(alpha=alpha))

    model.add(layers.Conv2D(128, (5, 5), strides=(2, 2), padding="same"))
    model.add(layers.BatchNormalization())
    model.add(layers.LeakyReLU(alpha=alpha))

    model.add(layers.Flatten())
    model.add(layers.Dropout(0.3))

    model.add(layers.Dense(1, activation="sigmoid"))

    return model

discriminator = build_discriminator(28, 28, 1)
discriminator.summary()

"""## Build DCGAN architecture"""

class DCGAN(keras.Model):
    def __init__(self, discriminator, generator, latent_dim):
        super().__init__()
        self.discriminator = discriminator
        self.generator = generator
        self.latent_dim = latent_dim
        self.d_loss_metric = keras.metrics.Mean(name="d_loss")
        self.g_loss_metric = keras.metrics.Mean(name="g_loss")

    def compile(self, d_optimizer, g_optimizer, loss_fn):
        super(DCGAN, self).compile()
        self.d_optimizer = d_optimizer
        self.g_optimizer = g_optimizer
        self.loss_fn = loss_fn

    @property
    def metrics(self):
        return [self.d_loss_metric, self.g_loss_metric]

    @tf.function
    def train_step(self, real_images):
        batch_size = tf.shape(real_images)[0]

        # Step 1. Train the discriminator with both real images (label as 1) and fake images (classified as label as 0)
        noise = tf.random.normal(shape=(batch_size, self.latent_dim))
        fake_images = self.generator(noise, training=True)

        pred_real = self.discriminator(real_images, training=True)
        pred_fake = self.discriminator(fake_images, training=True)

        d_loss_real = self.loss_fn(tf.ones_like(pred_real), pred_real)
        d_loss_fake = self.loss_fn(tf.zeros_like(pred_fake), pred_fake)
        d_loss = (d_loss_real + d_loss_fake) / 2

        grads = tf.gradients(d_loss, self.discriminator.trainable_variables)
        self.d_optimizer.apply_gradients(zip(grads, self.discriminator.trainable_variables))

        # Step 2. Train the generator (do not update weights of the discriminator)
        pred_fake = self.discriminator(fake_images, training=True)
        g_loss = self.loss_fn(tf.ones_like(pred_fake), pred_fake)

        grads = tf.gradients(g_loss, self.generator.trainable_variables)
        self.g_optimizer.apply_gradients(zip(grads, self.generator.trainable_variables))

        self.d_loss_metric.update_state(d_loss)
        self.g_loss_metric.update_state(g_loss)

        return {"d_loss": self.d_loss_metric.result(), "g_loss": self.g_loss_metric.result()}

"""## Callbacks"""

class GANMonitor(keras.callbacks.Callback):
    def __init__(self, num_img=3, latent_dim=100):
        self.num_img = num_img
        self.latent_dim = latent_dim
        self.seed = tf.random.normal([16, latent_dim])

    def on_epoch_end(self, epoch, logs=None):
        generated_images = self.model.generator(self.seed)
        generated_images = (generated_images * 127.5) + 127.5
        generated_images.numpy()

        fig = plt.figure(figsize=(5, 5))
        for i in range(self.num_img):
            plt.subplot(4, 4, i+1)
            img = keras.utils.array_to_img(generated_images[i])
            plt.imshow(img, cmap='gray')
            plt.axis('off')
        plt.show()

    def on_train_end(self, logs=None):
        self.model.generator.save('generator.h5')

"""## Compile.Fit.Train your GAN"""

dcgan = DCGAN(discriminator=discriminator, generator=generator, latent_dim=100)

LR = 0.0002

dcgan.compile(
    d_optimizer=keras.optimizers.Adam(learning_rate=LR, beta_1 = 0.5),
    g_optimizer=keras.optimizers.Adam(learning_rate=LR, beta_1 = 0.5),
    loss_fn=keras.losses.BinaryCrossentropy(),
)

NUM_EPOCHS = 10
dcgan.fit(train_images, epochs=NUM_EPOCHS, callbacks=[GANMonitor(num_img=16, latent_dim=100)])

"""## Evaluation"""

num_images_to_generate = 16  # Adjust as needed
random_noise = tf.random.normal(shape=(num_images_to_generate, LATENT_DIM))

generated_images = dcgan.generator(random_noise, training=False)

generated_images.shape

plt.figure(figsize=(8,8))
for i in range(generated_images.shape[0]):
  plt.subplot(4,4,i+1)
  plt.imshow(generated_images[i],cmap="gray")
  plt.axis("off")

import imageio
import time
from IPython.display import display, Image,clear_output

num_frames = 30

animation_noise = tf.random.normal(shape=(num_frames, LATENT_DIM))

animation_noise.shape

for i in range(num_frames):
    clear_output(wait=True)

    generated_image = dcgan.generator(animation_noise[i:i+1], training=False).numpy()

    plt.imshow(np.squeeze(generated_image), cmap="gray")
    plt.title(f"Frame {i+1}/{num_frames}")
    plt.axis("off")
    plt.show()

    time.sleep(0.2)

"""## What's next?: Road to Generative AI

- GitHub Repo: [https://github.com/lucifertrj/road-to-genAI](https://github.com/lucifertrj/road-to-genAI)
- Discord Community for discussions: [https://discord.com/invite/hEMqtDXCHA](https://discord.com/invite/hEMqtDXCHA)
"""