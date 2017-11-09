# Importing the libraries
import commands
import socket
import SocketServer
# Scamper port
global Scamper_port
Scamper_port=55006

# Function to ping the servers and get the rtt values
def get_rtt(ip):
        # command to get the rtt values
        command ="scamper -c 'ping -c 1' -i "+str(ip)+" |awk 'NR==5 {print $4}' |cut -d '/' -f 2"
        rtt=commands.getoutput(command)
        # if rtt is null change it to infinity
        if rtt=='':
                rtt='Infinity'
        return rtt

# Handle function overwritten for our rtt time values
class MeasureHandler(SocketServer.BaseRequestHandler):
        def handle(self):
                # receive the request sent
                client_ip=self.request.recv(1024).strip()
                # average time of the client ip
                average_time=get_rtt(client_ip)
                self.request.sendall(average_time)

# Function to start the server
def ec2_rtt():
        server=SocketServer.TCPServer(('',Scamper_port),MeasureHandler)
        server.serve_forever()

ec2_rtt()



