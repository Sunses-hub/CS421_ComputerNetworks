# CS421 Computer Networks Programming Assignment 1
# Mehmet Berk Şahin 21703190
# Emrecan Kutay 21702500

from socket import *
import sys

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

# This try and except structure is for understanding whether there is an interval or not
try:
    [file_URL, interval] = sys.argv[1:]
    # If program achieves this point, there is an interval. It extracts the lower and upper endpoints in the below
    lower_endpoint, upper_endpoint = interval.split("-")
    interval_flag = 1
except:
    # If there is an error above, this means interval was not entered. Hence, only take the main URL.
    file_URL = sys.argv[1]
    interval_flag = 0

# During the implementation, it was found that our code only excepts the URLs without HTTP://, due to our extraction algorithm.
# In order to prevent errors, HTTP part is removed to get the direk URL.
if file_URL.find("http://") != -1:
    file_URL = file_URL[file_URL.find("http://")+len("http://"):]

print("URL of the index file: " + file_URL)

# If the interval was entered, print the lower and upper endpoints
if interval_flag == 1:
    print("Lower endpoint = " + lower_endpoint)
    print("Upper endpoint = " + upper_endpoint)
# If the interval was not entered, state it
else:
    print("No range is given")

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
    print("ERROR  INDEX FILE NOT FOUND")
    exit()

# If the base HTML file was received properly, then send head requests to each link obtained from the base HTML
else:
    print("Index file is downloaded")
    links = extractURL(response)
    # Print the URL counts in the base HTML file
    print("There are " + str(len(links)) + " files in the index")

    # Iterate through each link obtained from the base HTML file
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

        # If code achieves this point in the loop, this means that there is a proper content in the URL

        # If interval flag = 0, this means there is not an interval, we should get the whole content
        if interval_flag == 0:
            # Send get message to get the whole content
            clientSocket.send(HTTP_GetMessage("GET", requestName, serverName))
            # Response initially 0 as explained above, for many possible response segments
            response = ""

            temp = clientSocket.recv(4096).decode()
            size = temp[temp.find("Content-Length: ") + len("Content-Length: "): (
                    temp.find("Content-Length: ") + len("Content-Length: ") + temp[temp.find(
                "Content-Length: ") + len("Content-Length: "):].find('\r'))]
            response += temp[temp.find("\n\r"):]

            while not(temp == "" or temp == " " or temp == "\n" or temp =="\r"):
                temp = clientSocket.recv(4096).decode()
                response += temp

            print(str(i) + f". {link} (size = {str(int(size))}) is downloaded")

        else:
            # Here, there is an interval and we should send range requests.
            lower_end, upper_end = interval.split('-')
            error = 0

            # This if structure was discussed with the TA, if there is a content with length 0, head response
            # does not contain content length in the head response message. Hence, take it 0 if does not exists.
            if response.find("Content-Length: ") == -1:
                size = 0
            else:
            # If there exist a content length part in the head response, extract its size
                size = response[response.find("Content-Length: ") + len("Content-Length: "): (
                        response.find("Content-Length: ") + len("Content-Length: ") + response[response.find(
                    "Content-Length: ") + len("Content-Length: "):].find('\r'))]

            # Convert all to integer for secure code
            size = int(size)
            lower_end = int(lower_end)
            upper_end = int(upper_end)

            # Comparing the boundaries.
            if lower_end > upper_end:
                error = 1
                print(str(i) + ". Lower end is higher than upper end for the link: " + link)
                continue

            # If upper end is greater than the size, make it equal to the size as can be seen in the example code
            # in the assignment
            if upper_end > size:
                upper_end = size

            if lower_end > size:
                error = 1
                print(str(i) + ". Lower end is higher than the size for the link: " + link)
                continue

            # If boundaries are proper then continue to downloading
            if error == 0:
                # Send get message to URL
                clientSocket.send(HTTP_GetMessage("GET", requestName, serverName, interval, interval_flag))
                response = ""

                temp = clientSocket.recv(4096).decode()
                if temp.find("206 Partial Content") == -1 and temp.find("200 OK") == -1:
                    print(str(i) + f". {link} (size = {size}) is not downloaded (Should receive 206 Message)")
                    continue
                response += temp[temp.find("\n\r"):]
                while (temp != ""):
                    temp = clientSocket.recv(4096).decode()
                    response += temp
                print(str(i) + f". {link} (range = {str(lower_end)}-{str(upper_end)}) is downloaded")

        # If content was obtained properly, save it in a .txt file with the name same as the original file.
        if interval_flag == 0 or (interval_flag == 1 and error == 0):
            name = link[link.rfind('/') + 1:]
            file1 = open(f"{name}", 'w')
            file1.write(response)
            file1.close()



