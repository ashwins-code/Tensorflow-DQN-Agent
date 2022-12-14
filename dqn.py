import numpy as np
import tensorflow as tf
import random
from matplotlib import pyplot as plt

def build_dense_policy_nn():
    def f(action_n):
        model = tf.keras.models.Sequential([
                tf.keras.layers.Dense(256, activation="relu"),
                tf.keras.layers.Dense(128, activation="relu"),
                tf.keras.layers.Dense(64, activation="relu"),
                tf.keras.layers.Dense(32, activation="relu"),
                tf.keras.layers.Dense(action_n, activation="linear"),
            ])

        model.compile(loss=tf.keras.losses.MeanSquaredError(), optimizer=tf.keras.optimizers.Adam(0.0001))

        return model

    return f

class DQN:
    def __init__(self, action_n, model):
        self.action_n = action_n
        self.policy = model(action_n)
        self.target = model(action_n)
        self.replay = []
        self.max_replay_size = 10000
        self.weights_initialised = False

    def play_episode(self, env, epsilon, max_timesteps):

        obs = env.reset()
        rewards = 0
        steps = 0

        for _ in range(max_timesteps):
            rand = np.random.uniform(0, 1)

            if rand <= epsilon:
                action = env.action_space.sample()
            else:
                actions = self.policy(np.array([obs]).astype(float)).numpy()
                action = np.argmax(actions)

                if not self.weights_initialised:
                    self.target.set_weights(self.policy.get_weights())
                    self.weights_initialised = True

            new_obs, reward, done, _ = env.step(action)
            if len(self.replay) >= self.max_replay_size:
                self.replay = self.replay[(len(self.replay) - self.max_replay_size) + 1:]
                
            self.replay.append([obs, action, reward, new_obs, done])
            rewards += reward
            obs = new_obs
            steps += 1

            yield steps, rewards

            if done:
                env.close()
                break


    def learn(self, env, timesteps, train_every = 5, update_target_every = 50, show_every_episode = 4, batch_size = 64, discount = 0.8, min_epsilon = 0.05, min_reward=150):
        max_episode_timesteps = 1000
        episodes = 1
        epsilon = 1
        decay = np.e ** (np.log(min_epsilon) / (timesteps * 0.85))
        steps = 0

        episode_list = []
        rewards_list = []

        while steps < timesteps:
            for ep_len, rewards in self.play_episode(env, epsilon, max_episode_timesteps):
                epsilon *= decay
                steps += 1


                if steps % train_every == 0 and len(self.replay) > batch_size:
                    batch = random.sample(self.replay, batch_size)
                    obs = np.array([o[0] for o in batch])
                    new_obs = np.array([o[3] for o in batch])

                    curr_qs = self.policy(obs).numpy()
                    future_qs = self.target(new_obs).numpy()

                    for row in range(len(batch)):
                        action = batch[row][1]
                        reward = batch[row][2]
                        done = batch[row][4]

                        if not done:
                            curr_qs[row][action] = reward + discount * np.max(future_qs[row])
                        else:
                            curr_qs[row][action] = reward
            
                    self.policy.fit(obs, curr_qs, batch_size=batch_size, verbose=0)
                
                if steps % update_target_every == 0 and len(self.replay) > batch_size:
                    self.target.set_weights(self.policy.get_weights())

            episodes += 1

            if episodes % show_every_episode == 0:
                print ("epsiode: ", episodes)
                print ("explore rate: ", epsilon)
                print ("episode reward: ", rewards)
                print ("episode length: ", ep_len)
                print ("timesteps done: ", steps)

                if rewards > min_reward:
                    self.policy.save(f"policy-model-{rewards}")
            
            episode_list.append(episodes)
            rewards_list.append(rewards)
        
        self.policy.save("policy-model-final")
        plt.plot(episode_list, rewards_list)
        plt.show()


    def play(self, env):
        for _ in range(10):
            obs = env.reset()
            done = False

            while not done:
                actions = self.policy(np.array([obs]).astype(float)).numpy()
                action = np.argmax(actions)
                obs, _, done, _ = env.step(action)
                env.render()

    def load(self, path):
      m = tf.keras.models.load_model(path)
      self.policy = m