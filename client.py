import asyncio
import websockets
import threading
from colorama import Fore, Style
import json
import os

import rsa

(public_key, private_key) = rsa.newkeys(1024)
server_public_key = None
server_private_key = None


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


def decrypt(encrypted_message, private_key):

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


colors = {
    "green": Fore.GREEN,
    "red": Fore.RED,
    "blue": Fore.BLUE,
    "reset": Style.RESET_ALL
}


class ChatClient:
    def __init__(self, host, port, username, room):
        self.host = host
        self.port = port
        self.username = username
        self.room = room
        self.websocket = None

    async def connect_to_server(self):
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

        receive_task = asyncio.create_task(self.receive_messages())
        await receive_task

    async def send_message(self, message):
        await self.websocket.send(json.dumps(message))

    async def receive_messages(self):
        global server_public_key, server_private_key

        while True:
            try:
                message_raw = await self.websocket.recv()
                message = json.loads(message_raw)

                if message["type"] == "SYSTEM_MESSAGE":
                    print(
                        f"{colors[message['color']]}{message['message']}{colors['reset']}"  # noqa
                    )
                    if message["code"] == 409:
                        self.username = input("Enter a different username: ")
                        msg = {
                            "type": "JOIN_ROOM",
                            "username": self.username,
                            "room": self.room,
                            "code": 200,
                            "public_key": public_key.save_pkcs1("PEM").decode()
                        }
                        await self.websocket.send(json.dumps(msg))
                        continue

                    elif not server_public_key and not server_private_key:
                        pub_key = bytes.fromhex(message["public_key"])
                        server_public_key = rsa.PublicKey.load_pkcs1(
                            decrypt(pub_key, private_key)
                        )

                        pri_key = bytes.fromhex(message["private_key"])
                        server_private_key = rsa.PrivateKey.load_pkcs1(
                            decrypt(pri_key, private_key)
                        )

                if message["type"] == "USER_MESSAGE" and message["message"]:
                    toSend = bytes.fromhex(message["message"])
                    toSend = decrypt(toSend, server_private_key)
                    print(
                        f"{colors[message['color']]}{message['username']}: {toSend}{colors['reset']}"   # noqa
                    )

                if message["type"] == "MEDIA_MESSAGE":
                    media_encoded = message["message"]
                    filename = message.get("filename", "unknown")

                    print(
                        f"Receiving {filename} from {message['username']}..."
                    )

                    if not os.path.exists("received_media"):
                        os.makedirs("received_media")

                    media_bytes = bytes.fromhex(media_encoded)
                    media_path = os.path.join("received_media", filename)
                    with open(media_path, "wb") as f:
                        f.write(media_bytes)

                    print(f"{colors['green']}Media saved to {media_path}{colors['reset']}")     # noqa

            except websockets.exceptions.ConnectionClosedError:
                print("Connection closed by the server.")
                break

            except Exception as e:
                print(f"Error receiving message: {e}")
                break


def user_input_loop(client):
    while True:
        message = input()
        type = "CHAT_MESSAGE"
        filename = None

        if message.startswith("/media"):
            try:
                with open(message.split()[1], "rb") as file:
                    file_content = file.read()
                type = "MEDIA_MESSAGE"
                filename = os.path.basename(message.split()[1])
                print(f"Sending {filename}...")
            except Exception as e:
                print(f"Error reading file: {e}")
                continue

        encrypted_message = (
            encrypt(message, server_public_key)
            if type == "CHAT_MESSAGE" else file_content
        )
        # print(encrypted_message)
        # print(encrypted_message.hex())
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


if __name__ == "__main__":
    HOST = '45.90.12.30'  # Server IP address
    PORT = 7081  # Server port

    username = input("Enter your username: ")
    room = input("Enter the chat room you want to join: ")

    client = ChatClient(HOST, PORT, username, room)

    # Start the user input loop in a separate thread
    input_thread = threading.Thread(target=user_input_loop, args=(client,))
    input_thread.start()

    # Run the WebSocket connection in the main thread
    asyncio.run(client.connect_to_server())
