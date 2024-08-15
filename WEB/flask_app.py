import asyncio
import websockets
from colorama import Fore, Style
import json
import os
import rsa
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit

# Initialize Flask app and SocketIO
app = Flask(__name__)
socket = SocketIO(app)

# Generate RSA keys for the server
(public_key, private_key) = rsa.newkeys(1024)
server_public_key = None
server_private_key = None
clients = {}


def encrypt(message, public_key):
    """
    Encrypts a message using the provided RSA public key.

    Args:
        message (str): The message to be encrypted.
        public_key (rsa.PublicKey): The RSA public key for encryption.

    Returns:
        bytes: The encrypted message.
    """
    max_block_size = rsa.common.byte_size(public_key.n) - 11
    chunks = [
        message[i:i+max_block_size]
        for i in range(0, len(message), max_block_size)
    ]
    encrypted_chunks = [
        rsa.encrypt(chunk.encode(), public_key) for chunk in chunks
    ]
    encrypted_message = b''.join(encrypted_chunks)

    return encrypted_message


def decrypt(encrypted_message, private_key):
    """
    Decrypts an encrypted message using the provided RSA private key.

    Args:
        encrypted_message (bytes): The encrypted message.
        private_key (rsa.PrivateKey): The RSA private key for decryption.

    Returns:
        str: The decrypted message.
    """
    max_block_size = rsa.common.byte_size(private_key.n)
    chunks = [
        encrypted_message[i:i+max_block_size]
        for i in range(0, len(encrypted_message), max_block_size)
    ]
    decrypted_chunks = [
        rsa.decrypt(chunk, private_key) for chunk in chunks
    ]
    decrypted_message = b''.join(decrypted_chunks)

    return decrypted_message.decode()


# Define color codes for different message types
colors = {
    "green": Fore.GREEN,
    "red": Fore.RED,
    "blue": Fore.BLUE,
    "reset": Style.RESET_ALL
}


class ChatClient:
    """
    Represents a chat client that connects to a chat server.
    """

    def __init__(self, host, port, username, room):
        """
        Initializes a new chat client.

        Args:
            host (str): The host address of the server.
            port (int): The port number of the server.
            username (str): The username of the client.
            room (str): The chat room to join.
        """
        self.host = host
        self.port = port
        self.username = username
        self.room = room
        self.websocket = None

    async def connect_to_server(self):
        """
        Connects to the chat server and joins the specified chat room.
        """
        uri = f"ws://{self.host}:{self.port}"
        self.websocket = await websockets.connect(uri)
        msg = {
            "type": "JOIN_ROOM",
            "username": self.username,
            "room": self.room,
            "code": 200,
            "public_key": public_key.save_pkcs1("PEM").decode()
        }
        await self.websocket.send(json.dumps(msg))

        # Start receiving messages from the server
        receive_task = asyncio.create_task(self.receive_messages())
        await receive_task

    async def send_message(self, message):
        """
        Sends a message to the chat server.

        Args:
            message (dict): The message to be sent.
        """
        await self.websocket.send(json.dumps(message))

    async def receive_messages(self):
        """
        Receives messages from the chat server and handles them.
        """
        global server_public_key, server_private_key, clients

        while True:
            try:
                message_raw = await self.websocket.recv()
                message = json.loads(message_raw)

                if message["type"] == "SYSTEM_MESSAGE":
                    # Emit system message to the client
                    emit('message_received', message)
                    if message["code"] == 409:
                        # Handle username conflict
                        continue
                    elif message["code"] == 400:
                        # Remove client from the room
                        clients[message["room"]].pop(message["username"])

                    elif not server_public_key and not server_private_key:
                        # Decrypt and load server's public and private keys
                        pub_key = bytes.fromhex(message["public_key"])
                        server_public_key = rsa.PublicKey.load_pkcs1(
                            decrypt(pub_key, private_key)
                        )

                        pri_key = bytes.fromhex(message["private_key"])
                        server_private_key = rsa.PrivateKey.load_pkcs1(
                            decrypt(pri_key, private_key)
                        )

                if message["type"] == "USER_MESSAGE" and message["message"]:
                    # Decrypt and emit user message
                    toSend = bytes.fromhex(message["message"])
                    toSend = decrypt(toSend, server_private_key)
                    message["message"] = toSend
                    emit('message_received', message)

                if message["type"] == "MEDIA_MESSAGE":
                    # Handle incoming media message
                    media_encoded = message["message"]
                    filename = message.get("filename", "unknown")

                    emit('message_received', message)

                    if not os.path.exists("received_media"):
                        os.makedirs("received_media")

                    media_bytes = bytes.fromhex(media_encoded)
                    media_path = os.path.join("received_media", filename)
                    with open(media_path, "wb") as f:
                        f.write(media_bytes)

                    emit('message_received', message)

            except websockets.exceptions.ConnectionClosedError:
                print("Connection closed by the server.")
                break

            except Exception as e:
                print(f"Error receiving message: {e}")
                break

    async def disconnect(self):
        """
        Disconnects the client from the chat server.
        """
        print("Disconnecting...")
        await self.websocket.close()


@app.route('/')
def home():
    """
    Renders the home page.
    """
    return render_template('index.html')


@socket.on('join')
def handle_join(data):
    """
    Handles a client joining a chat room.

    Args:
        data (dict): The data containing username and room information.
    """
    global clients

    username = data['username']
    room = data['room']
    print(f"Joining room {room} as {username}...")

    client = ChatClient(HOST, PORT, username, room)

    if room in clients:
        if username not in clients[room]:
            clients[room][username] = client
    else:
        clients[room] = {username: client}

    asyncio.run(client.connect_to_server())


@socket.on('send_message')
def handle_message(data):
    """
    Handles a client sending a message.

    Args:
        data (dict): The data containing message, room, and username information.
    """
    global clients

    print(data)
    message = data['message']
    room = data['room']
    username = data['username']

    client = clients[room][username]

    type = "CHAT_MESSAGE"
    filename = None

    if message.startswith("/media"):
        # Handle media message
        try:
            with open(message.split()[1], "rb") as file:
                file_content = file.read()
            type = "MEDIA_MESSAGE"
            filename = os.path.basename(message.split()[1])
            print(f"Sending {filename}...")
        except Exception as e:
            print(f"Error reading file: {e}")
            return

    encrypted_message = (
        encrypt(message, server_public_key)
        if type == "CHAT_MESSAGE" else file_content
    )

    msg = {
        "type": type,
        "username": client.username,
        "room": client.room,
        "message": encrypted_message.hex(),
        "code": 200,
        "filename": filename
    }

    asyncio.run(
        client.send_message(msg)
    )


@app.route('/user_disconnect', methods=['POST'])
def user_disconnect():
    """
    Handles a client disconnecting from a chat room.

    Returns:
        Response: A JSON response indicating the success of the operation.
    """
    global clients

    data = request.get_json()
    room = data['room']
    username = data['username']

    client = clients[room][username]
    msg = {
        "type": "LEAVE_ROOM",
        "username": client.username,
        "room": client.room,
        "code": 400
    }
    asyncio.run(client.send_message(msg))
    del clients[room][username]
    return jsonify({'message': 'Data received successfully'})


if __name__ == "__main__":
    HOST = '45.90.12.30'  # Server IP address
    PORT = 7081  # Server port

    socket.run(app, debug=True, host='0.0.0.0', port=6652)