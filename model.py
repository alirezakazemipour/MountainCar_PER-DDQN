from torch import nn
import torch.nn.functional as F


class Model(nn.Module):
    def __init__(self, n_states, n_actions):
        super(Model, self).__init__()
        self.n_states = n_states
        self.n_actions = n_actions

        self.fc1 = nn.Linear(self.n_states, 128)
        self.q_values = nn.Linear(128, self.n_actions)

        nn.init.kaiming_normal_(self.fc1.weight)
        self.fc1.bias.data.zero_()

        nn.init.xavier_uniform_(self.q_values.weight)
        self.q_values.bias.data.zero_()

    def forward(self, inputs):
        x = inputs
        x = F.relu(self.fc1(x))
        return self.q_values(x)


class RNDModel(nn.Module):
    def __init__(self, n_states, n_outputs):
        super(RNDModel, self).__init__()
        self.n_states = n_states
        self.n_outputs = n_outputs

        self.fc1 = nn.Linear(self.n_states, 128)
        self.encoded_features = nn.Linear(128, self.n_outputs)

        nn.init.kaiming_normal_(self.fc1.weight)
        self.fc1.bias.data.data.zero_()

        nn.init.xavier_uniform_(self.encoded_features.weight)
        self.encoded_features.bias.data.zero_()

    def forward(self, inputs):
        x = inputs
        x = F.relu(self.fc1(x))
        return self.encoded_features(x)
