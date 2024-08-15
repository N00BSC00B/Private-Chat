import asyncio
import websockets
import json
import rsa


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


class ChatRoom:
    """
    Represents a chat room where multiple clients can join and communicate.
    """

    def __init__(self, room_name):
        """
        Initializes a new chat room.

        Args:
            room_name (str): The name of the chat room.
        """
        self.room_name = room_name
        self.clients = []
        self.users = []
        (self.public_key, self.private_key) = rsa.newkeys(1024)

    async def add_client(self, client_socket, username):
        """
        Adds a new client to the chat room.

        Args:
            client_socket (websockets.WebSocketServerProtocol): The client's websocket connection.
            username (str): The username of the client.
        """
        # Add the client to the room
        self.clients.append(client_socket)
        self.users.append(username)

        welcome_message = {
            "type": "SYSTEM_MESSAGE",
            "color": "green",
            "message": f"{username} has joined the chat room.",
            "code": 200
        }
        await self.broadcast_message(
            json.dumps(welcome_message), client_socket
        )

    async def remove_client(self, client_socket):
        """
        Removes a client from the chat room.

        Args:
            client_socket (websockets.WebSocketServerProtocol): The client's websocket connection.
        """
        if client_socket in self.clients:
            for user, socket in zip(self.users, self.clients):
                if socket == client_socket:
                    username = user
                    break

            goodbye_message = {
                "type": "SYSTEM_MESSAGE",
                "color": "red",
                "message": f"{username} has left the chat room.",
                "code": 400,
                "username": username,
                "room": self.room_name
            }
            await self.broadcast_message(
                json.dumps(goodbye_message), client_socket
            )

            # Remove the client from the room
            self.clients.remove(client_socket)
            if username:
                self.users.remove(username)

    async def broadcast_message(self, message, sender_socket=None):
        """
        Broadcasts a message to all clients in the chat room except the sender.

        Args:
            message (str): The message to be broadcasted.
            sender_socket (websockets.WebSocketServerProtocol, optional): The sender's websocket connection. Defaults to None.
        """
        for client in self.clients:
            if client != sender_socket:
                try:
                    await client.send(message)
                except Exception as e:
                    print(f"Error sending message to client: {e}")

    def is_empty(self):
        """
        Checks if the chat room is empty.

        Returns:
            bool: True if the chat room is empty, False otherwise.
        """
        return len(self.clients) == 0


class ChatServer:
    """
    Represents a chat server that manages multiple chat rooms.
    """

    def __init__(self, host, port):
        """
        Initializes a new chat server.

        Args:
            host (str): The host address of the server.
            port (int): The port number of the server.
        """
        self.host = host
        self.port = port
        self.chat_rooms = {}
        print(f"Server listening on {self.host}:{self.port}")

    async def handle_client(self, websocket, path):
        """
        Handles incoming client connections and messages.

        Args:
            websocket (websockets.WebSocketServerProtocol): The client's websocket connection.
            path (str): The URL path of the websocket connection.
        """
        while True:
            try:
                message_raw = await websocket.recv()
                message = json.loads(message_raw)

                if not message:
                    print(f"Connection closed with {websocket.remote_address}")
                    await self.remove_client_from_rooms(websocket)
                    break

                if message["type"] == "JOIN_ROOM":
                    room_name = message["room"]
                    username = message["username"]

                    if room_name not in self.chat_rooms:
                        self.chat_rooms[room_name] = ChatRoom(room_name)

                    if self.is_username_unique(room_name, username):
                        await self.chat_rooms[room_name].add_client(
                            websocket, username
                        )
                        print(f"Added {username} to chat room {room_name}")

                        client_public_key = rsa.PublicKey.load_pkcs1(
                            message["public_key"].encode()
                        )
                        encrypted_public_key = encrypt(
                            self.chat_rooms[room_name].public_key.save_pkcs1("PEM").decode(),
                            client_public_key
                        )
                        encrypted_private_key = encrypt(
                            self.chat_rooms[room_name].private_key.save_pkcs1("PEM").decode(),
                            client_public_key
                        )

                        msg = {
                            "type": "SYSTEM_MESSAGE",
                            "color": "green",
                            "message": "[INFO] Connected to the chat room.",
                            "code": 200,
                            "public_key": encrypted_public_key.hex(),
                            "private_key": encrypted_private_key.hex(),
                        }
                    else:
                        msg = {
                            "type": "SYSTEM_MESSAGE",
                            "color": "red",
                            "message": "[ERROR] Username already exists in the room. Please choose a different username.",
                            "code": 409
                        }

                    await websocket.send(json.dumps(msg))
                    continue

                elif message["type"] == "CHAT_MESSAGE":
                    room_name = message["room"]
                    msg = {
                        "type": "USER_MESSAGE",
                        "color": "blue",
                        "username": message["username"],
                        "message": message["message"],
                        "code": 200,
                    }
                    await self.chat_rooms[room_name].broadcast_message(
                        json.dumps(msg), websocket
                    )

                elif message["type"] == "MEDIA_MESSAGE":
                    room_name = message["room"]
                    msg = {
                        "type": "MEDIA_MESSAGE",
                        "color": "blue",
                        "username": message["username"],
                        "message": message["message"],
                        "code": 200,
                        "filename": message["filename"],
                    }
                    await self.chat_rooms[room_name].broadcast_message(
                        json.dumps(msg), websocket
                    )

                elif message["type"] == "LEAVE_ROOM":
                    print("Disconnecting...")
                    self.remove_client_from_rooms(websocket)
                    print(f"Connection closed with {websocket.remote_address}")
                    continue

            except websockets.exceptions.ConnectionClosedError:
                print(f"Connection closed by peer: {websocket.remote_address}")
                await self.remove_client_from_rooms(websocket)
                break

            except Exception as e:
                print(f"Connection closed by peer: {websocket.remote_address}")
                await self.remove_client_from_rooms(websocket)
                print(f"Error handling client: {e}")
                break

    def is_username_unique(self, room_name, username):
        """
        Checks if a username is unique in a chat room.

        Args:
            room_name (str): The name of the chat room.
            username (str): The username to be checked.

        Returns:
            bool: True if the username is unique, False otherwise.
        """
        room = self.chat_rooms.get(room_name)
        if room:
            if username in room.users:
                return False
        return True

    async def remove_client_from_rooms(self, websocket):
        """
        Removes a client from all chat rooms.

        Args:
            websocket (websockets.WebSocketServerProtocol): The client's websocket connection.
        """
        for room in self.chat_rooms.values():
            await room.remove_client(websocket)

    async def remove_empty_rooms(self):
        """
        Removes all empty chat rooms.
        """
        empty_rooms = [
            room_name for room_name,
            chat_room in self.chat_rooms.items() if chat_room.is_empty()
        ]
        for room_name in empty_rooms:
            del self.chat_rooms[room_name]
            print(f"Room '{room_name}' deleted as it became empty.")

    async def start_server(self):
        """
        Starts the chat server and listens for incoming connections.
        """
        async with websockets.serve(self.handle_client, self.host, self.port):
            await self.remove_empty_rooms()
            await asyncio.Future()  # Run forever


if __name__ == "__main__":
    HOST = '0.0.0.0'  # Use '0.0.0.0' to listen on all available interfaces
    PORT = 7081  # Choose any available port
    server = ChatServer(HOST, PORT)
    asyncio.run(server.start_server())