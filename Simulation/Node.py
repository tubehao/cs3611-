class Node(object):
    m = 11
    ring_size = 2 ** m
    def __init__(self, node_id, m):
        self.node_id = node_id
        self.predecessor = self
        self.successor = self
        self.data = dict()
        self.fingers_table = [self]*m
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
        for i in range(1, len(self.fingers_table)):
            temp_node, _ = self.find_successor(self.node_id + 2 ** i)
            self.fingers_table[i] = temp_node
    def closest_preceding_node(self, node, hashed_key):
        for i in range(len(node.fingers_table)-1, 0, -1):
            if self.distance(node.fingers_table[i-1].node_id, hashed_key) < self.distance(node.fingers_table[i].node_id, hashed_key):
                return node.fingers_table[i-1]
        return node.fingers_table[-1]
    def distance(self, n1, n2):
        return n2-n1 if n1 <= n2 else self.ring_size - n1 + n2
    def find_successor(self, key):
        if self.node_id == key:
            return self, 1
        if self.distance(self.node_id, key) <= self.distance(self.successor.node_id, key):
            return self.successor, 1
        else:
            succ, path = self.closest_preceding_node(self, key).find_successor(key)
            return succ, path+1
