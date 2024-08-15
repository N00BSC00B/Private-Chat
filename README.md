# Chat Application

This project consists of a WebSocket server and a Flask web application for a chat system. The WebSocket server handles real-time messaging, while the Flask app provides a web interface for users to interact with the chat system.

## Components

-   **WebSocket Server**: Handles real-time chat communication and media sharing.
-   **Flask Web Application**: Provides a web interface for users and communicates with the WebSocket server.

## Prerequisites

-   Python 3.7 or higher
-   Required Python packages (listed in `requirements.txt`)

## Configuration

1. **Update Ports (if necessary)**

    Ensure the WebSocket server and Flask app use different ports. You can modify the ports in `main.py` if needed:
    [NOTE: Currently the ports are binded according to the centralized server.]

    ```python
    WEBSOCKET_PORT = 7081
    FLASK_PORT = 6652
    ```

2. **Set Server IP Address**

    Update the IP address in `web.py` to match your server's address:

    ```python
    HOST = '45.140.188.129'  # Update this with your server IP address
    PORT = 6651
    ```

## Usage

1. **Join a Chat Room**

    - Enter your username and the room name you want to join.
    - Click "Join" to connect to the WebSocket server and join the chat room.

2. **Send Messages**

    - Type your message in the input field and press "Send" to broadcast it to other users in the room.

3. **Leave the Chat Room**

    - Disconnect from the chat room by clicking the "Disconnect" button or closing the browser tab.

## Troubleshooting

-   **Port Binding Error**: Ensure that the ports are not in use by other applications. You can change the ports in `main.py` if needed.

-   **Connection Issues**: Check the server logs for errors and ensure that both WebSocket and Flask servers are running properly.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
