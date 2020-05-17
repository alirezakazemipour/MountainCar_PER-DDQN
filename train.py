import numpy as np
from model import Model, RNDModel
from memory import Memory, Transition
import torch
from torch import device
from torch import from_numpy
from torch.optim import Adam


class Agent:
    def __init__(self, env, n_actions, n_states, n_encoded_features):

        self.epsilon = 1.0
        self.min_epsilon = 0.01
        self.decay_rate = 5e-5
        self.n_actions = n_actions
        self.n_states = n_states
        self.n_encoded_features = n_encoded_features
        self.max_steps = 500
        self.max_episodes = 500
        self.target_update_period = 15
        self.mem_size = int(0.8 * self.max_steps)
        self.env = env
        self.recording_counter = 0
        self.batch_size = 32
        self.lr = 0.005
        self.gamma = 0.99
        self.device = device("cpu")

        self.q_target_model = Model(self.n_states, self.n_actions).to(self.device)
        self.q_eval_model = Model(self.n_states, self.n_actions).to(self.device)
        self.q_target_model.load_state_dict(self.q_eval_model.state_dict())

        self.rnd_predictor_model = RNDModel(self.n_states, self.n_encoded_features)
        self.rnd_target_model = RNDModel(self.n_states, self.n_encoded_features)

        self.memory = Memory(self.mem_size)

        self.loss_fn = torch.nn.MSELoss()
        self.optimizer = Adam(self.q_eval_model.parameters(), lr=self.lr)

    def choose_action(self, step, state):

        exp = np.random.rand()
        exp_probability = self.min_epsilon + (self.epsilon - self.min_epsilon) * np.exp(-self.decay_rate * step)

        if exp < exp_probability:
            return np.random.randint(self.n_actions)
        else:
            state = np.expand_dims(state, axis=0)
            return np.argmax(self.q_eval_model(state).item())

    def update_train_model(self):
        self.q_target_model.load_state_dict(self.q_eval_model.state_dict())

    def train(self):
        if len(self.memory) < self.batch_size:
            return 0  # as no loss
        batch = self.memory.sample(self.batch_size)
        states, actions, rewards, next_states, dones = self.unpack_batch(batch)

        x = states
        q_eval = self.q_eval_model(x).gather(dim=1, index=actions)
        with torch.no_grad():
            q_next = self.q_target_model(next_states)

            q_eval_next = self.q_eval_model(next_states)
            max_action = torch.argmax(q_eval_next, dim=-1)

            batch_indices = torch.arange(end=self.batch_size, dtype=torch.int32)
            target_value = q_next[batch_indices.long(), max_action] * (1 - dones)

            q_target = rewards + self.gamma * target_value
        loss = self.loss_fn(q_eval, q_target.view(self.batch_size, 1))

        self.optimizer.zero_grad()
        loss.backward()
        # torch.nn.utils.clip_grad_norm_(self.eval_model.parameters(), 100)  # clip gradients to help stabilise training

        # for param in self.Qnet.parameters():
        #     param.grad.data.clamp_(-1, 1)

        self.optimizer.step()
        var = loss.detach().cpu().numpy()

        return var

    def run(self):

        for episode in range(self.max_episodes):
            state = self.env.reset()

            for step in range(self.max_steps):
                action = self.choose_action(episode, state)
                next_state, reward, done, _, = self.env.step(action)
                total_reward = reward + self.get_intrinsic_reward(next_state).detach().clamp(-1, 1)
                self.store(state, total_reward, done, action, next_state)
                self.train()
                if done:
                    break
                state = next_state

            if episode % self.target_update_period == 0:
                self.update_train_model()

    def store(self, state, reward, done, action, next_state):
        state = from_numpy(state).float().to("cpu")
        reward = torch.Tensor([reward]).to("cpu")
        done = torch.Tensor([done]).to("cpu")
        action = torch.Tensor([action]).to("cpu")
        next_state = from_numpy(next_state).float().to("cpu")
        self.memory.add(state, reward, done, action, next_state)

    def get_intrinsic_reward(self, x):
        x = np.expand_dims(x, axis=0)
        predicted_features = self.rnd_predictor_model(x)
        target_features = self.rnd_target_model(x).detach()

        intrinsic_reward = (predicted_features - target_features).pow(2).sum()
        return intrinsic_reward

    def unpack_batch(self, batch):

        batch = Transition(*zip(*batch))

        states = torch.cat(batch.state).to(self.device).view(self.batch_size, *self.state_shape)
        actions = torch.cat(batch.action).to(self.device)
        rewards = torch.cat(batch.reward).to(self.device)
        next_states = torch.cat(batch.next_state).to(self.device).view(self.batch_size, *self.state_shape)
        dones = torch.cat(batch.done).to(self.device)
        states = states.permute(dims=[0, 3, 2, 1])
        actions = actions.view((-1, 1))
        next_states = next_states.permute(dims=[0, 3, 2, 1])
        return states, actions, rewards, next_states, dones