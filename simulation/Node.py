import socket
import threading
import time
import hashlib
import random
import sys
from copy import deepcopy
import sys
ring = {}
m = 7
ip = "127.0.0.1"
def nodeInf(port, ip = "127.0.0.1"):
    return ip + "|" + str(port) 

def hash(message):
    digest = hashlib.sha256(message.encode()).hexdigest()
    digest = int(digest, 16) % pow(2, m)
    return digest 


# The class DataStore is used to store the key value pairs at each node

class DataStore:
    def __init__(self):
        self.data = {}
    def insert(self, key, value):
        self.data[key] = value
    def delete(self, key):
        del self.data[key]
    def search(self, search_key):
        # print('Search key', search_key)
        if search_key in self.data:
            return self.data[search_key]
        else:
            # print('Not found')
            print(self.data)
            return None
#Class represents the actual Node, it stores ip and port of a node       
class NodeInfo:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
    def __str__(self):
        return self.ip + "|" + str(self.port)  
# The class Node is used to manage the each node that, it contains all the information about the node like ip, port,
# the node's successor, finger table, predecessor etc. 
class Node:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = int(port)
        self.nodeinfo = NodeInfo(ip, port)
        self.id = hash(str(self.nodeinfo))
        # print(self.id)
        self.predecessor = None
        self.successor = None
        self.finger_table = FingerTable(self.id)
        self.data_store = DataStore()
        self.request_handler = RequestHandler()

        self.exist = True

    def hash(self, message):
        # This function is used to find the id of any string and hence find it's correct position in the ring
        digest = hashlib.sha256(message.encode()).hexdigest()
        digest = int(digest, 16) % pow(2,m)
        return digest

    def process_requests(self, message):

        # The process_requests function is used to manage the differnt requests coming to any node it checks the message
        # and then calls the required function accordingly

        operation = message.split("|")[0]
        args = []
        if( len(message.split("|")) > 1):
            args = message.split("|")[1:]
        result = "Done"
        if operation == 'insert_server':
            # print('Inserting in my datastore', str(self.nodeinfo))
            data = message.split('|')[1].split(":")
            key = data[0]
            value = data[1]
            self.data_store.insert(key, value)
            result = 'Inserted'

        if operation == "delete_server":
            # print('deleting in my datastore', str(self.nodeinfo))
            data = message.split('|')[1]
            self.data_store.data.pop(data)
            result = 'Deleted'

        if operation == "search_server":
            # print('searching in my datastore', str(self.nodeinfo))
            data = message.split('|')[1]
            if data in self.data_store.data:
                return self.data_store.data[data]
            else:
                return "NOT FOUND"

        if operation == "send_keys":
            id_of_joining_node = int(args[0])
            result = self.send_keys(id_of_joining_node)

        if operation == "insert":
            # print("finding hop to insert the key" , str(self.nodeinfo) )
            data = message.split('|')[1].split(":")
            key = data[0]
            value = data[1]
            result = self.insert_key(key,value)


        if operation == "delete":
            # print("finding hop to delete the key" , str(self.nodeinfo) )
            data = message.split('|')[1]
            result = self.delete_key(data)


        if operation == 'search':
            # print('Seaching...')
            data = message.split('|')[1]
            result = self.search_key(data)



        if operation == "join_request":
            # print("join request recv")
            result  = self.join_request_from_other_node(int(args[0]))

        if operation == "find_predecessor":
            # print("finding predecessor")
            result, pathLength = self.find_predecessor(int(args[0]))
            result =  str(result)+"@"+str(pathLength)

        if operation == "find_successor":
            # print("finding successor")
            result, _ = self.find_successor(int(args[0]), False)

        if operation == "get_successor":
            # print("getting successor")
            result = self.get_successor()

        if operation == "get_predecessor":
            # print("getting predecessor")
            result = self.get_predecessor()

        if operation == "get_id":
            # print("getting id")
            result = self.get_id()

        if operation == "notify":
            # print("notifiying")
            self.notify(int(args[0]),args[1],args[2])
        # print(result)
        return str(result)
    # def serve_requests(self, conn, addr):
        
        # The serve_requests fucntion is used to listen to incoming requests on the open port and then reply to them, it 
        # takes as arguments the connection and the address of the connected device. 
        
        # with conn:
        #     # print('Connected by', addr)
            
        #     data = conn.recv(1024)
            
        #     data = str(data.decode('utf-8'))
        #     data = data.strip('\n')
        #     # print(data)
        #     data = self.process_requests(data)
        #     # print('Sending', data)
        #     data = bytes(str(data), 'utf-8')
        #     conn.sendall(data)
    def serve_requests(self, message):
        message = message.strip('\n')
        data = self.process_requests(message)
        return data

    def start(self):
        # The start function creates 3 threads for each node:
        # On the 1st thread the stabilize function is being called repeatedly in a definite interval of time
        # On the 2nd thread the fix_fingers function is being called repeatedly in a definite interval of time
        # and on the 3rd thread the serve_requests function is running which is continously listening for any new
        # incoming requests
        thread_for_stabalize = threading.Thread(target = self.stabilize)
        thread_for_stabalize.start()
        thread_for_fix_finger = threading.Thread(target=  self.fix_fingers)
        thread_for_fix_finger.start()
        # with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        #     s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        #     s.bind((self.nodeinfo.ip, self.nodeinfo.port))
        #     s.listen()
        #     while True:
        #         conn, addr = s.accept()
        #         t = threading.Thread(target=self.serve_requests, args=(conn,addr))
        #         t.start()   
    def append_to_log(self, operation, node_info, key, value, message):
        with open('log.txt', 'a') as log_file:
            log_file.write(str(time.time()) + " , " + operation + " , " + str(node_info) + " , " + key + " ,pathLength:" + str(message) + '\n')
    
    def insert_key(self,key,value):

        # The function to handle the incoming key_value pair insertion request from the client this function searches for the
        # correct node on which the key_value pair needs to be stored and then sends a message to that node to store the 
        # key_val pair in its data_store
        id_of_key = hash(str(key))
        succ, pathLength = self.find_successor(id_of_key, True)
        self.append_to_log('insert', (self.nodeinfo.ip, self.nodeinfo.port), str(key), str(value), pathLength)
        # print("Succ found for inserting key" , id_of_key , succ)
        ip,port = self.get_ip_port(succ)
        self.request_handler.send_message(ip,port,"insert_server|" + str(key) + ":" + str(value) )
        return "Inserted at node id " + str(Node(ip,port).id) + " key was " + str(key) + " key hash was " + str(id_of_key)  

    def delete_key(self,key):
        
        # The function to handle the incoming key_value pair deletion request from the client this function searches for the
        # correct node on which the key_value pair is stored and then sends a message to that node to delete the key_val
        # pair in its data_store.
        id_of_key = hash(str(key))
        succ, pathLength = self.find_successor(id_of_key, True)
        self.append_to_log('insert', (self.nodeinfo.ip, self.nodeinfo.port), str(key), "True", pathLength)

        # print("Succ found for deleting key" , id_of_key , succ)
        ip,port = self.get_ip_port(succ)
        self.request_handler.send_message(ip,port,"delete_server|" + str(key) )
        return "deleted at node id " + str(Node(ip,port).id) + " key was " + str(key) + " key hash was " + str(id_of_key)


    def search_key(self,key):
        # The function to handle the incoming key_value pair search request from the client this function searches for the
        # correct node on which the key_value pair is stored and then sends a message to that node to return the value 
        # corresponding to that key.
        id_of_key = hash(str(key))
        succ, pathLength = self.find_successor(id_of_key, True)
        self.append_to_log('insert', (self.nodeinfo.ip, self.nodeinfo.port), str(key), "True", pathLength)

        # print("Succ found for searching key" , id_of_key , succ)
        ip,port = self.get_ip_port(succ)
        data = self.request_handler.send_message(ip,port,"search_server|" + str(key) )
        return data




    def join_request_from_other_node(self, node_id):
        # will return successor for the node who is requesting to join
        return self.find_successor(node_id, False)[0]

    def join(self,node_ip, node_port):

        # this function is responsible to join any new nodes to the chord ring ,it finds out the successor and the predecessor of the
        # new incoming node in the ring and then it sends a send_keys request to its successor to recieve all the keys
        # smaller than its id from its successor.
        data = 'join_request|' + str(self.id)
        succ = self.request_handler.send_message(node_ip,node_port,data)
        # print("succ",succ)
        ip,port = self.get_ip_port(succ)
        # self.successor = Node(ip,port)!!!
        self.successor = ring[hash(str(nodeInf(port, ip)))]
        self.finger_table.table[0][1] = self.successor
        self.predecessor = self.successor.predecessor
        self.predecessor.successor = ring[self.id]

        if self.successor.id != self.id:
            data = self.request_handler.send_message(self.successor.ip , self.successor.port, "send_keys|"+str(self.id))
            # print("data recieved" , data)
            for key_value in data.split(':'):
                if len(key_value) > 1:
                    # print(key_value.split('|'))
                    self.data_store.data[key_value.split('|')[0]] = key_value.split('|')[1]

    def find_predecessor(self, search_id):
        # The find_predecessor function provides the predecessor of any value in the ring given its id.
        # print("finding pred for id ", search_id)
        if self.predecessor is not None and  self.successor.id == self.id:
            # print("teri maa ki ankh"+self.nodeinfo.__str__())
            return self.nodeinfo.__str__(), 1
        if self.get_forward_distance(self.successor.id) > self.get_forward_distance(search_id):  # 当前节点在后面比当前节点的后继在后面的少
            # print("yaar tu gandu hai kya"+self.nodeinfo.__str__())
            return self.nodeinfo.__str__(), 1
        else:
            new_node_hop = self.closest_preceding_node(search_id)
            # print("new node hop finding hops in find predecessor" , new_node_hop.nodeinfo.__str__() )
            if new_node_hop is None:
                return "None", 0
            ip, port = self.get_ip_port(new_node_hop.nodeinfo.__str__())
            if ip == self.ip and port == self.port:
                return self.nodeinfo.__str__(), 0

            max_retries = 10
            base_wait_time = 1

            for attempt in range(max_retries):
                data = self.request_handler.send_message(ip, port, "find_predecessor|" + str(search_id))
                if data:
                    data = data.split('@')
                    if len(data) < 2:
                        print(f"Unexpected data format: {data}")
                        continue
                    return data[0], int(data[1]) + 1
                wait_time = base_wait_time * (2 ** attempt)
                print(f"Attempt {attempt + 1} failed, retrying in {wait_time} seconds...")
                time.sleep(wait_time)

            return "None", 0

    def find_successor(self, search_id, flag = False):
        
        # The find_successor function provides the successor of any value in the ring given its id.
        
        if(search_id == self.id):
            return str(self.nodeinfo), 1
        # print("finding succ for id ", search_id)
        predecessor, pathLength = self.find_predecessor(search_id)
        # print("Path length", pathLength)
        # print(flag)
        # if (flag == True): print("Path length", pathLength)
        # print("predcessor found is ", predecessor)
        if(predecessor == "None"):
            return "None", 0
        ip,port = self.get_ip_port(predecessor)
        # print(ip ,port , "in find successor, data of predecesor")
        data = self.request_handler.send_message(ip , port, "get_successor")
        return data, pathLength

    def closest_preceding_node(self, search_id):
        closest_node = None
        min_distance = pow(2,m)+1
        for i in list(reversed(range(m))):
            # print("checking hops" ,i ,self.finger_table.table[i][1])
            if  self.finger_table.table[i][1] is not None and self.get_forward_distance_2nodes(self.finger_table.table[i][1].id,search_id) < min_distance  :
                closest_node = self.finger_table.table[i][1]
                min_distance = self.get_forward_distance_2nodes(self.finger_table.table[i][1].id,search_id)
                # print("Min distance",min_distance)

        return closest_node

    def send_keys(self, id_of_joining_node):
        # The send_keys function is used to send all the keys less than equal to the id_of_joining_node to the new node that
        # has joined the chord ring.
        # print(id_of_joining_node , "Asking for keys")
        data = ""
        keys_to_be_removed = []
        self.predecessor = ring[id_of_joining_node]
        for keys in self.data_store.data:
            key_id = hash(str(keys))
            if self.get_forward_distance_2nodes(key_id , id_of_joining_node) < self.get_forward_distance_2nodes(key_id,self.id):
                data += str(keys) + "|" + str(self.data_store.data[keys]) + ":"
                keys_to_be_removed.append(keys)
        for keys in keys_to_be_removed:
            self.data_store.data.pop(keys)
        return data

    
    def stabilize(self):
        
        # The stabilize function is called in repetitively in regular intervals as it is responsible to make sure that each 
        # node is pointing to its correct successor and predecessor nodes. By the help of the stabilize function each node
        # is able to gather information of new nodes joining the ring. 
        while self.exist:
            time.sleep(10)
            if self.exist == False:
                break
            if self.successor is None:
                time.sleep(10)
                continue
            data = "get_predecessor"

            if self.successor.ip == self.ip  and self.successor.port == self.port:
                time.sleep(10)
            # print(self.id, self.successor.id, "stabilizing")
            result = self.request_handler.send_message(self.successor.ip , self.successor.port , data)
            if result == "None" or result == None or len(result) == 0:
                self.request_handler.send_message(self.successor.ip , self.successor.port, "notify|"+ str(self.id) + "|" + self.nodeinfo.__str__())
                continue

            # print("found predecessor of my sucessor", result, self.successor.id)
            ip, port = self.get_ip_port(result)
            result = int(self.request_handler.send_message(ip,port,"get_id"))
            if self.get_backward_distance(result) > self.get_backward_distance(self.successor.id):
                # print("changing my succ in stablaize", result)
                self.successor = ring[hash(str(nodeInf(port, ip)))]
                self.finger_table.table[0][1] = self.successor
            self.request_handler.send_message(self.successor.ip , self.successor.port, "notify|"+ str(self.id) + "|" + self.nodeinfo.__str__())
            # print("===============================================")
            # print("STABILIZING")
            # print("===============================================")
            # print("ID: ", self.id)
            # if self.successor is not None:
            #     print("Successor ID: " , self.successor.id)
            # if self.predecessor is not None:
            #     print("predecessor ID: " , self.predecessor.id)
            # print("===============================================")
            # print("=============== FINGER TABLE ==================")
            # self.finger_table.print()
            # print("===============================================")
            # print("DATA STORE")
            # print("===============================================")
            # print(str(self.data_store.data))
            # print("===============================================")
            # print("+++++++++++++++ END +++++++++++++++++++++++++++")
            # print()
            # print()
            # print()

    def notify(self, node_id , node_ip , node_port):
        # Recevies notification from stabilized function when there is change in successor
        
        if self.predecessor is not None:
            if self.get_backward_distance(node_id) < self.get_backward_distance(self.predecessor.id):
                # print("someone notified me")
                # print("changing my pred", node_id)
                # self.predecessor = Node(node_ip,int(node_port))
                self.predecessor = ring[hash(str(nodeInf(node_port, node_ip)))]
                return
        if self.predecessor is None or self.predecessor == "None" or ( node_id > self.predecessor.id and node_id < self.id ) or ( self.id == self.predecessor.id and node_id != self.id) :
            # print("someone notified me")
            # print("changing my pred", node_id)
            # self.predecessor = Node(node_ip,int(node_port))
            self.predecessor = ring[hash(str(nodeInf(node_port, node_ip)))]
            if self.id == self.successor.id:
                # print("changing my succ", node_id)
                # self.successor = Node(node_ip,int(node_port))
                self.successor = ring[hash(str(nodeInf(node_port, node_ip)))]
                self.finger_table.table[0][1] = self.successor
        
    def fix_fingers(self):
        # The fix_fingers function is used to correct the finger table at regular interval of time this function waits for
        # 10 seconds and then picks one random index of the table and corrects it so that if any new node has joined the 
        # ring it can properly mark that node in its finger table.
        while self.exist:
            time.sleep(5)
            if self.exist == False:
                break
            random_index = random.randint(1,m-1)
            finger = self.finger_table.table[random_index][0]
            # print("in fix fingers , fixing index", random_index)
            data, _ = self.find_successor(finger, False)
            if data == "None":
                time.sleep(10)
                continue
            ip, port = self.get_ip_port(data)
            # self.finger_table.table[random_index][1] = Node(ip,port) !!!
            if ring.get(hash(str(nodeInf(port, ip))) ) != None:
                self.finger_table.table[random_index][1] = ring[hash(str(nodeInf(port, ip)))]

            
    def get_successor(self):
        # This function is used to return the successor of the node
        if self.successor is None:
            return "None"
        return self.successor.nodeinfo.__str__()
    def get_predecessor(self):
        # This function is used to return the predecessor of the node

        if self.predecessor is None:
            return "None"
        return self.predecessor.nodeinfo.__str__()
    def get_id(self):
        # This function is used to return the id of the node
        return str(self.id)
    def get_ip_port(self, string_format):
        # This function is used to return the ip and port number of a given node
        return string_format.strip().split('|')[0] , int(string_format.strip().split('|')[1])
    
    def get_backward_distance(self, node1):
        
        disjance = 0
        if(self.id > node1):
            disjance =   self.id - node1
        elif self.id == node1:
            disjance = 0
        else:
            disjance=  pow(2,m) - abs(self.id - node1)
        # print("BACK ward distance of ",self.id,node1 , disjance)
        return disjance

    def get_backward_distance_2nodes(self, node2, node1):
        
        disjance = 0
        if(node2 > node1):
            disjance =   node2 - node1
        elif node2 == node1:
            disjance = 0
        else:
            disjance=  pow(2,m) - abs(node2 - node1)
        # print("BACK word distance of ",node2,node1 , disjance)
        return disjance

    def get_forward_distance(self,nodeid):
        return pow(2,m) - self.get_backward_distance(nodeid)


    def get_forward_distance_2nodes(self,node2,node1):
        return pow(2,m) - self.get_backward_distance_2nodes(node2,node1)

    def leave(self):
        self.exist = False
        print(self.predecessor.port, self.successor.port, "leaving")
        if self.predecessor is not None:
            self.predecessor.successor = self.successor
            self.predecessor.finger_table.table[0][1] = self.successor
        self.successor.predecessor = self.predecessor
        print(self.predecessor.id, self.successor.id)


        #pass key to successor
        for key in sorted(self.data_store.data.keys()):
            # self.successor.data[key] = self.data[key]
            self.successor.data_store.insert(key, self.data_store.data[key])
            print(key)

# The class FingerTable is responsible for managing the finger table of each node.
class FingerTable:
    # The __init__ fucntion is used to initialize the table with values when 
    # a new node joins the ring.
    def __init__(self, my_id):
        self.table = []
        for i in range(m):
            x = pow(2, i)
            entry = (my_id + x) % pow(2,m)
            node = None
            self.table.append( [entry, node] )
        
    def print(self):
        # The print function is used to print the finger table of a node.
        for index, entry in enumerate(self.table):
            if entry[1] is None:
                print('Entry: ', index, " Interval start: ", entry[0]," Successor: ", "None")
            else:
                print('Entry: ', index, " Interval start: ", entry[0]," Successor: ", entry[1].id)

# The class RequestHandler is used to manage all the requests for sending messages from one node to another 
# the send_message function takes as the ip, port of the reciever and the message to be sent as the arguments and 
# then sends the message to the desired node.
class RequestHandler:

    def __init__(self):
        pass
    def send_message(self, ip, port, message, retries=10, backoff_factor=1.5):
        # attempt = 0
        # s = None
        # while attempt < retries:
        #     try:
        #         s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #         s.connect((ip, port))
        #         s.send(message.encode('utf-8'))
        #         data = s.recv(1024)
        #         return data.decode("utf-8")
        #     except ConnectionRefusedError as e:
        #         print(f"Error checking port {port}: {e}")
        #         attempt += 1
        #         print(f"Attempt {attempt}: Connection to {ip}:{port} refused. Retrying in {backoff_factor ** attempt:.2f} seconds...")
        #         time.sleep(backoff_factor ** attempt)
        #     finally:
        #         if s is not None:
        #             s.close()
        # print(f"Failed to connect to {ip}:{port} after {retries} attempts.")
        # return None
        return nodeMessageProcessor(ip, port, message)


def nodeMessageProcessor(ip, port, message):
    # from chord import Chord
    # print(ring)
    # print(hash(str(nodeInf(port, ip))))
    # print(message)
    if ring.get(hash(str(nodeInf(port, ip))) ) == None:
        print("Node does not exist")
        return None
    receiveNode = ring[hash(str(nodeInf(port, ip)))]
    response = receiveNode.serve_requests(message)
    return response

def addNode(port, ExistingNodePort):
    node = Node(ip, int(port))
    # print(hash(str(nodeInf(port, ip))) == node.id)

    if ring == {}:
        print("creating chord")
        ring[node.id] = node
        node.predecessor = node
        node.successor = node

        node.finger_table.table[0][1] = node
        node.start()
        print("Node added to chord")
        # print(ring)
        return
    elif ring.get(hash(nodeInf(ExistingNodePort))) == None:
        print("Existing node does not exist")
        return
    elif ring.get(hash(nodeInf(port))) == None:
        ring[node.id] = node

        node.join(ip, ExistingNodePort)
        node.start()
        print("Node added to chord")
        return
    else :
        print("Node already exists")
        return

def deleteNode(port):
    leavingNode = ring[hash(str(nodeInf(port)))]
    if leavingNode == None:
        print("Node does not exist")
        return
    leavingNode.leave()
    del ring[hash(str(nodeInf(port)))]

# def leaveChord():
#     for node in ring.values():
#         node.leave()

def enterNode(port, ip = "127.0.0.1"):
    nodeId = hash(str(nodeInf(port, ip)))
    if ring.get(nodeId) == None:
        print("Node does not exist")
        return
    else:
        node = ring[nodeId]
        # print(nodeId)
        display(node)
        return

def display(node):
    print("Node id : ", node.id)
    print("Node ip : ", node.ip)
    print("Node port : ", node.port)
    print("Node finger table : ", node.finger_table.table)
    while(True):
        print("************************MENU*************************")
        print("PRESS ***********************************************")
        print("1. TO ENTER *****************************************")
        print("2. TO SHOW ******************************************")
        print("3. TO DELTE *****************************************")
        print("0. TO EXIT ******************************************")
        print("*****************************************************")
        choice = input()


        if(choice == '1'):
            key = input("ENTER THE KEY : ")
            val = input("ENTER THE VALUE : ")
            message = "insert|" + str(key) + ":" + str(val)
            
            data = nodeMessageProcessor(node.ip, node.port, message)
            print(data)

        elif(choice == '2'):
            key = input("ENTER THE KEY")
            message = "search|" + str(key)
            data = nodeMessageProcessor(node.ip, node.port, message)
            
            print("The value corresponding to the key is : ",data)

        elif(choice == '3'):
            key = input("ENTER THE KEY")
            message = "delete|" + str(key)
            data = nodeMessageProcessor(node.ip, node.port, message)
            print(data)

        elif(choice == '0'):
            print("Exiting Node")
            break
            
        else:
            print("INCORRECT CHOICE")



if __name__ == "__main__":
    node_count = 2

    for i in range(node_count):
        addNode(5000 + i, 5000 + i - 1)


    while(True):
        # print(ring)
        print("************************MENU*************************")
        print("PRESS ***********************************************")
        print("1. Add a node *****************************************")
        print("2. Delete a node ******************************************")
        print("3. Enter a node *****************************************")
        print("0. EXIT ******************************************")
        print("*****************************************************")
        choice = input()

        if(choice == '1'):
            port = input("ENTER THE port : ")
            ExistingNodePort = None
            if ring != {}:
                ExistingNodePort = input("ENTER THE EXISTING NODE PORT (if any): ")
            addNode(port, ExistingNodePort)
            # print(f"Add node id {id} to the chord")
            continue

        elif(choice == '2'):
            port = input("ENTER THE port : ")
            deleteNode(port)
            print(f"Node with port {port} has been deleted")
            continue

        elif(choice == '3'):
            enterNode(input("ENTER THE port : "))
            continue

        elif(choice == '0'):
            print("bye~")
            exit()
            
        else:
            print("INCORRECT CHOICE")
            continue