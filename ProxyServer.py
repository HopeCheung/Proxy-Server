# Simple proxy server for Class assignment
from socket import *
import sys
import os
import datetime
import shutil
import threading

if len(sys.argv) <= 1:
    print 'Usage: "python ProxyServer.py server_ip"\n[server_ip : It is the IP Address of the Proxy Server'
    sys.exit(2)

# Fetch the server ip, prepare a server socket
server_ip = sys.argv[1] 
print (server_ip)

# date_structure is a timeline used to record the cache file's latest modified time
date_structure = {}


# Create a server socket
tcpSerPort = 8888
tcpSerSock = socket(AF_INET, SOCK_STREAM)


# Bind the host with the port we set, and listen
tcpSerSock.bind((server_ip, tcpSerPort))
tcpSerSock.listen(5)

# Save the headers of the receiving message
def saveHeader(message):
    """
    saveHeader is the function which will handle the received function
    and keep the headers.
    """
    headers = message.split("\r\n")
    for i in range(len(headers)):
        headers[i] = headers[i]+"\r\n"
    print(headers[:-2])
    return headers[:-2]

# Deal with the situation that some request file is unavailable 
def errorHandling(tcpCliSock):
    """
    errorHandling is the function which will feedback "404 Not Found"
    when meet unavaliable request
    """
    tcpCliSock.send("HTTP/1.0 404 Not Found\r\n")
    tcpCliSock.send("Content-Type:text/html\r\n\r\n")
    f = open("./index.html", "r")
    for row in f.readlines():
        tcpCliSock.send(row)

def handler(tcpCliSock, addr):
    """
    handler is function used to achieve web proxy, 
    which is also the target process in the thread 
    """
    # Get the name of current thread
    print(threading.currentThread().getName())

    # tcpCliSock: Socket in the client end
    # tcpSerSock: Socket in the server end
    # message: message received from the client end (whihc is input by user)
    message = tcpCliSock.recv(4096)
    print("-----------------------------client receiving message------------------------------------")
    print(message)

    # Save all the headers of the receiving messsage
    headers = saveHeader(message)
    
    # Extract the filename from the given message
    filename = message.split()[1].partition("/")[2]
    fileExist = "false"
    filetouse = "/" + filename

    # Extract the host name from the received message
    # host: the host of teh web input by user
    backup = message.split()
    host = filename.split("/")[0]
    if "Referer:" in backup:
        host = backup[backup.index("Referer:")+1].split("/")[-1]
    print("host:{0}".format(host))

    try:
        # Check whether the file exists in the cache
        # if the file exists in the cache, check wheter the file have been modified
        # from the last time 
        f = open(filetouse[1:], "r")
        outputdata = f.readlines()
        fileExist = "true"
        print('File Exists!')

        # If the file exist, then check the version of the file using date_structure record
        # create a new socket
        d = socket(AF_INET, SOCK_STREAM)
        version_host = host.replace("www.", "", 1)
        d.connect((version_host, 80))
        version_file = d.makefile("r", 0)

        # query the server whether the file in cache is modified from last time
        if host == filename:
            version_file.write("GET " + "/" + " HTTP/1.0\n")
            version_file.write("Host: " + filename + "\n")
        else:
            version_file.write("GET " + filetouse + " HTTP/1.0\n")
            version_file.write("Host: " + host + "\n")

        # Check whether the file in the date_structure 
        # If yes, just sent the conditional GET request
        # else, send the conditional GET request with curr time
        if filename in date_structure:
            version_file.write("If-Modified-Since: " + date_structure[filename] + "\n\n") 
        else:
            GMT_FORMAT =  '%a, %d %b %Y %H:%M:%S GMT'
            curr_time = datetime.datetime.utcnow().strftime(GMT_FORMAT)
            version_file.write("If-Modified-Since: " + curr_time + "\n\n") 

        # If the file is not modified, the server will response "304 Noe Modified"
        # We just need to send the clien that the request is fine, and send the 
        # information in the cache to the client
        version_buff = version_file.readlines()
        if "304 Not Modified" in version_buff[0]:
            print("No, it's not modified")
            # ProxyServer finds a cache hit and generates a response message
            tcpCliSock.send("HTTP/1.0 200 OK\r\n")
            tcpCliSock.send("Content-Type:text/html\r\n")
            # Send the content of the requested file to the client
            for i in range(0, len(outputdata)):
                tcpCliSock.send(outputdata[i])
            print('Read from cache')

        # If the file is modified, we need to replace the file with newest version file
        # Send the newest information to the client.
        else:
            print("Yes, it's modified")
            tmpFile = open("./" + filename, "wb")
            for row in version_buff:
                tmpFile.write(row)
                tcpCliSock.send(row)
            print("successfully build new file")

    except IOError:
        # Error handling for file not found in cache
        # Create a new socket
        # Send reuqest to server for the web information 
        if fileExist == "false":
            # Create a socket on the proxyserver
            print('Creating socket on proxyserver')
            c = socket(AF_INET, SOCK_STREAM)

            # Get the host name of the request
            print(filename)
            hostn = host.replace("www.", "", 1)
            print('Host Name: ', hostn)

            try:
                # Connect to the socket to port 80
                # Check whether the request to server is valid
                c.connect((hostn, 80))
                print('Socket connected to port 80 of the host')

                # Create a temporary file on this socket and ask port 80
                # for the file requested by the client 
                fileobj = c.makefile('r', 0)
                print("File is made successfully")

                # Send the request to the server
                for head in headers:
                    if "GET " in head:
                        if host == filename:
                            fileobj.write("GET " + "/" + " HTTP/1.0\r\n")
                        else:
                            fileobj.write("GET " + filetouse + " HTTP/1.0\r\n")
                    elif "Host:" in head:
                        if host == filename:
                            fileobj.write("Host: " + filename + "\r\n")
                        else:
                            fileobj.write("Host: " + host + "\r\n")
                    elif ("Accept-Language: " in head) or ("Accept: " in head) or ("Upgrade-Insecure-Requests: " in head) \
                            or ("Accept-Encoding: " in head) or ("Cookie: " in head):
                         fileobj.write(head)
                fileobj.write("\r\n")

                # Read the response into buffer
                buff = fileobj.readlines()
                # Error handling
                # If request file is unavailiable, send cliet with "404 Not Found" file
                # else build a cache to store the files
                flag = 0
                if "404 Not Found" in buff[0]:
                    flag = 1
                print("Buld HTML file:")

                # If the request file is unavailiable, send the 404 HTML to the client
                if flag == 1:
                    print("404 Not Found")
                    errorHandling(tcpCliSock)

                # Create a new file in the cache for the requested file.
                # Also send the response in the buffer to client socket
                # and the corresponding file in the cache
                else:
                    # Build the director according to the receiving message's path
                    directory = "/".join(filetouse.split("/")[1:-1])
                    if not os.path.exists(directory):
                        if directory != "" and directory[0] != "/":
                            os.makedirs(directory)

                    # Store the information from the server in the cache directory
                    tmpFile = open("./" + filename, "wb")
                    for row in buff:
                        tmpFile.write(row)
                        tcpCliSock.send(row)
                    print("Create cache successfully")

                    # Store the HTML file built-time in date_structure
                    GMT_FORMAT =  '%a, %d %b %Y %H:%M:%S GMT'
                    curr_time = datetime.datetime.utcnow().strftime(GMT_FORMAT)
                    date_structure[filename] = curr_time

            # If the request to server raise a exception
            # We consider it as the illegal request
            except Exception as inst:
                print('Illegal request')
                print(inst)

        else:
            # HTTP response message for file not found
            # Show 404 Not Found
            print(message)
            tcpCliSock.send("HTTP/1.0 404 Not Found\r\n")
            tcpCliSock.send("Content-Type:text/html\r\n")
            
    # Close the socket and the server sockets
    tcpCliSock.close()

while 1:
    # Start receiving data from the client
    print('Ready to serve...')

    # Accept a connection. a pair(new socket obj, address which bound to the socket)
    tcpCliSock, addr = tcpSerSock.accept()
    print('Received a connection from: ', addr)

    try:
    	# Create threads
        t = threading.Thread(target = handler, args=(tcpCliSock, addr,))
        t.start()

    except Exception as e:
        tcpCliSock.close()

