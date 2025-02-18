import hashlib
import os
import sys
from random import choice, sample
import concurrent.futures
import time
import threading
import pydotplus
from PIL import Image
from lstmNode import Node
class NetworkError(Exception):
    def __init__(self, msg='[-]Network Error!', *args, **kwargs):
        super().__init__(msg, *args, **kwargs)
class Network:
    def __init__(self, m, node_ids):
        self.nodes = []
        self.m = m
        self.ring_size = 2 ** m
        self.insert_first_node(node_ids[0])
        self.first_node = self.nodes[0]
        node_ids.pop(0)
        self.times = 0
    def __str__(self):
        return f'Chord network:\n |Nodes Alive: {len(self.nodes)} nodes. \n |Total Capacity: {self.ring_size} nodes. \n |Parameter m: {self.m} \n |First Node Inserted: {self.first_node.node_id} \n '
    def print_network(self):
        for node in self.nodes:
            node.print_fingers_table()
            print(node.data)
    def fix_network_fingers(self):
        self.first_node.fix_fingers()
        curr = self.first_node.fingers_table[0]
        while curr != self.first_node:
            curr.fix_fingers()
            curr = curr.fingers_table[0]
    def hash_function(self, key):
        num_bits = Node.m
        bt = hashlib.sha1(str.encode(key)).digest()
        req_bytes = (num_bits + 7) // 8
        hashed_id = int.from_bytes(bt[:req_bytes], 'big')
        if num_bits % 8:
            hashed_id >>= 8 - num_bits % 8
        return hashed_id
    def create_node(self, node_id):
        node = Node(node_id, self.m)
        return node
    def insert_nodes(self, nodes):
        for node in nodes:
            try:
                if(node.node_id > self.ring_size):
                    raise NetworkError(
                        '[-]Node id should be smaller or equal to the networks size.')
                print(
                    f'[+]Node {node.node_id} joined the network via node: {self.first_node.node_id}')
                node.join(self.first_node)
            except NetworkError as e:
                print(e)
    def insert_node(self, node_id):
        self.times += 1
        try:
            if(node_id > self.ring_size):
                raise NetworkError(
                    '[-]Node id should be smaller or equal to the networks size.')
            self.nodes.append(self.create_node(node_id))
            node = self.nodes[-1]
            print(
                f'[+]Node {node.node_id} joined the network via node: {self.first_node.node_id}')
            node.join(self.first_node)
            if self.times % 20 == 0:
                self.fix_network_fingers()
        except NetworkError as e:
            print(e)
    def delete_node(self, node_id):
        try:
            node = list(filter(lambda temp_node: temp_node.node_id ==
                               node_id, self.nodes))[0]
        except:
            print(f'[-]Node {node_id} wasn\'t found!')
        else:
            node.leave()
            self.nodes.remove(node)
            self.fix_network_fingers()
    def insert_first_node(self, node_id):
        print(f'[!]Initializing network , inserting first node {node_id}\n')
        node = Node(node_id, self.m)
        self.nodes.append(node)
    def find_data(self, data):
        hashed_key = self.hash_function(data)
        node = self.first_node
        node, path = node.find_successor(hashed_key)
        found_data = node.data.get(hashed_key, None)
        node.train_model(hashed_key)
        if found_data != None:
            print(
                f'[+]Found \'{data}\' in node {node.node_id} with key {hashed_key}, pathLength: {path}')
        else:
            print(f'[-]\'{data}\' not exist in the network')
        return path
    def insert_data(self, key):
        node = self.first_node
        hashed_key = self.hash_function(key)
        print(
            f'[+]Saving Key:{key} with Hash:{hashed_key} -> Node:{node.find_successor(hashed_key)[0].node_id}, path: {node.find_successor(hashed_key)[1]}')
        succ, path = node.find_successor(hashed_key)
        succ.data[hashed_key] = key
        node.fix_fingers()
        return path
    def delete_data(self, value):
        hashed_key = self.hash_function(value)
        node = self.first_node
        node, path = node.find_successor(hashed_key)
        if hashed_key in node.data:
            del node.data[hashed_key]
            print(f'[+]Deleted \'{value}\' from node {node.node_id} with key {hashed_key}, pathLength: {path}')
        else:
            print(f'[-]\'{value}\' not found in the network')
        return path
    def generate_fake_data(self, num):
        extensions = ['.txt', '.png', '.doc', '.mov', '.jpg', '.py']
        files = [f'file_{i}'+choice(extensions) for i in range(num)]
        start_time = time.time()
        for temp in files:
            self.insert_data(temp)
        print(f'\n {float(time.time() - start_time)/num} seconds ---')
    def print_network(self):
        f = open('graph.dot', 'w+')
        f.write('digraph G {\r\n')
        for node in self.nodes:
            data = 'Keys:\n-------------\n'
            f.write(f'{node.node_id} -> {node.successor.node_id}\r\n')
            for key in sorted(node.data.keys()):
                data += f'key: {key} - data: \'{node.data[key]}\'\n'
            fingers = 'Finger Table:\n-------------\n'
            for i in range(self.m):
                fingers += f'{(node.node_id + 2 ** i) % self.ring_size} : {node.fingers_table[i].node_id}\n'
            if data != '' and data != 'Keys:\n-------------\n':
                f.write(
                    f'data_{node.node_id} [label=\"{data}\", shape=box]\r\n')
                f.write(f'{node.node_id}->data_{node.node_id}\r\n')
            if fingers != '':
                f.write(
                    f'fingers_{node.node_id} [label=\"{fingers}\", shape=box]\r\n')
                f.write(f'{node.node_id}->fingers_{node.node_id}\r\n')
        f.write('}')
        f.close()
        try:
            graph_a = pydotplus.graph_from_dot_file('graph.dot')
            graph_a.write_png('graph.png', prog='circo')
            graph_image = Image.open('graph.png')
            graph_image.show()
        except pydotplus.graphviz.InvocationException:
            pass
    def periodic_fix(self):
        threading.Timer(15, self.fix_network_fingers).start()
