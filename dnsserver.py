#Importing required Libraries
from struct import *
from best_replica_server import best_replica
import struct
import collections
import random
import socket, sys
import getopt
import SocketServer 

# Dictionary to store the padding values
padding={}

# Function to convert the padding values to Big endian format
def pad(padding):
    # Default pad bits
    padding[1] = 0x0000
    padding[2] = 0x290f
    padding[3] = 0xa000
    padding[4] = 0x0000
    padding[5] = 0x0000
    padding[6] = 0x00
    # Big Endian format
    Big_Endian_format= struct.pack('>HHHHHB',padding.get(1),padding.get(2),padding.get(3),padding.get(4),padding.get(5),padding.get(6))
        
    return Big_Endian_format  

# Function to pack the dns header
def pack_dnsheader(dnsid,flag,count,dns_answercount,nsaccount,arcount):
    packedheader=struct.pack('>HHHHHH',dnsid,flag,count,dns_answercount,nsaccount,arcount) 
    return packedheader

# Function to unpack the dns header
def unpack_dnsheader(header):
    unpackedheader=struct.unpack('>HHHHHH',header)
    return unpackedheader


# Function to pack the dns query
def pack_query(dns_questiontype, dns_questionclass):
    packedquery=struct.pack('>HH', dns_questiontype, dns_questionclass)
    return packedquery

# Function to unpack the dns query
def unpack_query(dns_querydata, q_index):
    #Each is of 2 bytes , hence the format H( unsigned short) and the formatting is done in big endian.
    
    unpackedquery=struct.unpack('>HH',dns_querydata[q_index:q_index+4])
    return unpackedquery


# Function to unpack the dns packet
def unpackDNS(packet, requestdata):
    
    header=requestdata[ :12]
    # Unpacking the header which is of length 12 of the DNS request. 
    unpackeddata=unpack_dnsheader(header)
    
    # dns_id
    packet.dns_id=unpackeddata[0]

    # dns_flag
    packet.dns_flag=unpackeddata[1]

    # dns_questioncount
    packet.dns_qdcount=unpackeddata[2]

    # dns_answercount
    packet.dns_answercount=unpackeddata[3]

    # dns_nscount
    packet.dns_nscount=unpackeddata[4]

    # dns_arcount
    packet.dns_arcount=unpackeddata[5]
    
    #Question data follows after the header. 
    dns_querydata = requestdata[len(header): ]
    
    # Domain name is followed by Question Type and question class
    q_index = dns_querydata.index('\x00')+len('\x00')
        
    
    # Unpacking question type anc question class from Request.
    unpackedquery=unpack_query(dns_querydata, q_index)
    packet.dns_questiontype=unpackedquery[0] 
    packet.dns_questionclass= unpackedquery[1]
    # This piece of code tries to parse the domain name from the query. We need this to check if the domain name is the name of the DNS server.    
    r = dns_querydata[0:q_index]        
    counter=1
    packet.dns_questionname=""
    try :
        count =ord(r[counter-1])
        while count!=0:                       
            packet.dns_questionname+=r[counter:counter+count]+"."
            counter+=count+1
            count =ord(r[counter-1])
        packet.dns_questionname=packet.dns_questionname[:-1]                
            
    except:
        #Default Domain name or Question Name
        print "exception"
        packet.dns_questionname='cs5700cdn.example.com'


# Class to build the DNS Packet
class myDNSPacket():
    # Build the DNS Packet
    def buildDNS(self, ip):
        self.dns_answercount = 1 # Says the Packet has one answer
        self.dns_flag = 0x8180 # All the flags listed below
                            # QR - 1 says it's a response
                            #OPCODE - 0 Standard query
                            #TC - 0 Not truncated
                            # RD - Recurision requested
                            # RA - 1 server can do recursion
                            # Z - 0 Reserved
                            # RCODE - 0 

        # DNS Header of the DNS that was unpacked previously is packed again in Big Endian
        
        dns_header = pack_dnsheader(self.dns_id,self.dns_flag,self.dns_qdcount,self.dns_answercount,self.dns_nscount,self.dns_arcount)
        
        # Reconstructing the domain name that was parsed previously such that the length of the string is followed by the original string. eg: google.com will become 06google03com
        #dns_query=self.dns_questionname.replace(".","")
        
        dns_query=""
        dns_components=self.dns_questionname.split('.')
        for namespace in dns_components:
            chrfromAscii = chr(len(namespace))
            dns_query+=chrfromAscii+namespace
        
        
        # \x00 marks the end of the domain name
        dns_query += '\x00'
       
        # Packing the question type and question class
        complete_query = dns_query + pack_query(self.dns_questiontype, self.dns_questionclass)
        
        #Answername represents that the name is the pointer to the questionname that was constructed previously. 0C marks that the question name is after 12th position in question. 
        dns_answername = 0xC00C
        # answer is of type A
        dns_answertype = 0x0001
        # answer is of class IN
        dns_answerclass = 0x0001
        # The time to TTL for the packets
        dns_answerttl = 0x0000
        dns_answertt2 = 0x0100
        # The answer length that follows. It is 4 for an IP
        dns_answerlength = 0x0004
        # Here are the padding bits that are added to every answer.
        
        # Function to pad the bits
        padding_bits=pad(padding)
        
        # The final answer to be delivered
        complete_answer = struct.pack('>HHHHHH4s',dns_answername,dns_answertype,dns_answerclass,dns_answerttl,dns_answertt2,dns_answerlength, socket.inet_aton(ip));
        
        # Bundling up the packet
        dns_packet = dns_header+ complete_query+ complete_answer
        
        return dns_packet
        


class myDNSHandler(SocketServer.BaseRequestHandler):
    # BaseRequestHandler class is used to run te UDP server.
    # We override the handle function
    def handle(self):
        # The data and client are stored as a pair in the self.request
        requestdata = self.request[0]
        
        #Socket for the UDP Server
        socket= self.request[1]
       
        # Object of the DNS packet to be sent
        packet = myDNSPacket()
        # Unpack the DNS Packet first and load the values in variable called packet.
        unpackDNS(packet,requestdata)
        
        # We will be dealing with QTYPE A requests for the assignment
        if packet.dns_questiontype == 1 and packet.dns_questionname == self.server.name:
            
            # Retreive the client ip 
            client_ip = self.client_address[0]

            # Match the ip to the best available replica servers
            ip = best_replica(client_ip)

            #Build the DNS Packet with the iven IP
            response = packet.buildDNS(ip)
            # Send the response to the client address
            socket.sendto(response,self.client_address)
        else:
            # Send the response to the client address
            socket.sendto(requestdata,self.client_address)
            
        

class myDNSServer(SocketServer.UDPServer):
    # My custom UDPServer server. The Handler class has the logic for handling incoming DNS packets
    def __init__(self,cdnname,portnumber,handler=myDNSHandler):
        self.name = cdnname
        SocketServer.UDPServer.__init__(self,('',portnumber), handler)
        return

# Initial function to start the dns server

# Check the parameters
if len(sys.argv)!=5 or sys.argv[3]!="-n" or sys.argv[1]!="-p":
    print "Please enter correct parameters"
    exit()

# Port number
portnumber = int(sys.argv[2])
# Cdn server
cdnname = sys.argv[4]
# Dns server
mydnsserver = myDNSServer(cdnname,portnumber)
#My DNS Server runs on the port given by command line.
mydnsserver.serve_forever()








