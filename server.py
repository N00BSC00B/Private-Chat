import asyncio
import websockets
import json
import rsa


def encrypt(message, public_key):

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
    def __init__(self, room_name):
        self.room_name = room_name
        self.clients = []
        self.users = []
        (self.public_key, self.private_key) = rsa.newkeys(1024)

    async def add_client(self, client_socket, username):

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
        if client_socket in self.clients:
            for user, socket in zip(self.users, self.clients):
                if socket == client_socket:
                    username = user
                    break

            # goodbye_message = f"[LEAVE]{username} has left the chat room."
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

    async def broadcast_message(
        self, message, sender_socket=None
    ):
        for client in self.clients:
            if client != sender_socket:
                try:
                    await client.send(message)
                except Exception as e:
                    print(f"Error sending message to client: {e}")

    def is_empty(self):
        return len(self.clients) == 0


class ChatServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.chat_rooms = {}
        print(f"Server listening on {self.host}:{self.port}")

    async def handle_client(self, websocket, path):
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
                            self.chat_rooms[room_name].public_key.save_pkcs1("PEM").decode(),  # noqa
                            client_public_key
                        )
                        encrypted_private_key = encrypt(
                            self.chat_rooms[room_name].private_key.save_pkcs1("PEM").decode(),  # noqa
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
                            "message": "[ERROR] Username already exists in the room. Please choose a different username.",  # noqa
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
                    # print(
                    #     "Received message from "
                    #     f"{websocket.remote_address}: {username}: {message['message']}"      # noqa
                    # )
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
        room = self.chat_rooms.get(room_name)
        if room:
            if username in room.users:
                return False
        return True

    async def remove_client_from_rooms(self, websocket):
        for room in self.chat_rooms.values():
            await room.remove_client(websocket)

    async def remove_empty_rooms(self):
        empty_rooms = [
            room_name for room_name,
            chat_room in self.chat_rooms.items() if chat_room.is_empty()
        ]
        for room_name in empty_rooms:
            del self.chat_rooms[room_name]
            print(f"Room '{room_name}' deleted as it became empty.")

    async def start_server(self):
        async with websockets.serve(self.handle_client, self.host, self.port):
            await self.remove_empty_rooms()
            await asyncio.Future()  # Run forever


if __name__ == "__main__":
    HOST = '0.0.0.0'  # Use '0.0.0.0' to listen on all available interfaces
    PORT = 7081  # Choose any available port
    server = ChatServer(HOST, PORT)
    asyncio.run(server.start_server())
