import torch
import torch.nn as nn
import numpy as np
import hashlib
class LSTMPredictor(nn.Module):
    def __init__(self, input_size, hidden_size, output_size, num_layers=1):
        super(LSTMPredictor, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, output_size)
    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])
        return out
class Node(object):
    m = 11
    ring_size = 2 ** m
    def __init__(self, node_id, m):
        self.node_id = node_id
        self.predecessor = self
        self.successor = self
        self.data = dict()
        self.fingers_table = [self]*m
        self.access_count = {}
        self.access_history = {}
        self.lstm_model = LSTMPredictor(input_size=1, hidden_size=50, output_size=1)
        self.criterion = nn.MSELoss()
        self.optimizer = torch.optim.Adam(self.lstm_model.parameters(), lr=0.001)
    def __str__(self):
        return f'Node {self.node_id}'
    def __lt__(self, other):
        return self.node_id < other.node_id
    def print_fingers_table(self):
        print(
            f'Node: {self.node_id} has Successor:{self.successor.node_id}  and Pred:{self.predecessor.node_id}')
        print('Finger Table:')
        for i in range(self.m):
            print(
                f'{(self.node_id + 2 ** i) % self.ring_size} : {self.fingers_table[i].node_id}')
    def record_access(self, key):
        if key in self.access_count:
            self.access_count[key] += 1
        else:
            self.access_count[key] = 1
        if key not in self.access_history:
            self.access_history[key] = []
        self.access_history[key].append(self.access_count[key])
    def train_model(self, key):
        if self.access_history.get(key) is None:
            return
        if len(self.access_history[key]) < 10:
            return  
        sequence = torch.tensor(self.access_history[key], dtype=torch.float).view(-1, 1, 1)
        target = sequence[1:]
        sequence = sequence[:-1]
        self.optimizer.zero_grad()
        output = self.lstm_model(sequence)
        loss = self.criterion(output, target)
        loss.backward()
        self.optimizer.step()
    def predict_access(self, key):
        if key not in self.access_history or len(self.access_history[key]) < 10:
            return 0
        with torch.no_grad():
            sequence = torch.tensor(self.access_history[key], dtype=torch.float).view(-1, 1, 1)
            prediction = self.lstm_model(sequence)
        return prediction[-1].item()
    def join(self, node):
        succ_node, path = node.find_successor(self.node_id)
        pred_node = succ_node.predecessor
        self.find_node_place(pred_node, succ_node)
        self.fix_fingers()
        self.take_successor_keys()
    def leave(self):
        self.predecessor.successor = self.successor
        self.predecessor.fingers_table[0] = self.successor
        self.successor.predecessor = self.predecessor
        for key in sorted(self.data.keys()):
            self.successor.data[key] = self.data[key]
    def find_node_place(self, pred_node, succ_node):
        pred_node.fingers_table[0] = self
        pred_node.successor = self
        succ_node.predecessor = self
        self.fingers_table[0] = succ_node
        self.successor = succ_node
        self.predecessor = pred_node
    def take_successor_keys(self):
        self.data = {key: self.successor.data[key] for key in sorted(
            self.successor.data.keys()) if key <= self.node_id}
        for key in sorted(self.data.keys()):
            if key in self.successor.data:
                del self.successor.data[key]
    def fix_fingers(self):
        print("fix_finger_______________________________")
        predictions = {key: self.predict_access(key) for key in self.access_history.keys()}
        sorted_keys = sorted(predictions.keys(), key=lambda k: predictions[k], reverse=True)
        print("Predictions:", predictions)
        print("Sorted Keys:", sorted_keys)
        for i in range(1, len(self.fingers_table)):
            start = (self.node_id + 2 ** i) % self.ring_size
            end = (self.node_id + 2 ** (i + 1)) % self.ring_size
            print(f"Updating finger {i}, start: {start}, end: {end}")
            found = False
            for hot_key in sorted_keys:
                hot_key_hashed = hot_key
                if start < end:
                    if start < hot_key_hashed <= end:
                        self.fingers_table[i], _ = self.find_successor(hot_key_hashed)
                        print(f"Finger {i} updated to hot key {hot_key} with node {self.fingers_table[i].node_id}")
                        found = True
                        break
                else:
                    if start < hot_key_hashed or hot_key_hashed <= end:
                        self.fingers_table[i], _ = self.find_successor(hot_key_hashed)
                        print(f"Finger {i} updated to hot key {hot_key} with node {self.fingers_table[i].node_id}")
                        found = True
                        break
            if not found:
                self.fingers_table[i], _ = self.find_successor(start)
                print(f"Finger {i} updated to node {self.fingers_table[i].node_id}")
        print("finish fix finger")
    def closest_preceding_node(self, node, hashed_key):
        for i in range(len(node.fingers_table)-1, 0, -1):
            if self.distance(node.fingers_table[i-1].node_id, hashed_key) < self.distance(node.fingers_table[i].node_id, hashed_key):
                return node.fingers_table[i-1]
        return node.fingers_table[-1]
    def distance(self, n1, n2):
        return n2-n1 if n1 <= n2 else self.ring_size - n1 + n2
    def find_successor(self, key):
        print(f"find_successor called with key: {key}")
        if self.node_id == key:
            print(f"Node {self.node_id} is the successor of key {key}")
            return self, 1
        if self.distance(self.node_id, key) <= self.distance(self.successor.node_id, key):
            print(f"Node {self.successor.node_id} is the successor of key {key}")
            self.record_access(key)
            return self.successor, 1
        next_node = self.closest_preceding_node(self, key)
        print(f"Closest preceding node for key {key} is {next_node.node_id}")
        next_node, path = next_node.find_successor(key)
        self.record_access(key)
        return next_node, path+1
