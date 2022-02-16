# CS421 Computer Networks Programming Assignment 2
# Mehmet Berk Şahin 21703190
# Emrecan Kutay 21702500

from socket import *
import sys
import threading
import os
import math


# This function gets Command (GET, HEAD), requestURL (URL belongs to main server),
# serverName(main server, ex. cs.bilkent.edu.tr), and flag which is 0 for normal get, 1 for range get
def HTTP_GetMessage(cmd, request, serverName, interval="0-0", flag=0):
    if flag == 0:
        getMessage = cmd + " " + request + " HTTP/1.1\r\nHost: " + serverName + "\r\n\r\n"

    else:
        getMessage = cmd + " " + request + " HTTP/1.1\r\nHost: " + serverName + "\r\n" + "Range: bytes=" + interval + "\r\n\r\n"

    return getMessage.encode()


# This function extracts the URLs from the base HTML file by taking the ones containing .txt
def extractURL(responseMessage):
    list = responseMessage.splitlines()
    urls = []
    for el in list:
        if ".txt" in el:
            urls.append(el)

    return urls


# This function will be executed by each threat. It takes the interval for range request
# Count is used to handle the unsorted packets
def threadFunction(link, interval_begin, interval_end, results, count):
    [serverName, requestName] = [link[0:link.find('/')], link[link.find('/'): len(link)]]

    clientSocket = socket(AF_INET, SOCK_STREAM)
    clientSocket.connect((serverName, 80))

    # After connecting the socket, send HEAD request to each one
    clientSocket.send(HTTP_GetMessage("GET", requestName, serverName, str(interval_begin) + "-" + str(interval_end), 1))
    response = ""

    temp = clientSocket.recv(4096).decode()
    if temp.find("206 Partial Content") == -1 and temp.find("200 OK") == -1:
        print(f". {link} is not downloaded (Should receive 206 Message)")
    response += temp[temp.find("\r\n\r\n") + 4:]

    while temp != "":
        temp = clientSocket.recv(4096).decode()

        response += temp

    clientSocket.close()
    # Count is used to put packets in the correct index
    results[count] = response
    sys.exit()


# This try and except structure is for understanding whether there is an interval or not
try:
    [file_URL, connection_count] = sys.argv[1:]
    # Check that inputs are received correctly
except:
    # If code reaches here, inputs are not proper. Hence, display an error message and exit.
    print("Improper input")
    exit()

# Connection count cannot be 0
if connection_count == 0:
    print("Improper input")
    exit()

# During the implementation, it was found that our code only excepts the URLs without HTTP://, due to our extraction algorithm.
# In order to prevent errors, HTTP part is removed to get the direk URL.
if file_URL.find("http://") != -1:
    file_URL = file_URL[file_URL.find("http://") + len("http://"):]

print("URL of the index file: " + file_URL)

print("Number of parallel connections: " + str(connection_count))

# Get the main serverName (ex. www.bilkent.cs.edu.tr)
# Get the requestName (ex. /~cs421/fall21/project1/index1.txt )
[serverName, requestName] = [file_URL[0:file_URL.find('/')], file_URL[file_URL.find('/'): len(file_URL)]]

# Create a client socket and connect to the main server
clientSocket = socket(AF_INET, SOCK_STREAM)
clientSocket.connect((serverName, 80))

# Send e GET message to get the base HTML file
clientSocket.send(HTTP_GetMessage("GET", requestName, serverName))

# Response was initially empty. As the packets are received they will be appended to the response
# Since we don't know how many packets to expect, this structure was implemented.
response = ""
temp = clientSocket.recv(4096).decode()
response += temp

# Continue to receive segments as long as they contain a data
while not (temp == "" or temp == " " or temp == "\n" or temp == "\r"):
    temp = clientSocket.recv(4096).decode()
    response += temp

# If the base HTML file couldn't be received properly, exit.
if response.find("200 OK") == -1:
    print("ERROR  REQUESTED FILE NOT FOUND")
    exit()

# If the base HTML file was received properly, then send head requests to each link obtained from the base HTML
else:
    print("Index file is downloaded")
    links = extractURL(response)
    # Print the URL counts in the base HTML file
    print("There are " + str(len(links)) + " files in the index")

    for i, link in enumerate(links, 1):
        # Since each URL may have different main Server, close the old socket and connect to new one
        clientSocket.close()
        [serverName, requestName] = [link[0:link.find('/')], link[link.find('/'): len(link)]]

        clientSocket = socket(AF_INET, SOCK_STREAM)
        clientSocket.connect((serverName, 80))

        # After connecting the socket, send HEAD request to each one
        clientSocket.send(HTTP_GetMessage("HEAD", requestName, serverName))
        response = clientSocket.recv(4096).decode()

        # If there is not a proper content, skip the current URL
        if response.find("200 OK") == -1:
            print(str(i) + f". {link} is not found")
            continue
        # It was observed that if there is no content length part in the header, then size is 0!
        if response.find("Content-Length: ") == -1:
            size = 0
        else:
            # If there exist a content length part in the head response, extract its size
            size = response[response.find("Content-Length: ") + len("Content-Length: "): (
                    response.find("Content-Length: ") + len("Content-Length: ") + response[response.find(
                "Content-Length: ") + len("Content-Length: "):].find('\r'))]

        # Store each threat
        thread_list = []

        # Convert size and connection count to integer
        size = int(size)
        connection_count = int(connection_count)

        # If size is not 0
        if size != 0:
            # If connection count is greater than size
            # Then each socket will download single byte
            if size < connection_count:
                connection_count = size

        # Calculate the packet_size
        packet_size = math.ceil(size / connection_count)
        count = 0
        # Initalize variables for usage
        # Results array will store the received packets
        results = ["" for a in range(connection_count)]

        # These two array will store the begin and end points for the intervarl. Just for display!
        file_parts_begin = []
        file_parts_end = []

        # Received packets will then be combined in the final response
        final_response = ""

        # If packet size is not 0, and connection count is not size
        if packet_size != 0 and connection_count != size:
            for q in range(packet_size, size + packet_size - 1, packet_size):
                # If size is greater than q, we have not reach the end yet
                if size > q:
                    file_parts_begin.append(q - packet_size)
                    file_parts_end.append(q - 1)
                    thread = threading.Thread(target=threadFunction,
                                              args=(link, q - packet_size, q - 1, results, count))
                    thread_list.append(thread)

                # Here, just take the remaining part. This will be smaller than the calculated packet size.
                else:
                    file_parts_begin.append(q - packet_size)
                    file_parts_end.append(size - 1)
                    thread = threading.Thread(target=threadFunction,
                                              args=(link, q - packet_size, size - 1, results, count))
                    thread_list.append(thread)
                count += 1

            # Start threads
            for thread in thread_list:
                thread.start()

            # Wait and get
            for thread in thread_list:
                thread.join()

            for resp in results:
                final_response += resp

        # If packet size is not 0 and connection count is equal to size
        if packet_size != 0 and connection_count == size:
            for q in range(0, size, packet_size):
                file_parts_begin.append(q)
                file_parts_end.append(q)
                thread = threading.Thread(target=threadFunction, args=(link, q, q, results, count))
                thread_list.append(thread)
                count += 1

            for thread in thread_list:
                thread.start()

            for thread in thread_list:
                thread.join()

            for resp in results:
                final_response += resp

        # Save txt files.
        name = link[link.rfind('/') + 1:]
        file1 = open(f"{name}", 'w')
        file1.write(final_response)
        file1.close()
        print(str(i) + f". {link} (size = {str(int(size))}) is downloaded")

        # If content length is not 0, print the boundaries for each packet
        if packet_size != 0:
            strr = ""
            for z in range(0, len(file_parts_begin)):
                strr += str(file_parts_begin[z]) + ":" + str(file_parts_end[z]) + "(" + str(
                    file_parts_end[z] - file_parts_begin[z] + 1) + ")" + ","
            print("File parts: " + strr[:len(strr) - 1])
        # If packet size = 0 it states for the empty page. Content length is 0 in the webpage.
        else:
            print("File parts: 0:0 (0)")
