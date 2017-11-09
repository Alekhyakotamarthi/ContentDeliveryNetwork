import math

import urllib2

from struct import *

import socket

import threading

import re

from Queue import Queue
from threading import Thread



hosts=[]

URL='http://ipinfo.io/'

SCAMPER_PORT = 55006

rtt_hashmap = {}



def best_replica(target_ip):

    if is_private(target_ip):

        return '54.255.148.115'

    rtt_map = measure_AllRTT(target_ip)
    
    if not len(set(rtt_map.values())) > 2:

        geo_map = replica_geo(target_ip)       

        best_ec2=sorted([(value,key) for (key,value) in geo_map.items()])
        
        return best_ec2[0][1]

    else:

        best_ec2=sorted([(value,key) for (key,value) in rtt_map.items()])
        
        return best_ec2[0][1]

# Generic implementation of threadpool
# Worker threads in thread pool are spawned here
class WorkerThread(Thread):
    
    def __init__(self, functions):
        Thread.__init__(self)
        # The list of functions that the thread has to perform
        self.functions = functions
        # So the thread can be a background thread and doesnt block the 
        # application from closing
        self.daemon = True
        # Start thread
        self.start()

    def run(self):
        # Defines what each of the threads has to do
        while True:
            # If the function has additional arguments, they would be stored here
            func,arguments,additionalargs = self.functions.get()
            try:
                func(*arguments,**additionalargs)
            except Exception,e:
                print e
            finally:
                #Finish the task
                self.functions.task_done()
#Threadpool class
class Pool:
    #Initialize the pool with the number of threads    
    def __init__(self):
        # Add all functions into the Queue of functions
        self.functions = Queue(10)
        #Initialize the threads
        i=0
        while i<10:
            WorkerThread(self.functions)
            i+=1
        
    #Adds function to the queue of my functions
    def addtoqueue(self, func,*arguments,**additionalargs):
            self.functions.put((func,arguments,additionalargs))
    # Waits for all threads to finish their tasks
    def waitforcompletion(self):
            self.functions.join()        

def run(host,target):

        mysocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        ip =socket.gethostbyname(host)
    
        try:

            mysocket.connect((ip,SCAMPER_PORT))

            mysocket.sendall(target)

            RTT = mysocket.recv(1024)
        
            print host,"IP:RTT",RTT
        except socket.error as e:

            print str(e)

            RTT = 'inf'

        finally:
            
            rtt_hashmap.update({host: float(RTT)})

            mysocket.close()



def measure_AllRTT(client):

    pool = Pool()
    f=open("replicas",'r')
    replicas=f.readlines()
    f.close()
    for ip in replicas:
        ipaddr=ip.split(':')[0]
        pool.addtoqueue(run, ipaddr,client)
   
    pool.waitforcompletion()

    return rtt_hashmap

def get_location(ip):

    res = urllib2.urlopen(URL +ip+'/json')

    location = res.read().split(',')

    return float(location[5][11:]), float(location[6].strip('"'))



def get_distance(target, src):

    return math.sqrt(math.pow((src[1] - target[1]),2) + math.pow((src[0] - target[0]),2))

       

def  replica_geo(target_ip):

    

    distance = {}

    f=open("replicas",'r')
    replicas=f.readlines()
    f.close()
   

    target_address = get_location(target_ip)

    for replica in replicas:
        ip=replica.split(':')[0]
        lat=float(replica.split(':')[1])
        lon=float(replica.split(':')[2])
        location=(lat,lon)


        distance[ip] = get_distance(target_address, location)

    return distance



def is_private(ip):

    private_ip=re.compile("^(?:10|127|172\.(?:1[6-9]|2[0-9]|3[01])|192\.168)\..*")

    return private_ip.match(ip)



#best_replica('8.8.8.8')

