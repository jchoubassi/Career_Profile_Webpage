import os
import socket
import threading
import sys
import base64
from urllib.parse import parse_qs
import json
import requests


# 23003517 = my ID
username = '23003517'
password = '23003517'

def gobble_file(filename, mode='r'):
    with open(filename, mode) as fin:
        content = fin.read()
    return content

def parse_http_req(request):
    lines = request.decode().split("\r\n")
    if len(lines) > 0:
        parts = lines[0].split()
        if len(parts) >= 2:
            return {'method': parts[0], 'path': parts[1]}
    return None

#aUTHORIZATION
def authorization(request, username, password):
    lines = request.decode().split("\r\n")
    for line in lines:
        if line.startswith("Authorization: "):
            encoded = line.split()[2]
            decoded = base64.b64decode(encoded).decode()
            return decoded == f"{username}:{password}"
    return False

#submit and parse
def do_request(connection_socket):
    request = connection_socket.recv(4096)
    httpd = parse_http_req(request)
    if httpd['path'] == '/submit' and httpd['method'] == 'POST':
        headers, body = request.decode(errors = 'ignore').split('\r\n\r\n',1)

        data_form = parse_qs(body)
        print("Your form has been submitted: ", data_form)

        with open("data_form.txt", "w") as f:
            for key, value in data_form.items():
                f.write(f"{key}: {value}\n")

        response = 'HTTP/1.1 200 OK\r\n'
        response += 'Content-Type: text/html\r\n\r\n'
        response +='''
        <html>
            <head><title>Form Submitted</title></head>
            <body>
                <h2>Awesome!</h2>
                <p>Your form was submitted successfully</p>
            </body>
        </html>'''
        connection_socket.send(response.encode())
        connection_socket.close()
        return

    if not authorization(request, username, password):
        response = 'HTTP/1.1 401 Unauthorized\r\n'
        response += 'WWW-Authenticate: Basic realm="Restricted"\r\n\r\n'
        response += '<html><h1>401 Unauthorized</h1></html>'
        connection_socket.send(response.encode())
        connection_socket.close()
        return

    if httpd is None:
        connection_socket.send(b'HTTP/1.1 400 BAD REQUEST \r\n\r\n')
        connection_socket.close()
        return

    print(f"REQUEST: {httpd['method']} {httpd['path']} Thread: {threading.get_native_id()}")

    #/analyze
    if httpd['path'] == '/analyze':
        if not os.path.exists("data_form.txt"):
            response = 'HTTP/1.1 400 BAD REQUEST\r\n\r\n'
            response += '<html><h1>No form data found.</h1></html>'
            connection_socket.send(response.encode())
            connection_socket.close()
            return
        #read form data
        form_data = {}
        with open("data_form.txt", "r") as f:
            for line in f:
                key, value = line.strip().split(": ", 1)
                form_data[key] = value.strip("[]").replace("'", "").split(", ")
        name = form_data.get("name", ["anon"])[0]
        job = form_data.get("job", ["na"])[0]
        pets = form_data.get("pets", [])
        message = form_data.get("message", [""])[0]

        if job =="ceo":
            job_message = "Eviilllll"
            movie = "business"
        elif job == "astronaut":
            job_message = "Okay Elon Musk..."
            movie = "space"
        elif job == "doctor":
            job_message = "What a try-hard!"
            movie = "hospital"
        elif job == "model":
            job_message = "When the chile is tea but the finna is gag, sis I'm dead as chile yesss"
            movie = "fashion"
        elif job == "rockstar":
            job_message = "It's giving Nirvana ;p"
            movie = "music"
        elif job == "garbage": #garbage or nothing?
            job_message = "When you take out the garbage and the garbage water gets on you :("
            movie = "life"
        else:
            job_message = f"Good luck with {job}"
            movie = "life"

        #movie api
        movie_key = "" # EMAIL FOR KEY
        movie_profile = requests.get(f"http://www.omdbapi.com/?apikey={movie_key}&s={movie}")
        movies = []
        if movie_profile.status_code == 200:
            data = movie_profile.json()
            if "Search" in data:
                movies = [m["Title"] for m in data["Search"][:3]]

        #pets api
        pet_pics = {}
        if "dog" in pets:
            req = requests.get("https://dog.ceo/api/breeds/image/random")
            if req.status_code == 200:
                pet_pics["dog"] = req.json().get("message")
        if "cat" in pets:
            req = requests.get("https://api.thecatapi.com/v1/images/search")
            if req.status_code == 200:
                pet_pics["cat"] = req.json()[0].get("url")
        if "duck" in pets:
            req = requests.get("https://random-d.uk/api/v2/random")
            if req.status_code == 200:
                pet_pics["duck"] = req.json().get("url")

        profile_data = {
            "name": name,
            "job": job,
            "job_message": job_message,
            "movies": movies,
            "pets": pets,
            "pet_images": pet_pics,
            "message": message
        }

        with open("profile_data.json", "w") as pf:
            json.dump(profile_data, pf)

        response = 'HTTP/1.1 200 OK\r\n'
        response += 'Content-Type: text/plain\r\n\r\n'
        response += 'Analysis complete. Profile saved.'
        connection_socket.send(response.encode())
        connection_socket.close()
        return

    #/view/input
    if httpd['path'] == '/view/input':
        if not os.path.exists("data_form.txt"):
            response = 'HTTP/1.1 404 NOT FOUND\r\n\r\n'
            response += json.dumps({"error": "No form data found"})
            connection_socket.send(response.encode())
            connection_socket.close()
            return
        form_data = {}
        with open("data_form.txt", "r") as f:
            for line in f:
                key, value = line.strip().split(": ",1)
                form_data[key] = value.strip("[]").replace("'", "").split(", ")
        j_response = json.dumps(form_data)

        response = 'HTTP/1.1 200 OK\r\n'
        response += 'Content-Type: application/json\r\n\r\n'
        response += j_response
        connection_socket.send(response.encode())
        connection_socket.close()
        return

    if httpd['path'] == '/view/profile':
        if not os.path.exists("profile_data.json"):
            response = 'HTTP/1.1 404 NOT FOUND\r\n\r\n'
            response += json.dumps({"error": "No profile data found"})
            connection_socket.send(response.encode())
            connection_socket.close()
            return
        with open("profile_data.json", "r") as pf:
            profile_json = pf.read()

        response = 'HTTP/1.1 200 OK\r\n'
        response += 'Content-Type: application/json\r\n\r\n'
        response += profile_json
        connection_socket.send(response.encode())
        connection_socket.close()
        return

    if httpd['path'] =='/':
        filename = 'index.html'
    elif httpd['path'] == '/form':
        filename = 'psycho.html'
    else:
        filename = httpd['path'].lstrip('/')

    default = b'<html><h1>Default Response</h1></html>'

    if os.path.exists(filename):
        connection_socket.send(b'HTTP/1.1 200 OK\r\n')

        if filename.endswith('.html'):
            content = gobble_file(filename)
            connection_socket.send(b'Content-Type: text/html\r\n\r\n')
            connection_socket.send(content.encode())

        elif filename.endswith('.jpg'):
            content = gobble_file(filename, mode='rb')
            connection_socket.send(b'Content-Type: image/jpeg\r\n')
            connection_socket.send(b'Accept-Ranges: bytes\r\n\r\n')
            connection_socket.send(content)

        elif filename.endswith('.ico'):
            content = gobble_file(filename, mode='rb')
            connection_socket.send(b'Content-Type: image/x-icon\r\n')
            connection_socket.send(b'Accept-Ranges: bytes\r\n\r\n')
            connection_socket.send(content)

        else:
            connection_socket.send(default)
    else:
        response  = 'HTTP/1.1 404 NOT FOUND\r\n\r\n'
        response += f'<html><h1>404 NOT FOUND</h1><p>{filename}</p></html>'
        connection_socket.send(response.encode())

    # Close the connection
    connection_socket.close()

def main():
    if len(sys.argv) > 1:
        server_port = int(sys.argv[1])
    else:
        server_port = 8080 #default port if none given
    # Create the server socket object
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Bind the server socket to the port
    server_socket.bind(('', server_port))
    # Start listening for new connections
    server_socket.listen(1)
    print('The server is ready to receive messages on port:', server_port)

    while True:
        # Accept a connection from a client
        connection_socket, addr = server_socket.accept()

        # Handle each connection in a separate thread
        threading.Thread(target=do_request, args=(connection_socket,)).start()

if __name__ == '__main__':
    main()

