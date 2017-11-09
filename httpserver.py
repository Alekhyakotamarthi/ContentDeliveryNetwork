
#Importing required libraries
import random
import socket, sys
import getopt
import urllib2
import os
import errno
from urllib2 import *
from SocketServer import ThreadingMixIn
#import SimpleHTTPServer
import BaseHTTPServer
import threading

# Length for keeping track of data
datalength=0
# Max file size
max_file_size=10000000

# Class for implementing Multithreading
class ThreadingSimpleServer(ThreadingMixIn, BaseHTTPServer.HTTPServer):
    pass

#  Function to send response to the client
class myHTTPHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    #Function to send response to the client
    def sendResponse(self, responseData):

        # First set the response code to OK
        self.send_response(200)
        # Set content type to plain
        self.send_header('Content-type','text/plain')
        self.end_headers()
        #Write data to the client
        self.wfile.write(responseData)

    #Function to initialize the server's cache and origin server   
    def __init__(self,originserver,cacheditems, *args):
       self.originserver = originserver
       self.cacheditems = cacheditems
       BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, *args)

    # This function  handles all the incoming requests to the HTTPServer
    def do_GET(self):

    # Checking to see if the file is in the cache
        if self.path in self.cacheditems:
            # If the file exists in cache send it to the client from cache            
            self.WriteResponseFromCache()
                       
        else:            
            try:
                # File is not in the cache. Connect to the originserver and get the file from there
                originrequest = 'http://'+self.originserver+':8080'+self.path
                response = urlopen(originrequest)
                    #First send the response to the client                    
                responsecopy = response.read()
                self.sendResponse(responsecopy)
                # Check wehther the file size is greater than the max file size
                if len(responsecopy) < max_file_size:
                    global datalength
                    datalength+=len(responsecopy)
                        # If the size of the file exceeds 10MB then LFU is done
                    if datalength < max_file_size:
                            # Update cache
                        self.WriteResponseToCache(responsecopy)
                    else:
                        while datalength >= max_file_size:
                            # If cache is empty to do LFU then print the respective error message
                            # Ordered dictionary to pop out LFU value
                            # Get the file name to be popped
                            minkey=min(self.cacheditems, key=self.cacheditems.get)   
                            removed=self.cacheditems.pop(minkey, None)
                            # Get the length of the file data
                            requestedfile= open(os.getcwd()+minkey,'r')
                                
                            lenoffile=len(requestedfile.read())
                            
                            # delete the length of data
                            datalength-=lenoffile

                            requestedfile.close()
                            # Remove the file from the cache
                            os.remove(os.getcwd()+minkey)

                        # Send response to the client   
                        self.WriteResponseToCache(responsecopy)

            except (HTTPError,URLError,IOError) as ex:
                #Sends error if the request to origin server gives back a 404 or any other error code
                self.send_error(ex.code,ex.reason)
                return
            except:
                #Generic exception
                print 'Exception in GET'
                raise

    def WriteResponseToCache(self, response):
        #this function is used to update the cache
        #gets the current working directory and appends the path
        pathtodownload = os.getcwd() +self.path
        
        # Directory in which all the files should be created
        directorytocreate = os.path.split(pathtodownload)[0]
        
        #If the directory does not exist
        if not os.path.exists(directorytocreate):
            os.makedirs(directorytocreate)
        file1 = open(pathtodownload,'w')

        try:
            #write response to the file
            file1.write(response)
            #update cache with the path
            self.cacheditems[self.path]=1
            file1.close()
           
        except IOError:
            
            print IOError.reason
        

    def WriteResponseFromCache(self):
        # File already there in cache, respond to client with the file
        
        abspath = os.getcwd() +self.path
       
        requestedfile = open(abspath, 'r')
        # Read the data and sent it
        self.sendResponse(requestedfile.read())
        requestedfile.close()
        # Increase the counts accordingly
        self.cacheditems[self.path]+=1


# Function to send the arguments to the handler function
def PassArgsForHandlerInit(originserver,mycache):
    return lambda *args: myHTTPHandler(originserver,mycache, *args)

# Main program: check the parameters
try:
    if len(sys.argv)!=5 or sys.argv[3]!="-o" or sys.argv[1]!="-p":
        print "Enter correct parameters"
        sys.exit()
    portnumber = int(sys.argv[2])
    originserver = sys.argv[4]
    #cache is initially empty
    mycache ={}
    myhandler = PassArgsForHandlerInit(originserver,mycache)
    #Threading - multi threading
    ThreadingSimpleServer(('',portnumber),myhandler).serve_forever()
except:
    print 'Exception in Http connection ' 
    raise
